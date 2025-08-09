# ファイル転送とIoTデバイス管理

## 9.1 MQTT-based File Transfer の基本概念

2025年現在、IoTデバイスのファイル転送は以下の用途で重要性が増しています：

- **OTA（Over-The-Air）ファームウェア更新**
- **設定ファイルの配布**
- **機械学習モデルの配信**
- **ログファイルの収集**
- **証明書の更新**

### 9.1.1 プロトコル選択の指針（2025年版）

| ファイルサイズ | 推奨プロトコル | 理由 |
|---------------|---------------|------|
| < 128KB | MQTT | 単一パケットで送信可能、シンプル |
| 128KB - 1MB | MQTT (chunked) | MQTTの利点を活用、セッション継続性 |
| 1MB - 16MB | MQTT vs HTTP | デバイスリソースとネットワーク状況による |
| > 16MB | HTTP/HTTPS | コスト効率、専用プロトコル |

## 9.2 AWS IoT MQTT-based File Delivery

### 9.2.1 基本実装

```javascript
const awsIot = require('aws-iot-device-sdk-v2');
const fs = require('fs');
const crypto = require('crypto');

class AWSIoTFileTransfer {
    constructor(connectionConfig) {
        this.connection = null;
        this.connectionConfig = connectionConfig;
        this.activeTransfers = new Map();
    }
    
    async initialize() {
        // AWS IoT接続設定は前章と同様
        this.connection = await this.createConnection(this.connectionConfig);
        
        // ファイル転送関連トピックの購読
        await this.subscribeToFileTopics();
    }
    
    async subscribeToFileTopics() {
        // ファイル転送ストリーム情報取得
        await this.connection.subscribe('$aws/things/+/streams/+/data/+', 
            awsIot.mqtt.QoS.AtLeastOnce, (topic, payload) => {
                this.handleStreamData(topic, payload);
            });
            
        // ファイル転送ストリームリスト
        await this.connection.subscribe('$aws/things/+/streams/+/get/accepted',
            awsIot.mqtt.QoS.AtLeastOnce, (topic, payload) => {
                this.handleStreamInfo(topic, payload);
            });
    }
    
    async requestFileTransfer(streamId, fileName) {
        const transferId = this.generateTransferId();
        
        // ファイル転送要求
        const request = {
            clientToken: transferId,
            s: streamId,  // Stream ID
            f: fileName   // File ID
        };
        
        const topic = `$aws/things/${this.connectionConfig.thingName}/streams/${streamId}/get`;
        
        await this.connection.publish(topic, JSON.stringify(request), 
            awsIot.mqtt.QoS.AtLeastOnce);
            
        console.log(`File transfer requested: ${fileName}`);
        
        return new Promise((resolve, reject) => {
            this.activeTransfers.set(transferId, {
                resolve,
                reject,
                streamId,
                fileName,
                blocks: new Map(),
                totalBlocks: 0,
                receivedBlocks: 0,
                startTime: Date.now()
            });
            
            // タイムアウト設定
            setTimeout(() => {
                if (this.activeTransfers.has(transferId)) {
                    this.activeTransfers.delete(transferId);
                    reject(new Error('File transfer timeout'));
                }
            }, 300000); // 5分タイムアウト
        });
    }
    
    handleStreamInfo(topic, payload) {
        try {
            const data = JSON.parse(payload.toString());
            const transferId = data.clientToken;
            const transfer = this.activeTransfers.get(transferId);
            
            if (!transfer) return;
            
            // ファイル情報の解析
            const fileInfo = data.files && data.files[transfer.fileName];
            if (fileInfo) {
                transfer.totalBlocks = Math.ceil(fileInfo.s / 1024); // 1KBブロックと仮定
                transfer.fileSize = fileInfo.s;
                transfer.checksum = fileInfo.c;
                
                console.log(`File info received: ${transfer.fileName}, size: ${fileInfo.s} bytes`);
                
                // ブロックデータの要求開始
                this.requestFileBlocks(transferId);
            }
        } catch (error) {
            console.error('Error handling stream info:', error);
        }
    }
    
    async requestFileBlocks(transferId) {
        const transfer = this.activeTransfers.get(transferId);
        if (!transfer) return;
        
        // 複数ブロックを並行して要求
        const batchSize = 5;
        
        for (let blockId = 0; blockId < transfer.totalBlocks; blockId += batchSize) {
            const blockRequests = [];
            
            for (let i = 0; i < batchSize && (blockId + i) < transfer.totalBlocks; i++) {
                const currentBlockId = blockId + i;
                blockRequests.push(this.requestSingleBlock(transferId, currentBlockId));
            }
            
            // バッチ処理
            await Promise.all(blockRequests);
            
            // レート制限（デバイスリソース保護）
            await this.sleep(100);
        }
    }
    
    async requestSingleBlock(transferId, blockId) {
        const transfer = this.activeTransfers.get(transferId);
        if (!transfer) return;
        
        const request = {
            clientToken: transferId,
            s: transfer.streamId,
            f: transfer.fileName,
            l: 1024, // ブロックサイズ
            o: blockId * 1024, // オフセット
            n: 1  // 要求ブロック数
        };
        
        const topic = `$aws/things/${this.connectionConfig.thingName}/streams/${transfer.streamId}/data`;
        
        await this.connection.publish(topic, JSON.stringify(request), 
            awsIot.mqtt.QoS.AtLeastOnce);
    }
    
    handleStreamData(topic, payload) {
        try {
            const data = JSON.parse(payload.toString());
            const transferId = data.clientToken;
            const transfer = this.activeTransfers.get(transferId);
            
            if (!transfer) return;
            
            // ブロックデータの保存
            if (data.p) { // payload
                const blockData = Buffer.from(data.p, 'base64');
                const blockId = Math.floor(data.o / 1024);
                
                transfer.blocks.set(blockId, blockData);
                transfer.receivedBlocks++;
                
                console.log(`Block received: ${blockId + 1}/${transfer.totalBlocks}`);
                
                // 全ブロック受信完了チェック
                if (transfer.receivedBlocks === transfer.totalBlocks) {
                    this.completeFileTransfer(transferId);
                }
            }
        } catch (error) {
            console.error('Error handling stream data:', error);
        }
    }
    
    completeFileTransfer(transferId) {
        const transfer = this.activeTransfers.get(transferId);
        if (!transfer) return;
        
        try {
            // ブロックデータの結合
            const fileBuffer = this.assembleFileFromBlocks(transfer.blocks, transfer.totalBlocks);
            
            // チェックサム検証
            if (transfer.checksum) {
                const calculatedChecksum = crypto.createHash('sha256').update(fileBuffer).digest('hex');
                if (calculatedChecksum !== transfer.checksum) {
                    throw new Error('Checksum mismatch');
                }
            }
            
            // ファイル保存
            const filePath = `./downloads/${transfer.fileName}`;
            fs.writeFileSync(filePath, fileBuffer);
            
            const transferTime = Date.now() - transfer.startTime;
            console.log(`File transfer completed: ${transfer.fileName}, ${transferTime}ms`);
            
            transfer.resolve({
                fileName: transfer.fileName,
                filePath: filePath,
                fileSize: fileBuffer.length,
                transferTime: transferTime
            });
            
        } catch (error) {
            transfer.reject(error);
        } finally {
            this.activeTransfers.delete(transferId);
        }
    }
    
    assembleFileFromBlocks(blocks, totalBlocks) {
        const buffers = [];
        
        for (let i = 0; i < totalBlocks; i++) {
            const block = blocks.get(i);
            if (!block) {
                throw new Error(`Missing block: ${i}`);
            }
            buffers.push(block);
        }
        
        return Buffer.concat(buffers);
    }
    
    generateTransferId() {
        return `transfer_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }
}

