# QoSとメッセージ信頼性

## 5.1 QoS（Quality of Service）の深い理解

Quality of Serviceは、MQTTにおけるメッセージ配信の信頼性保証機能です。ネットワークの不安定性やデバイスの制約を考慮して、3つの異なるレベルが定義されています。

### 5.1.1 QoS Level 0: At most once

**"Fire and Forget"** - 最も軽量な配信方式

```
Client                    Broker                    Subscriber
  |                         |                         |
  |------ PUBLISH(QoS0) ---->|                         |
  |                         |------ PUBLISH(QoS0) ---->|
  |                         |                         |
  ✓ 送信完了                 ✓ 転送完了                ✓ 受信完了
```

**特徴:**
- **オーバーヘッド**: 最小（追加のハンドシェイクなし）
- **帯域幅**: 最少
- **電力消費**: 最小
- **信頼性**: 最低（メッセージが失われる可能性）
- **重複**: なし

**実装例:**
```javascript
// QoS 0での送信
client.publish('sensors/temperature', '23.5', { qos: 0 }, (err) => {
    if (err) {
        console.log('Publish failed (but no retry)');
    } else {
        console.log('Message sent (no guarantee)');
    }
});
```

**適用シナリオ:**
- 環境センサーの定期データ（温度、湿度など）
- GPS位置情報のリアルタイム更新
- ログデータやデバッグ情報
- 高頻度のメトリクス収集

### 5.1.2 QoS Level 1: At least once

**確実な配信保証付き**

```
Client                    Broker                    Subscriber
  |                         |                         |
  |------ PUBLISH(QoS1) ---->|                         |
  |<------- PUBACK ---------|                         |
  |                         |------ PUBLISH(QoS1) ---->|
  |                         |<------- PUBACK ---------|
  ✓ 送信確認済み             ✓ 配信確認済み            ✓ 受信確認済み
```

**特徴:**
- **オーバーヘッド**: 中程度（確認応答が必要）
- **信頼性**: 高い（メッセージは必ず配信）
- **重複**: 可能性あり（ネットワーク問題時）
- **再送**: 自動的に実行

**実装例（JavaScript）:**
```javascript
client.publish('alerts/fire', JSON.stringify({
    location: 'Building A',
    severity: 'high',
    timestamp: Date.now()
}), { qos: 1 }, (err) => {
    if (err) {
        console.log('Alert failed to send');
    } else {
        console.log('Alert confirmed sent');
    }
});
```

**実装例（Python）:**
```python
import paho.mqtt.client as mqtt
import json
import time

def on_publish(client, userdata, mid):
    print(f"Message {mid} confirmed published")

client = mqtt.Client()
client.on_publish = on_publish
client.connect("broker.hivemq.com", 1883, 60)

# QoS 1でのアラート送信
alert_data = {
    "device_id": "sensor_001",
    "alert_type": "temperature_high",
    "value": 85.5,
    "threshold": 80.0,
    "timestamp": int(time.time())
}

result = client.publish(
    "alerts/temperature", 
    json.dumps(alert_data), 
    qos=1
)

# 送信完了まで待機
result.wait_for_publish()
```

**重複処理の実装:**
```javascript
class DeduplicatedMQTTHandler {
    constructor() {
        this.processedMessages = new Map();
        this.cleanupInterval = 60000; // 1分間隔でクリーンアップ
        
        setInterval(() => this.cleanup(), this.cleanupInterval);
    }
    
    handleMessage(topic, message) {
        const messageData = JSON.parse(message.toString());
        const messageId = messageData.id || this.generateHash(message);
        const now = Date.now();
        
        // 重複チェック
        if (this.processedMessages.has(messageId)) {
            console.log(`Duplicate message ignored: ${messageId}`);
            return;
        }
        
        // メッセージ処理
        this.processMessage(topic, messageData);
        
        // 処理済みとしてマーク
        this.processedMessages.set(messageId, now);
    }
    
    processMessage(topic, data) {
        console.log(`Processing unique message on ${topic}:`, data);
        // 実際のビジネスロジック
    }
    
    cleanup() {
        const cutoff = Date.now() - (5 * 60 * 1000); // 5分前
        for (const [id, timestamp] of this.processedMessages.entries()) {
            if (timestamp < cutoff) {
                this.processedMessages.delete(id);
            }
        }
    }
    
    generateHash(message) {
        return require('crypto')
            .createHash('md5')
            .update(message)
            .digest('hex');
    }
}
```

