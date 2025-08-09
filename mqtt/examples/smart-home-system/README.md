# Smart Home System - MQTT実装例

## 🏠 概要

このサンプルは、MQTTを使用した完全なスマートホームシステムの実装例です。リアルタイムでのデバイス制御、状態監視、自動化ルールを提供します。

### 主な機能
- **デバイス制御**: 照明、エアコン、スマートプラグの遠隔制御
- **センサー監視**: 温度、湿度、人感センサーからのデータ収集
- **自動化**: 条件に基づく自動制御（例：人がいない時は照明を消す）
- **Webダッシュボード**: リアルタイムでの状態表示と制御
- **モバイル対応**: レスポンシブなWebUI
- **通知システム**: 重要なイベントの通知

## 🏗 システム構成

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Smart Devices │───▶│  MQTT Broker    │◀───│   Web Dashboard │
│                 │    │                 │    │                 │
│ • Smart Lights  │    │ • Eclipse       │    │ • Vue.js        │
│ • Temperature   │    │   Mosquitto     │    │ • Socket.io     │
│ • Motion Sensor │    │ • Port 1883     │    │ • Chart.js      │
│ • Smart Plug    │    │                 │    │ • Bootstrap     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         ▲                        ▲                        │
         │              ┌─────────────────┐                │
         │              │  Backend API    │◀───────────────┘
         │              │                 │
         └──────────────│ • Node.js       │
                        │ • Express       │ 
                        │ • SQLite        │
                        │ • Automation    │
                        └─────────────────┘
```

## 🚀 クイックスタート

### 1. 前提条件
- Node.js 18+
- Docker (MQTTブローカー用)

### 2. MQTTブローカーの起動
```bash
docker run -d --name mosquitto -p 1883:1883 -p 9001:9001 eclipse-mosquitto:2.0
```

### 3. アプリケーションのセットアップ
```bash
# リポジトリのクローン
git clone <repository-url>
cd smart-home-system

# 依存関係のインストール
npm install

# データベースの初期化
npm run init-db

# アプリケーションの起動
npm start
```

### 4. アクセス
- **Webダッシュボード**: http://localhost:3000
- **MQTT Broker**: localhost:1883

## 📱 デバイス シミュレーター

実際のハードウェアがなくても、仮想デバイスでシステムをテストできます。

### デバイスシミュレーターの起動
```bash
# 全デバイスの起動
npm run simulate-devices

# 個別デバイスの起動
node simulators/smart-light.js
node simulators/temperature-sensor.js  
node simulators/motion-sensor.js
node simulators/smart-plug.js
```

### サポートされるデバイスタイプ

#### 1. Smart Light (スマート照明)
```javascript
// トピック構造
home/living-room/light/
├── state          // on/off状態
├── brightness     // 明度 (0-100)
├── color          // RGB色情報
└── command        // 制御コマンド受信
```

#### 2. Temperature Sensor (温度センサー)
```javascript 
// トピック構造
home/living-room/temperature/
├── value          // 温度値
├── humidity       // 湿度値
├── battery        // バッテリー残量
└── status         // センサー状態
```

#### 3. Motion Sensor (人感センサー)
```javascript
// トピック構造  
home/living-room/motion/
├── detected       // 人の検知状態
├── last_motion    // 最後の検知時刻
├── battery        // バッテリー残量
└── sensitivity    // 感度設定
```

#### 4. Smart Plug (スマートプラグ)
```javascript
// トピック構造
home/living-room/plug/
├── state          // on/off状態  
├── power          // 現在の消費電力
├── energy         // 累積電力量
└── command        // 制御コマンド受信
```

## 🎛 Web ダッシュボード

### 機能一覧
- **デバイス一覧**: 全デバイスの状態をリアルタイム表示
- **制御パネル**: デバイスの遠隔制御
- **グラフ表示**: 温度・電力消費のトレンド
- **自動化ルール**: 条件ベースの自動制御設定
- **通知センター**: アラート・イベント履歴

### メイン画面の構成
```html
<!-- index.html -->
<!DOCTYPE html>
<html>
<head>
    <title>Smart Home Dashboard</title>
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.1.3/dist/css/bootstrap.min.css" rel="stylesheet">
    <script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/3.9.1/chart.min.js"></script>
