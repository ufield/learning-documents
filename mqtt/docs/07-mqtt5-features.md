# MQTT 5.0の新機能

## 7.1 MQTT 5.0概要

MQTT 5.0は2019年にOASIS標準として承認された最新バージョンで、MQTT 3.1.1からの大幅な機能拡張が行われています。2025年現在、主要なブローカーとクライアントライブラリがMQTT 5.0をサポートしています。

### 7.1.1 主な改善点

| カテゴリ | MQTT 3.1.1 | MQTT 5.0 |
|----------|------------|----------|
| **エラーハンドリング** | 基本的な理由コード | 詳細な理由コードとプロパティ |
| **セッション管理** | Clean Sessionのみ | Clean Start + Session Expiry |
| **メッセージ拡張** | 固定フォーマット | User Properties対応 |
| **パフォーマンス** | 基本的な最適化 | Topic Alias, Shared Subscriptions |
| **フロー制御** | 限定的 | Receive Maximum, Maximum Packet Size |
| **セキュリティ** | 基本認証 | Enhanced Authentication |

### 7.1.2 後方互換性

```javascript
// MQTT 3.1.1クライアント
const client311 = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 4  // MQTT 3.1.1
});

// MQTT 5.0クライアント
const client50 = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5  // MQTT 5.0
});

// 同じブローカーで両方のクライアントが共存可能
```

## 7.2 Enhanced Session Management

### 7.2.1 Clean Start と Session Expiry

MQTT 5.0では、セッション開始時の挙動と終了時の挙動を独立して制御できます。

```javascript
const client = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    clean: false,  // Clean Start = false（既存セッション再開）
    sessionExpiryInterval: 3600,  // 1時間後にセッション期限切れ
    clientId: 'persistent-client'
});

client.on('connect', (connack) => {
    console.log('Session Present:', connack.sessionPresent);
    console.log('Reason Code:', connack.reasonCode);
});
```

**実用的な使用例:**

```python
import paho.mqtt.client as mqtt
import paho.mqtt.properties as properties

def on_connect(client, userdata, flags, rc, prop):
    if rc == 0:
        print(f"Connected. Session present: {flags['session_present']}")
        if not flags['session_present']:
            # 新しいセッション：必要な購読を設定
            client.subscribe("sensors/+/data", qos=1)
        else:
            print("Resuming existing session with subscriptions")

client = mqtt.Client(protocol=mqtt.MQTTv5)
client.on_connect = on_connect

# 接続プロパティ設定
connect_props = properties.Properties(properties.PacketTypes.CONNECT)
connect_props.SessionExpiryInterval = 7200  # 2時間
connect_props.ReceiveMaximum = 100  # 同時処理可能な未確認メッセージ数

client.connect("broker.example.com", 1883, 60, properties=connect_props)
client.loop_forever()
```

### 7.2.2 Will Message の拡張

```javascript
const client = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    will: {
        topic: 'devices/sensor001/status',
        payload: JSON.stringify({
            status: 'offline',
            reason: 'unexpected_disconnect',
            timestamp: Date.now()
        }),
        qos: 1,
        retain: true,
        properties: {
            willDelayInterval: 30,  // 30秒後にWillメッセージ送信
            payloadFormatIndicator: 1,  // UTF-8文字列
            contentType: 'application/json',
            userProperties: {
                'device_type': 'temperature_sensor',
                'location': 'warehouse_a'
            }
        }
    }
});
```

## 7.3 Reason Codes と Error Handling

### 7.3.1 詳細な理由コード

MQTT 5.0では、操作結果に対して詳細な理由コードが提供されます：

```javascript
client.publish('sensors/data', JSON.stringify(sensorData), {
    qos: 1,
    properties: {
        messageExpiryInterval: 300  // 5分で期限切れ
    }
}, (err, packet) => {
    if (err) {
        console.error('Publish failed:', err);
    } else if (packet && packet.reasonCode) {
        switch (packet.reasonCode) {
            case 0:
                console.log('Publish successful');
                break;
            case 16:
                console.log('No matching subscribers');
                break;
            case 135:
                console.log('Not authorized');
                break;
            case 151:
                console.log('Quota exceeded');
                break;
            default:
                console.log('Publish result:', packet.reasonCode);
        }
    }
});
```