### 5.1.3 QoS Level 2: Exactly once

**最も信頼性の高い配信方式**

```
Client                    Broker                    Subscriber
  |                         |                         |
  |------ PUBLISH(QoS2) ---->|                         |
  |<------- PUBREC ---------|                         |
  |------- PUBREL --------->|                         |
  |<------ PUBCOMP ---------|                         |
  |                         |------ PUBLISH(QoS2) ---->|
  |                         |<------- PUBREC ---------|
  |                         |------- PUBREL --------->|
  |                         |<------ PUBCOMP ---------|
```

**特徴:**
- **オーバーヘッド**: 最大（4ウェイハンドシェイク）
- **信頼性**: 最高（重複なし、欠落なし）
- **帯域幅**: 最大
- **処理時間**: 最長

**実装例:**
```javascript
// 重要な制御コマンド送信
client.publish('actuators/valve/control', JSON.stringify({
    command: 'close',
    valve_id: 'V001',
    user_id: 'operator123',
    timestamp: Date.now()
}), { qos: 2 }, (err) => {
    if (err) {
        console.error('Critical command failed');
    } else {
        console.log('Command confirmed delivered exactly once');
    }
});
```

**QoS 2状態管理:**
```python
class QoS2StateManager:
    def __init__(self):
        self.pending_messages = {}  # 送信中のメッセージ
        self.received_pubrec = set()  # PUBREC受信済みメッセージID
        
    def handle_pubrec(self, packet_id):
        """PUBREC受信時の処理"""
        if packet_id in self.pending_messages:
            self.received_pubrec.add(packet_id)
            # PUBRELを送信
            return self.create_pubrel(packet_id)
        return None
        
    def handle_pubcomp(self, packet_id):
        """PUBCOMP受信時の処理"""
        if packet_id in self.pending_messages:
            del self.pending_messages[packet_id]
            self.received_pubrec.discard(packet_id)
            print(f"Message {packet_id} delivered exactly once")
        
    def create_pubrel(self, packet_id):
        return {
            'message_type': 'PUBREL',
            'packet_id': packet_id
        }
```

## 5.2 QoS選択の決定フローチャート

```
メッセージの性質を評価
        ↓
    重複は許容可能？
       ／      ＼
     Yes        No
      ↓          ↓
  欠落は許容可能？  QoS 2を使用
    ／    ＼      （制御コマンド、
   Yes     No      課金情報等）
    ↓      ↓
  QoS 0   QoS 1
 （センサー （アラート、
  データ等） 通知等）
```

### 5.2.1 用途別QoS推奨設定

| 用途カテゴリ | 具体例 | 推奨QoS | 理由 |
|-------------|--------|---------|------|
| **センサーデータ** | 温度、湿度、照度 | QoS 0 | 定期的、次のデータで補完可能 |
| **位置情報** | GPS、ビーコン | QoS 0 | リアルタイム性優先 |
| **ログ・メトリクス** | システムログ、性能データ | QoS 0 | 大量データ、一部欠落許容 |
| **アラート・通知** | 異常検知、警告 | QoS 1 | 確実な配信が重要 |
| **設定変更** | 閾値更新、モード変更 | QoS 1 | 確実な配信、冪等性で重複対応 |
| **制御コマンド** | バルブ開閉、モーター制御 | QoS 2 | 重複実行の危険性 |
| **財務データ** | 課金情報、売上データ | QoS 2 | 法的要件、重複不可 |
| **セキュリティ** | アクセス許可、認証 | QoS 2 | セキュリティ要件 |

## 5.3 Persistent Session（永続セッション）

### 5.3.1 Clean Session vs Persistent Session

