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

```python
import json
import time
import hashlib
import base64
import os
from typing import Dict, Optional, Callable
from concurrent.futures import ThreadPoolExecutor
import asyncio
from awsiot.mqtt import MqttClient, QoS

class AWSIoTFileTransfer:
    def __init__(self, connection_config):
        self.connection = None
        self.connection_config = connection_config
        self.active_transfers = {}
        
    async def initialize(self):
        # AWS IoT接続設定は前章と同様
        self.connection = await self.create_connection(self.connection_config)
        
        # ファイル転送関連トピックの購読
        await self.subscribe_to_file_topics()
    
    async def subscribe_to_file_topics(self):
        # ファイル転送ストリーム情報取得
        await self.connection.subscribe(
            '$aws/things/+/streams/+/data/+',
            QoS.AT_LEAST_ONCE,
            self.handle_stream_data
        )
        
        # ファイル転送ストリームリスト
        await self.connection.subscribe(
            '$aws/things/+/streams/+/get/accepted',
            QoS.AT_LEAST_ONCE,
            self.handle_stream_info
        )
    
    async def request_file_transfer(self, stream_id, file_name):
        transfer_id = self.generate_transfer_id()
        
        # ファイル転送要求
        request = {
            'clientToken': transfer_id,
            's': stream_id,  # Stream ID
            'f': file_name   # File ID
        }
        
        topic = f"$aws/things/{self.connection_config['thingName']}/streams/{stream_id}/get"
        
        await self.connection.publish(
            topic,
            json.dumps(request),
            QoS.AT_LEAST_ONCE
        )
        
        print(f"File transfer requested: {file_name}")
        
        # Promiseの代わりにasyncio.Eventを使用
        transfer_complete = asyncio.Event()
        transfer_result = {'success': False, 'data': None, 'error': None}
        
        self.active_transfers[transfer_id] = {
            'event': transfer_complete,
            'result': transfer_result,
            'stream_id': stream_id,
            'file_name': file_name,
            'blocks': {},
            'total_blocks': 0,
            'received_blocks': 0,
            'start_time': time.time()
        }
        
        # タイムアウト設定
        try:
            await asyncio.wait_for(transfer_complete.wait(), timeout=300)  # 5分タイムアウト
            if transfer_result['success']:
                return transfer_result['data']
            else:
                raise Exception(transfer_result['error'])
        except asyncio.TimeoutError:
            if transfer_id in self.active_transfers:
                del self.active_transfers[transfer_id]
            raise Exception('File transfer timeout')
    
    def handle_stream_info(self, topic, payload):
        try:
            data = json.loads(payload.decode())
            transfer_id = data.get('clientToken')
            transfer = self.active_transfers.get(transfer_id)
            
            if not transfer:
                return
            
            # ファイル情報の解析
            file_info = data.get('files', {}).get(transfer['file_name'])
            if file_info:
                transfer['total_blocks'] = (file_info['s'] + 1023) // 1024  # 1KBブロックと仮定
                transfer['file_size'] = file_info['s']
                transfer['checksum'] = file_info.get('c')
                
                print(f"File info received: {transfer['file_name']}, size: {file_info['s']} bytes")
                
                # ブロックデータの要求開始
                asyncio.create_task(self.request_file_blocks(transfer_id))
                
        except Exception as error:
            print(f"Error handling stream info: {error}")
    
    async def request_file_blocks(self, transfer_id):
        transfer = self.active_transfers.get(transfer_id)
        if not transfer:
            return
        
        # 複数ブロックを並行して要求
        batch_size = 5
        
        for block_id in range(0, transfer['total_blocks'], batch_size):
            tasks = []
            
            for i in range(batch_size):
                current_block_id = block_id + i
                if current_block_id < transfer['total_blocks']:
                    tasks.append(self.request_single_block(transfer_id, current_block_id))
            
            # バッチ処理
            await asyncio.gather(*tasks)
            
            # レート制限（デバイスリソース保護）
            await asyncio.sleep(0.1)
    
    async def request_single_block(self, transfer_id, block_id):
        transfer = self.active_transfers.get(transfer_id)
        if not transfer:
            return
        
        request = {
            'clientToken': transfer_id,
            's': transfer['stream_id'],
            'f': transfer['file_name'],
            'l': 1024,  # ブロックサイズ
            'o': block_id * 1024,  # オフセット
            'n': 1  # 要求ブロック数
        }
        
        topic = f"$aws/things/{self.connection_config['thingName']}/streams/{transfer['stream_id']}/data"
        
        await self.connection.publish(
            topic,
            json.dumps(request),
            QoS.AT_LEAST_ONCE
        )
    
    def handle_stream_data(self, topic, payload):
        try:
            data = json.loads(payload.decode())
            transfer_id = data.get('clientToken')
            transfer = self.active_transfers.get(transfer_id)
            
            if not transfer:
                return
            
            # ブロックデータの保存
            if 'p' in data:  # payload
                block_data = base64.b64decode(data['p'])
                block_id = data['o'] // 1024
                
                transfer['blocks'][block_id] = block_data
                transfer['received_blocks'] += 1
                
                print(f"Block received: {block_id + 1}/{transfer['total_blocks']}")
                
                # 全ブロック受信完了チェック
                if transfer['received_blocks'] == transfer['total_blocks']:
                    self.complete_file_transfer(transfer_id)
                    
        except Exception as error:
            print(f"Error handling stream data: {error}")
    
    def complete_file_transfer(self, transfer_id):
        transfer = self.active_transfers.get(transfer_id)
        if not transfer:
            return
        
        try:
            # ブロックデータの結合
            file_buffer = self.assemble_file_from_blocks(
                transfer['blocks'], 
                transfer['total_blocks']
            )
            
            # チェックサム検証
            if transfer.get('checksum'):
                calculated_checksum = hashlib.sha256(file_buffer).hexdigest()
                if calculated_checksum != transfer['checksum']:
                    raise Exception('Checksum mismatch')
            
            # ファイル保存
            os.makedirs('./downloads', exist_ok=True)
            file_path = f"./downloads/{transfer['file_name']}"
            
            with open(file_path, 'wb') as f:
                f.write(file_buffer)
            
            transfer_time = (time.time() - transfer['start_time']) * 1000
            print(f"File transfer completed: {transfer['file_name']}, {transfer_time:.0f}ms")
            
            # 結果を設定
            transfer['result']['success'] = True
            transfer['result']['data'] = {
                'file_name': transfer['file_name'],
                'file_path': file_path,
                'file_size': len(file_buffer),
                'transfer_time': transfer_time
            }
            
        except Exception as error:
            transfer['result']['success'] = False
            transfer['result']['error'] = str(error)
        finally:
            # イベントをセットして待機中のタスクに通知
            transfer['event'].set()
            del self.active_transfers[transfer_id]
    
    def assemble_file_from_blocks(self, blocks, total_blocks):
        buffers = []
        
        for i in range(total_blocks):
            if i not in blocks:
                raise Exception(f"Missing block: {i}")
            buffers.append(blocks[i])
        
        return b''.join(buffers)
    
    def generate_transfer_id(self):
        import random
        import string
        timestamp = int(time.time() * 1000)
        random_str = ''.join(random.choices(string.ascii_letters + string.digits, k=9))
        return f"transfer_{timestamp}_{random_str}"

# 使用例
async def download_firmware_update():
    file_transfer = AWSIoTFileTransfer({
        'thingName': 'industrial-sensor-001',
        'endpoint': 'your-endpoint.iot.us-east-1.amazonaws.com',
        'certPath': './certificate.pem.crt',
        'keyPath': './private.pem.key'
    })
    
    await file_transfer.initialize()
    
    try:
        result = await file_transfer.request_file_transfer(
            'firmware-stream-v1',  # Stream ID
            'firmware-v2.1.0.bin'  # File name
        )
        
        print('Firmware download completed:', result)
        
        # ファームウェア更新処理
        await apply_firmware_update(result['filePath'])
        
    except Exception as error:
        print(f'Firmware download failed: {error}')
```