// 使用例
async function downloadFirmwareUpdate() {
    const fileTransfer = new AWSIoTFileTransfer({
        thingName: 'industrial-sensor-001',
        endpoint: 'your-endpoint.iot.us-east-1.amazonaws.com',
        certPath: './certificate.pem.crt',
        keyPath: './private.pem.key'
    });
    
    await fileTransfer.initialize();
    
    try {
        const result = await fileTransfer.requestFileTransfer(
            'firmware-stream-v1',  // Stream ID
            'firmware-v2.1.0.bin'   // File name
        );
        
        console.log('Firmware download completed:', result);
        
        // ファームウェア更新処理
        await applyFirmwareUpdate(result.filePath);
        
    } catch (error) {
        console.error('Firmware download failed:', error);
    }
}
```

### 9.2.2 AWS S3 + Pre-signed URLs との組み合わせ

```javascript
class HybridFileTransfer {
    constructor(awsConfig) {
        this.awsConfig = awsConfig;
        this.s3Client = new AWS.S3();
        this.iotConnection = null;
    }
    
    async initialize() {
        // AWS IoT接続
        this.iotConnection = await this.createIoTConnection();
        
        // ファイル要求トピックの購読
        await this.iotConnection.subscribe(`files/${this.awsConfig.thingName}/request`, 
            awsIot.mqtt.QoS.AtLeastOnce, (topic, payload) => {
                this.handleFileRequest(topic, payload);
            });
    }
    