```javascript
// Clean Session = true（デフォルト）
const clientClean = mqtt.connect('mqtt://broker.example.com', {
    clean: true,
    clientId: 'device001'
});
// 接続終了時に全てのセッション情報が破棄される

// Persistent Session
const clientPersistent = mqtt.connect('mqtt://broker.example.com', {
    clean: false,
    clientId: 'device001' // 同じclientIdが重要
});
// セッション情報が保持される
```

**Persistent Sessionで保持される情報:**
1. Subscriptions（購読情報）
2. QoS 1およびQoS 2の送信待ちメッセージ
3. QoS 1およびQoS 2の未確認メッセージ
4. QoS 2の受信メッセージ状態

### 5.3.2 MQTT 5.0のSession Expiry

```javascript
// MQTT 5.0のより柔軟なセッション管理
const client = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    clean: false,
    sessionExpiryInterval: 3600, // 1時間後にセッション期限切れ
    clientId: 'device001'
});
```

**セッション期限切れの動作:**
```python
class SessionManager:
    def __init__(self):
        self.sessions = {}
        
    def create_session(self, client_id, expiry_interval):
        """新しいセッションを作成"""
        session = {
            'client_id': client_id,
            'subscriptions': {},
            'pending_messages': [],
            'expiry_time': time.time() + expiry_interval if expiry_interval > 0 else None
        }
        self.sessions[client_id] = session
        return session
        
    def cleanup_expired_sessions(self):
        """期限切れセッションのクリーンアップ"""
        current_time = time.time()
        expired_sessions = []
        
        for client_id, session in self.sessions.items():
            if session['expiry_time'] and current_time > session['expiry_time']:
                expired_sessions.append(client_id)
                
        for client_id in expired_sessions:
            del self.sessions[client_id]
            print(f"Session expired for client: {client_id}")
```

## 5.4 Message Ordering（メッセージ順序保証）

MQTTでは、**同じクライアントから同じトピックへの**メッセージ順序のみが保証されます。

### 5.4.1 順序保証の実装例

```javascript
class OrderedMQTTPublisher {
    constructor(brokerUrl, options = {}) {
        this.client = mqtt.connect(brokerUrl, options);
        this.messageQueue = new Map(); // topic別キュー
        this.publishing = new Map(); // topic別公開中フラグ
    }
    
    async publishOrdered(topic, message, options = {}) {
        return new Promise((resolve, reject) => {
            // トピック別キューに追加
            if (!this.messageQueue.has(topic)) {
                this.messageQueue.set(topic, []);
            }
            
            this.messageQueue.get(topic).push({
                message,
                options,
                resolve,
                reject
            });
            
            // キューの処理を開始
            this.processQueue(topic);
        });
    }
    
    async processQueue(topic) {
        // 既に処理中の場合はスキップ
        if (this.publishing.get(topic)) {
            return;
        }
        
        this.publishing.set(topic, true);
        
        const queue = this.messageQueue.get(topic);
        
        while (queue.length > 0) {
            const { message, options, resolve, reject } = queue.shift();
            
            try {
                await new Promise((publishResolve, publishReject) => {
                    this.client.publish(topic, message, options, (err) => {
                        if (err) publishReject(err);
                        else publishResolve();
                    });
                });
                resolve();
            } catch (err) {
                reject(err);
            }
        }
        
        this.publishing.set(topic, false);
    }
}
```

### 5.4.2 アプリケーションレベルでの順序管理