**主要な理由コード:**

| Code | Name | Description |
|------|------|-------------|
| 0x00 | Success | 成功 |
| 0x10 | No matching subscribers | 該当するサブスクライバーなし |
| 0x80 | Unspecified error | 未特定エラー |
| 0x87 | Not authorized | 認証されていない |
| 0x97 | Quota exceeded | クォータ超過 |
| 0x98 | Payload format invalid | ペイロードフォーマット無効 |

### 7.3.2 Server Disconnect

```python
def on_disconnect(client, userdata, rc, prop):
    """切断時の詳細処理"""
    reason_codes = {
        0: "Normal disconnection",
        4: "Disconnect with Will Message",
        128: "Unspecified error",
        129: "Malformed Packet",
        130: "Protocol Error",
        131: "Implementation specific error",
        135: "Not authorized",
        137: "Server unavailable",
        139: "Server shutting down",
        141: "Keep Alive timeout",
        142: "Session taken over",
        143: "Topic Filter invalid",
        144: "Topic Name invalid",
        147: "Receive Maximum exceeded",
        148: "Topic Alias invalid",
        149: "Packet too large",
        150: "Message rate too high",
        151: "Quota exceeded",
        152: "Administrative action",
        153: "Payload format invalid"
    }
    
    reason = reason_codes.get(rc, f"Unknown reason: {rc}")
    print(f"Disconnected: {reason}")
    
    # プロパティから追加情報取得
    if prop and hasattr(prop, 'ReasonString'):
        print(f"Reason String: {prop.ReasonString}")
    if prop and hasattr(prop, 'UserProperty'):
        print(f"User Properties: {prop.UserProperty}")

client.on_disconnect = on_disconnect
```

## 7.4 User Properties

### 7.4.1 メタデータの追加

```javascript
// センサーデータにメタデータを追加
client.publish('sensors/temperature', '23.5', {
    qos: 1,
    properties: {
        payloadFormatIndicator: 1,  // UTF-8文字列
        contentType: 'text/plain',
        userProperties: {
            'sensor_id': 'TEMP001',
            'location': 'Building-A-Floor-2',
            'unit': 'celsius',
            'accuracy': '±0.1°C',
            'calibration_date': '2025-01-15',
            'firmware_version': '1.2.3'
        }
    }
});

// 受信側でメタデータ活用
client.on('message', (topic, message, packet) => {
    const userProps = packet.properties?.userProperties || {};
    
    console.log(`Data: ${message.toString()}`);
    console.log(`Sensor: ${userProps.sensor_id}`);
    console.log(`Location: ${userProps.location}`);
    console.log(`Unit: ${userProps.unit}`);
    
    // メタデータに基づく処理分岐
    if (userProps.firmware_version && 
        semver.lt(userProps.firmware_version, '1.2.0')) {
        console.warn('Old firmware detected, please update');
    }
});
```

### 7.4.2 ルーティングとフィルタリング

```python
class SmartMQTTRouter:
    def __init__(self, mqtt_client):
        self.client = mqtt_client
        self.routing_rules = []
        
    def add_routing_rule(self, condition, action):
        """ルーティングルールの追加"""
        self.routing_rules.append({
            'condition': condition,
            'action': action
        })
        
    def on_message(self, client, userdata, message):
        """メッセージ受信時の処理"""
        user_props = getattr(message.properties, 'UserProperty', {}) if message.properties else {}
        
        message_data = {
            'topic': message.topic,
            'payload': message.payload.decode(),
            'qos': message.qos,
            'user_properties': user_props
        }
        
        # ルーティングルールの適用
        for rule in self.routing_rules:
            if rule['condition'](message_data):
                rule['action'](message_data)
                
    def priority_condition(self, message_data):
        """優先度による条件分岐"""
        priority = message_data['user_properties'].get('priority', 'normal')
        return priority == 'high'
        
    def location_condition(self, message_data):
        """位置による条件分岐"""
        location = message_data['user_properties'].get('location', '')
        return 'critical_zone' in location.lower()
        
    def high_priority_action(self, message_data):
        """高優先度メッセージの処理"""
        # 即座にアラート送信
        alert_topic = f"alerts/{message_data['user_properties'].get('sensor_id', 'unknown')}"
        self.client.publish(alert_topic, message_data['payload'], qos=2)
        
    def archive_action(self, message_data):
        """アーカイブ処理"""
        # データベースに保存
        self.store_to_database(message_data)

# 使用例
router = SmartMQTTRouter(client)
router.add_routing_rule(router.priority_condition, router.high_priority_action)
router.add_routing_rule(router.location_condition, router.archive_action)
client.on_message = router.on_message
```