### 9.2.2 AWS S3 + Pre-signed URLs との組み合わせ

```python
import boto3
from datetime import datetime, timedelta

class HybridFileTransfer:
    def __init__(self, aws_config):
        self.aws_config = aws_config
        self.s3_client = boto3.client('s3')
        self.iot_connection = None
    
    async def initialize(self):
        # AWS IoT接続
        self.iot_connection = await self.create_iot_connection()
        
        # ファイル要求トピックの購読
        await self.iot_connection.subscribe(
            f"files/{self.aws_config['thingName']}/request",
            QoS.AT_LEAST_ONCE,
            self.handle_file_request
        )
    
    async def handle_file_request(self, topic, payload):
        try:
            request = json.loads(payload.decode())
            file_type = request.get('fileType')
            version = request.get('version')
            priority = request.get('priority')
            
            # ファイルサイズに応じた転送方法の選択
            file_info = await self.get_file_info(file_type, version)
            
            if file_info['size'] < 1024 * 1024:  # 1MB未満
                # MQTT経由での転送
                await self.transfer_via_mqtt(file_info)
            else:
                # S3 Pre-signed URL経由での転送
                await self.transfer_via_s3(file_info, priority)
                
        except Exception as error:
            print(f'Error handling file request: {error}')
    
    async def transfer_via_mqtt(self, file_info):
        print(f"Transferring {file_info['name']} via MQTT")
        
        with open(file_info['path'], 'rb') as f:
            file_data = f.read()
        
        chunks = self.split_into_chunks(file_data, 32 * 1024)  # 32KB chunks
        
        # ファイル転送開始通知
        await self.iot_connection.publish(
            f"files/{self.aws_config['thingName']}/start",
            json.dumps({
                'fileName': file_info['name'],
                'fileSize': file_info['size'],
                'totalChunks': len(chunks),
                'checksum': hashlib.sha256(file_data).hexdigest()
            }),
            QoS.AT_LEAST_ONCE
        )
        
        # チャンク送信
        for i, chunk in enumerate(chunks):
            await self.iot_connection.publish(
                f"files/{self.aws_config['thingName']}/chunk",
                json.dumps({
                    'fileName': file_info['name'],
                    'chunkIndex': i,
                    'totalChunks': len(chunks),
                    'data': base64.b64encode(chunk).decode()
                }),
                QoS.AT_LEAST_ONCE
            )
            
            # レート制限
            await asyncio.sleep(0.05)
        
        # 転送完了通知
        await self.iot_connection.publish(
            f"files/{self.aws_config['thingName']}/complete",
            json.dumps({
                'fileName': file_info['name'],
                'status': 'completed'
            }),
            QoS.AT_LEAST_ONCE
        )
    
    async def transfer_via_s3(self, file_info, priority='normal'):
        print(f"Transferring {file_info['name']} via S3")
        
        # S3にファイルアップロード（既にアップロード済みと仮定）
        s3_key = f"firmware/{file_info['name']}"
        
        # Pre-signed URL生成
        expiration_time = 3600 if priority == 'urgent' else 7200  # 1-2時間
        
        presigned_url = self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': self.aws_config['s3Bucket'],
                'Key': s3_key
            },
            ExpiresIn=expiration_time
        )
        
        # デバイスにダウンロード指示
        expires_at = datetime.now() + timedelta(seconds=expiration_time)
        
        await self.iot_connection.publish(
            f"files/{self.aws_config['thingName']}/download",
            json.dumps({
                'fileName': file_info['name'],
                'fileSize': file_info['size'],
                'downloadUrl': presigned_url,
                'method': 'https',
                'checksum': await self.calculate_s3_file_checksum(s3_key),
                'priority': priority,
                'expiresAt': expires_at.isoformat()
            }),
            QoS.AT_LEAST_ONCE
        )
    
    def split_into_chunks(self, data, chunk_size):
        chunks = []
        for i in range(0, len(data), chunk_size):
            chunks.append(data[i:i + chunk_size])
        return chunks
    
    async def calculate_s3_file_checksum(self, s3_key):
        response = self.s3_client.get_object(
            Bucket=self.aws_config['s3Bucket'],
            Key=s3_key
        )
        
        return hashlib.sha256(response['Body'].read()).hexdigest()
```

