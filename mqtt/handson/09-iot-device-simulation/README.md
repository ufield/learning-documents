# ハンズオン 09: IoTデバイスシミュレーション

## 🎯 学習目標

このハンズオンでは実践的なIoTシステムを構築します：

- 複数の仮想IoTデバイスの作成とシミュレーション
- リアルなセンサーデータの生成とパターン化
- デバイス管理とファームウェア更新のシミュレーション
- エラー処理と復旧機能の実装
- 大規模IoTシステムの運用課題の理解

**所要時間**: 約90分

## 📋 前提条件

- これまでのハンズオンの完了
- Node.js/Pythonの中級レベルの知識
- ファイルシステムとJSON操作の理解

## 🏭 IoTシミュレーションアーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Device Farm   │───▶│  MQTT Broker    │◀───│ Management App  │
│                 │    │                 │    │                 │
│ • Temperature   │    │ • Message       │    │ • Monitoring    │
│ • Humidity      │    │   Routing       │    │ • Control       │
│ • Pressure      │    │ • QoS Handling  │    │ • Analytics     │
│ • Motion        │    │ • Persistence   │    │ • Alerts        │
│ • GPS Tracker   │    └─────────────────┘    └─────────────────┘
└─────────────────┘
```

## 📝 実装演習

### Exercise 1: IoTデバイスシミュレーター基盤

`src/iot-device-simulator.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');
const fs = require('fs').promises;
const path = require('path');

class IoTDevice {
    constructor(config) {
        this.deviceId = config.deviceId;
        this.deviceType = config.deviceType;
        this.location = config.location;
        this.reportInterval = config.reportInterval || 30000; // 30秒
        this.errorRate = config.errorRate || 0.02; // 2%エラー率
        
        // デバイス状態
        this.isOnline = false;
        this.batteryLevel = 100;
        this.firmwareVersion = '1.0.0';
        this.lastSeen = null;
        
        // センサーデータ生成用
        this.sensorState = this.initializeSensorState();
        
        // MQTT設定
        this.client = mqtt.connect('mqtt://localhost:1883', {
            clientId: this.deviceId,
            clean: false, // セッション保持
            keepalive: 60,
            will: {
                topic: `devices/${this.deviceId}/status`,
                payload: JSON.stringify({
                    status: 'offline',
                    timestamp: new Date().toISOString(),
                    reason: 'unexpected_disconnect'
                }),
                qos: 1,
                retain: true
            }
        });
        
        this.setupMQTTHandlers();
        this.reportTimer = null;
    }
    
    initializeSensorState() {
        const states = {
            temperature: {
                value: 20 + Math.random() * 10, // 20-30度
                trend: 0,
                noise: 0.5
            },
            humidity: {
                value: 40 + Math.random() * 20, // 40-60%
                trend: 0,
                noise: 2
            },
            pressure: {
                value: 1013 + Math.random() * 20, // 1013-1033 hPa
                trend: 0,
                noise: 1
            }
        };
        
        // デバイスタイプ別の特別なセンサー
        if (this.deviceType === 'motion') {
            states.motion = {
                detected: false,
                lastDetected: null
            };
        } else if (this.deviceType === 'gps') {
            states.location = {
                latitude: 35.6762 + (Math.random() - 0.5) * 0.1, // 東京周辺
                longitude: 139.6503 + (Math.random() - 0.5) * 0.1,
                altitude: Math.random() * 100,
                speed: 0
            };
        }
        
        return states;
    }
    
    setupMQTTHandlers() {
        this.client.on('connect', () => {
            this.isOnline = true;
            this.lastSeen = new Date().toISOString();
            
            console.log(chalk.green(`🟢 Device ${this.deviceId} connected`));
            
            // デバイス管理トピックを購読
            this.subscribeToManagementTopics();
            
            // オンライン状態を報告
            this.reportStatus('online');
            
            // 定期報告開始
            this.startPeriodicReporting();
        });
        
        this.client.on('message', (topic, message) => {
            this.handleCommand(topic, message);
        });
        
        this.client.on('error', (error) => {
            console.error(chalk.red(`❌ Device ${this.deviceId} error:`), error.message);
        });
        
        this.client.on('offline', () => {
            this.isOnline = false;
            console.log(chalk.yellow(`🟡 Device ${this.deviceId} went offline`));
            this.stopPeriodicReporting();
        });
    }
    
    subscribeToManagementTopics() {
        const topics = [
            `devices/${this.deviceId}/commands/+`,
            `devices/broadcast/+`,
            `firmware/${this.deviceType}/+`
        ];
        
        topics.forEach(topic => {
            this.client.subscribe(topic, { qos: 1 });
        });
    }
    
