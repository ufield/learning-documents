# ブローカーとクライアントの理解

## 4.1 MQTTブローカーの選択

2025年現在、多様なMQTTブローカーが利用可能です。用途に応じた適切な選択が重要です。

### 4.1.1 オープンソースブローカー

#### Eclipse Mosquitto

**特徴:**
- 軽量で高速
- 簡単なセットアップ
- 豊富なドキュメント
- 個人プロジェクトや中小規模に最適

**インストールと基本設定:**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mosquitto mosquitto-clients

# macOS (Homebrew)
brew install mosquitto

# Docker
docker run -it -p 1883:1883 eclipse-mosquitto:2.0
```

**設定ファイル例 (`mosquitto.conf`):**
```ini
# 基本設定
port 1883
listener 9001
protocol websockets

# セキュリティ
allow_anonymous false
password_file /etc/mosquitto/passwd

# ログ設定
log_dest file /var/log/mosquitto/mosquitto.log
log_type all

# 持続化
persistence true
persistence_location /var/lib/mosquitto/
```

#### EMQX

**特徴:**
- 数百万の同時接続をサポート
- 高可用性クラスター構成
- 豊富な認証・認可オプション
- エンタープライズグレード

**Dockerでの起動:**
```bash
docker run -d --name emqx \
  -p 1883:1883 \
  -p 8083:8083 \
  -p 8084:8084 \
  -p 8883:8883 \
  -p 18083:18083 \
  emqx/emqx:latest
```

**設定例 (`emqx.conf`):**
```hocon
node {
  name = "emqx@127.0.0.1"
  cookie = "emqxsecretcookie"
}

cluster {
  name = emqxcl
  discovery_strategy = manual
}

listeners.tcp.default {
  bind = "0.0.0.0:1883"
  max_connections = 1024000
}

listeners.ws.default {
  bind = "0.0.0.0:8083"
  max_connections = 102400
}
```

#### VerneMQ

**特徴:**
- 高可用性重視
- マスターレス分散アーキテクチャ
- プラグイン拡張可能
- ミッションクリティカル用途

**Docker Compose例:**
```yaml
version: '3.8'
services:
  vernemq1:
    image: vernemq/vernemq:latest
    environment:
      DOCKER_VERNEMQ_ACCEPT_EULA: "yes"
      DOCKER_VERNEMQ_NODENAME: "VerneMQ@vernemq1.local"
    ports:
      - "1883:1883"
      - "8080:8080"
```

### 4.1.2 マネージドサービス

#### AWS IoT Core

**特徴:**
- フルマネージドサービス
- 自動スケーリング
- 高いセキュリティレベル
- AWSサービスとのシームレスな統合

**基本的な使用例:**
```javascript
const AWS = require('aws-sdk');
const AWSIoTData = require('aws-iot-device-sdk-v2');

// デバイス証明書を使用した接続
const config = {
    host: 'your-endpoint.iot.region.amazonaws.com',
    port: 8883,
    clientId: 'myDevice',
    thingName: 'myDevice',
    caCert: './AmazonRootCA1.pem',
    clientCert: './certificate.pem.crt',
    privateKey: './private.pem.key'
};

const device = awsIot.device(config);

device.on('connect', () => {
    console.log('Connected to AWS IoT Core');
    device.subscribe('topic/subtopic');
});
```

#### Google Cloud IoT Core

**注意:** Google Cloud IoT Coreは2023年8月16日にサービス終了しました。新規プロジェクトには以下の代替案を検討してください：

- **Pub/Sub + Cloud Run**: MQTTプロキシとしてCloud Runを使用
- **Anthos Service Mesh**: マイクロサービス間のメッセージング
- **サードパーティ**: HiveMQ Cloud、AWS IoT Core等

#### Azure IoT Hub

**特徴:**
- エンタープライズグレード
- デバイス管理機能
- Azure サービス統合
- ハイブリッドクラウド対応

```javascript
const IoTHubTransport = require('azure-iot-device-mqtt').Mqtt;
const Client = require('azure-iot-device').Client;