## 7.5 Topic Alias

### 7.5.1 帯域幅最適化

```javascript
class TopicAliasManager {
    constructor(maxTopicAlias = 10) {
        this.maxTopicAlias = maxTopicAlias;
        this.aliases = new Map(); // topic -> alias
        this.reverseAliases = new Map(); // alias -> topic
        this.nextAlias = 1;
    }
    
    publish(client, topic, message, options = {}) {
        let topicAlias = this.aliases.get(topic);
        
        if (!topicAlias && this.nextAlias <= this.maxTopicAlias) {
            // 新しいエイリアスを割り当て
            topicAlias = this.nextAlias++;
            this.aliases.set(topic, topicAlias);
            this.reverseAliases.set(topicAlias, topic);
            
            // 最初の送信：トピック名とエイリアス両方を含む
            return client.publish(topic, message, {
                ...options,
                properties: {
                    ...options.properties,
                    topicAlias: topicAlias
                }
            });
        } else if (topicAlias) {
            // エイリアスのみで送信（帯域幅節約）
            return client.publish('', message, {
                ...options,
                properties: {
                    ...options.properties,
                    topicAlias: topicAlias
                }
            });
        } else {
            // エイリアス上限に達した場合は通常送信
            return client.publish(topic, message, options);
        }
    }
    
    getTopicFromAlias(alias) {
        return this.reverseAliases.get(alias);
    }
}

// 使用例
const aliasManager = new TopicAliasManager(10);

// 頻繁に使用されるトピックを最適化
setInterval(() => {
    const longTopic = 'industrial/manufacturing/line1/station5/sensor/temperature/celsius';
    const data = generateSensorData();
    
    // 最初の送信後は帯域幅を大幅に節約
    aliasManager.publish(client, longTopic, JSON.stringify(data), { qos: 1 });
}, 1000);
```

### 7.5.2 大規模IoTでの効果

```python
import time
import statistics

class BandwidthAnalyzer:
    def __init__(self):
        self.traditional_usage = []
        self.optimized_usage = []
        
    def calculate_bandwidth_savings(self, topics, message_count_per_topic):
        """帯域幅節約効果の分析"""
        
        for topic in topics:
            topic_length = len(topic.encode('utf-8'))
            
            # 従来方式（毎回フルトピック送信）
            traditional_bytes = topic_length * message_count_per_topic
            
            # MQTT 5.0 Topic Alias（最初の1回のみフルトピック）
            optimized_bytes = topic_length + (2 * (message_count_per_topic - 1))  # 2バイト = エイリアス
            
            self.traditional_usage.append(traditional_bytes)
            self.optimized_usage.append(optimized_bytes)
            
        total_traditional = sum(self.traditional_usage)
        total_optimized = sum(self.optimized_usage)
        savings_percentage = ((total_traditional - total_optimized) / total_traditional) * 100
        
        return {
            'traditional_bytes': total_traditional,
            'optimized_bytes': total_optimized,
            'savings_bytes': total_traditional - total_optimized,
            'savings_percentage': savings_percentage
        }

# 実際のIoTシナリオでの分析
topics = [
    'smart_city/district_a/building_15/floor_3/room_301/sensors/temperature',
    'smart_city/district_a/building_15/floor_3/room_301/sensors/humidity',
    'smart_city/district_a/building_15/floor_3/room_301/sensors/pressure',
    'smart_city/district_a/building_15/floor_3/room_302/sensors/temperature',
    # ... 数百のトピック
]

analyzer = BandwidthAnalyzer()
results = analyzer.calculate_bandwidth_savings(topics, 1440)  # 1日あたり1440メッセージ
print(f"Bandwidth savings: {results['savings_percentage']:.1f}%")
```