    async handleFileRequest(topic, payload) {
        try {
            const request = JSON.parse(payload.toString());
            const { fileType, version, priority } = request;
            
            // ファイルサイズに応じた転送方法の選択
            const fileInfo = await this.getFileInfo(fileType, version);
            
            if (fileInfo.size < 1024 * 1024) { // 1MB未満
                // MQTT経由での転送
                await this.transferViaMQTT(fileInfo);
            } else {
                // S3 Pre-signed URL経由での転送
                await this.transferViaS3(fileInfo, priority);
            }
            
        } catch (error) {
            console.error('Error handling file request:', error);
        }
    }
    
    async transferViaMQTT(fileInfo) {
        console.log(`Transferring ${fileInfo.name} via MQTT`);
        
        const fileData = await fs.promises.readFile(fileInfo.path);
        const chunks = this.splitIntoChunks(fileData, 32 * 1024); // 32KB chunks
        
        // ファイル転送開始通知
        await this.iotConnection.publish(`files/${this.awsConfig.thingName}/start`, 
            JSON.stringify({
                fileName: fileInfo.name,
                fileSize: fileInfo.size,
                totalChunks: chunks.length,
                checksum: crypto.createHash('sha256').update(fileData).digest('hex')
            }), awsIot.mqtt.QoS.AtLeastOnce);
        
        // チャンク送信
        for (let i = 0; i < chunks.length; i++) {
            await this.iotConnection.publish(`files/${this.awsConfig.thingName}/chunk`, 
                JSON.stringify({
                    fileName: fileInfo.name,
                    chunkIndex: i,
                    totalChunks: chunks.length,
                    data: chunks[i].toString('base64')
                }), awsIot.mqtt.QoS.AtLeastOnce);
                
            // レート制限
            await this.sleep(50);
        }
        
        // 転送完了通知
        await this.iotConnection.publish(`files/${this.awsConfig.thingName}/complete`, 
            JSON.stringify({
                fileName: fileInfo.name,
                status: 'completed'
            }), awsIot.mqtt.QoS.AtLeastOnce);
    }
    
    async transferViaS3(fileInfo, priority = 'normal') {
        console.log(`Transferring ${fileInfo.name} via S3`);
        
        // S3にファイルアップロード（既にアップロード済みと仮定）
        const s3Key = `firmware/${fileInfo.name}`;
        
        // Pre-signed URL生成
        const expirationTime = priority === 'urgent' ? 3600 : 7200; // 1-2時間
        
        const presignedUrl = await this.s3Client.getSignedUrlPromise('getObject', {
            Bucket: this.awsConfig.s3Bucket,
            Key: s3Key,
            Expires: expirationTime
        });
        
        // デバイスにダウンロード指示
        await this.iotConnection.publish(`files/${this.awsConfig.thingName}/download`, 
            JSON.stringify({
                fileName: fileInfo.name,
                fileSize: fileInfo.size,
                downloadUrl: presignedUrl,
                method: 'https',
                checksum: await this.calculateS3FileChecksum(s3Key),
                priority: priority,
                expiresAt: new Date(Date.now() + expirationTime * 1000).toISOString()
            }), awsIot.mqtt.QoS.AtLeastOnce);
    }
    
    splitIntoChunks(buffer, chunkSize) {
        const chunks = [];
        for (let i = 0; i < buffer.length; i += chunkSize) {
            chunks.push(buffer.slice(i, i + chunkSize));
        }
        return chunks;
    }
    
    async calculateS3FileChecksum(s3Key) {
        const response = await this.s3Client.getObject({
            Bucket: this.awsConfig.s3Bucket,
            Key: s3Key
        }).promise();
        
        return crypto.createHash('sha256').update(response.Body).digest('hex');
    }
}
```

## 9.3 デバイス側実装 - ファイル受信とOTA更新

### 9.3.1 堅牢なファイル受信機構

```javascript
class RobustFileReceiver {
    constructor(mqttClient, options = {}) {
        this.mqttClient = mqttClient;
        this.downloadDir = options.downloadDir || './downloads';
        this.tempDir = options.tempDir || './tmp';
        this.maxRetries = options.maxRetries || 3;
        this.activeDownloads = new Map();
        
        this.setupDirectories();
        this.setupMQTTHandlers();
    }
    
    setupDirectories() {
        [this.downloadDir, this.tempDir].forEach(dir => {
            if (!fs.existsSync(dir)) {
                fs.mkdirSync(dir, { recursive: true });
            }
        });
    }
    