    handleCommand(topic, message) {
        try {
            const command = JSON.parse(message.toString());
            const topicParts = topic.split('/');
            const commandType = topicParts[topicParts.length - 1];
            
            console.log(chalk.blue(`📡 Device ${this.deviceId} received command: ${commandType}`));
            
            switch (commandType) {
                case 'reboot':
                    this.handleReboot(command);
                    break;
                case 'update_interval':
                    this.handleUpdateInterval(command);
                    break;
                case 'firmware_update':
                    this.handleFirmwareUpdate(command);
                    break;
                case 'calibrate':
                    this.handleCalibrate(command);
                    break;
                default:
                    console.log(chalk.yellow(`⚠️  Unknown command: ${commandType}`));
            }
        } catch (error) {
            console.error(chalk.red(`❌ Command parsing error: ${error.message}`));
        }
    }
    
    async handleReboot(command) {
        console.log(chalk.yellow(`🔄 Device ${this.deviceId} rebooting...`));
        
        // オフライン状態を報告
        this.reportStatus('rebooting');
        
        // 接続を一時的に切断
        this.client.end();
        
        // 3-10秒のランダムな再起動時間
        const rebootTime = 3000 + Math.random() * 7000;
        
        setTimeout(() => {
            // 再接続
            this.client.reconnect();
            console.log(chalk.green(`✅ Device ${this.deviceId} rebooted successfully`));
        }, rebootTime);
    }
    
    handleUpdateInterval(command) {
        const newInterval = command.interval * 1000; // 秒をミリ秒に変換
        
        if (newInterval >= 5000 && newInterval <= 300000) { // 5秒-5分の範囲
            this.reportInterval = newInterval;
            console.log(chalk.green(`✅ Device ${this.deviceId} interval updated to ${command.interval}s`));
            
            // 定期報告を再開
            this.stopPeriodicReporting();
            this.startPeriodicReporting();
            
            // 確認応答
            this.client.publish(`devices/${this.deviceId}/responses/update_interval`, 
                JSON.stringify({
                    success: true,
                    newInterval: command.interval,
                    timestamp: new Date().toISOString()
                }), { qos: 1 });
        } else {
            console.log(chalk.red(`❌ Invalid interval: ${command.interval}s`));
        }
    }
    
    async handleFirmwareUpdate(command) {
        console.log(chalk.blue(`📦 Device ${this.deviceId} starting firmware update...`));
        
        // ファームウェア更新シミュレーション
        const updateSteps = [
            'Downloading firmware',
            'Verifying checksum', 
            'Backing up current firmware',
            'Installing new firmware',
            'Rebooting device'
        ];
        
        for (let i = 0; i < updateSteps.length; i++) {
            const step = updateSteps[i];
            const progress = ((i + 1) / updateSteps.length) * 100;
            
            console.log(chalk.blue(`📦 ${step}... (${progress.toFixed(0)}%)`));
            
            // 進捗を報告
            this.client.publish(`devices/${this.deviceId}/firmware_update_progress`,
                JSON.stringify({
                    step: step,
                    progress: progress,
                    timestamp: new Date().toISOString()
                }), { qos: 1 });
                
            // 各ステップに時間をかける
            await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));
            