</head>
<body>
    <div id="app">
        <!-- ナビゲーションバー -->
        <nav class="navbar navbar-expand-lg navbar-dark bg-primary">
            <div class="container">
                <a class="navbar-brand" href="#">🏠 Smart Home</a>
                <div class="navbar-nav ms-auto">
                    <span class="nav-text">{{ connectedDevices }} devices connected</span>
                </div>
            </div>
        </nav>
        
        <!-- メインコンテンツ -->
        <div class="container mt-4">
            <div class="row">
                <!-- デバイス制御カード -->
                <div class="col-md-6 col-lg-4" v-for="device in devices" :key="device.id">
                    <div class="card mb-4">
                        <div class="card-header d-flex justify-content-between align-items-center">
                            <h6 class="mb-0">{{ device.name }}</h6>
                            <span :class="deviceStatusClass(device)">{{ device.status }}</span>
                        </div>
                        <div class="card-body">
                            <!-- デバイス固有の制御UI -->
                            <component :is="getDeviceComponent(device.type)" 
                                      :device="device" 
                                      @command="sendCommand">
                            </component>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 環境データグラフ -->
            <div class="row mt-4">
                <div class="col-12">
                    <div class="card">
                        <div class="card-header">
                            <h5>Environmental Data</h5>
                        </div>
                        <div class="card-body">
                            <canvas id="environmentChart"></canvas>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
```

## ⚙️ 自動化システム

### ルール定義例

#### 1. 人感連動照明
```javascript
// automation/motion-light.js
const motionLightRule = {
    name: "Motion-activated lighting",
    trigger: {
        topic: "home/+/motion/detected",
        condition: (message) => message.value === true
    },
    actions: [
        {
            topic: "home/{room}/light/command",
            payload: { state: "on", brightness: 80 }
        }
    ],
    delay: 0
};
```

#### 2. 省エネ自動制御
```javascript  
// automation/energy-saving.js
const energySavingRule = {
    name: "Energy saving mode",
    trigger: {
        topic: "home/+/motion/detected", 
        condition: (message) => message.value === false,
        timeout: 300000 // 5分間人がいない
    },
    actions: [
        {
            topic: "home/{room}/light/command",
            payload: { state: "off" }
        },
        {
            topic: "home/{room}/plug/command",
            payload: { state: "off" }
        }
    ]
};
```

#### 3. 温度連動エアコン制御
```javascript
// automation/temperature-control.js  
const temperatureControlRule = {
    name: "Temperature-based AC control",
    trigger: {
        topic: "home/+/temperature/value",
        condition: (message) => {
            return message.value > 28 || message.value < 18;
        }
    },
    actions: [
        {
            topic: "home/{room}/ac/command",
            payload: (trigger) => ({
                state: "on",
                mode: trigger.value > 28 ? "cool" : "heat",
                temperature: trigger.value > 28 ? 24 : 22
            })
        }
    ]
};
```

### 自動化エンジンの実装
```javascript
// src/automation-engine.js
class AutomationEngine {
    constructor(mqttClient) {
        this.client = mqttClient;
        this.rules = [];
        this.activeTimers = new Map();
        this.setupMQTTHandlers();
    }
    
    addRule(rule) {
        this.rules.push(rule);
        console.log(`Added automation rule: ${rule.name}`);
    }
    
    setupMQTTHandlers() {
        this.client.on('message', (topic, message) => {
            this.processMessage(topic, JSON.parse(message.toString()));
        });
    }
    
    processMessage(topic, message) {
        this.rules.forEach(rule => {
            if (this.matchesTrigger(rule.trigger, topic, message)) {
                if (rule.trigger.timeout) {
                    this.scheduleDelayedAction(rule, topic, message);
                } else {
                    this.executeActions(rule.actions, topic, message);
                }
            }
        });
    }
    
