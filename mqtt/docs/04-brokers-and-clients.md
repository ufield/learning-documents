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
```python
import boto3
import json
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient

# デバイス証明書を使用した接続
myAWSIoTMQTTClient = AWSIoTMQTTClient("myClientID")
myAWSIoTMQTTClient.configureEndpoint("your-endpoint.iot.region.amazonaws.com", 8883)
myAWSIoTMQTTClient.configureCredentials("./AmazonRootCA1.pem", "./private.pem.key", "./certificate.pem.crt")

# AWSIoTMQTTClient connection configuration
myAWSIoTMQTTClient.configureAutoReconnectBackoffTime(1, 32, 20)
myAWSIoTMQTTClient.configureOfflinePublishQueueing(-1)  # Infinite offline Publish queueing
myAWSIoTMQTTClient.configureDrainingFrequency(2)  # Draining: 2 Hz
myAWSIoTMQTTClient.configureConnectDisconnectTimeout(10)  # 10 sec
myAWSIoTMQTTClient.configureMQTTOperationTimeout(5)  # 5 sec

# Connect and subscribe to AWS IoT
myAWSIoTMQTTClient.connect()
print('Connected to AWS IoT Core')
myAWSIoTMQTTClient.subscribe("topic/subtopic", 1, customCallback)
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

```python
from azure.iot.device import IoTHubDeviceClient, Message
import asyncio

# 接続文字列を使用した接続
connection_string = "HostName=myiothub.azure-devices.net;DeviceId=myDevice;SharedAccessKey=key"
client = IoTHubDeviceClient.create_from_connection_string(connection_string)

async def main():
    try:
        # IoT Hubに接続
        await client.connect()
        print('Connected to Azure IoT Hub')
        
        # メッセージ送信例
        message = Message('{"temperature": 22.5}')
        await client.send_message(message)
        print('Message sent successfully')
        
    except Exception as e:
        print(f'Connection failed: {e}')
    finally:
        await client.disconnect()

# 実行
asyncio.run(main())
```

### 4.1.3 ブローカー選択の基準

| 要件 | 小規模 | 中規模 | 大規模・エンタープライズ |
|------|--------|--------|-------------------------|
| **同時接続数** | ~1,000 | ~10,000 | 100,000+ |
| **推奨ブローカー** | Mosquitto | EMQX CE | EMQX Enterprise, AWS IoT Core |
| **主な考慮点** | シンプル性 | コスト効率 | スケーラビリティ、可用性 |
| **運用負荷** | 低 | 中 | 低（マネージド）～高（自己管理） |

## 4.2 クライアントライブラリの選択

### 4.2.1 Python（推奨）

#### Paho MQTT（Python推奨）

```bash
pip install paho-mqtt
```

```python
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    print('Connected')
    client.subscribe('test/topic')
    client.publish('test/topic', 'Hello World!')