            // 10%の確率で失敗シミュレーション
            if (Math.random() < 0.1 && i === 3) {
                console.log(chalk.red(`❌ Firmware update failed at step: ${step}`));
                this.client.publish(`devices/${this.deviceId}/firmware_update_result`,
                    JSON.stringify({
                        success: false,
                        error: `Failed at: ${step}`,
                        timestamp: new Date().toISOString()
                    }), { qos: 1 });
                return;
            }
        }
        
        // 成功時
        this.firmwareVersion = command.version;
        console.log(chalk.green(`✅ Device ${this.deviceId} firmware updated to ${command.version}`));
        
        this.client.publish(`devices/${this.deviceId}/firmware_update_result`,
            JSON.stringify({
                success: true,
                oldVersion: '1.0.0',
                newVersion: command.version,
                timestamp: new Date().toISOString()
            }), { qos: 1 });
    }
    
    handleCalibrate(command) {
        console.log(chalk.blue(`🔧 Device ${this.deviceId} calibrating sensors...`));
        
        // センサーキャリブレーション
        Object.keys(this.sensorState).forEach(sensorType => {
            if (command.sensors && command.sensors[sensorType]) {
                const calibration = command.sensors[sensorType];
                if (this.sensorState[sensorType].value !== undefined) {
                    this.sensorState[sensorType].value += calibration.offset || 0;
                }
            }
        });
        
        console.log(chalk.green(`✅ Device ${this.deviceId} calibration completed`));
        
        // 校正結果を報告
        this.client.publish(`devices/${this.deviceId}/responses/calibrate`,
            JSON.stringify({
                success: true,
                calibratedSensors: Object.keys(command.sensors || {}),
                timestamp: new Date().toISOString()
            }), { qos: 1 });
    }
    
    startPeriodicReporting() {
        if (this.reportTimer) {
            clearInterval(this.reportTimer);
        }
        
        this.reportTimer = setInterval(() => {
            this.generateAndSendSensorData();
        }, this.reportInterval);
    }
    
    stopPeriodicReporting() {
        if (this.reportTimer) {
            clearInterval(this.reportTimer);
            this.reportTimer = null;
        }
    }
    
    generateAndSendSensorData() {
        // バッテリー消耗シミュレーション
        this.batteryLevel = Math.max(0, this.batteryLevel - 0.01);
        this.lastSeen = new Date().toISOString();
        
        // エラー発生シミュレーション
        if (Math.random() < this.errorRate) {
            this.sendErrorReport();
            return;
        }
        
        // センサーデータ生成
        const sensorData = this.generateSensorData();
        
        // データ送信
        this.sendSensorData(sensorData);
        
        // 低バッテリー警告
        if (this.batteryLevel < 20) {
            this.sendLowBatteryAlert();
        }
    }
    
    generateSensorData() {
        const data = {
            deviceId: this.deviceId,
            deviceType: this.deviceType,
            location: this.location,
            timestamp: new Date().toISOString(),
            batteryLevel: this.batteryLevel,
            firmwareVersion: this.firmwareVersion
        };
        
        // 基本センサーデータの生成
        ['temperature', 'humidity', 'pressure'].forEach(sensorType => {
            if (this.sensorState[sensorType]) {
                const sensor = this.sensorState[sensorType];
                
                // トレンド変化
                sensor.trend += (Math.random() - 0.5) * 0.1;
                sensor.trend = Math.max(-1, Math.min(1, sensor.trend));
                
                // 値の更新（トレンド + ノイズ）
                sensor.value += sensor.trend + (Math.random() - 0.5) * sensor.noise;
                
                // 範囲制限
                if (sensorType === 'temperature') {
                    sensor.value = Math.max(-10, Math.min(50, sensor.value));
                } else if (sensorType === 'humidity') {
                    sensor.value = Math.max(0, Math.min(100, sensor.value));
                } else if (sensorType === 'pressure') {
                    sensor.value = Math.max(980, Math.min(1050, sensor.value));
                }
                
                data[sensorType] = parseFloat(sensor.value.toFixed(2));
            }
        });
        
        // デバイス固有のデータ
        if (this.deviceType === 'motion') {
            const motionDetected = Math.random() < 0.1; // 10%の確率で動きを検知
            data.motionDetected = motionDetected;
            if (motionDetected) {
                this.sensorState.motion.lastDetected = data.timestamp;
                data.lastMotionTime = data.timestamp;
            }
        } else if (this.deviceType === 'gps') {
            const location = this.sensorState.location;
            
            // GPS位置の微小変動（歩行シミュレーション）
            location.latitude += (Math.random() - 0.5) * 0.0001;
            location.longitude += (Math.random() - 0.5) * 0.0001;
            location.speed = Math.random() * 5; // 0-5 km/h
            
            data.gps = {
                latitude: parseFloat(location.latitude.toFixed(6)),
                longitude: parseFloat(location.longitude.toFixed(6)),
                altitude: parseFloat(location.altitude.toFixed(1)),
                speed: parseFloat(location.speed.toFixed(1))
            };
        }
        
        return data;
    }
    
    sendSensorData(data) {
        const topic = `sensors/${this.deviceType}/${this.deviceId}/data`;
        
        this.client.publish(topic, JSON.stringify(data), { qos: 1 }, (error) => {
            if (error) {
                console.error(chalk.red(`❌ Failed to send data from ${this.deviceId}`), error);
            } else {
                console.log(chalk.gray(`📊 Data sent from ${this.deviceId}: T:${data.temperature}°C`));
            }
        });
    }
    
    sendErrorReport() {
        const errorTypes = [
            'sensor_read_failed',
            'low_battery',
            'network_instability',
            'memory_overflow',
            'temperature_out_of_range'
        ];
        
        const errorReport = {
            deviceId: this.deviceId,
            errorType: errorTypes[Math.floor(Math.random() * errorTypes.length)],
            timestamp: new Date().toISOString(),
            batteryLevel: this.batteryLevel,
            details: `Error occurred during normal operation`
        };
        
        this.client.publish(`devices/${this.deviceId}/errors`, JSON.stringify(errorReport), { qos: 1 });
        console.log(chalk.red(`🚨 Error reported from ${this.deviceId}: ${errorReport.errorType}`));
    }
    
    sendLowBatteryAlert() {
        const alert = {
            deviceId: this.deviceId,
            alertType: 'low_battery',
            batteryLevel: this.batteryLevel,
            timestamp: new Date().toISOString(),
            severity: this.batteryLevel < 10 ? 'critical' : 'warning'
        };
        
        this.client.publish(`alerts/low_battery/${this.deviceId}`, JSON.stringify(alert), { qos: 1 });
        console.log(chalk.yellow(`🪫 Low battery alert from ${this.deviceId}: ${this.batteryLevel}%`));
    }
    
    reportStatus(status) {
        const statusReport = {
            deviceId: this.deviceId,
            status: status,
            timestamp: new Date().toISOString(),
            batteryLevel: this.batteryLevel,
            firmwareVersion: this.firmwareVersion
        };
        
        this.client.publish(`devices/${this.deviceId}/status`, JSON.stringify(statusReport), { 
            qos: 1, 
            retain: true 
        });
    }
    
    async saveState() {
        const state = {
            deviceId: this.deviceId,
            deviceType: this.deviceType,
            location: this.location,
            isOnline: this.isOnline,
            batteryLevel: this.batteryLevel,
            firmwareVersion: this.firmwareVersion,
            lastSeen: this.lastSeen,
            sensorState: this.sensorState,
            reportInterval: this.reportInterval
        };
        
        try {
            const stateDir = './device_states';
            await fs.mkdir(stateDir, { recursive: true });
            
            const statePath = path.join(stateDir, `${this.deviceId}.json`);
            await fs.writeFile(statePath, JSON.stringify(state, null, 2));
        } catch (error) {
            console.error(chalk.red(`❌ Failed to save state for ${this.deviceId}:`, error.message));
        }
    }
    
    disconnect() {
        this.stopPeriodicReporting();
        this.reportStatus('offline');
        
        setTimeout(() => {
            this.client.end();
            console.log(chalk.yellow(`👋 Device ${this.deviceId} disconnected`));
        }, 1000);
    }
}