```python
import threading
import queue
import time

class SequentialMQTTHandler:
    def __init__(self, mqtt_client):
        self.mqtt_client = mqtt_client
        self.sequence_numbers = {}
        self.message_buffer = {}  # 順序待ちメッセージ
        self.lock = threading.Lock()
        
    def send_with_sequence(self, topic, payload, qos=1):
        """シーケンス番号付きでメッセージ送信"""
        with self.lock:
            if topic not in self.sequence_numbers:
                self.sequence_numbers[topic] = 0
            
            seq_num = self.sequence_numbers[topic]
            self.sequence_numbers[topic] += 1
            
        message_data = {
            'sequence': seq_num,
            'timestamp': int(time.time() * 1000),
            'payload': payload
        }
        
        self.mqtt_client.publish(topic, json.dumps(message_data), qos=qos)
        
    def handle_ordered_message(self, topic, message_data):
        """順序保証されたメッセージ処理"""
        sequence = message_data['sequence']
        
        if topic not in self.message_buffer:
            self.message_buffer[topic] = {
                'expected_sequence': 0,
                'buffer': {}
            }
            
        topic_buffer = self.message_buffer[topic]
        
        if sequence == topic_buffer['expected_sequence']:
            # 期待通りの順序
            self.process_message(topic, message_data)
            topic_buffer['expected_sequence'] += 1
            
            # バッファー内の連続するメッセージを処理
            while topic_buffer['expected_sequence'] in topic_buffer['buffer']:
                buffered_msg = topic_buffer['buffer'].pop(topic_buffer['expected_sequence'])
                self.process_message(topic, buffered_msg)
                topic_buffer['expected_sequence'] += 1
                
        elif sequence > topic_buffer['expected_sequence']:
            # 順序が早い（バッファに保存）
            topic_buffer['buffer'][sequence] = message_data
            
        # else: 順序が遅い（既に処理済み、無視）
        
    def process_message(self, topic, message_data):
        print(f"Processing ordered message {message_data['sequence']} on {topic}")
        # 実際のビジネスロジック
```

## 5.5 Message Persistence（メッセージ永続化）

### 5.5.1 Retained Messages

```javascript
// Retainedメッセージの送信
client.publish('devices/sensor001/status', 'online', {
    qos: 1,
    retain: true  // Retainedフラグをセット
});

// 新しいサブスクライバー
client.subscribe('devices/+/status', (err) => {
    if (!err) {
        // すぐに最新のstatusメッセージを受信
    }
});
```

**Retained Message管理:**
```python
class RetainedMessageManager:
    def __init__(self):
        self.retained_messages = {}  # topic -> message mapping
        
    def set_retained_message(self, topic, message, qos):
        """Retainedメッセージの設定"""
        if len(message) == 0:
            # 空のペイロードでRetainedメッセージをクリア
            if topic in self.retained_messages:
                del self.retained_messages[topic]
        else:
            self.retained_messages[topic] = {
                'payload': message,
                'qos': qos,
                'timestamp': time.time()
            }
    
    def get_matching_retained(self, topic_pattern):
        """パターンにマッチするRetainedメッセージを取得"""
        import fnmatch
        
        # MQTTワイルドカードをfnmatchパターンに変換
        pattern = topic_pattern.replace('+', '*').replace('#', '*')
        
        matching_messages = []
        for topic, message in self.retained_messages.items():
            if fnmatch.fnmatch(topic, pattern):
                matching_messages.append((topic, message))
                
        return matching_messages
```

### 5.5.2 Message Store（メッセージストア）

**ファイルベース永続化:**
```python
import pickle
import os
from threading import Lock

class FilePersistentStore:
    def __init__(self, store_path):
        self.store_path = store_path
        self.lock = Lock()
        self.ensure_directory()
        
    def ensure_directory(self):
        os.makedirs(self.store_path, exist_ok=True)
        
    def store_message(self, client_id, message_id, message_data):
        """QoS 1,2メッセージの永続化"""
        filename = f"{client_id}_{message_id}.msg"
        filepath = os.path.join(self.store_path, filename)
        
        with self.lock:
            with open(filepath, 'wb') as f:
                pickle.dump(message_data, f)
                
    def retrieve_messages(self, client_id):
        """クライアント用メッセージの取得"""
        messages = []
        pattern = f"{client_id}_*.msg"
        
        with self.lock:
            for filename in os.listdir(self.store_path):
                if filename.startswith(f"{client_id}_"):
                    filepath = os.path.join(self.store_path, filename)
                    try:
                        with open(filepath, 'rb') as f:
                            message = pickle.load(f)
                            messages.append(message)
                    except (IOError, pickle.PickleError):
                        # 破損ファイルを削除
                        os.remove(filepath)
                        
        return messages
        
    def remove_message(self, client_id, message_id):
        """メッセージの削除（確認応答後）"""
        filename = f"{client_id}_{message_id}.msg"
        filepath = os.path.join(self.store_path, filename)
        
        with self.lock:
            if os.path.exists(filepath):
                os.remove(filepath)
```