## 7.6 Shared Subscriptions

### 7.6.1 負荷分散の実装

```javascript
// ワーカープロセス1
const worker1 = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    clientId: 'worker-1'
});

worker1.subscribe('$share/data-processors/sensors/+/data', { qos: 1 });

// ワーカープロセス2  
const worker2 = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    clientId: 'worker-2'
});

worker2.subscribe('$share/data-processors/sensors/+/data', { qos: 1 });

// ワーカープロセス3
const worker3 = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    clientId: 'worker-3'
});

worker3.subscribe('$share/data-processors/sensors/+/data', { qos: 1 });

// メッセージは3つのワーカー間で負荷分散される
[worker1, worker2, worker3].forEach((worker, index) => {
    worker.on('message', (topic, message) => {
        console.log(`Worker ${index + 1} processing: ${topic}`);
        // メッセージ処理ロジック
    });
});
```

### 7.6.2 高可用性クラスター

```python
import paho.mqtt.client as mqtt
import threading
import json
import time
from typing import List

class HighAvailabilityWorker:
    def __init__(self, worker_id: str, brokers: List[str], share_group: str):
        self.worker_id = worker_id
        self.brokers = brokers
        self.share_group = share_group
        self.current_broker_index = 0
        self.client = None
        self.is_running = False
        self.processed_messages = 0
        
    def start(self):
        """ワーカー開始"""
        self.is_running = True
        threading.Thread(target=self._maintain_connection, daemon=True).start()
        threading.Thread(target=self._health_reporter, daemon=True).start()
        
    def _maintain_connection(self):
        """接続維持とフェイルオーバー"""
        while self.is_running:
            try:
                self._connect_to_current_broker()
                self.client.loop_forever()
            except Exception as e:
                print(f"Connection lost: {e}")
                self._failover_to_next_broker()
                time.sleep(5)
                
    def _connect_to_current_broker(self):
        """現在のブローカーに接続"""
        broker_url = self.brokers[self.current_broker_index]
        
        self.client = mqtt.Client(protocol=mqtt.MQTTv5)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.client.on_disconnect = self._on_disconnect
        
        print(f"Connecting to broker: {broker_url}")
        host, port = broker_url.split(':')
        self.client.connect(host, int(port), 60)
        
    def _on_connect(self, client, userdata, flags, rc, props):
        """接続成功時の処理"""
        if rc == 0:
            print(f"Worker {self.worker_id} connected successfully")
            # 共有購読の設定
            shared_topic = f"$share/{self.share_group}/tasks/+"
            client.subscribe(shared_topic, qos=1)
        else:
            print(f"Connection failed: {rc}")
            
    def _on_message(self, client, userdata, message):
        """メッセージ処理"""
        try:
            task_data = json.loads(message.payload.decode())
            
            print(f"Worker {self.worker_id} processing task: {task_data.get('id', 'unknown')}")
            
            # タスク処理（実際のビジネスロジック）
            processing_time = self._process_task(task_data)
            
            # 処理結果をレポート
            result = {
                'worker_id': self.worker_id,
                'task_id': task_data.get('id'),
                'processing_time': processing_time,
                'status': 'completed',
                'timestamp': int(time.time())
            }
            
            client.publish('results/completed', json.dumps(result), qos=1)
            self.processed_messages += 1
            
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def _process_task(self, task_data) -> float:
        """タスク処理の実装"""
        start_time = time.time()
        
        # シミュレート処理
        task_type = task_data.get('type', 'default')
        if task_type == 'heavy':
            time.sleep(2)
        elif task_type == 'medium':
            time.sleep(0.5)
        else:
            time.sleep(0.1)
            
        return time.time() - start_time
        
    def _failover_to_next_broker(self):
        """次のブローカーにフェイルオーバー"""
        self.current_broker_index = (self.current_broker_index + 1) % len(self.brokers)
        print(f"Failing over to broker: {self.brokers[self.current_broker_index]}")
        
    def _health_reporter(self):
        """ヘルスレポート送信"""
        while self.is_running:
            health_data = {
                'worker_id': self.worker_id,
                'processed_messages': self.processed_messages,
                'current_broker': self.brokers[self.current_broker_index],
                'timestamp': int(time.time())
            }
            
            # ヘルスレポート送信（別の接続を使用することも可能）
            print(f"Health: {health_data}")
            time.sleep(30)
            
    def stop(self):
        """ワーカー停止"""
        self.is_running = False
        if self.client:
            self.client.disconnect()

# クラスター起動例
if __name__ == "__main__":
    brokers = ['broker1.example.com:1883', 'broker2.example.com:1883', 'broker3.example.com:1883']
    
    # 複数のワーカーを起動
    workers = []
    for i in range(5):
        worker = HighAvailabilityWorker(f'worker-{i}', brokers, 'task-processors')
        worker.start()
        workers.append(worker)
        
    try:
        # メインプロセス継続
        time.sleep(3600)  # 1時間実行
    except KeyboardInterrupt:
        print("Shutting down workers...")
        for worker in workers:
            worker.stop()
```