    setupMQTTHandlers() {
        const deviceId = this.mqttClient.options.clientId;
        
        // ファイル転送開始
        this.mqttClient.subscribe(`files/${deviceId}/start`);
        
        // チャンクデータ受信
        this.mqttClient.subscribe(`files/${deviceId}/chunk`);
        
        // 転送完了通知
        this.mqttClient.subscribe(`files/${deviceId}/complete`);
        
        // S3ダウンロード指示
        this.mqttClient.subscribe(`files/${deviceId}/download`);
        
        this.mqttClient.on('message', (topic, message) => {
            this.handleFileMessage(topic, message);
        });
    }
    
    handleFileMessage(topic, message) {
        try {
            const data = JSON.parse(message.toString());
            
            if (topic.endsWith('/start')) {
                this.handleTransferStart(data);
            } else if (topic.endsWith('/chunk')) {
                this.handleChunkReceived(data);
            } else if (topic.endsWith('/complete')) {
                this.handleTransferComplete(data);
            } else if (topic.endsWith('/download')) {
                this.handleS3Download(data);
            }
        } catch (error) {
            console.error('Error handling file message:', error);
        }
    }
    
    handleTransferStart(data) {
        const { fileName, fileSize, totalChunks, checksum } = data;
        
        console.log(`File transfer started: ${fileName} (${fileSize} bytes)`);
        
        const download = {
            fileName,
            fileSize,
            totalChunks,
            checksum,
            receivedChunks: new Map(),
            startTime: Date.now(),
            retryCount: 0
        };
        
        this.activeDownloads.set(fileName, download);
    }
    
    handleChunkReceived(data) {
        const { fileName, chunkIndex, totalChunks, data: chunkData } = data;
        const download = this.activeDownloads.get(fileName);
        
        if (!download) {
            console.warn(`No active download for: ${fileName}`);
            return;
        }
        
        // チャンクデータをデコード
        const chunkBuffer = Buffer.from(chunkData, 'base64');
        download.receivedChunks.set(chunkIndex, chunkBuffer);
        
        const progress = (download.receivedChunks.size / totalChunks * 100).toFixed(1);
        console.log(`Progress ${fileName}: ${progress}% (${download.receivedChunks.size}/${totalChunks})`);
        
        // 全チャンク受信チェック
        if (download.receivedChunks.size === totalChunks) {
            this.assembleAndVerifyFile(fileName);
        }
    }
    
    async assembleAndVerifyFile(fileName) {
        const download = this.activeDownloads.get(fileName);
        if (!download) return;
        
        try {
            // チャンクを順序通りに結合
            const chunks = [];
            for (let i = 0; i < download.totalChunks; i++) {
                const chunk = download.receivedChunks.get(i);
                if (!chunk) {
                    throw new Error(`Missing chunk: ${i}`);
                }
                chunks.push(chunk);
            }
            
            const fileBuffer = Buffer.concat(chunks);
            
            // チェックサム検証
            const calculatedChecksum = crypto.createHash('sha256').update(fileBuffer).digest('hex');
            if (calculatedChecksum !== download.checksum) {
                throw new Error('Checksum verification failed');
            }
            
            // ファイル保存
            const tempPath = path.join(this.tempDir, `${fileName}.tmp`);
            const finalPath = path.join(this.downloadDir, fileName);
            
            await fs.promises.writeFile(tempPath, fileBuffer);
            await fs.promises.rename(tempPath, finalPath);
            
            const transferTime = Date.now() - download.startTime;
            console.log(`File received successfully: ${fileName} in ${transferTime}ms`);
            
            // ダウンロード完了イベント
            this.onFileReceived(fileName, finalPath, fileBuffer.length);
            
        } catch (error) {
            console.error(`Error assembling file ${fileName}:`, error);
            await this.handleTransferError(fileName, error);
        } finally {
            this.activeDownloads.delete(fileName);
        }
    }
    
    async handleS3Download(data) {
        const { fileName, downloadUrl, checksum, priority } = data;
        
        console.log(`Starting S3 download: ${fileName}`);
        
        try {
            const response = await this.downloadFromUrl(downloadUrl, {
                timeout: priority === 'urgent' ? 60000 : 300000
            });
            
            // チェックサム検証
            const calculatedChecksum = crypto.createHash('sha256').update(response.data).digest('hex');
            if (calculatedChecksum !== checksum) {
                throw new Error('S3 download checksum verification failed');
            }
            
            // ファイル保存
            const finalPath = path.join(this.downloadDir, fileName);
            await fs.promises.writeFile(finalPath, response.data);
            
            console.log(`S3 file downloaded successfully: ${fileName}`);
            this.onFileReceived(fileName, finalPath, response.data.length);
            
        } catch (error) {
            console.error(`S3 download failed for ${fileName}:`, error);
        }
    }
    