// デバイスファーム管理クラス
class IoTDeviceFarm {
    constructor() {
        this.devices = new Map();
        this.isRunning = false;
    }
    
    createDevice(config) {
        const device = new IoTDevice(config);
        this.devices.set(config.deviceId, device);
        return device;
    }
    
    createDeviceFarm(farmConfig) {
        console.log(chalk.blue(`🏭 Creating IoT device farm with ${farmConfig.deviceCount} devices`));
        
        const deviceTypes = ['temperature', 'motion', 'gps', 'environmental'];
        const locations = ['Building-A', 'Building-B', 'Warehouse', 'Factory-Floor', 'Office'];
        
        for (let i = 0; i < farmConfig.deviceCount; i++) {
            const deviceType = deviceTypes[i % deviceTypes.length];
            const location = locations[i % locations.length];
            
            const config = {
                deviceId: `${deviceType}-${String(i + 1).padStart(3, '0')}`,
                deviceType: deviceType,
                location: `${location}-${Math.floor(i / locations.length) + 1}`,
                reportInterval: 20000 + Math.random() * 20000, // 20-40秒
                errorRate: 0.01 + Math.random() * 0.02 // 1-3%
            };
            
            this.createDevice(config);
        }
        
        console.log(chalk.green(`✅ Created ${this.devices.size} IoT devices`));
    }
    
    start() {
        this.isRunning = true;
        console.log(chalk.green('🟢 IoT Device Farm started'));
        
        // 定期的に状態を保存
        this.stateInterval = setInterval(() => {
            this.saveAllStates();
        }, 60000); // 1分間隔
    }
    
    stop() {
        this.isRunning = false;
        
        if (this.stateInterval) {
            clearInterval(this.stateInterval);
        }
        
        console.log(chalk.yellow('🟡 Stopping all devices...'));
        
        Array.from(this.devices.values()).forEach(device => {
            device.disconnect();
        });
        
        console.log(chalk.red('🔴 IoT Device Farm stopped'));
    }
    