## 7.7 Flow Control

### 7.7.1 Receive Maximum

```javascript
const client = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    properties: {
        receiveMaximum: 50,  // 同時に50個まで未確認メッセージを処理
        maximumPacketSize: 65536  // 最大64KBパケット
    }
});

client.on('connect', (connack) => {
    console.log('Server capabilities:');
    console.log('- Receive Maximum:', connack.properties?.receiveMaximum);
    console.log('- Maximum QoS:', connack.properties?.maximumQoS);
    console.log('- Retain Available:', connack.properties?.retainAvailable);
    console.log('- Wildcard Subscription:', connack.properties?.wildcardSubscriptionAvailable);
});
```

### 7.7.2 バックプレッシャー制御

```python
import asyncio
import paho.mqtt.client as mqtt
from asyncio import Queue, Semaphore
import time

class BackpressureController:
    def __init__(self, max_concurrent_messages=10):
        self.max_concurrent = max_concurrent_messages
        self.semaphore = Semaphore(max_concurrent_messages)
        self.message_queue = Queue(maxsize=100)
        self.processing_stats = {
            'processed': 0,
            'dropped': 0,
            'avg_processing_time': 0
        }
        
    async def handle_message(self, topic: str, payload: bytes):
        """メッセージ処理（バックプレッシャー制御付き）"""
        if self.message_queue.full():
            # キューが満杯の場合はメッセージを破棄
            self.processing_stats['dropped'] += 1
            print(f"Message dropped due to backpressure: {topic}")
            return
            
        await self.message_queue.put((topic, payload, time.time()))
        
    async def process_messages(self):
        """メッセージ処理ワーカー"""
        while True:
            try:
                topic, payload, enqueue_time = await self.message_queue.get()
                
                # セマフォで同時処理数を制限
                async with self.semaphore:
                    start_time = time.time()
                    
                    # 実際の処理
                    await self._process_single_message(topic, payload)
                    
                    # 統計更新
                    processing_time = time.time() - start_time
                    self._update_stats(processing_time)
                    
                    # キューイング遅延の監視
                    queue_delay = start_time - enqueue_time
                    if queue_delay > 5.0:  # 5秒以上の遅延
                        print(f"High queue delay detected: {queue_delay:.2f}s")
                        
            except Exception as e:
                print(f"Error processing message: {e}")
                
    async def _process_single_message(self, topic: str, payload: bytes):
        """単一メッセージの処理"""
        # シミュレート処理時間
        await asyncio.sleep(0.1)
        
        # 実際のビジネスロジック
        print(f"Processed: {topic}")
        
    def _update_stats(self, processing_time: float):
        """処理統計の更新"""
        self.processing_stats['processed'] += 1
        
        # 移動平均での処理時間計算
        alpha = 0.1  # 平滑化係数
        if self.processing_stats['avg_processing_time'] == 0:
            self.processing_stats['avg_processing_time'] = processing_time
        else:
            self.processing_stats['avg_processing_time'] = (
                alpha * processing_time + 
                (1 - alpha) * self.processing_stats['avg_processing_time']
            )
            
    def get_stats(self):
        """処理統計の取得"""
        return self.processing_stats.copy()
```