def on_message(client, userdata, msg):
    print(f"Received {msg.payload.decode()} on {msg.topic}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message

client.connect('broker.hivemq.com', 1883, 60)
client.loop_forever()
```

#### 高度な設定例:

```python
import paho.mqtt.client as mqtt
import ssl
import time
import random
import string

# ユニークなクライアントIDを生成
client_id = f"unique-client-{''.join(random.choices(string.ascii_lowercase + string.digits, k=8))}"

# クライアント作成
client = mqtt.Client(client_id=client_id, clean_session=True)

# セキュリティ設定
client.username_pw_set('user', 'pass')

# SSL/TLS設定
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.check_hostname = False
context.verify_mode = ssl.CERT_REQUIRED
context.load_verify_locations('./ca.crt')
context.load_cert_chain('./client.crt', './client.key')
client.tls_set_context(context)

# Will Message設定
client.will_set(
    topic='clients/client-id/status',
    payload='offline',
    qos=1,
    retain=True
)

# 接続タイムアウトとKeep Alive設定
client.connect('broker.example.com', 8883, keepalive=60)
client.loop_start()

# 再接続は自動的に処理される
```

### 4.2.2 JavaScript/Node.js（参考）

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

```python
import paho.mqtt.client as mqtt
import threading
import time
from typing import List, Dict, Any

class MQTTConnectionPool:
    def __init__(self, options: Dict[str, Any]):
        self.broker_url = options['broker_url']
        self.port = options.get('port', 1883)
        self.pool_size = options.get('pool_size', 5)
        self.connections: List[mqtt.Client] = []
        self.round_robin = 0
        self.lock = threading.Lock()
    
    def initialize(self):
        """接続プールを初期化"""
        for i in range(self.pool_size):
            client = self.create_connection(i)
            self.connections.append(client)
    
    def create_connection(self, index: int) -> mqtt.Client:
        """個別の接続を作成"""
        client_id = f"pool_{index}_{int(time.time())}"
        client = mqtt.Client(client_id=client_id, clean_session=True)
        
        # 接続完了を待つためのイベント
        connected = threading.Event()
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                connected.set()
            else:
                print(f"Connection failed for client {index}: {rc}")
        
        def on_disconnect(client, userdata, rc):
            if rc != 0:
                print(f"Unexpected disconnection for client {index}")
                # 自動再接続は有効なので、特別な処理は不要
        
        client.on_connect = on_connect
        client.on_disconnect = on_disconnect
        
        # 接続実行
        client.connect(self.broker_url, self.port, 60)
        client.loop_start()
        
        # 接続完了を待機（タイムアウト10秒）
        if not connected.wait(timeout=10):
            raise Exception(f"Connection timeout for client {index}")
        
        return client
    
    def get_connection(self) -> mqtt.Client:
        """ラウンドロビンで接続を取得"""
        with self.lock:
            connection = self.connections[self.round_robin]
            self.round_robin = (self.round_robin + 1) % self.pool_size
            return connection
    
    def publish_with_load_balancing(self, topic: str, message: str, qos: int = 0) -> bool:
        """負荷分散してメッセージを送信"""
        connection = self.get_connection()
        result = connection.publish(topic, message, qos)
        result.wait_for_publish()  # 送信完了を待機
        return result.is_published()

# 使用例
pool_options = {
    'broker_url': 'broker.hivemq.com',
    'port': 1883,
    'pool_size': 5
}

pool = MQTTConnectionPool(pool_options)
pool.initialize()

# 負荷分散して送信
pool.publish_with_load_balancing('test/topic', 'Hello from pool!')
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

```python
import gzip
import json
import paho.mqtt.client as mqtt
from typing import Callable, Dict, Any

class CompressedMQTTClient:
    def __init__(self, broker_url: str, port: int = 1883):
        self.client = mqtt.Client()
        self.broker_url = broker_url
        self.port = port
        self.compression_threshold = 100  # 100バイト以上で圧縮
        self.message_headers = {}
        
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
        self.connect()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Connected to broker")
    
    def on_message(self, client, userdata, msg):
        # メタデータトピックの処理は個別のコールバックで処理
        pass
    
    def connect(self):
        self.client.connect(self.broker_url, self.port, 60)
        self.client.loop_start()
    
    def publish_compressed(self, topic: str, payload: str, qos: int = 0) -> bool:
        """圧縮してメッセージを送信"""
        final_payload = payload.encode('utf-8')
        headers = {'compressed': False}
        
        if len(payload.encode('utf-8')) > self.compression_threshold:
            final_payload = gzip.compress(payload.encode('utf-8'))
            headers['compressed'] = True
            print(f"Compressed: {len(payload.encode('utf-8'))} -> {len(final_payload)} bytes")
        
        # ヘッダー情報を送信
        meta_topic = f"{topic}/meta"
        self.client.publish(meta_topic, json.dumps(headers), qos=0)
        
        # 実際のデータを送信
        result = self.client.publish(topic, final_payload, qos)
        return result.is_published()
    
    def subscribe_with_decompression(self, topic: str, callback: Callable[[str, str], None]):
        """圧縮解除機能付きサブスクライブ"""
        meta_topic = f"{topic}/meta"
        
        def internal_callback(client, userdata, msg):
            if msg.topic == meta_topic:
                # メタデータを保存
                self.message_headers[topic] = json.loads(msg.payload.decode())
                return
            
            if msg.topic == topic:
                final_message = msg.payload
                
                # 圧縮されている場合は解凍
                headers = self.message_headers.get(topic, {})
                if headers.get('compressed', False):
                    final_message = gzip.decompress(msg.payload)
                
                # コールバック実行
                callback(msg.topic, final_message.decode('utf-8'))
                
                # ヘッダーをリセット
                if topic in self.message_headers:
                    del self.message_headers[topic]
        
        self.client.subscribe([(topic, qos), (meta_topic, 0)])
        self.client.message_callback_add(topic, internal_callback)
        self.client.message_callback_add(meta_topic, internal_callback)

# 使用例
def message_handler(topic: str, message: str):
    print(f"Received: {message} on {topic}")

client = CompressedMQTTClient('broker.hivemq.com')
client.subscribe_with_decompression('test/compressed', message_handler)

# 大きなメッセージを送信（自動的に圧縮される）
large_message = "This is a large message that will be compressed" * 10
client.publish_compressed('test/compressed', large_message, qos=1)
```

## 4.4 エラーハンドリングとレジリエンシー

### 4.4.1 指数バックオフ再接続

```python
import paho.mqtt.client as mqtt
import time
import threading
import random
from typing import Optional, Dict, Any

class ResilientMQTTClient:
    def __init__(self, broker_url: str, port: int = 1883, options: Optional[Dict[str, Any]] = None):
        self.broker_url = broker_url
        self.port = port
        self.options = options or {}
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.options.get('max_reconnect_attempts', 10)
        self.base_delay = self.options.get('base_delay', 1)
        self.max_delay = self.options.get('max_delay', 30)
        self.client: Optional[mqtt.Client] = None
        self.connected = threading.Event()
        self.should_reconnect = True
    
    def connect(self) -> bool:
        """ブローカーに接続"""
        try:
            self.client = mqtt.Client(
                client_id=self.options.get('client_id', ''),
                clean_session=self.options.get('clean_session', True)
            )
            
            # コールバック設定
            self.client.on_connect = self.on_connect
            self.client.on_disconnect = self.on_disconnect
            self.client.on_message = self.on_message
            
            # 認証設定
            if 'username' in self.options and 'password' in self.options:
                self.client.username_pw_set(
                    self.options['username'],
                    self.options['password']
                )
            
            # 接続実行（自動再接続は無効にする）
            self.client.connect(self.broker_url, self.port, 60)
            self.client.loop_start()
            
            # 接続完了を待機
            if self.connected.wait(timeout=10):
                print('Connected successfully')
                self.reconnect_attempts = 0
                return True
            else:
                print('Connection timeout')
                return False
                
        except Exception as e:
            print(f'Connection error: {e}')
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected.set()
        else:
            print(f'Connection failed with code: {rc}')
            self.handle_reconnection()
    
    def on_disconnect(self, client, userdata, rc):
        self.connected.clear()
        if rc != 0 and self.should_reconnect:
            print('Unexpected disconnection')
            self.handle_reconnection()
        else:
            print('Disconnected gracefully')
    
    def on_message(self, client, userdata, msg):
        # サブクラスでオーバーライドしてメッセージ処理を実装
        print(f"Received message: {msg.payload.decode()} on {msg.topic}")
    
    def handle_reconnection(self):
        """指数バックオフで再接続を試行"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            print('Max reconnection attempts reached')
            return
        
        # 指数バックオフ + ジッター
        base_delay = min(
            self.base_delay * (2 ** self.reconnect_attempts),
            self.max_delay
        )
        # ジッターを追加（サンダリングハード問題を避ける）
        delay = base_delay + random.uniform(0, base_delay * 0.1)
        
        print(f'Reconnecting in {delay:.1f}s (attempt {self.reconnect_attempts + 1})')
        self.reconnect_attempts += 1
        
        def delayed_reconnect():
            time.sleep(delay)
            if self.should_reconnect:
                self.connect()
        
        # 別スレッドで再接続実行
        threading.Thread(target=delayed_reconnect, daemon=True).start()
    
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
        """メッセージを送信"""
        if self.client and self.connected.is_set():
            result = self.client.publish(topic, payload, qos, retain)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        return False
    
    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """トピックをサブスクライブ"""
        if self.client and self.connected.is_set():
            result = self.client.subscribe(topic, qos)
            return result[0] == mqtt.MQTT_ERR_SUCCESS
        return False
    
    def disconnect(self):
        """接続を切断"""
        self.should_reconnect = False
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()

# 使用例
client_options = {
    'client_id': 'resilient_client_001',
    'username': 'user',
    'password': 'pass',
    'max_reconnect_attempts': 5,
    'base_delay': 2,
    'max_delay': 60
}

client = ResilientMQTTClient('broker.hivemq.com', 1883, client_options)
if client.connect():
    client.subscribe('test/topic')
    client.publish('test/topic', 'Hello from resilient client!')
    
    # 接続を維持
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        client.disconnect()
```

## 参考リンク

- [Eclipse Mosquitto Documentation](https://mosquitto.org/documentation/)
- [EMQX Documentation](https://docs.emqx.com/)
- [AWS IoT Core Developer Guide](https://docs.aws.amazon.com/iot/latest/developerguide/)
- [MQTT.js Documentation](https://github.com/mqttjs/MQTT.js)
- [Paho MQTT Python Documentation](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)

---

**次の章**: [05-qos-and-reliability.md](05-qos-and-reliability.md) - QoSとメッセージ信頼性