    async saveAllStates() {
        const savePromises = Array.from(this.devices.values()).map(device => 
            device.saveState()
        );
        
        try {
            await Promise.all(savePromises);
            console.log(chalk.gray(`💾 Saved states for ${this.devices.size} devices`));
        } catch (error) {
            console.error(chalk.red('❌ Failed to save device states:', error.message));
        }
    }
    
    getStatus() {
        const onlineDevices = Array.from(this.devices.values()).filter(device => device.isOnline);
        
        return {
            totalDevices: this.devices.size,
            onlineDevices: onlineDevices.length,
            offlineDevices: this.devices.size - onlineDevices.length,
            isRunning: this.isRunning
        };
    }
}

// 実行部分
if (require.main === module) {
    const deviceFarm = new IoTDeviceFarm();
    
    // 設定
    const farmConfig = {
        deviceCount: parseInt(process.argv[2]) || 10
    };
    
    // デバイスファームの作成と開始
    deviceFarm.createDeviceFarm(farmConfig);
    deviceFarm.start();
    
    // 終了処理
    process.on('SIGINT', () => {
        console.log(chalk.yellow('\n👋 Gracefully shutting down device farm...'));
        deviceFarm.stop();
        
        setTimeout(() => {
            process.exit(0);
        }, 3000);
    });
    
    // 定期的な状態表示
    setInterval(() => {
        const status = deviceFarm.getStatus();
        console.log(chalk.blue(`📊 Farm Status: ${status.onlineDevices}/${status.totalDevices} devices online`));
    }, 30000);
}

module.exports = { IoTDevice, IoTDeviceFarm };
```

### Exercise 2: デバイス管理アプリケーション

`src/device-manager.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');
const readline = require('readline');

class IoTDeviceManager {
    constructor() {
        this.client = mqtt.connect('mqtt://localhost:1883', {
            clientId: 'device-manager',
            clean: true
        });
        
        this.devices = new Map();
        this.setupMQTTHandlers();
        this.setupCLI();
    }
    
    setupMQTTHandlers() {
        this.client.on('connect', () => {
            console.log(chalk.green('🎛️  Device Manager connected'));
            this.subscribeToDeviceTopics();
        });
        
        this.client.on('message', (topic, message) => {
            this.handleDeviceMessage(topic, message);
        });
    }
    
    subscribeToDeviceTopics() {
        const topics = [
            'devices/+/status',
            'sensors/+/+/data', 
            'devices/+/errors',
            'alerts/+/+',
            'devices/+/responses/+',
            'devices/+/firmware_update_progress',
            'devices/+/firmware_update_result'
        ];
        
        topics.forEach(topic => {
            this.client.subscribe(topic, { qos: 1 });
        });
        
        console.log(chalk.blue('📡 Subscribed to device management topics'));
    }
    
    handleDeviceMessage(topic, message) {
        try {
            const data = JSON.parse(message.toString());
            const topicParts = topic.split('/');
            
            if (topic.includes('/status')) {
                this.updateDeviceStatus(data);
            } else if (topic.includes('/data')) {
                this.processSensorData(topicParts, data);
            } else if (topic.includes('/errors')) {
                this.handleDeviceError(data);
            } else if (topic.includes('/alerts/')) {
                this.handleAlert(topicParts, data);
            } else if (topic.includes('/responses/')) {
                this.handleCommandResponse(topicParts, data);
            } else if (topic.includes('/firmware_update')) {
                this.handleFirmwareUpdate(topicParts, data);
            }
        } catch (error) {
            console.error(chalk.red('❌ Message parsing error:'), error.message);
        }
    }
    
    updateDeviceStatus(statusData) {
        const deviceId = statusData.deviceId;
        
        if (!this.devices.has(deviceId)) {
            this.devices.set(deviceId, {
                deviceId: deviceId,
                firstSeen: new Date().toISOString(),
                messageCount: 0,
                errors: [],
                alerts: []
            });
        }
        
        const device = this.devices.get(deviceId);
        Object.assign(device, statusData);
        
        const statusColor = statusData.status === 'online' ? 'green' : 
                           statusData.status === 'offline' ? 'red' : 'yellow';
        
        console.log(chalk[statusColor](`📱 Device ${deviceId}: ${statusData.status}`));
    }
    
    processSensorData(topicParts, data) {
        const deviceId = data.deviceId;
        
        if (this.devices.has(deviceId)) {
            const device = this.devices.get(deviceId);
            device.messageCount++;
            device.lastData = data;
            device.lastSeen = data.timestamp;
            
            // 異常値の検知
            this.checkAnomalyValues(data);
        }
    }
    