## 5.6 Error Handling and Recovery

### 5.6.1 タイムアウト処理

```javascript
class ReliableMQTTClient {
    constructor(brokerUrl, options = {}) {
        this.brokerUrl = brokerUrl;
        this.options = {
            ...options,
            reconnectPeriod: 0 // 自動再接続を無効
        };
        this.publishTimeout = options.publishTimeout || 30000;
        this.pendingPublishes = new Map();
        this.client = null;
    }
    
    async publishWithTimeout(topic, message, options = {}) {
        return new Promise((resolve, reject) => {
            const messageId = this.generateMessageId();
            
            // タイムアウト設定
            const timeoutId = setTimeout(() => {
                this.pendingPublishes.delete(messageId);
                reject(new Error(`Publish timeout after ${this.publishTimeout}ms`));
            }, this.publishTimeout);
            
            this.pendingPublishes.set(messageId, {
                resolve,
                reject,
                timeoutId
            });
            
            this.client.publish(topic, message, options, (err) => {
                const pending = this.pendingPublishes.get(messageId);
                if (pending) {
                    clearTimeout(pending.timeoutId);
                    this.pendingPublishes.delete(messageId);
                    
                    if (err) {
                        pending.reject(err);
                    } else {
                        pending.resolve();
                    }
                }
            });
        });
    }
    
    generateMessageId() {
        return Math.random().toString(36).substr(2, 9);
    }
}
```

### 5.6.2 Circuit Breaker パターン

```javascript
class MQTTCircuitBreaker {
    constructor(mqtt_client, options = {}) {
        this.client = mqtt_client;
        this.failureThreshold = options.failureThreshold || 5;
        this.recoveryTimeout = options.recoveryTimeout || 60000;
        this.monitoringInterval = options.monitoringInterval || 10000;
        
        this.state = 'CLOSED'; // CLOSED, OPEN, HALF_OPEN
        this.failureCount = 0;
        this.lastFailureTime = 0;
        this.successCount = 0;
        
        this.startMonitoring();
    }
    
    async publish(topic, message, options = {}) {
        if (this.state === 'OPEN') {
            if (Date.now() - this.lastFailureTime < this.recoveryTimeout) {
                throw new Error('Circuit breaker is OPEN');
            } else {
                this.state = 'HALF_OPEN';
                this.successCount = 0;
            }
        }
        
        try {
            await this.executePublish(topic, message, options);
            this.onSuccess();
            return;
        } catch (error) {
            this.onFailure();
            throw error;
        }
    }
    
    async executePublish(topic, message, options) {
        return new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                reject(new Error('Publish timeout'));
            }, 10000);
            
            this.client.publish(topic, message, options, (err) => {
                clearTimeout(timeout);
                if (err) reject(err);
                else resolve();
            });
        });
    }
    
    onSuccess() {
        this.failureCount = 0;
        
        if (this.state === 'HALF_OPEN') {
            this.successCount++;
            if (this.successCount >= 3) {
                this.state = 'CLOSED';
            }
        }
    }
    
    onFailure() {
        this.failureCount++;
        this.lastFailureTime = Date.now();
        
        if (this.failureCount >= this.failureThreshold) {
            this.state = 'OPEN';
        }
    }
    
    startMonitoring() {
        setInterval(() => {
            console.log(`Circuit Breaker State: ${this.state}, Failures: ${this.failureCount}`);
        }, this.monitoringInterval);
    }
}
```

## 参考リンク

- [MQTT QoS Levels Explained - HiveMQ](https://www.hivemq.com/blog/mqtt-essentials-part-6-mqtt-quality-of-service-levels/)
- [MQTT Persistent Session - EMQX](https://docs.emqx.com/en/emqx/latest/mqtt/mqtt-session.html)
- [Message Ordering in MQTT](https://www.hivemq.com/blog/mqtt-essentials-part-4-mqtt-publish-subscribe-unsubscribe/)
- [MQTT 5.0 Features](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)

---

**次の章**: [06-security.md](06-security.md) - セキュリティとベストプラクティス