const connectionString = 'HostName=myiothub.azure-devices.net;DeviceId=myDevice;SharedAccessKey=key';
const client = Client.fromConnectionString(connectionString, IoTHubTransport);

client.open((err) => {
    if (err) {
        console.error('Connection failed: ' + err.message);
    } else {
        console.log('Connected to Azure IoT Hub');
    }
});
```

### 4.1.3 ブローカー選択の基準

| 要件 | 小規模 | 中規模 | 大規模・エンタープライズ |
|------|--------|--------|-------------------------|
| **同時接続数** | ~1,000 | ~10,000 | 100,000+ |
| **推奨ブローカー** | Mosquitto | EMQX CE | EMQX Enterprise, AWS IoT Core |
| **主な考慮点** | シンプル性 | コスト効率 | スケーラビリティ、可用性 |
| **運用負荷** | 低 | 中 | 低（マネージド）～高（自己管理） |

## 4.2 クライアントライブラリの選択

### 4.2.1 JavaScript/Node.js

#### MQTT.js（最も人気）

```javascript
npm install mqtt

const mqtt = require('mqtt');
const client = mqtt.connect('mqtt://broker.hivemq.com');

client.on('connect', () => {
    console.log('Connected');
    client.subscribe('test/topic', (err) => {
        if (!err) {
            client.publish('test/topic', 'Hello World!');
        }
    });
});

client.on('message', (topic, message) => {
    console.log(`Received ${message} on ${topic}`);
});
```

#### 高度な設定例:

```javascript
const client = mqtt.connect('mqtts://broker.example.com:8883', {
    // 基本設定
    clientId: 'unique-client-id-' + Math.random().toString(16).substr(2, 8),
    clean: true,
    keepalive: 60,
    
    // セキュリティ
    username: 'user',
    password: 'pass',
    
    // SSL/TLS
    rejectUnauthorized: true,
    ca: fs.readFileSync('./ca.crt'),
    cert: fs.readFileSync('./client.crt'),
    key: fs.readFileSync('./client.key'),
    
    // 再接続
    reconnectPeriod: 1000,
    connectTimeout: 30 * 1000,
    
    // Will Message
    will: {
        topic: 'clients/client-id/status',
        payload: 'offline',
        qos: 1,
        retain: true
    }
});
```

### 4.2.2 Python

#### Paho MQTT（公式推奨）

```python
pip install paho-mqtt

import paho.mqtt.client as mqtt
import json
import time