    checkAnomalyValues(data) {
        const anomalies = [];
        
        if (data.temperature && (data.temperature < -5 || data.temperature > 45)) {
            anomalies.push(`Temperature: ${data.temperature}°C`);
        }
        
        if (data.humidity && (data.humidity < 10 || data.humidity > 95)) {
            anomalies.push(`Humidity: ${data.humidity}%`);
        }
        
        if (data.batteryLevel && data.batteryLevel < 15) {
            anomalies.push(`Low battery: ${data.batteryLevel}%`);
        }
        
        if (anomalies.length > 0) {
            console.log(chalk.yellow(`⚠️  Anomaly detected in ${data.deviceId}:`));
            anomalies.forEach(anomaly => {
                console.log(chalk.yellow(`   - ${anomaly}`));
            });
        }
    }
    
    handleDeviceError(errorData) {
        console.log(chalk.red(`🚨 Device Error: ${errorData.deviceId}`));
        console.log(chalk.red(`   Type: ${errorData.errorType}`));
        console.log(chalk.red(`   Time: ${errorData.timestamp}`));
        
        if (this.devices.has(errorData.deviceId)) {
            const device = this.devices.get(errorData.deviceId);
            device.errors.push(errorData);
            
            // エラーが頻発している場合は警告
            const recentErrors = device.errors.filter(error => 
                new Date(error.timestamp) > new Date(Date.now() - 300000) // 5分以内
            );
            
            if (recentErrors.length > 3) {
                console.log(chalk.red(`🔥 Multiple errors from ${errorData.deviceId} - requires attention`));
            }
        }
    }
    
    handleAlert(topicParts, alertData) {
        const alertType = topicParts[1];
        
        console.log(chalk.yellow(`🚨 ALERT [${alertType}]: ${alertData.deviceId}`));
        console.log(chalk.yellow(`   Severity: ${alertData.severity}`));
        
        if (this.devices.has(alertData.deviceId)) {
            const device = this.devices.get(alertData.deviceId);
            device.alerts.push(alertData);
        }
    }
    
    handleCommandResponse(topicParts, responseData) {
        const command = topicParts[3];
        console.log(chalk.blue(`📋 Command Response [${command}]: ${responseData.deviceId}`));
        console.log(chalk.blue(`   Success: ${responseData.success}`));
    }
    
    handleFirmwareUpdate(topicParts, updateData) {
        const updateType = topicParts[3];
        
        if (updateType === 'progress') {
            console.log(chalk.blue(`📦 Firmware Update Progress: ${updateData.deviceId}`));
            console.log(chalk.blue(`   ${updateData.step}: ${updateData.progress}%`));
        } else if (updateType === 'result') {
            const status = updateData.success ? 'SUCCESS' : 'FAILED';
            const color = updateData.success ? 'green' : 'red';
            
            console.log(chalk[color](`📦 Firmware Update ${status}: ${updateData.deviceId}`));
            if (updateData.success) {
                console.log(chalk.green(`   Updated to version: ${updateData.newVersion}`));
            } else {
                console.log(chalk.red(`   Error: ${updateData.error}`));
            }
        }
    }
    