## 7.8 Request/Response パターン

### 7.8.1 Response Topic の活用

```javascript
class MQTTRequestResponse {
    constructor(client) {
        this.client = client;
        this.responseTopicPrefix = `responses/${client.options.clientId}`;
        this.pendingRequests = new Map();
        this.setupResponseHandler();
    }
    
    setupResponseHandler() {
        // レスポンス用トピックを購読
        this.client.subscribe(`${this.responseTopicPrefix}/+`, { qos: 1 });
        
        this.client.on('message', (topic, message, packet) => {
            if (topic.startsWith(this.responseTopicPrefix)) {
                this.handleResponse(topic, message, packet);
            }
        });
    }
    
    async sendRequest(requestTopic, requestData, timeout = 30000) {
        const correlationId = this.generateCorrelationId();
        const responseTopic = `${this.responseTopicPrefix}/${correlationId}`;
        
        return new Promise((resolve, reject) => {
            // タイムアウト設定
            const timeoutId = setTimeout(() => {
                this.pendingRequests.delete(correlationId);
                reject(new Error(`Request timeout after ${timeout}ms`));
            }, timeout);
            
            this.pendingRequests.set(correlationId, {
                resolve,
                reject,
                timeoutId,
                timestamp: Date.now()
            });
            
            // リクエスト送信
            this.client.publish(requestTopic, JSON.stringify(requestData), {
                qos: 1,
                properties: {
                    responseTopic: responseTopic,
                    correlationData: Buffer.from(correlationId),
                    userProperties: {
                        'request_type': 'api_call',
                        'client_version': '1.0.0'
                    }
                }
            }, (err) => {
                if (err) {
                    clearTimeout(timeoutId);
                    this.pendingRequests.delete(correlationId);
                    reject(err);
                }
            });
        });
    }
    
    handleResponse(topic, message, packet) {
        const correlationData = packet.properties?.correlationData;
        if (!correlationData) return;
        
        const correlationId = correlationData.toString();
        const pendingRequest = this.pendingRequests.get(correlationId);
        
        if (pendingRequest) {
            clearTimeout(pendingRequest.timeoutId);
            this.pendingRequests.delete(correlationId);
            
            try {
                const responseData = JSON.parse(message.toString());
                pendingRequest.resolve(responseData);
            } catch (err) {
                pendingRequest.reject(new Error('Invalid response format'));
            }
        }
    }
    
    generateCorrelationId() {
        return `${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
}

// 使用例
const requestResponse = new MQTTRequestResponse(client);

// デバイス設定取得
try {
    const config = await requestResponse.sendRequest('devices/sensor001/get_config', {
        sections: ['network', 'sampling']
    }, 10000);
    
    console.log('Device config:', config);
} catch (error) {
    console.error('Failed to get config:', error);
}

// デバイス制御コマンド
try {
    const result = await requestResponse.sendRequest('devices/actuator001/control', {
        action: 'set_position',
        position: 45,
        speed: 'normal'
    });
    
    console.log('Control result:', result);
} catch (error) {
    console.error('Control command failed:', error);
}
```

### 7.8.2 サービス側の実装

```python
import paho.mqtt.client as mqtt
import paho.mqtt.properties as properties
import json
import time
import threading
from typing import Dict, Callable