    matchesTrigger(trigger, topic, message) {
        // トピックパターンマッチング
        const topicRegex = trigger.topic.replace(/\+/g, '[^/]+').replace(/#/g, '.*');
        if (!new RegExp(topicRegex).test(topic)) {
            return false;
        }
        
        // 条件チェック
        if (trigger.condition) {
            return trigger.condition(message);
        }
        
        return true;
    }
    
    scheduleDelayedAction(rule, topic, message) {
        const ruleId = `${rule.name}_${topic}`;
        
        // 既存のタイマーをキャンセル
        if (this.activeTimers.has(ruleId)) {
            clearTimeout(this.activeTimers.get(ruleId));
        }
        
        // 新しいタイマーを設定
        const timer = setTimeout(() => {
            this.executeActions(rule.actions, topic, message);
            this.activeTimers.delete(ruleId);
        }, rule.trigger.timeout);
        
        this.activeTimers.set(ruleId, timer);
    }
    
    executeActions(actions, triggerTopic, triggerMessage) {
        actions.forEach(action => {
            let targetTopic = action.topic;
            let payload = action.payload;
            
            // トピックの動的置換
            const roomMatch = triggerTopic.match(/home\/([^\/]+)\//);
            if (roomMatch) {
                targetTopic = targetTopic.replace('{room}', roomMatch[1]);
            }
            
            // ペイロードの動的生成
            if (typeof payload === 'function') {
                payload = payload(triggerMessage);
            }
            
            console.log(`Executing automation action: ${targetTopic}`);
            this.client.publish(targetTopic, JSON.stringify(payload));
        });
    }
}
```

## 📊 データ分析とレポート

### データ収集
```javascript
// src/data-collector.js
class DataCollector {
    constructor(mqttClient, database) {
        this.client = mqttClient;
        this.db = database;
        this.setupDataCollection();
    }
    
    setupDataCollection() {
        // 全デバイスデータの収集
        this.client.subscribe('home/+/+/+');
        
        this.client.on('message', (topic, message) => {
            this.storeData(topic, JSON.parse(message.toString()));
        });
    }
    
    storeData(topic, data) {
        const [, room, device, metric] = topic.split('/');
        
        const record = {
            timestamp: new Date(),
            room: room,
            device: device,
            metric: metric,
            value: data.value || data,
            raw_data: JSON.stringify(data)
        };
        
        this.db.run(`
            INSERT INTO sensor_data (timestamp, room, device, metric, value, raw_data)
            VALUES (?, ?, ?, ?, ?, ?)
        `, [record.timestamp, record.room, record.device, record.metric, record.value, record.raw_data]);
    }
    
    async getEnergyReport(startDate, endDate) {
        return new Promise((resolve, reject) => {
            this.db.all(`
                SELECT 
                    room,
                    device,
                    SUM(CAST(value AS REAL)) as total_energy,
                    AVG(CAST(value AS REAL)) as avg_power,
                    COUNT(*) as data_points
                FROM sensor_data 
                WHERE metric = 'power' 
                    AND timestamp BETWEEN ? AND ?
                GROUP BY room, device
                ORDER BY total_energy DESC
            `, [startDate, endDate], (err, rows) => {
                if (err) reject(err);
                else resolve(rows);
            });
        });
    }
    
    async getTemperatureTrends(room, hours = 24) {
        const startTime = new Date(Date.now() - hours * 60 * 60 * 1000);
        
        return new Promise((resolve, reject) => {
            this.db.all(`
                SELECT 
                    datetime(timestamp) as time,
                    CAST(value AS REAL) as temperature
                FROM sensor_data
                WHERE room = ? 
                    AND metric = 'value'
                    AND device = 'temperature'
                    AND timestamp > ?
                ORDER BY timestamp
            `, [room, startTime], (err, rows) => {
                if (err) reject(err);
                else resolve(rows);
            });
        });
    }
}
```

### エネルギー使用量分析
```javascript
// src/energy-analytics.js
class EnergyAnalytics {
    constructor(dataCollector) {
        this.dataCollector = dataCollector;
    }
    
    async generateDailyReport(date) {
        const startDate = new Date(date);
        startDate.setHours(0, 0, 0, 0);
        
        const endDate = new Date(date);
        endDate.setHours(23, 59, 59, 999);
        
        const energyData = await this.dataCollector.getEnergyReport(startDate, endDate);
        
        const totalEnergy = energyData.reduce((sum, item) => sum + item.total_energy, 0);
        const totalCost = totalEnergy * 0.27; // 27円/kWh
        
        return {
            date: date.toISOString().split('T')[0],
            totalEnergy: totalEnergy.toFixed(2),
            totalCost: totalCost.toFixed(0),
            deviceBreakdown: energyData,
            recommendations: this.generateRecommendations(energyData)
        };
    }
    
    generateRecommendations(energyData) {
        const recommendations = [];
        
        // 高消費デバイスの特定
        const highConsumers = energyData.filter(item => item.total_energy > 5);
        if (highConsumers.length > 0) {
            recommendations.push({
                type: 'warning',
                message: `High energy consumption detected: ${highConsumers.map(d => d.device).join(', ')}`,
                suggestion: 'Consider adjusting usage patterns or device settings'
            });
        }
        
        // 待機電力の検出
        const standbyDevices = energyData.filter(item => 
            item.avg_power > 0 && item.avg_power < 10
        );
        if (standbyDevices.length > 0) {
            recommendations.push({
                type: 'tip',
                message: 'Standby power consumption detected',
                suggestion: 'Use smart plugs to eliminate phantom loads'
            });
        }
        
        return recommendations;
    }
}
```

## 🔔 通知システム

### リアルタイム通知
```javascript
// src/notification-system.js
class NotificationSystem {
    constructor(mqttClient, webSocketServer) {
        this.client = mqttClient;
        this.wsServer = webSocketServer;
        this.setupNotificationHandlers();
    }
    
    setupNotificationHandlers() {
        // 緊急アラートの監視
        this.client.subscribe('alerts/+/+');
        this.client.subscribe('home/+/+/error');
        
        this.client.on('message', (topic, message) => {
            if (topic.startsWith('alerts/')) {
                this.handleAlert(topic, JSON.parse(message.toString()));
            } else if (topic.includes('/error')) {
                this.handleError(topic, JSON.parse(message.toString()));
            }
        });
    }
    
    handleAlert(topic, alertData) {
        const notification = {
            id: Date.now(),
            type: 'alert',
            severity: alertData.severity || 'info',
            title: this.getAlertTitle(topic),
            message: alertData.message || 'Alert triggered',
            timestamp: new Date(),
            data: alertData
        };
        
        // WebSocketでフロントエンドに送信
        this.broadcastNotification(notification);
        
        // 重要度に応じて追加アクション
        if (alertData.severity === 'critical') {
            this.sendEmailAlert(notification);
            this.triggerEmergencyProtocol(alertData);
        }
    }
    
    handleError(topic, errorData) {
        const [, room, device] = topic.split('/');
        
        const notification = {
            id: Date.now(),
            type: 'error',
            severity: 'warning',
            title: `Device Error: ${device}`,
            message: `${device} in ${room} reported an error`,
            timestamp: new Date(),
            data: errorData
        };
        
        this.broadcastNotification(notification);
    }
    
    broadcastNotification(notification) {
        this.wsServer.emit('notification', notification);
        console.log(`📢 Notification: ${notification.title}`);
    }
    
    getAlertTitle(topic) {
        const alertType = topic.split('/')[1];
        const titleMap = {
            'fire': '🔥 Fire Alarm',
            'security': '🔒 Security Alert',
            'energy': '⚡ Energy Alert',
            'temperature': '🌡️ Temperature Alert',
            'motion': '👤 Motion Alert'
        };
        return titleMap[alertType] || '📢 System Alert';
    }
    
    async sendEmailAlert(notification) {
        // メール送信ロジック（実装例）
        console.log(`📧 Sending email alert: ${notification.title}`);
        // 実際のメール送信実装...
    }
    
    triggerEmergencyProtocol(alertData) {
        // 緊急時プロトコル
        if (alertData.type === 'fire') {
            // 全照明を点灯
            this.client.publish('home/all/light/command', JSON.stringify({
                state: 'on',
                brightness: 100
            }));
            
            // 非常用電源を確保
            this.client.publish('home/all/plug/command', JSON.stringify({
                state: 'off',
                exclude: ['emergency']
            }));
        }
    }
}
```

## 🔐 セキュリティ実装

### デバイス認証
```javascript
// src/device-auth.js
class DeviceAuthenticator {
    constructor() {
        this.deviceRegistry = new Map();
        this.loadDeviceRegistry();
    }
    
    loadDeviceRegistry() {
        // デバイス登録情報の読み込み
        const registeredDevices = [
            {
                deviceId: 'light_living_room_001',
                deviceType: 'smart_light',
                apiKey: 'sk_light_001_abc123',
                permissions: ['home/living-room/light/*']
            },
            {
                deviceId: 'temp_sensor_001', 
                deviceType: 'temperature_sensor',
                apiKey: 'sk_temp_001_def456',
                permissions: ['home/+/temperature/*']
            }
        ];
        
        registeredDevices.forEach(device => {
            this.deviceRegistry.set(device.deviceId, device);
        });
    }
    
    authenticate(clientId, username, password) {
        const device = this.deviceRegistry.get(clientId);
        
        if (!device) {
            console.log(`❌ Unknown device: ${clientId}`);
            return false;
        }
        
        if (device.apiKey !== password) {
            console.log(`❌ Invalid API key for device: ${clientId}`);
            return false;
        }
        
        console.log(`✅ Device authenticated: ${clientId}`);
        return true;
    }
    
    authorize(clientId, topic, action) {
        const device = this.deviceRegistry.get(clientId);
        
        if (!device) {
            return false;
        }
        
        // パーミッションチェック
        return device.permissions.some(permission => {
            const regex = permission.replace(/\+/g, '[^/]+').replace(/\*/g, '.*');
            return new RegExp(`^${regex}$`).test(topic);
        });
    }
}
```

## 📱 モバイル対応

### レスポンシブUI
```css
/* public/styles/mobile.css */
@media (max-width: 768px) {
    .device-grid {
        grid-template-columns: 1fr;
        gap: 1rem;
    }
    
    .device-card {
        margin-bottom: 1rem;
    }
    
    .control-slider {
        width: 100%;
        margin: 0.5rem 0;
    }
    
    .chart-container {
        height: 250px;
        overflow-x: auto;
    }
    
    .navbar-brand {
        font-size: 1.1rem;
    }
    
    .btn-group {
        flex-direction: column;
    }
    
    .btn-group .btn {
        margin-bottom: 0.5rem;
        border-radius: 0.375rem !important;
    }
}

/* Progressive Web App対応 */
@media (display-mode: standalone) {
    body {
        padding-top: env(safe-area-inset-top);
        padding-bottom: env(safe-area-inset-bottom);
    }
}
```

### PWA マニフェスト
```json
{
  "name": "Smart Home Control",
  "short_name": "SmartHome",
  "description": "Control your smart home devices",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#ffffff",
  "theme_color": "#007bff",
  "icons": [
    {
      "src": "icons/icon-72x72.png",
      "sizes": "72x72",
      "type": "image/png"
    },
    {
      "src": "icons/icon-144x144.png", 
      "sizes": "144x144",
      "type": "image/png"
    },
    {
      "src": "icons/icon-512x512.png",
      "sizes": "512x512",
      "type": "image/png"
    }
  ]
}
```

## 🧪 テストとデバッグ

### ユニットテスト
```javascript
// tests/automation-engine.test.js
const { expect } = require('chai');
const mqtt = require('mqtt');
const AutomationEngine = require('../src/automation-engine');

describe('AutomationEngine', () => {
    let client, engine;
    
    beforeEach(() => {
        client = mqtt.connect('mqtt://localhost:1883');
        engine = new AutomationEngine(client);
    });
    
    it('should execute motion light rule', (done) => {
        const rule = {
            name: "Test Motion Light",
            trigger: {
                topic: "home/+/motion/detected",
                condition: (message) => message.value === true
            },
            actions: [{
                topic: "home/{room}/light/command",
                payload: { state: "on" }
            }]
        };
        
        engine.addRule(rule);
        
        // コマンド実行の監視
        client.subscribe('home/living-room/light/command');
        client.on('message', (topic, message) => {
            if (topic === 'home/living-room/light/command') {
                const command = JSON.parse(message.toString());
                expect(command.state).to.equal('on');
                done();
            }
        });
        
        // トリガーの発火
        client.publish('home/living-room/motion/detected', JSON.stringify({
            value: true,
            timestamp: new Date()
        }));
    });
});
```

### デバッグ用ログ出力
```javascript
// src/debug-logger.js
class DebugLogger {
    constructor(mqttClient) {
        this.client = mqttClient;
        this.logMessages = [];
        this.maxLogEntries = 1000;
        
        this.setupLogging();
    }
    
    setupLogging() {
        this.client.on('message', (topic, message) => {
            this.logMessage('RECEIVED', topic, message);
        });
        
        // publish メソッドをラップ
        const originalPublish = this.client.publish;
        this.client.publish = (topic, message, options, callback) => {
            this.logMessage('SENT', topic, message);
            return originalPublish.call(this.client, topic, message, options, callback);
        };
    }
    
    logMessage(direction, topic, message) {
        const logEntry = {
            timestamp: new Date(),
            direction: direction,
            topic: topic,
            payload: message.toString(),
            size: Buffer.byteLength(message)
        };
        
        this.logMessages.push(logEntry);
        
        // ログサイズ制限
        if (this.logMessages.length > this.maxLogEntries) {
            this.logMessages.shift();
        }
        
        // コンソールに出力
        const timestamp = logEntry.timestamp.toLocaleTimeString();
        console.log(`[${timestamp}] ${direction}: ${topic} (${logEntry.size} bytes)`);
    }
    
    getRecentLogs(count = 50) {
        return this.logMessages.slice(-count);
    }
    
    exportLogs() {
        const fs = require('fs');
        const filename = `mqtt-logs-${new Date().toISOString().split('T')[0]}.json`;
        fs.writeFileSync(filename, JSON.stringify(this.logMessages, null, 2));
        console.log(`Logs exported to ${filename}`);
    }
}
```

## 🚀 本番環境へのデプロイ

### Docker構成
```dockerfile
# Dockerfile
FROM node:18-alpine

WORKDIR /app

COPY package*.json ./
RUN npm ci --only=production

COPY . .

EXPOSE 3000

CMD ["npm", "start"]
```

```yaml
# docker-compose.yml
version: '3.8'
services:
  mqtt-broker:
    image: eclipse-mosquitto:2.0
    ports:
      - "1883:1883"
      - "9001:9001" 
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf
    
  smart-home-app:
    build: .
    ports:
      - "3000:3000"
    environment:
      - MQTT_BROKER=mqtt://mqtt-broker:1883
      - NODE_ENV=production
    depends_on:
      - mqtt-broker
    volumes:
      - ./data:/app/data
      
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./ssl:/etc/nginx/ssl
    depends_on:
      - smart-home-app
```

## 📈 パフォーマンス最適化

### メッセージ圧縮
```javascript
// src/message-compression.js
const zlib = require('zlib');

class MessageCompressor {
    static compress(message) {
        if (Buffer.byteLength(message) > 100) {
            return zlib.gzipSync(message);
        }
        return message;
    }
    
    static decompress(compressedMessage) {
        try {
            return zlib.gunzipSync(compressedMessage).toString();
        } catch (error) {
            return compressedMessage.toString();
        }
    }
}
```

### 接続プール管理
```javascript
// src/connection-pool.js
class MQTTConnectionPool {
    constructor(brokerUrl, poolSize = 5) {
        this.brokerUrl = brokerUrl;
        this.poolSize = poolSize;
        this.connections = [];
        this.currentIndex = 0;
        
        this.initializePool();
    }
    
    initializePool() {
        for (let i = 0; i < this.poolSize; i++) {
            const client = mqtt.connect(this.brokerUrl, {
                clientId: `smart-home-${i}-${Date.now()}`
            });
            this.connections.push(client);
        }
    }
    
    getConnection() {
        const connection = this.connections[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.poolSize;
        return connection;
    }
}
```

---

これで、完全に機能するスマートホームシステムのサンプルが完成です。実際のハードウェアと組み合わせることで、本格的なスマートホームシステムを構築できます。