    async downloadFromUrl(url, options = {}) {
        const https = require('https');
        const http = require('http');
        
        return new Promise((resolve, reject) => {
            const client = url.startsWith('https:') ? https : http;
            const timeout = options.timeout || 120000;
            
            const request = client.get(url, (response) => {
                if (response.statusCode !== 200) {
                    reject(new Error(`HTTP ${response.statusCode}: ${response.statusMessage}`));
                    return;
                }
                
                const chunks = [];
                response.on('data', (chunk) => chunks.push(chunk));
                response.on('end', () => {
                    resolve({ data: Buffer.concat(chunks) });
                });
            });
            
            request.setTimeout(timeout, () => {
                request.abort();
                reject(new Error('Download timeout'));
            });
            
            request.on('error', reject);
        });
    }
    
    async handleTransferError(fileName, error) {
        const download = this.activeDownloads.get(fileName);
        if (!download) return;
        
        download.retryCount++;
        
        if (download.retryCount <= this.maxRetries) {
            console.log(`Retrying transfer for ${fileName} (attempt ${download.retryCount})`);
            
            // 再送要求
            await this.requestFileRetransfer(fileName);
        } else {
            console.error(`Max retries exceeded for ${fileName}`);
            this.activeDownloads.delete(fileName);
            
            // エラー通知
            this.onTransferFailed(fileName, error);
        }
    }
    
    async requestFileRetransfer(fileName) {
        const deviceId = this.mqttClient.options.clientId;
        
        await this.mqttClient.publish(`files/${deviceId}/retry`, JSON.stringify({
            fileName: fileName,
            reason: 'transfer_error',
            timestamp: new Date().toISOString()
        }), { qos: 1 });
    }
    
    onFileReceived(fileName, filePath, fileSize) {
        console.log(`File received event: ${fileName}`);
        
        // ファイルタイプに応じた処理
        if (fileName.includes('firmware')) {
            this.handleFirmwareUpdate(filePath);
        } else if (fileName.includes('config')) {
            this.handleConfigUpdate(filePath);
        } else if (fileName.includes('model')) {
            this.handleMLModelUpdate(filePath);
        }
    }
    
    async handleFirmwareUpdate(filePath) {
        console.log(`Processing firmware update: ${filePath}`);
        
        try {
            // ファームウェア検証
            const isValid = await this.validateFirmware(filePath);
            if (!isValid) {
                throw new Error('Firmware validation failed');
            }
            
            // 現在のファームウェアのバックアップ
            await this.backupCurrentFirmware();
            
            // ファームウェア適用
            await this.applyFirmware(filePath);
            
            // 更新完了通知
            await this.reportFirmwareUpdateStatus('success');
            
            console.log('Firmware update completed successfully');
            
        } catch (error) {
            console.error('Firmware update failed:', error);
            await this.reportFirmwareUpdateStatus('failed', error.message);
        }
    }
    
    async validateFirmware(filePath) {
        // ファームウェア固有の検証ロジック
        // - デジタル署名検証
        // - ハードウェア互換性チェック
        // - バージョン確認
        return true; // 簡略化
    }
    
    async applyFirmware(filePath) {
        // プラットフォーム固有のファームウェア適用
        console.log('Applying firmware...');
        
        // シミュレーション
        await new Promise(resolve => setTimeout(resolve, 5000));
        
        console.log('Firmware applied, rebooting...');
        // 実際の環境では process.exit() やシステム再起動
    }
    
    async reportFirmwareUpdateStatus(status, error = null) {
        const deviceId = this.mqttClient.options.clientId;
        
        const report = {
            deviceId: deviceId,
            updateType: 'firmware',
            status: status,
            timestamp: new Date().toISOString(),
            error: error
        };
        
        await this.mqttClient.publish(`status/${deviceId}/firmware_update`, 
            JSON.stringify(report), { qos: 1 });
    }
    
    onTransferFailed(fileName, error) {
        console.error(`File transfer failed: ${fileName}`, error);
        
        // 失敗通知の送信
        const deviceId = this.mqttClient.options.clientId;
        this.mqttClient.publish(`status/${deviceId}/transfer_failed`, JSON.stringify({
            fileName: fileName,
            error: error.message,
            timestamp: new Date().toISOString()
        }), { qos: 1 });
    }
}
```

## 9.4 Best Practices とセキュリティ考慮事項

### 9.4.1 セキュアなファイル転送

```javascript
class SecureFileTransfer {
    constructor(mqttClient, securityConfig) {
        this.mqttClient = mqttClient;
        this.securityConfig = securityConfig;
        this.crypto = require('crypto');
    }
    