class MQTTClient:
    def __init__(self, broker_host, broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client()
        
        # コールバック設定
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected successfully")
            # 接続成功時に自動的に購読
            client.subscribe("sensors/+/temperature")
        else:
            print(f"Connection failed with code {rc}")
    
    def on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())
            print(f"Topic: {msg.topic}")
            print(f"Message: {payload}")
        except json.JSONDecodeError:
            print(f"Raw message: {msg.payload}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print("Unexpected disconnection")
    
    def connect(self, username=None, password=None):
        if username and password:
            self.client.username_pw_set(username, password)
        
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_start()
    
    def publish(self, topic, payload, qos=0, retain=False):
        msg_info = self.client.publish(topic, payload, qos, retain)
        msg_info.wait_for_publish()
    
    def subscribe(self, topic, qos=0):
        self.client.subscribe(topic, qos)
    
    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()

# 使用例
client = MQTTClient('broker.hivemq.com')
client.connect()

# センサーデータ送信
sensor_data = {
    "temperature": 23.5,
    "humidity": 45.2,
    "timestamp": int(time.time())
}

client.publish("sensors/room1/data", json.dumps(sensor_data), qos=1)
```

### 4.2.3 Java

#### Eclipse Paho Java

```xml
<dependency>
    <groupId>org.eclipse.paho</groupId>
    <artifactId>org.eclipse.paho.client.mqttv3</artifactId>
    <version>1.2.5</version>
</dependency>
```

```java
import org.eclipse.paho.client.mqttv3.*;
import org.eclipse.paho.client.mqttv3.persist.MemoryPersistence;

public class MQTTClient implements MqttCallback {
    private MqttClient client;
    private String brokerUrl;
    private String clientId;
    
    public MQTTClient(String brokerUrl, String clientId) {
        this.brokerUrl = brokerUrl;
        this.clientId = clientId;
    }
    
    public void connect() throws MqttException {
        MemoryPersistence persistence = new MemoryPersistence();
        client = new MqttClient(brokerUrl, clientId, persistence);
        
        MqttConnectOptions connOpts = new MqttConnectOptions();
        connOpts.setCleanSession(true);
        connOpts.setKeepAliveInterval(30);
        connOpts.setConnectionTimeout(10);
        
        client.setCallback(this);
        client.connect(connOpts);
        
        System.out.println("Connected to broker: " + brokerUrl);
    }
    
    public void publish(String topic, String message, int qos) throws MqttException {
        MqttMessage mqttMessage = new MqttMessage(message.getBytes());
        mqttMessage.setQos(qos);
        client.publish(topic, mqttMessage);
    }
    
    public void subscribe(String topic, int qos) throws MqttException {
        client.subscribe(topic, qos);
    }
    
    @Override
    public void connectionLost(Throwable cause) {
        System.out.println("Connection lost: " + cause.getMessage());
        // 再接続ロジック
        reconnect();
    }
    
    @Override
    public void messageArrived(String topic, MqttMessage message) throws Exception {
        System.out.printf("Topic: %s%n", topic);
        System.out.printf("Message: %s%n", new String(message.getPayload()));
        System.out.printf("QoS: %d%n", message.getQos());
    }
    
    @Override
    public void deliveryComplete(IMqttDeliveryToken token) {
        System.out.println("Message delivered successfully");
    }
    
    private void reconnect() {
        try {
            Thread.sleep(3000);
            connect();
        } catch (Exception e) {
            System.err.println("Reconnection failed: " + e.getMessage());
        }
    }
}
```

### 4.2.4 C/C++（組み込み系）

#### Eclipse Paho C

```c
#include "MQTTClient.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define ADDRESS     "tcp://broker.hivemq.com:1883"
#define CLIENTID    "EmbeddedDevice001"
#define TOPIC       "sensors/temperature"
#define PAYLOAD     "23.5"
#define QOS         1
#define TIMEOUT     10000L

volatile MQTTClient_deliveryToken deliveredtoken;

void delivered(void *context, MQTTClient_deliveryToken dt) {
    printf("Message with token value %d delivery confirmed\\n", dt);
    deliveredtoken = dt;
}

int msgarrvd(void *context, char *topicName, int topicLen, MQTTClient_message *message) {
    printf("Message arrived\\n");
    printf("     topic: %s\\n", topicName);
    printf("   message: %.*s\\n", message->payloadlen, (char*)message->payload);
    
    MQTTClient_freeMessage(&message);
    MQTTClient_free(topicName);
    return 1;
}

void connlost(void *context, char *cause) {
    printf("\\nConnection lost\\n");
    printf("     cause: %s\\n", cause);
}

int main() {
    MQTTClient client;
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;
    MQTTClient_message pubmsg = MQTTClient_message_initializer;
    MQTTClient_deliveryToken token;
    int rc;
    
    MQTTClient_create(&client, ADDRESS, CLIENTID, MQTTCLIENT_PERSISTENCE_NONE, NULL);
    
    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;
    
    MQTTClient_setCallbacks(client, NULL, connlost, msgarrvd, delivered);
    
    if ((rc = MQTTClient_connect(client, &conn_opts)) != MQTTCLIENT_SUCCESS) {
        printf("Failed to connect, return code %d\\n", rc);
        exit(EXIT_FAILURE);
    }
    
    pubmsg.payload = PAYLOAD;
    pubmsg.payloadlen = strlen(PAYLOAD);
    pubmsg.qos = QOS;
    pubmsg.retained = 0;
    
    MQTTClient_publishMessage(client, TOPIC, &pubmsg, &token);
    printf("Waiting for up to %d seconds for publication\\n", (int)(TIMEOUT/1000));
    
    rc = MQTTClient_waitForCompletion(client, token, TIMEOUT);
    printf("Message with delivery token %d delivered\\n", token);
    
    MQTTClient_disconnect(client, 10000);
    MQTTClient_destroy(&client);
    return rc;
}
```

## 4.3 パフォーマンス最適化

### 4.3.1 接続プール管理

```javascript
class MQTTConnectionPool {
    constructor(options) {
        this.brokerUrl = options.brokerUrl;
        this.poolSize = options.poolSize || 5;
        this.connections = [];
        this.roundRobin = 0;
    }
    
    async initialize() {
        const promises = [];
        for (let i = 0; i < this.poolSize; i++) {
            promises.push(this.createConnection(i));
        }
        this.connections = await Promise.all(promises);
    }
    
    async createConnection(index) {
        return new Promise((resolve, reject) => {
            const client = mqtt.connect(this.brokerUrl, {
                clientId: `pool_${index}_${Date.now()}`,
                clean: true,
                reconnectPeriod: 1000
            });
            
            client.on('connect', () => resolve(client));
            client.on('error', reject);
            
            setTimeout(() => reject(new Error('Connection timeout')), 10000);
        });
    }
    
    getConnection() {
        const connection = this.connections[this.roundRobin];
        this.roundRobin = (this.roundRobin + 1) % this.poolSize;
        return connection;
    }
    
    async publishWithLoadBalancing(topic, message, options = {}) {
        const connection = this.getConnection();
        return new Promise((resolve, reject) => {
            connection.publish(topic, message, options, (err) => {
                if (err) reject(err);
                else resolve();
            });
        });
    }
}
```

### 4.3.2 バッチ処理

```python
import paho.mqtt.client as mqtt
import json
import time
from threading import Timer
import queue

class BatchMQTTPublisher:
    def __init__(self, broker_host, batch_size=10, flush_interval=5):
        self.client = mqtt.Client()
        self.broker_host = broker_host
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.message_queue = queue.Queue()
        self.timer = None
        
        self.client.on_connect = self.on_connect
        self.client.connect(broker_host)
        self.client.loop_start()
        
        self.start_flush_timer()
    
    def on_connect(self, client, userdata, flags, rc):
        print(f"Connected with result code {rc}")
    
    def add_message(self, topic, payload, qos=0):
        message = {
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'timestamp': time.time()
        }
        self.message_queue.put(message)
        
        if self.message_queue.qsize() >= self.batch_size:
            self.flush_messages()
    
    def flush_messages(self):
        if self.timer:
            self.timer.cancel()
        
        messages = []
        while not self.message_queue.empty() and len(messages) < self.batch_size:
            messages.append(self.message_queue.get())
        
        if messages:
            # バッチメッセージとして送信
            batch_topic = "batch/messages"
            batch_payload = json.dumps(messages)
            self.client.publish(batch_topic, batch_payload, qos=1)
            print(f"Published batch of {len(messages)} messages")
        
        self.start_flush_timer()
    
    def start_flush_timer(self):
        self.timer = Timer(self.flush_interval, self.flush_messages)
        self.timer.start()

# 使用例
publisher = BatchMQTTPublisher('broker.hivemq.com')

for i in range(50):
    publisher.add_message(f'sensor/{i}', f'value_{i}')
    time.sleep(0.1)
```

### 4.3.3 メッセージ圧縮

```javascript
const zlib = require('zlib');
const mqtt = require('mqtt');

class CompressedMQTTClient {
    constructor(brokerUrl) {
        this.client = mqtt.connect(brokerUrl);
        this.compressionThreshold = 100; // 100バイト以上で圧縮
    }
    
    async publishCompressed(topic, payload, options = {}) {
        let finalPayload = payload;
        let headers = { compressed: false };
        
        if (Buffer.byteLength(payload, 'utf8') > this.compressionThreshold) {
            finalPayload = zlib.gzipSync(Buffer.from(payload, 'utf8'));
            headers.compressed = true;
            console.log(`Compressed: ${Buffer.byteLength(payload, 'utf8')} -> ${finalPayload.length} bytes`);
        }
        
        // ヘッダー情報をトピックに追加
        const metaTopic = `${topic}/meta`;
        await this.publish(metaTopic, JSON.stringify(headers), { qos: 0 });
        
        // 実際のデータを送信
        return this.publish(topic, finalPayload, options);
    }
    
    publish(topic, payload, options = {}) {
        return new Promise((resolve, reject) => {
            this.client.publish(topic, payload, options, (err) => {
                if (err) reject(err);
                else resolve();
            });
        });
    }
    
    subscribeWithDecompression(topic, callback) {
        const metaTopic = `${topic}/meta`;
        let messageHeaders = {};
        
        this.client.subscribe([topic, metaTopic]);
        
        this.client.on('message', (receivedTopic, message) => {
            if (receivedTopic === metaTopic) {
                messageHeaders = JSON.parse(message.toString());
                return;
            }
            
            if (receivedTopic === topic) {
                let finalMessage = message;
                
                if (messageHeaders.compressed) {
                    finalMessage = zlib.gunzipSync(message);
                }
                
                callback(receivedTopic, finalMessage.toString());
                messageHeaders = {}; // リセット
            }
        });
    }
}
```

## 4.4 エラーハンドリングとレジリエンシー

### 4.4.1 指数バックオフ再接続

```javascript
class ResilientMQTTClient {
    constructor(brokerUrl, options = {}) {
        this.brokerUrl = brokerUrl;
        this.options = options;
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
        this.baseDelay = options.baseDelay || 1000;
        this.maxDelay = options.maxDelay || 30000;
        this.client = null;
    }
    
    connect() {
        return new Promise((resolve, reject) => {
            this.client = mqtt.connect(this.brokerUrl, {
                ...this.options,
                reconnectPeriod: 0 // 自動再接続無効
            });
            
            this.client.on('connect', () => {
                console.log('Connected successfully');
                this.reconnectAttempts = 0;
                resolve();
            });
            
            this.client.on('error', (err) => {
                console.error('Connection error:', err);
                this.handleReconnection();
            });
            
            this.client.on('close', () => {
                console.log('Connection closed');
                this.handleReconnection();
            });
        });
    }
    
    async handleReconnection() {
        if (this.reconnectAttempts >= this.maxReconnectAttempts) {
            console.error('Max reconnection attempts reached');
            return;
        }
        
        const delay = Math.min(
            this.baseDelay * Math.pow(2, this.reconnectAttempts),
            this.maxDelay
        );
        
        console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts + 1})`);
        this.reconnectAttempts++;
        
        setTimeout(async () => {
            try {
                await this.connect();
            } catch (err) {
                console.error('Reconnection failed:', err);
            }
        }, delay);
    }
}
```

## 参考リンク

- [Eclipse Mosquitto Documentation](https://mosquitto.org/documentation/)
- [EMQX Documentation](https://docs.emqx.com/)
- [AWS IoT Core Developer Guide](https://docs.aws.amazon.com/iot/latest/developerguide/)
- [MQTT.js Documentation](https://github.com/mqttjs/MQTT.js)
- [Paho MQTT Python Documentation](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)

---

**次の章**: [05-qos-and-reliability.md](05-qos-and-reliability.md) - QoSとメッセージ信頼性