    setupCLI() {
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            prompt: chalk.blue('DeviceManager> ')
        });
        
        this.rl.on('line', (input) => {
            this.handleCommand(input.trim());
        });
        
        // 初期プロンプト表示
        setTimeout(() => {
            console.log(chalk.yellow('\n🎛️  IoT Device Manager CLI'));
            console.log(chalk.gray('Type "help" for available commands\n'));
            this.rl.prompt();
        }, 2000);
    }
    
    handleCommand(input) {
        const [command, ...args] = input.split(' ');
        
        switch (command.toLowerCase()) {
            case 'help':
                this.showHelp();
                break;
            case 'list':
                this.listDevices();
                break;
            case 'status':
                this.showDeviceStatus(args[0]);
                break;
            case 'reboot':
                this.rebootDevice(args[0]);
                break;
            case 'interval':
                this.updateReportInterval(args[0], parseInt(args[1]));
                break;
            case 'firmware':
                this.updateFirmware(args[0], args[1]);
                break;
            case 'calibrate':
                this.calibrateDevice(args[0]);
                break;
            case 'broadcast':
                this.broadcastCommand(args[0], args.slice(1));
                break;
            case 'stats':
                this.showSystemStats();
                break;
            case 'errors':
                this.showRecentErrors();
                break;
            case 'alerts':
                this.showRecentAlerts();
                break;
            case 'quit':
                this.quit();
                return;
            default:
                console.log(chalk.red(`❌ Unknown command: ${command}`));
                console.log(chalk.gray('Type "help" for available commands'));
        }
        
        this.rl.prompt();
    }
    
    showHelp() {
        console.log(chalk.blue('\n📖 Available Commands:'));
        console.log('  help                     - Show this help');
        console.log('  list                     - List all devices');  
        console.log('  status <deviceId>        - Show device details');
        console.log('  reboot <deviceId>        - Reboot a device');
        console.log('  interval <deviceId> <sec> - Update report interval');
        console.log('  firmware <deviceId> <ver> - Update firmware');
        console.log('  calibrate <deviceId>     - Calibrate sensors');
        console.log('  broadcast <command>      - Send command to all devices');
        console.log('  stats                    - Show system statistics');
        console.log('  errors                   - Show recent errors');
        console.log('  alerts                   - Show recent alerts');
        console.log('  quit                     - Exit manager\n');
    }
    
    listDevices() {
        if (this.devices.size === 0) {
            console.log(chalk.yellow('📱 No devices found'));
            return;
        }
        
        console.log(chalk.blue(`\n📱 Devices (${this.devices.size} total):`));
        console.log(chalk.gray('ID'.padEnd(20) + 'Status'.padEnd(12) + 'Battery'.padEnd(10) + 'Messages'.padEnd(10) + 'Last Seen'));
        console.log(chalk.gray('-'.repeat(80)));
        
        Array.from(this.devices.values()).forEach(device => {
            const status = device.status || 'unknown';
            const battery = device.batteryLevel ? `${device.batteryLevel.toFixed(1)}%` : 'N/A';
            const messages = device.messageCount || 0;
            const lastSeen = device.lastSeen ? new Date(device.lastSeen).toLocaleTimeString() : 'Never';
            
            const statusColor = status === 'online' ? 'green' : 
                               status === 'offline' ? 'red' : 'yellow';
            
            console.log(
                device.deviceId.padEnd(20) + 
                chalk[statusColor](status.padEnd(12)) +
                battery.padEnd(10) +
                messages.toString().padEnd(10) +
                lastSeen
            );
        });
    }
    
    showDeviceStatus(deviceId) {
        if (!deviceId) {
            console.log(chalk.red('❌ Please specify a device ID'));
            return;
        }
        
        const device = this.devices.get(deviceId);
        if (!device) {
            console.log(chalk.red(`❌ Device not found: ${deviceId}`));
            return;
        }
        
        console.log(chalk.blue(`\n📱 Device Details: ${deviceId}`));
        console.log(`Status: ${device.status || 'unknown'}`);
        console.log(`Battery: ${device.batteryLevel ? device.batteryLevel.toFixed(1) + '%' : 'N/A'}`);
        console.log(`Firmware: ${device.firmwareVersion || 'N/A'}`);
        console.log(`Messages: ${device.messageCount || 0}`);
        console.log(`First Seen: ${device.firstSeen ? new Date(device.firstSeen).toLocaleString() : 'N/A'}`);
        console.log(`Last Seen: ${device.lastSeen ? new Date(device.lastSeen).toLocaleString() : 'Never'}`);
        
        if (device.lastData) {
            console.log('\nLast Sensor Data:');
            Object.entries(device.lastData).forEach(([key, value]) => {
                if (key !== 'deviceId' && key !== 'timestamp') {
                    console.log(`  ${key}: ${JSON.stringify(value)}`);
                }
            });
        }
        
        if (device.errors && device.errors.length > 0) {
            console.log(chalk.red(`\nRecent Errors (${device.errors.length}):`));
            device.errors.slice(-5).forEach(error => {
                console.log(chalk.red(`  ${error.errorType} - ${new Date(error.timestamp).toLocaleString()}`));
            });
        }
    }
    
    rebootDevice(deviceId) {
        if (!deviceId) {
            console.log(chalk.red('❌ Please specify a device ID'));
            return;
        }
        
        console.log(chalk.blue(`🔄 Sending reboot command to ${deviceId}`));
        
        const command = {
            timestamp: new Date().toISOString(),
            requestId: `reboot_${Date.now()}`
        };
        
        this.client.publish(`devices/${deviceId}/commands/reboot`, JSON.stringify(command), { qos: 1 });
    }
    
    updateReportInterval(deviceId, intervalSeconds) {
        if (!deviceId || !intervalSeconds) {
            console.log(chalk.red('❌ Usage: interval <deviceId> <seconds>'));
            return;
        }
        
        if (intervalSeconds < 5 || intervalSeconds > 300) {
            console.log(chalk.red('❌ Interval must be between 5 and 300 seconds'));
            return;
        }
        
        console.log(chalk.blue(`⏱️  Updating report interval for ${deviceId} to ${intervalSeconds}s`));
        
        const command = {
            interval: intervalSeconds,
            timestamp: new Date().toISOString()
        };
        
        this.client.publish(`devices/${deviceId}/commands/update_interval`, JSON.stringify(command), { qos: 1 });
    }
    
    updateFirmware(deviceId, version) {
        if (!deviceId || !version) {
            console.log(chalk.red('❌ Usage: firmware <deviceId> <version>'));
            return;
        }
        
        console.log(chalk.blue(`📦 Starting firmware update for ${deviceId} to version ${version}`));
        
        const command = {
            version: version,
            downloadUrl: `https://firmware.example.com/${version}.bin`,
            checksum: 'sha256:example_checksum',
            timestamp: new Date().toISOString()
        };
        
        this.client.publish(`devices/${deviceId}/commands/firmware_update`, JSON.stringify(command), { qos: 1 });
    }
    
    showSystemStats() {
        const totalDevices = this.devices.size;
        const onlineDevices = Array.from(this.devices.values()).filter(d => d.status === 'online').length;
        const devicesWithErrors = Array.from(this.devices.values()).filter(d => d.errors && d.errors.length > 0).length;
        const totalMessages = Array.from(this.devices.values()).reduce((sum, d) => sum + (d.messageCount || 0), 0);
        
        console.log(chalk.blue('\n📊 System Statistics:'));
        console.log(`Total Devices: ${totalDevices}`);
        console.log(`Online Devices: ${onlineDevices}`);
        console.log(`Offline Devices: ${totalDevices - onlineDevices}`);
        console.log(`Devices with Errors: ${devicesWithErrors}`);
        console.log(`Total Messages: ${totalMessages}`);
    }
    
    quit() {
        console.log(chalk.yellow('\n👋 Device Manager shutting down...'));
        this.rl.close();
        this.client.end();
        process.exit(0);
    }
}