    async encryptAndTransferFile(filePath, recipientPublicKey) {
        try {
            // ファイル読み込み
            const fileBuffer = await fs.promises.readFile(filePath);
            
            // AES暗号化（ファイル本体）
            const aesKey = this.crypto.randomBytes(32);
            const iv = this.crypto.randomBytes(16);
            
            const cipher = this.crypto.createCipher('aes-256-cbc', aesKey, iv);
            let encryptedFile = cipher.update(fileBuffer);
            encryptedFile = Buffer.concat([encryptedFile, cipher.final()]);
            
            // RSA暗号化（AESキー）
            const encryptedAESKey = this.crypto.publicEncrypt(recipientPublicKey, aesKey);
            
            // デジタル署名
            const sign = this.crypto.createSign('SHA256');
            sign.update(fileBuffer);
            const signature = sign.sign(this.securityConfig.privateKey);
            
            // メタデータ
            const metadata = {
                fileName: path.basename(filePath),
                originalSize: fileBuffer.length,
                encryptedSize: encryptedFile.length,
                iv: iv.toString('hex'),
                signature: signature.toString('base64'),
                timestamp: new Date().toISOString(),
                version: '1.0'
            };
            
            // セキュアファイルパッケージの作成
            const securePackage = {
                metadata: metadata,
                encryptedKey: encryptedAESKey.toString('base64'),
                encryptedFile: encryptedFile.toString('base64')
            };
            
            // MQTT経由で送信
            await this.sendSecurePackage(securePackage);
            
            return {
                success: true,
                packageSize: Buffer.from(JSON.stringify(securePackage)).length
            };
            
        } catch (error) {
            console.error('Secure file transfer failed:', error);
            throw error;
        }
    }
    
    async receiveAndDecryptFile(securePackageData) {
        try {
            const { metadata, encryptedKey, encryptedFile } = securePackageData;
            
            // AESキーの復号化
            const encryptedAESKeyBuffer = Buffer.from(encryptedKey, 'base64');
            const aesKey = this.crypto.privateDecrypt(this.securityConfig.privateKey, encryptedAESKeyBuffer);
            
            // ファイルの復号化
            const iv = Buffer.from(metadata.iv, 'hex');
            const encryptedFileBuffer = Buffer.from(encryptedFile, 'base64');
            
            const decipher = this.crypto.createDecipher('aes-256-cbc', aesKey, iv);
            let decryptedFile = decipher.update(encryptedFileBuffer);
            decryptedFile = Buffer.concat([decryptedFile, decipher.final()]);
            
            // デジタル署名検証
            const verify = this.crypto.createVerify('SHA256');
            verify.update(decryptedFile);
            const signatureBuffer = Buffer.from(metadata.signature, 'base64');
            
            const isSignatureValid = verify.verify(this.securityConfig.senderPublicKey, signatureBuffer);
            if (!isSignatureValid) {
                throw new Error('Digital signature verification failed');
            }
            
            // ファイル整合性チェック
            if (decryptedFile.length !== metadata.originalSize) {
                throw new Error('File size mismatch after decryption');
            }
            
            // ファイル保存
            const outputPath = path.join('./secure_downloads', metadata.fileName);
            await fs.promises.writeFile(outputPath, decryptedFile);
            
            console.log(`Secure file received: ${metadata.fileName}`);
            
            return {
                success: true,
                fileName: metadata.fileName,
                filePath: outputPath,
                fileSize: decryptedFile.length
            };
            
        } catch (error) {
            console.error('Secure file decryption failed:', error);
            throw error;
        }
    }
}
```

### 9.4.2 バージョン管理とロールバック

```javascript
class FirmwareVersionManager {
    constructor(mqttClient, storageConfig) {
        this.mqttClient = mqttClient;
        this.storageConfig = storageConfig;
        this.versionsDir = storageConfig.versionsDir || './firmware_versions';
        this.currentVersionFile = storageConfig.currentVersionFile || './current_version.json';
        
        this.initializeVersioning();
    }
    
    async initializeVersioning() {
        // バージョン管理ディレクトリの作成
        if (!fs.existsSync(this.versionsDir)) {
            fs.mkdirSync(this.versionsDir, { recursive: true });
        }
        
        // 現在のバージョン情報を読み込み
        await this.loadCurrentVersion();
    }
    
    async loadCurrentVersion() {
        try {
            if (fs.existsSync(this.currentVersionFile)) {
                const versionData = await fs.promises.readFile(this.currentVersionFile, 'utf8');
                this.currentVersion = JSON.parse(versionData);
            } else {
                // 初期バージョン情報
                this.currentVersion = {
                    version: '1.0.0',
                    build: Date.now(),
                    installDate: new Date().toISOString(),
                    source: 'factory'
                };
                await this.saveCurrentVersion();
            }
            
            console.log('Current firmware version:', this.currentVersion);
        } catch (error) {
            console.error('Failed to load current version:', error);
        }
    }
    