## 9.3 デバイス側実装 - ファイル受信とOTA更新

### 9.3.1 堅牢なファイル受信機構

```python
import os
import shutil
import aiohttp
from pathlib import Path

class RobustFileReceiver:
    def __init__(self, mqtt_client, options=None):
        if options is None:
            options = {}
        
        self.mqtt_client = mqtt_client
        self.download_dir = options.get('download_dir', './downloads')
        self.temp_dir = options.get('temp_dir', './tmp')
        self.max_retries = options.get('max_retries', 3)
        self.active_downloads = {}
        
        self.setup_directories()
        self.setup_mqtt_handlers()
    
    def setup_directories(self):
        for directory in [self.download_dir, self.temp_dir]:
            os.makedirs(directory, exist_ok=True)
    
    def setup_mqtt_handlers(self):
        device_id = self.mqtt_client.client_id
        
        # ファイル転送開始
        self.mqtt_client.subscribe(f'files/{device_id}/start')
        
        # チャンクデータ受信
        self.mqtt_client.subscribe(f'files/{device_id}/chunk')
        
        # 転送完了通知
        self.mqtt_client.subscribe(f'files/{device_id}/complete')
        
        # S3ダウンロード指示
        self.mqtt_client.subscribe(f'files/{device_id}/download')
        
        self.mqtt_client.on_message = self.handle_file_message
    
    def handle_file_message(self, client, userdata, message):
        try:
            data = json.loads(message.payload.decode())
            topic = message.topic
            
            if topic.endswith('/start'):
                self.handle_transfer_start(data)
            elif topic.endswith('/chunk'):
                self.handle_chunk_received(data)
            elif topic.endswith('/complete'):
                self.handle_transfer_complete(data)
            elif topic.endswith('/download'):
                asyncio.create_task(self.handle_s3_download(data))
        except Exception as error:
            print(f'Error handling file message: {error}')
    
    def handle_transfer_start(self, data):
        file_name = data.get('fileName')
        file_size = data.get('fileSize')
        total_chunks = data.get('totalChunks')
        checksum = data.get('checksum')
        
        print(f"File transfer started: {file_name} ({file_size} bytes)")
        
        download = {
            'file_name': file_name,
            'file_size': file_size,
            'total_chunks': total_chunks,
            'checksum': checksum,
            'received_chunks': {},
            'start_time': time.time(),
            'retry_count': 0
        }
        
        self.active_downloads[file_name] = download
    
    def handle_chunk_received(self, data):
        file_name = data.get('fileName')
        chunk_index = data.get('chunkIndex')
        total_chunks = data.get('totalChunks')
        chunk_data = data.get('data')
        
        download = self.active_downloads.get(file_name)
        
        if not download:
            print(f"No active download for: {file_name}")
            return
        
        # チャンクデータをデコード
        chunk_buffer = base64.b64decode(chunk_data)
        download['received_chunks'][chunk_index] = chunk_buffer
        
        progress = len(download['received_chunks']) / total_chunks * 100
        print(f"Progress {file_name}: {progress:.1f}% ({len(download['received_chunks'])}/{total_chunks})")
        
        # 全チャンク受信チェック
        if len(download['received_chunks']) == total_chunks:
            asyncio.create_task(self.assemble_and_verify_file(file_name))
    
    async def assemble_and_verify_file(self, file_name):
        download = self.active_downloads.get(file_name)
        if not download:
            return
        
        try:
            # チャンクを順序通りに結合
            chunks = []
            for i in range(download['total_chunks']):
                if i not in download['received_chunks']:
                    raise Exception(f"Missing chunk: {i}")
                chunks.append(download['received_chunks'][i])
            
            file_buffer = b''.join(chunks)
            
            # チェックサム検証
            calculated_checksum = hashlib.sha256(file_buffer).hexdigest()
            if calculated_checksum != download['checksum']:
                raise Exception('Checksum verification failed')
            
            # ファイル保存
            temp_path = os.path.join(self.temp_dir, f"{file_name}.tmp")
            final_path = os.path.join(self.download_dir, file_name)
            
            with open(temp_path, 'wb') as f:
                f.write(file_buffer)
            
            shutil.move(temp_path, final_path)
            
            transfer_time = (time.time() - download['start_time']) * 1000
            print(f"File received successfully: {file_name} in {transfer_time:.0f}ms")
            
            # ダウンロード完了イベント
            self.on_file_received(file_name, final_path, len(file_buffer))
            
        except Exception as error:
            print(f"Error assembling file {file_name}: {error}")
            await self.handle_transfer_error(file_name, error)
        finally:
            if file_name in self.active_downloads:
                del self.active_downloads[file_name]
    
    async def handle_s3_download(self, data):
        file_name = data.get('fileName')
        download_url = data.get('downloadUrl')
        checksum = data.get('checksum')
        priority = data.get('priority')
        
        print(f"Starting S3 download: {file_name}")
        
        try:
            timeout = 60 if priority == 'urgent' else 300
            response_data = await self.download_from_url(download_url, timeout=timeout)
            
            # チェックサム検証
            calculated_checksum = hashlib.sha256(response_data).hexdigest()
            if calculated_checksum != checksum:
                raise Exception('S3 download checksum verification failed')
            
            # ファイル保存
            final_path = os.path.join(self.download_dir, file_name)
            with open(final_path, 'wb') as f:
                f.write(response_data)
            
            print(f"S3 file downloaded successfully: {file_name}")
            self.on_file_received(file_name, final_path, len(response_data))
            
        except Exception as error:
            print(f"S3 download failed for {file_name}: {error}")
    
    async def download_from_url(self, url, timeout=120):
        timeout_obj = aiohttp.ClientTimeout(total=timeout)
        
        async with aiohttp.ClientSession(timeout=timeout_obj) as session:
            async with session.get(url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}: {response.reason}")
                
                return await response.read()
    
    async def handle_transfer_error(self, file_name, error):
        download = self.active_downloads.get(file_name)
        if not download:
            return
        
        download['retry_count'] += 1
        
        if download['retry_count'] <= self.max_retries:
            print(f"Retrying transfer for {file_name} (attempt {download['retry_count']})")
            
            # 再送要求
            await self.request_file_retransfer(file_name)
        else:
            print(f"Max retries exceeded for {file_name}")
            if file_name in self.active_downloads:
                del self.active_downloads[file_name]
            
            # エラー通知
            self.on_transfer_failed(file_name, error)
    
    async def request_file_retransfer(self, file_name):
        device_id = self.mqtt_client.client_id
        
        self.mqtt_client.publish(
            f'files/{device_id}/retry',
            json.dumps({
                'fileName': file_name,
                'reason': 'transfer_error',
                'timestamp': datetime.now().isoformat()
            }),
            qos=1
        )
    
    def on_file_received(self, file_name, file_path, file_size):
        print(f"File received event: {file_name}")
        
        # ファイルタイプに応じた処理
        if 'firmware' in file_name:
            asyncio.create_task(self.handle_firmware_update(file_path))
        elif 'config' in file_name:
            self.handle_config_update(file_path)
        elif 'model' in file_name:
            self.handle_ml_model_update(file_path)
    
    async def handle_firmware_update(self, file_path):
        print(f"Processing firmware update: {file_path}")
        
        try:
            # ファームウェア検証
            is_valid = await self.validate_firmware(file_path)
            if not is_valid:
                raise Exception('Firmware validation failed')
            
            # 現在のファームウェアのバックアップ
            await self.backup_current_firmware()
            
            # ファームウェア適用
            await self.apply_firmware(file_path)
            
            # 更新完了通知
            await self.report_firmware_update_status('success')
            
            print('Firmware update completed successfully')
            
        except Exception as error:
            print(f'Firmware update failed: {error}')
            await self.report_firmware_update_status('failed', str(error))
    
    async def validate_firmware(self, file_path):
        # ファームウェア固有の検証ロジック
        # - デジタル署名検証
        # - ハードウェア互換性チェック
        # - バージョン確認
        return True  # 簡略化
    
    async def apply_firmware(self, file_path):
        # プラットフォーム固有のファームウェア適用
        print('Applying firmware...')
        
        # シミュレーション
        await asyncio.sleep(5)
        
        print('Firmware applied, rebooting...')
        # 実際の環境では os._exit() やシステム再起動
    
    async def report_firmware_update_status(self, status, error=None):
        device_id = self.mqtt_client.client_id
        
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