// 実行
if (require.main === module) {
    new IoTDeviceManager();
}

module.exports = IoTDeviceManager;
```

## 🎯 練習問題

### 問題1: デバイス起動とモニタリング
1. `iot-device-simulator.js`を使って10台のデバイスを起動してください
2. `device-manager.js`で各デバイスの状態を監視してください
3. いくつかのデバイスをリブートして、状態変化を観察してください

### 問題2: ファームウェア更新
1. デバイスマネージャーから特定のデバイスのファームウェアを更新してください
2. 更新プロセスの進捗を観察してください
3. 故意に失敗を発生させて、エラーハンドリングを確認してください

### 問題3: カスタムデバイスタイプ
以下の仕様で新しいデバイスタイプ「smart-meter」を作成してください：
- 電力消費量（kWh）を測定
- 5分間隔でデータ送信
- 使用量が500kWhを超えるとアラート送信
- 料金計算機能（1kWh = 30円）

## ✅ 確認チェックリスト

- [ ] 複数のIoTデバイスをシミュレーションできた
- [ ] リアルタイムでデバイス状態を監視できた
- [ ] デバイス管理コマンドを実行できた
- [ ] ファームウェア更新プロセスを理解した
- [ ] エラーレポートとアラートシステムを確認した
- [ ] デバイス固有のデータ生成を実装できた
- [ ] 大規模IoTシステムの運用課題を理解した

## 🔧 実用的な拡張例

このハンズオンで作成したシミュレーターは、以下のような実用的な拡張が可能です：

### データベース連携
```javascript
// PostgreSQL/InfluxDBへのデータ保存
const { Client } = require('pg');
const client = new Client({
    connectionString: 'postgresql://user:pass@localhost/iotdb'
});

// データ保存
async function saveSensorData(data) {
    await client.query(
        'INSERT INTO sensor_data (device_id, temperature, humidity, timestamp) VALUES ($1, $2, $3, $4)',
        [data.deviceId, data.temperature, data.humidity, data.timestamp]
    );
}
```

### Grafana/Prometheusとの統合
```javascript
// Prometheusメトリクスの出力
const promClient = require('prom-client');

const temperatureGauge = new promClient.Gauge({
    name: 'iot_temperature_celsius',
    help: 'Temperature in Celsius',
    labelNames: ['device_id', 'location']
});

// メトリクスの更新
temperatureGauge.set({
    device_id: data.deviceId,
    location: data.location
}, data.temperature);
```

---

**次のステップ**: [10-monitoring-dashboard](../10-monitoring-dashboard/) で監視ダッシュボードの構築を学習しましょう！