    async saveCurrentVersion() {
        await fs.promises.writeFile(this.currentVersionFile, 
            JSON.stringify(this.currentVersion, null, 2));
    }
    
    async installNewFirmware(firmwarePath, versionInfo) {
        try {
            console.log(`Installing firmware version: ${versionInfo.version}`);
            
            // 現在のファームウェアをバックアップ
            await this.backupCurrentFirmware();
            
            // 新しいファームウェアのバージョン管理
            const versionDir = path.join(this.versionsDir, versionInfo.version);
            if (!fs.existsSync(versionDir)) {
                fs.mkdirSync(versionDir, { recursive: true });
            }
            
            // ファームウェアファイルをバージョンディレクトリにコピー
            const versionedFirmwarePath = path.join(versionDir, 'firmware.bin');
            await fs.promises.copyFile(firmwarePath, versionedFirmwarePath);
            
            // バージョン情報の保存
            const fullVersionInfo = {
                ...versionInfo,
                installDate: new Date().toISOString(),
                previousVersion: this.currentVersion.version,
                firmwarePath: versionedFirmwarePath,
                verified: false
            };
            
            await fs.promises.writeFile(path.join(versionDir, 'version.json'), 
                JSON.stringify(fullVersionInfo, null, 2));
            
            // ファームウェア適用
            const success = await this.applyFirmware(versionedFirmwarePath);
            
            if (success) {
                // バージョン情報の更新
                this.currentVersion = fullVersionInfo;
                this.currentVersion.verified = true;
                await this.saveCurrentVersion();
                
                // 成功報告
                await this.reportInstallationStatus('success', versionInfo.version);
                
                console.log(`Firmware ${versionInfo.version} installed successfully`);
                
                // 古いバージョンのクリーンアップ（オプション）
                await this.cleanupOldVersions();
                
            } else {
                throw new Error('Firmware application failed');
            }
            
        } catch (error) {
            console.error('Firmware installation failed:', error);
            
            // 失敗時のロールバック
            await this.rollbackToPreviousVersion();
            
            // エラー報告
            await this.reportInstallationStatus('failed', versionInfo.version, error.message);
        }
    }
    
    async backupCurrentFirmware() {
        if (this.currentVersion.firmwarePath && fs.existsSync(this.currentVersion.firmwarePath)) {
            const backupDir = path.join(this.versionsDir, 'backup');
            if (!fs.existsSync(backupDir)) {
                fs.mkdirSync(backupDir, { recursive: true });
            }
            
            const backupPath = path.join(backupDir, `firmware_${this.currentVersion.version}.bin`);
            await fs.promises.copyFile(this.currentVersion.firmwarePath, backupPath);
            
            console.log(`Current firmware backed up: ${backupPath}`);
        }
    }
    
    async rollbackToPreviousVersion() {
        try {
            console.log('Initiating firmware rollback...');
            
            if (!this.currentVersion.previousVersion) {
                throw new Error('No previous version available for rollback');
            }
            
            const previousVersionDir = path.join(this.versionsDir, this.currentVersion.previousVersion);
            const previousVersionPath = path.join(previousVersionDir, 'firmware.bin');
            
            if (!fs.existsSync(previousVersionPath)) {
                throw new Error(`Previous version firmware not found: ${previousVersionPath}`);
            }
            
            // 前のバージョンのファームウェアを適用
            const success = await this.applyFirmware(previousVersionPath);
            
            if (success) {
                // バージョン情報をロールバック
                const previousVersionInfo = JSON.parse(
                    await fs.promises.readFile(path.join(previousVersionDir, 'version.json'), 'utf8')
                );
                
                this.currentVersion = previousVersionInfo;
                await this.saveCurrentVersion();
                
                console.log(`Rollback completed to version: ${this.currentVersion.version}`);
                
                // ロールバック報告
                await this.reportRollbackStatus('success');
                
            } else {
                throw new Error('Rollback firmware application failed');
            }
            
        } catch (error) {
            console.error('Rollback failed:', error);
            await this.reportRollbackStatus('failed', error.message);
        }
    }
    
    async applyFirmware(firmwarePath) {
        // プラットフォーム固有のファームウェア適用ロジック
        console.log(`Applying firmware from: ${firmwarePath}`);
        
        // ファームウェア検証
        const isValid = await this.validateFirmwareFile(firmwarePath);
        if (!isValid) {
            throw new Error('Firmware validation failed');
        }
        
        // シミュレーション（実際の実装では適切な更新処理）
        await new Promise(resolve => setTimeout(resolve, 3000));
        
        return true;
    }
    