class MQTTServiceProvider:
    def __init__(self, client_id: str, broker_host: str):
        self.client = mqtt.Client(client_id=client_id, protocol=mqtt.MQTTv5)
        self.broker_host = broker_host
        self.service_handlers: Dict[str, Callable] = {}
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def register_service(self, service_topic: str, handler: Callable):
        """サービスハンドラーの登録"""
        self.service_handlers[service_topic] = handler
        
    def on_connect(self, client, userdata, flags, rc, props):
        if rc == 0:
            print("Service provider connected")
            # 登録されたサービストピックを購読
            for service_topic in self.service_handlers:
                client.subscribe(service_topic, qos=1)
        else:
            print(f"Connection failed: {rc}")
            
    def on_message(self, client, userdata, message):
        """リクエスト処理"""
        topic = message.topic
        handler = self.service_handlers.get(topic)
        
        if not handler:
            return
            
        try:
            # リクエストデータの解析
            request_data = json.loads(message.payload.decode())
            
            # プロパティから応答情報取得
            response_topic = getattr(message.properties, 'ResponseTopic', None)
            correlation_data = getattr(message.properties, 'CorrelationData', None)
            user_props = getattr(message.properties, 'UserProperty', {})
            
            if not response_topic:
                print("No response topic specified")
                return
                
            # サービス処理を別スレッドで実行（非ブロッキング）
            threading.Thread(
                target=self._handle_service_request,
                args=(handler, request_data, response_topic, correlation_data, user_props),
                daemon=True
            ).start()
            
        except Exception as e:
            print(f"Error handling request: {e}")
            
    def _handle_service_request(self, handler, request_data, response_topic, correlation_data, user_props):
        """サービスリクエストの処理"""
        start_time = time.time()
        
        try:
            # ハンドラー実行
            response_data = handler(request_data, user_props)
            
            # 成功レスポンス
            response = {
                'status': 'success',
                'data': response_data,
                'processing_time': time.time() - start_time
            }
            
        except Exception as e:
            # エラーレスポンス
            response = {
                'status': 'error',
                'error': str(e),
                'processing_time': time.time() - start_time
            }
            
        # レスポンス送信
        response_props = properties.Properties(properties.PacketTypes.PUBLISH)
        if correlation_data:
            response_props.CorrelationData = correlation_data
            
        response_props.UserProperty = [
            ('service_version', '1.0'),
            ('response_timestamp', str(int(time.time())))
        ]
        
        self.client.publish(
            response_topic,
            json.dumps(response),
            qos=1,
            properties=response_props
        )
        
    def start(self):
        """サービス開始"""
        self.client.connect(self.broker_host, 1883, 60)
        self.client.loop_forever()

# サービス実装例
def get_device_config(request_data, user_props):
    """デバイス設定取得サービス"""
    sections = request_data.get('sections', ['all'])
    
    # シミュレート設定データ
    config = {
        'network': {
            'ssid': 'IoT-Network',
            'ip': '192.168.1.100',
            'gateway': '192.168.1.1'
        },
        'sampling': {
            'interval': 60,
            'precision': 'high',
            'sensors': ['temperature', 'humidity']
        }
    }
    
    if 'all' in sections:
        return config
    else:
        return {section: config.get(section, {}) for section in sections}

def device_control(request_data, user_props):
    """デバイス制御サービス"""
    action = request_data.get('action')
    
    if action == 'set_position':
        position = request_data.get('position', 0)
        speed = request_data.get('speed', 'normal')
        
        # シミュレート制御処理
        time.sleep(0.5)  # 制御実行時間
        
        return {
            'current_position': position,
            'status': 'positioned',
            'execution_time': 0.5
        }
    else:
        raise ValueError(f"Unknown action: {action}")

# サービス起動
service = MQTTServiceProvider('device-service', 'broker.example.com')
service.register_service('devices/+/get_config', get_device_config)
service.register_service('devices/+/control', device_control)
service.start()
```

## 参考リンク

- [MQTT 5.0 Specification](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
- [MQTT 5.0 New Features - HiveMQ](https://www.hivemq.com/blog/mqtt5-essentials-all-new-features/)
- [AWS IoT Core MQTT 5.0 Support](https://aws.amazon.com/blogs/iot/introducing-new-mqttv5-features-for-aws-iot-core-to-help-build-flexible-architecture-patterns/)
- [Eclipse Paho MQTT 5.0](https://github.com/eclipse/paho.mqtt.python)

---

**次の章**: [08-cloud-integration.md](08-cloud-integration.md) - クラウドサービスとの統合