    async validateFirmwareFile(firmwarePath) {
        try {
            const stats = await fs.promises.stat(firmwarePath);
            
            // 基本的な検証
            if (stats.size < 1024 || stats.size > 50 * 1024 * 1024) { // 1KB-50MB
                return false;
            }
            
            // より詳細な検証（署名チェック、CRCなど）をここに実装
            
            return true;
        } catch (error) {
            console.error('Firmware validation error:', error);
            return false;
        }
    }
    
    async cleanupOldVersions(keepVersions = 3) {
        try {
            const versionDirs = await fs.promises.readdir(this.versionsDir);
            const versionInfos = [];
            
            for (const dir of versionDirs) {
                if (dir === 'backup') continue;
                
                const versionFile = path.join(this.versionsDir, dir, 'version.json');
                if (fs.existsSync(versionFile)) {
                    const info = JSON.parse(await fs.promises.readFile(versionFile, 'utf8'));
                    info.directory = dir;
                    versionInfos.push(info);
                }
            }
            
            // インストール日時でソート（新しい順）
            versionInfos.sort((a, b) => new Date(b.installDate) - new Date(a.installDate));
            
            // 古いバージョンを削除
            const versionsToDelete = versionInfos.slice(keepVersions);
            
            for (const versionInfo of versionsToDelete) {
                const versionDir = path.join(this.versionsDir, versionInfo.directory);
                await this.removeDirectory(versionDir);
                console.log(`Cleaned up old version: ${versionInfo.version}`);
            }
            
        } catch (error) {
            console.error('Cleanup failed:', error);
        }
    }
    
    async removeDirectory(dirPath) {
        const entries = await fs.promises.readdir(dirPath, { withFileTypes: true });
        
        for (const entry of entries) {
            const fullPath = path.join(dirPath, entry.name);
            if (entry.isDirectory()) {
                await this.removeDirectory(fullPath);
            } else {
                await fs.promises.unlink(fullPath);
            }
        }
        
        await fs.promises.rmdir(dirPath);
    }
    
    async reportInstallationStatus(status, version, error = null) {
        const deviceId = this.mqttClient.options.clientId;
        
        const report = {
            deviceId: deviceId,
            operation: 'firmware_install',
            version: version,
            previousVersion: this.currentVersion.previousVersion,
            status: status,
            timestamp: new Date().toISOString(),
            error: error
        };
        
        await this.mqttClient.publish(`status/${deviceId}/firmware_update`, 
            JSON.stringify(report), { qos: 1 });
    }
    
    async reportRollbackStatus(status, error = null) {
        const deviceId = this.mqttClient.options.clientId;
        
        const report = {
            deviceId: deviceId,
            operation: 'firmware_rollback',
            currentVersion: this.currentVersion.version,
            status: status,
            timestamp: new Date().toISOString(),
            error: error
        };
        
        await this.mqttClient.publish(`status/${deviceId}/firmware_rollback`, 
            JSON.stringify(report), { qos: 1 });
    }
    
    getCurrentVersion() {
        return this.currentVersion;
    }
    
    async getVersionHistory() {
        const versionDirs = await fs.promises.readdir(this.versionsDir);
        const history = [];
        
        for (const dir of versionDirs) {
            if (dir === 'backup') continue;
            
            const versionFile = path.join(this.versionsDir, dir, 'version.json');
            if (fs.existsSync(versionFile)) {
                const info = JSON.parse(await fs.promises.readFile(versionFile, 'utf8'));
                history.push(info);
            }
        }
        
        return history.sort((a, b) => new Date(b.installDate) - new Date(a.installDate));
    }
}
```

## 参考リンク

- [AWS IoT MQTT-based File Delivery](https://docs.aws.amazon.com/iot/latest/developerguide/mqtt-based-file-delivery.html)
- [AWS IoT OTA Update Service](https://docs.aws.amazon.com/freertos/latest/userguide/freertos-ota-dev.html)
- [MQTT File Transfer Best Practices - EMQX](https://docs.emqx.com/en/emqx/latest/file-transfer/introduction.html)
- [IoT Device Management Patterns](https://aws.amazon.com/blogs/iot/device-management-patterns/)
- [Secure IoT Firmware Updates](https://www.nist.gov/publications/cybersecurity-iot-device-cybersecurity-guidance)

---

**次の章**: [10-monitoring-and-troubleshooting.md](10-monitoring-and-troubleshooting.md) - 監視とトラブルシューティング