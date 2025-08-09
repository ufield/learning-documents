# 監視とトラブルシューティング

## 10.1 MQTTシステムの監視戦略

2025年現在、IoTシステムの規模拡大に伴い、包括的な監視戦略が必要不可欠です。

### 10.1.1 監視レイヤー

```
┌─────────────────────────────────────────────────┐
│            アプリケーション監視                     │
│  ・ビジネスメトリクス                             │
│  ・エラー率、レイテンシ                            │
│  ・データ品質                                     │
├─────────────────────────────────────────────────┤
│              MQTT監視                          │
│  ・接続数、メッセージレート                        │
│  ・QoS配信統計                                    │
│  ・トピック別メトリクス                            │
├─────────────────────────────────────────────────┤
│            インフラストラクチャ監視                │
│  ・CPU、メモリ、ディスク                           │
│  ・ネットワーク帯域幅                             │
│  ・システムログ                                   │
└─────────────────────────────────────────────────┘
```

### 10.1.2 重要メトリクス（2025年版）

| カテゴリ | メトリクス | 閾値例 | 重要度 |
|----------|-----------|--------|--------|
| **接続** | 同時接続数 | > 90% capacity | 高 |
| **接続** | 接続エラー率 | > 5% | 高 |
| **メッセージ** | Publish レート | > 10,000 msg/sec | 中 |
| **メッセージ** | QoS 1 配信失敗率 | > 1% | 高 |
| **レイテンシ** | E2E遅延 | > 500ms | 中 |
| **リソース** | メモリ使用率 | > 85% | 高 |
| **セキュリティ** | 認証失敗率 | > 2% | 高 |

## 10.2 Prometheus + Grafana による監視

### 10.2.1 MQTT Exporter実装

```python
import paho.mqtt.client as mqtt
import json
import time
from prometheus_client import Counter, Histogram, Gauge, start_http_server
from collections import defaultdict
import threading
import re

class MQTTPrometheusExporter:
    def __init__(self, broker_host, broker_port=1883, metrics_port=8000):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.metrics_port = metrics_port
        
        # Prometheusメトリクス定義
        self.setup_metrics()
        
        # MQTT接続設定
        self.client = mqtt.Client(client_id="prometheus-exporter")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # 内部状態
        self.connection_state = False
        self.topic_stats = defaultdict(lambda: {'count': 0, 'size': 0})
        
    def setup_metrics(self):
        """Prometheusメトリクスの設定"""
        
        # 接続関連
        self.mqtt_connection_status = Gauge(
            'mqtt_connection_status', 
            'MQTT broker connection status (1=connected, 0=disconnected)'
        )
        
        self.mqtt_clients_connected = Gauge(
            'mqtt_clients_connected', 
            'Number of connected MQTT clients'
        )
        
        # メッセージ関連
        self.mqtt_messages_received_total = Counter(
            'mqtt_messages_received_total', 
            'Total number of MQTT messages received',
            ['topic_pattern', 'qos']
        )
        
        self.mqtt_message_size_bytes = Histogram(
            'mqtt_message_size_bytes',
            'Size of MQTT messages in bytes',
            ['topic_pattern'],
            buckets=[100, 500, 1024, 5120, 10240, 50000, 100000, 500000]
        )
        
        self.mqtt_publish_latency_seconds = Histogram(
            'mqtt_publish_latency_seconds',
            'Latency of MQTT message publishing',
            ['topic_pattern', 'qos'],
            buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
        )
        
        # エラー関連
        self.mqtt_connection_errors_total = Counter(
            'mqtt_connection_errors_total',
            'Total number of MQTT connection errors',
            ['error_type']
        )
        
        self.mqtt_publish_errors_total = Counter(
            'mqtt_publish_errors_total',
            'Total number of MQTT publish errors',
            ['topic_pattern', 'error_type']
        )
        
        # システム関連
        self.mqtt_system_uptime_seconds = Gauge(
            'mqtt_system_uptime_seconds',
            'MQTT system uptime in seconds'
        )
        
        # ブローカー固有メトリクス（$SYS トピック）
        self.mqtt_broker_load_bytes_received = Gauge(
            'mqtt_broker_load_bytes_received',
            'Bytes received by broker'
        )
        
        self.mqtt_broker_load_bytes_sent = Gauge(
            'mqtt_broker_load_bytes_sent', 
            'Bytes sent by broker'
        )
        
        self.mqtt_broker_subscriptions_count = Gauge(
            'mqtt_broker_subscriptions_count',
            'Number of subscriptions on broker'
        )
        
    def start_monitoring(self):
        """監視開始"""
        # Prometheusメトリクスサーバー開始
        start_http_server(self.metrics_port)
        print(f"Prometheus metrics server started on port {self.metrics_port}")
        
        # MQTT接続
        self.client.connect(self.broker_host, self.broker_port, 60)
        
        # 監視スレッド開始
        threading.Thread(target=self.update_system_metrics, daemon=True).start()
        
        # メッセージループ開始
        self.client.loop_forever()
        
    def on_connect(self, client, userdata, flags, rc):
        """接続時の処理"""
        if rc == 0:
            print("Connected to MQTT broker for monitoring")
            self.connection_state = True
            self.mqtt_connection_status.set(1)
            
            # 監視対象トピック購読
            monitoring_topics = [
                ('sensors/+/+', 1),        # センサーデータ
                ('devices/+/status', 1),   # デバイス状態
                ('alerts/+', 1),           # アラート
                ('$SYS/broker/+', 0),      # ブローカー統計
                ('+/+/+', 0)               # 全メッセージ（サンプリング用）
            ]
            
            for topic, qos in monitoring_topics:
                client.subscribe(topic, qos)
                
        else:
            self.connection_state = False
            self.mqtt_connection_status.set(0)
            self.mqtt_connection_errors_total.labels(
                error_type=f'connection_rc_{rc}'
            ).inc()
            
    def on_disconnect(self, client, userdata, rc):
        """切断時の処理"""
        self.connection_state = False
        self.mqtt_connection_status.set(0)
        
        if rc != 0:
            self.mqtt_connection_errors_total.labels(
                error_type='unexpected_disconnect'
            ).inc()
            
    def on_message(self, client, userdata, msg):
        """メッセージ受信時の処理"""
        try:
            topic = msg.topic
            payload_size = len(msg.payload)
            qos = msg.qos
            
            # トピックパターンの抽出
            topic_pattern = self.extract_topic_pattern(topic)
            
            # メッセージカウンターの更新
            self.mqtt_messages_received_total.labels(
                topic_pattern=topic_pattern,
                qos=qos
            ).inc()
            
            # メッセージサイズの記録
            self.mqtt_message_size_bytes.labels(
                topic_pattern=topic_pattern
            ).observe(payload_size)
            
            # $SYSトピックの処理
            if topic.startswith('$SYS/'):
                self.handle_sys_topic(topic, msg.payload)
                
            # カスタムメッセージ処理
            self.handle_custom_metrics(topic, msg.payload, qos)
            
        except Exception as e:
            print(f"Error processing message: {e}")
            
    def extract_topic_pattern(self, topic):
        """トピックから汎用パターンを抽出"""
        # デバイスIDや具体的な値を汎用化
        patterns = [
            (r'/\d+/', '/[id]/'),           # 数値ID
            (r'/[a-f0-9-]{36}/', '/[uuid]/'), # UUID
            (r'/device_\w+/', '/device_[id]/'), # デバイスID
            (r'/sensor_\w+/', '/sensor_[id]/'), # センサーID
        ]
        
        pattern = topic
        for regex, replacement in patterns:
            pattern = re.sub(regex, replacement, pattern)
            
        return pattern
        
    def handle_sys_topic(self, topic, payload):
        """$SYSトピックの統計処理"""
        try:
            value = float(payload.decode())
            
            if 'load/bytes/received' in topic:
                self.mqtt_broker_load_bytes_received.set(value)
            elif 'load/bytes/sent' in topic:
                self.mqtt_broker_load_bytes_sent.set(value)
            elif 'clients/connected' in topic:
                self.mqtt_clients_connected.set(value)
            elif 'subscriptions/count' in topic:
                self.mqtt_broker_subscriptions_count.set(value)
                
        except (ValueError, UnicodeDecodeError):
            pass  # 数値以外のSYSトピックは無視
            
    def handle_custom_metrics(self, topic, payload, qos):
        """カスタムメトリクスの処理"""
        try:
            # JSONペイロードの解析
            if payload.startswith(b'{'):
                data = json.loads(payload.decode())
                
                # レイテンシ情報がある場合
                if 'timestamp' in data:
                    message_time = data['timestamp']
                    current_time = time.time() * 1000  # ミリ秒
                    
                    if isinstance(message_time, (int, float)):
                        latency = (current_time - message_time) / 1000  # 秒に変換
                        if 0 <= latency <= 60:  # 妥当な範囲内
                            topic_pattern = self.extract_topic_pattern(topic)
                            self.mqtt_publish_latency_seconds.labels(
                                topic_pattern=topic_pattern,
                                qos=qos
                            ).observe(latency)
                            
        except (json.JSONDecodeError, UnicodeDecodeError):
            pass  # JSON以外のペイロードは無視
            
    def update_system_metrics(self):
        """システムメトリクスの定期更新"""
        start_time = time.time()
        
        while True:
            uptime = time.time() - start_time
            self.mqtt_system_uptime_seconds.set(uptime)
            
            # 60秒間隔で更新
            time.sleep(60)

# 監視開始
if __name__ == "__main__":
    exporter = MQTTPrometheusExporter(
        broker_host="localhost",
        broker_port=1883,
        metrics_port=8000
    )
    
    try:
        exporter.start_monitoring()
    except KeyboardInterrupt:
        print("Monitoring stopped")
```

### 10.2.2 Grafana ダッシュボード設定

```json
{
  "dashboard": {
    "id": null,
    "title": "MQTT IoT System Monitoring",
    "tags": ["mqtt", "iot", "monitoring"],
    "timezone": "browser",
    "panels": [
      {
        "id": 1,
        "title": "Connection Status",
        "type": "stat",
        "targets": [
          {
            "expr": "mqtt_connection_status",
            "refId": "A"
          }
        ],
        "fieldConfig": {
          "defaults": {
            "color": {
              "mode": "thresholds"
            },
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "green", "value": 1}
              ]
            }
          }
        }
      },
      {
        "id": 2,
        "title": "Message Rate",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mqtt_messages_received_total[5m])",
            "legendFormat": "Messages/sec - {{topic_pattern}}",
            "refId": "A"
          }
        ],
        "yAxes": [
          {
            "label": "Messages per second"
          }
        ]
      },
      {
        "id": 3,
        "title": "Connected Clients",
        "type": "graph",
        "targets": [
          {
            "expr": "mqtt_clients_connected",
            "legendFormat": "Connected Clients",
            "refId": "A"
          }
        ]
      },
      {
        "id": 4,
        "title": "Message Latency",
        "type": "graph",
        "targets": [
          {
            "expr": "histogram_quantile(0.95, rate(mqtt_publish_latency_seconds_bucket[5m]))",
            "legendFormat": "95th percentile",
            "refId": "A"
          },
          {
            "expr": "histogram_quantile(0.50, rate(mqtt_publish_latency_seconds_bucket[5m]))",
            "legendFormat": "50th percentile",
            "refId": "B"
          }
        ]
      },
      {
        "id": 5,
        "title": "Error Rates",
        "type": "graph",
        "targets": [
          {
            "expr": "rate(mqtt_connection_errors_total[5m])",
            "legendFormat": "Connection Errors/sec - {{error_type}}",
            "refId": "A"
          },
          {
            "expr": "rate(mqtt_publish_errors_total[5m])",
            "legendFormat": "Publish Errors/sec - {{topic_pattern}}",
            "refId": "B"
          }
        ]
      },
      {
        "id": 6,
        "title": "Data Volume",
        "type": "graph",
        "targets": [
          {
            "expr": "mqtt_broker_load_bytes_received",
            "legendFormat": "Bytes Received",
            "refId": "A"
          },
          {
            "expr": "mqtt_broker_load_bytes_sent", 
            "legendFormat": "Bytes Sent",
            "refId": "B"
          }
        ]
      }
    ],
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "refresh": "30s"
  }
}
```

## 10.3 ログ分析とトラブルシューティング

### 10.3.1 構造化ログ実装

```python
import logging
import json
import re
import sys
from datetime import datetime
from logging.handlers import RotatingFileHandler
import paho.mqtt.client as mqtt

class StructuredMQTTLogger:
    def __init__(self, options=None):
        if options is None:
            options = {}
        
        self.correlation_id = None
        self.session_id = None
        self.setup_logger(options)
    
    def setup_logger(self, options):
        # カスタムフォーマッター
        class CustomFormatter(logging.Formatter):
            def __init__(self, mqtt_logger):
                super().__init__()
                self.mqtt_logger = mqtt_logger
            
            def format(self, record):
                log_entry = {
                    '@timestamp': datetime.fromtimestamp(record.created).isoformat(),
                    'level': record.levelname.lower(),
                    'message': record.getMessage(),
                    'service': 'mqtt-client',
                    'version': '1.0.0'
                }
                
                # メタデータの追加
                if hasattr(record, '__dict__'):
                    for key, value in record.__dict__.items():
                        if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 
                                     'pathname', 'filename', 'module', 'lineno', 
                                     'funcName', 'created', 'msecs', 'relativeCreated', 
                                     'thread', 'threadName', 'processName', 'process',
                                     'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                            log_entry[key] = value
                
                # 関連ID追加
                if self.mqtt_logger.correlation_id:
                    log_entry['correlationId'] = self.mqtt_logger.correlation_id
                
                if self.mqtt_logger.session_id:
                    log_entry['sessionId'] = self.mqtt_logger.session_id
                
                return json.dumps(log_entry)
        
        # ロガー設定
        self.logger = logging.getLogger('mqtt_client')
        self.logger.setLevel(getattr(logging, options.get('level', 'INFO').upper()))
        
        # ハンドラーをクリア
        for handler in self.logger.handlers[:]:
            self.logger.removeHandler(handler)
        
        # コンソールハンドラー
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(CustomFormatter(self))
        self.logger.addHandler(console_handler)
        
        # ファイルハンドラー
        log_file = options.get('log_file', 'mqtt-client.log')
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5
        )
        file_handler.setFormatter(CustomFormatter(self))
        self.logger.addHandler(file_handler)
    
    def set_correlation_id(self, correlation_id):
        self.correlation_id = correlation_id
    
    def set_session_id(self, session_id):
        self.session_id = session_id
    
    def log_connection(self, event, details=None):
        if details is None:
            details = {}
        
        self.logger.info('MQTT connection event', extra={
            'event': event,
            'category': 'connection',
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_message(self, direction, topic, payload, options=None):
        if options is None:
            options = {}
        
        # ペイロードサイズ計算
        if isinstance(payload, bytes):
            payload_size = len(payload)
        else:
            payload_size = len(str(payload).encode('utf-8'))
        
        message_info = {
            'event': f'message_{direction}',
            'category': 'message',
            'topic': topic,
            'payloadSize': payload_size,
            'qos': options.get('qos', 0),
            'retain': options.get('retain', False),
            'timestamp': datetime.now().isoformat()
        }
        
        # センシティブデータのマスキング
        if self.is_sensitive_topic(topic):
            message_info['payloadPreview'] = '[SENSITIVE]'
        else:
            message_info['payloadPreview'] = self.truncate_payload(payload)
        
        self.logger.info(f'Message {direction}', extra=message_info)
    
    def log_error(self, error, context=None):
        if context is None:
            context = {}
        
        error_info = {
            'event': 'error',
            'category': 'error',
            'error': {
                'message': str(error),
                'type': type(error).__name__
            },
            'context': context,
            'timestamp': datetime.now().isoformat()
        }
        
        # スタックトレース情報があれば追加
        import traceback
        if hasattr(error, '__traceback__') and error.__traceback__:
            error_info['error']['stack'] = ''.join(traceback.format_tb(error.__traceback__))
        
        self.logger.error('MQTT error occurred', extra=error_info)
    
    def log_performance(self, operation, duration, details=None):
        if details is None:
            details = {}
        
        self.logger.info('Performance metric', extra={
            'event': 'performance',
            'category': 'performance',
            'operation': operation,
            'durationMs': duration * 1000 if duration < 1 else duration,  # ミリ秒に変換
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def log_security(self, event, details=None):
        if details is None:
            details = {}
        
        self.logger.warning('Security event', extra={
            'event': event,
            'category': 'security',
            'details': details,
            'timestamp': datetime.now().isoformat()
        })
    
    def is_sensitive_topic(self, topic):
        sensitive_patterns = [
            r'/password$',
            r'/secret$',
            r'/key$',
            r'/token$',
            r'/credential$'
        ]
        
        return any(re.search(pattern, topic) for pattern in sensitive_patterns)
    
    def truncate_payload(self, payload, max_length=200):
        payload_str = str(payload)
        if len(payload_str) <= max_length:
            return payload_str
        return payload_str[:max_length] + '...'

# 使用例：ログ付きMQTTクライアント
class LoggedMQTTClient:
    def __init__(self, broker_url, options=None):
        if options is None:
            options = {}
        
        self.broker_url = broker_url
        self.options = options
        self.logger = StructuredMQTTLogger(options.get('logging', {}))
        self.client = None
        self.connection_start_time = None
    
    async def connect(self):
        import random
        import string
        
        self.connection_start_time = time.time()
        session_id = f"session_{int(time.time() * 1000)}"
        self.logger.set_session_id(session_id)
        
        # 接続完了を待つためのイベント
        import asyncio
        connection_event = asyncio.Event()
        connection_result = {'success': False, 'error': None}
        
        def on_connect(client, userdata, flags, rc):
            nonlocal connection_result
            if rc == 0:
                connection_duration = (time.time() - self.connection_start_time) * 1000
                
                self.logger.log_connection('connected', {
                    'broker': self.broker_url,
                    'clientId': self.options.get('client_id'),
                    'cleanSession': self.options.get('clean_session', True),
                    'connectionDuration': connection_duration,
                    'sessionPresent': flags.get('session_present', False)
                })
                
                self.logger.log_performance('connection_establish', connection_duration)
                connection_result['success'] = True
            else:
                error_msg = f"Connection failed with code {rc}"
                connection_result['error'] = Exception(error_msg)
            
            connection_event.set()
        
        def on_disconnect(client, userdata, rc):
            self.logger.log_connection('disconnected')
        
        def on_message(client, userdata, msg):
            self.logger.log_message('received', msg.topic, msg.payload, {
                'qos': msg.qos,
                'retain': msg.retain
            })
        
        def on_error(client, userdata, error):
            self.logger.log_error(error, {
                'operation': 'connection',
                'broker': self.broker_url
            })
            
            # セキュリティイベントの監視
            error_str = str(error)
            if 'ENOTFOUND' in error_str or 'ECONNREFUSED' in error_str:
                self.logger.log_security('connection_blocked', {
                    'broker': self.broker_url,
                    'errorCode': error_str
                })
        
        # MQTTクライアント作成
        client_id = self.options.get('client_id', f"logged_client_{int(time.time())}")
        self.client = mqtt.Client(client_id=client_id)
        
        # コールバック設定
        self.client.on_connect = on_connect
        self.client.on_disconnect = on_disconnect
        self.client.on_message = on_message
        
        # 接続実行
        try:
            # broker_url からホストとポートを解析
            if '://' in self.broker_url:
                # mqtt://host:port 形式
                url_parts = self.broker_url.split('://', 1)[1]
            else:
                url_parts = self.broker_url
            
            if ':' in url_parts:
                host, port_str = url_parts.split(':', 1)
                port = int(port_str)
            else:
                host = url_parts
                port = 1883
            
            self.client.connect(host, port, 60)
            self.client.loop_start()
            
            # 接続完了を待機
            await asyncio.wait_for(connection_event.wait(), timeout=30)
            
            if not connection_result['success']:
                error = connection_result.get('error', Exception("Connection failed"))
                raise error
                
        except Exception as error:
            self.logger.log_error(error, {
                'operation': 'connection',
                'broker': self.broker_url
            })
            raise
    
    async def publish(self, topic, message, options=None):
        if options is None:
            options = {}
        
        import random
        import string
        
        correlation_id = f"pub_{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
        self.logger.set_correlation_id(correlation_id)
        
        publish_start_time = time.time()
        
        # 発行完了を待つためのイベント
        publish_event = asyncio.Event()
        publish_result = {'success': False, 'error': None, 'packet': None}
        
        def on_publish(client, userdata, mid):
            nonlocal publish_result
            publish_duration = (time.time() - publish_start_time) * 1000
            
            publish_result['success'] = True
            publish_result['packet'] = mid
            
            self.logger.log_message('sent', topic, message, options)
            self.logger.log_performance('message_publish', publish_duration, {
                'topic': topic,
                'qos': options.get('qos', 0)
            })
            
            publish_event.set()
        
        # 一時的にコールバック設定
        original_on_publish = self.client.on_publish
        self.client.on_publish = on_publish
        
        try:
            # メッセージ発行
            result = self.client.publish(topic, message, **options)
            
            if result.rc != mqtt.MQTT_ERR_SUCCESS:
                error = Exception(f"Publish failed with code {result.rc}")
                self.logger.log_error(error, {
                    'operation': 'publish',
                    'topic': topic,
                    'correlationId': correlation_id
                })
                raise error
            
            # QoS 0の場合は即座に成功
            if options.get('qos', 0) == 0:
                publish_duration = (time.time() - publish_start_time) * 1000
                self.logger.log_message('sent', topic, message, options)
                self.logger.log_performance('message_publish', publish_duration, {
                    'topic': topic,
                    'qos': 0
                })
                return result
            
            # QoS 1,2の場合は確認を待つ
            await asyncio.wait_for(publish_event.wait(), timeout=30)
            
            if not publish_result['success']:
                error = publish_result.get('error', Exception("Publish failed"))
                raise error
                
            return publish_result['packet']
            
        finally:
            # コールバックを元に戻す
            self.client.on_publish = original_on_publish
    
    async def subscribe(self, topic, options=None):
        if options is None:
            options = {}
        
        import random
        import string
        
        correlation_id = f"sub_{int(time.time() * 1000)}_{''.join(random.choices(string.ascii_letters + string.digits, k=6))}"
        self.logger.set_correlation_id(correlation_id)
        
        # 購読完了を待つためのイベント
        subscribe_event = asyncio.Event()
        subscribe_result = {'success': False, 'error': None, 'granted': None}
        
        def on_subscribe(client, userdata, mid, granted_qos):
            nonlocal subscribe_result
            subscribe_result['success'] = True
            subscribe_result['granted'] = granted_qos
            
            self.logger.log_connection('subscribed', {
                'topic': topic,
                'qos': options.get('qos', 0),
                'granted': granted_qos
            })
            
            subscribe_event.set()
        
        # 一時的にコールバック設定
        original_on_subscribe = self.client.on_subscribe
        self.client.on_subscribe = on_subscribe
        
        try:
            # 購読実行
            result = self.client.subscribe(topic, options.get('qos', 0))
            
            if result[0] != mqtt.MQTT_ERR_SUCCESS:
                error = Exception(f"Subscribe failed with code {result[0]}")
                self.logger.log_error(error, {
                    'operation': 'subscribe',
                    'topic': topic,
                    'correlationId': correlation_id
                })
                raise error
            
            # 購読確認を待機
            await asyncio.wait_for(subscribe_event.wait(), timeout=30)
            
            if not subscribe_result['success']:
                error = subscribe_result.get('error', Exception("Subscribe failed"))
                raise error
                
            return subscribe_result['granted']
            
        finally:
            # コールバックを元に戻す
            self.client.on_subscribe = original_on_subscribe
```

### 10.3.2 ELK Stackによるログ分析

```yaml
# docker-compose.yml for ELK Stack
version: '3.7'
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.11.0
    environment:
      - discovery.type=single-node
      - "ES_JAVA_OPTS=-Xms512m -Xmx512m"
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - elasticsearch_data:/usr/share/elasticsearch/data
      
  logstash:
    image: docker.elastic.co/logstash/logstash:8.11.0
    ports:
      - "5044:5044"
    volumes:
      - ./logstash/pipeline:/usr/share/logstash/pipeline:ro
      - ./logstash/config:/usr/share/logstash/config:ro
    depends_on:
      - elasticsearch
      
  kibana:
    image: docker.elastic.co/kibana/kibana:8.11.0
    ports:
      - "5601:5601"
    environment:
      - ELASTICSEARCH_HOSTS=http://elasticsearch:9200
    depends_on:
      - elasticsearch
      
  filebeat:
    image: docker.elastic.co/beats/filebeat:8.11.0
    user: root
    volumes:
      - ./filebeat/filebeat.yml:/usr/share/filebeat/filebeat.yml:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - ./logs:/logs:ro
    depends_on:
      - logstash

volumes:
  elasticsearch_data:
```

```ruby
# logstash/pipeline/mqtt.conf
input {
  beats {
    port => 5044
  }
}

filter {
  if [fields][service] == "mqtt" {
    json {
      source => "message"
    }
    
    # タイムスタンプの正規化
    if [@timestamp] {
      date {
        match => [ "@timestamp", "ISO8601" ]
      }
    }
    
    # エラーレベルの分類
    if [level] == "error" {
      mutate {
        add_field => { "severity" => "high" }
      }
    } else if [level] == "warn" {
      mutate {
        add_field => { "severity" => "medium" }
      }
    } else {
      mutate {
        add_field => { "severity" => "low" }
      }
    }
    
    # トピック階層の解析
    if [details][topic] {
      ruby {
        code => '
          topic = event.get("[details][topic]")
          if topic
            parts = topic.split("/")
            event.set("[topic_levels]", parts.length)
            event.set("[topic_root]", parts[0]) if parts.length > 0
            event.set("[topic_device]", parts[1]) if parts.length > 1
            event.set("[topic_metric]", parts[2]) if parts.length > 2
          end
        '
      }
    }
    
    # パフォーマンスアラート
    if [category] == "performance" and [durationMs] {
      if [durationMs] > 1000 {
        mutate {
          add_field => { "performance_alert" => "slow_operation" }
        }
      }
    }
    
    # セキュリティイベントの強化
    if [category] == "security" {
      mutate {
        add_field => { 
          "alert_type" => "security"
          "requires_investigation" => "true"
        }
      }
    }
  }
}

output {
  elasticsearch {
    hosts => ["elasticsearch:9200"]
    index => "mqtt-logs-%{+YYYY.MM.dd}"
  }
  
  # 重要なアラートはSlackに通知
  if [severity] == "high" or [alert_type] == "security" {
    http {
      url => "https://hooks.slack.com/services/YOUR/SLACK/WEBHOOK"
      http_method => "post"
      format => "json"
      mapping => {
        "text" => "MQTT Alert: %{message}"
        "channel" => "#mqtt-alerts"
        "username" => "LogstashBot"
      }
    }
  }
}
```

### 10.3.3 Kibanaダッシュボードとアラート

```json
{
  "version": "8.11.0",
  "objects": [
    {
      "id": "mqtt-overview-dashboard",
      "type": "dashboard",
      "attributes": {
        "title": "MQTT System Overview",
        "panelsJSON": "[{\"id\":\"connection-status\",\"type\":\"visualization\",\"gridData\":{\"x\":0,\"y\":0,\"w\":24,\"h\":15}},{\"id\":\"message-volume\",\"type\":\"visualization\",\"gridData\":{\"x\":24,\"y\":0,\"w\":24,\"h\":15}},{\"id\":\"error-trends\",\"type\":\"visualization\",\"gridData\":{\"x\":0,\"y\":15,\"w\":48,\"h\":20}}]"
      }
    },
    {
      "id": "connection-status",
      "type": "visualization",
      "attributes": {
        "title": "Connection Events Over Time",
        "visState": {
          "type": "line",
          "params": {
            "categoryAxes": [{"id": "CategoryAxis-1", "type": "category", "position": "bottom"}],
            "valueAxes": [{"id": "ValueAxis-1", "type": "value", "position": "left"}]
          }
        },
        "kibanaSavedObjectMeta": {
          "searchSourceJSON": "{\"query\":{\"match\":{\"category\":\"connection\"}},\"filter\":[{\"range\":{\"@timestamp\":{\"gte\":\"now-1h\",\"lte\":\"now\"}}}],\"aggs\":{\"2\":{\"date_histogram\":{\"field\":\"@timestamp\",\"interval\":\"auto\"}}}}"
        }
      }
    }
  ]
}
```

## 10.4 パフォーマンス分析とチューニング

### 10.4.1 負荷テストツール

```python
import asyncio
import aiofiles
import json
import time
import statistics
from datetime import datetime, timedelta
import paho.mqtt.client as mqtt
from concurrent.futures import ThreadPoolExecutor
import argparse

class MQTTLoadTester:
    def __init__(self, config):
        self.config = config
        self.results = {
            'connections': [],
            'publishes': [],
            'subscribes': [],
            'latencies': [],
            'errors': []
        }
        self.active_clients = []
        self.message_count = 0
        self.error_count = 0
        
    async def run_load_test(self):
        """負荷テストの実行"""
        print(f"Starting MQTT load test...")
        print(f"Target: {self.config['broker_host']}:{self.config['broker_port']}")
        print(f"Clients: {self.config['num_clients']}")
        print(f"Duration: {self.config['duration_seconds']}s")
        print(f"Message rate: {self.config['messages_per_second']} msg/s")
        
        start_time = time.time()
        
        # クライアント接続
        await self.create_clients()
        
        # メッセージ送信タスク
        publish_task = asyncio.create_task(self.publish_messages())
        
        # 統計収集タスク
        stats_task = asyncio.create_task(self.collect_statistics())
        
        # テスト実行
        await asyncio.sleep(self.config['duration_seconds'])
        
        # クリーンアップ
        publish_task.cancel()
        stats_task.cancel()
        await self.disconnect_clients()
        
        # 結果レポート生成
        await self.generate_report(time.time() - start_time)
        
    async def create_clients(self):
        """MQTTクライアント作成"""
        tasks = []
        
        for i in range(self.config['num_clients']):
            task = asyncio.create_task(self.create_single_client(i))
            tasks.append(task)
            
            # 接続レート制限
            if i % 10 == 0:
                await asyncio.sleep(0.1)
                
        await asyncio.gather(*tasks)
        print(f"Created {len(self.active_clients)} clients")
        
    async def create_single_client(self, client_index):
        """単一クライアントの作成"""
        client_id = f"load_test_client_{client_index}_{int(time.time())}"
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                self.results['connections'].append({
                    'timestamp': time.time(),
                    'client_id': client_id,
                    'success': True
                })
            else:
                self.results['connections'].append({
                    'timestamp': time.time(),
                    'client_id': client_id,
                    'success': False,
                    'error_code': rc
                })
                
        def on_message(client, userdata, msg):
            receive_time = time.time()
            try:
                payload = json.loads(msg.payload.decode())
                send_time = payload.get('timestamp', receive_time)
                latency = (receive_time - send_time) * 1000  # ミリ秒
                
                self.results['latencies'].append({
                    'timestamp': receive_time,
                    'latency_ms': latency,
                    'topic': msg.topic
                })
            except:
                pass
                
        client = mqtt.Client(client_id=client_id)
        client.on_connect = on_connect
        client.on_message = on_message
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None, 
                lambda: client.connect(
                    self.config['broker_host'], 
                    self.config['broker_port'], 
                    60
                )
            )
            
            # バックグラウンドループ開始
            client.loop_start()
            
            # 購読設定
            if self.config.get('subscribe_topics'):
                for topic in self.config['subscribe_topics']:
                    client.subscribe(topic, qos=1)
                    
            self.active_clients.append(client)
            
        except Exception as e:
            self.results['errors'].append({
                'timestamp': time.time(),
                'client_id': client_id,
                'operation': 'connect',
                'error': str(e)
            })
            
    async def publish_messages(self):
        """メッセージ送信"""
        message_interval = 1.0 / self.config['messages_per_second']
        
        while True:
            try:
                if not self.active_clients:
                    await asyncio.sleep(1)
                    continue
                    
                # ランダムクライアントを選択
                import random
                client = random.choice(self.active_clients)
                
                # テストメッセージ作成
                message = {
                    'timestamp': time.time(),
                    'client_id': client._client_id.decode(),
                    'message_id': self.message_count,
                    'data': self.generate_test_data()
                }
                
                topic = self.config.get('publish_topic', 'test/load')
                
                # メッセージ送信
                result = client.publish(topic, json.dumps(message), qos=1)
                
                self.results['publishes'].append({
                    'timestamp': time.time(),
                    'message_id': self.message_count,
                    'client_id': client._client_id.decode(),
                    'topic': topic,
                    'success': result.rc == mqtt.MQTT_ERR_SUCCESS
                })
                
                self.message_count += 1
                
                await asyncio.sleep(message_interval)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.error_count += 1
                self.results['errors'].append({
                    'timestamp': time.time(),
                    'operation': 'publish',
                    'error': str(e)
                })
                
    def generate_test_data(self):
        """テストデータ生成"""
        import random
        
        data_types = self.config.get('data_types', ['sensor', 'status', 'alert'])
        data_type = random.choice(data_types)
        
        if data_type == 'sensor':
            return {
                'type': 'sensor_reading',
                'sensor_id': f'sensor_{random.randint(1, 100)}',
                'temperature': round(random.uniform(20.0, 30.0), 2),
                'humidity': round(random.uniform(40.0, 60.0), 2)
            }
        elif data_type == 'status':
            return {
                'type': 'device_status',
                'device_id': f'device_{random.randint(1, 50)}',
                'status': random.choice(['online', 'offline', 'maintenance']),
                'battery_level': random.randint(0, 100)
            }
        else:
            return {
                'type': 'alert',
                'alert_id': f'alert_{random.randint(1, 10)}',
                'severity': random.choice(['low', 'medium', 'high']),
                'message': 'Test alert message'
            }
            
    async def collect_statistics(self):
        """統計情報の収集"""
        while True:
            try:
                await asyncio.sleep(10)  # 10秒間隔
                
                # 現在の統計
                current_stats = {
                    'timestamp': time.time(),
                    'active_clients': len(self.active_clients),
                    'total_messages': self.message_count,
                    'total_errors': self.error_count
                }
                
                print(f"Stats: {current_stats}")
                
            except asyncio.CancelledError:
                break
                
    async def disconnect_clients(self):
        """クライアント切断"""
        print("Disconnecting clients...")
        
        for client in self.active_clients:
            try:
                client.loop_stop()
                client.disconnect()
            except:
                pass
                
        self.active_clients.clear()
        
    async def generate_report(self, total_duration):
        """テストレポート生成"""
        print("\n" + "="*50)
        print("MQTT Load Test Results")
        print("="*50)
        
        # 基本統計
        successful_connections = len([c for c in self.results['connections'] if c['success']])
        failed_connections = len(self.results['connections']) - successful_connections
        
        successful_publishes = len([p for p in self.results['publishes'] if p['success']])
        failed_publishes = len(self.results['publishes']) - successful_publishes
        
        print(f"Test Duration: {total_duration:.2f} seconds")
        print(f"Target Clients: {self.config['num_clients']}")
        print(f"Successful Connections: {successful_connections}")
        print(f"Failed Connections: {failed_connections}")
        print(f"Total Messages Sent: {len(self.results['publishes'])}")
        print(f"Successful Publishes: {successful_publishes}")
        print(f"Failed Publishes: {failed_publishes}")
        
        # レイテンシ統計
        if self.results['latencies']:
            latencies = [l['latency_ms'] for l in self.results['latencies']]
            print(f"\nLatency Statistics (ms):")
            print(f"  Average: {statistics.mean(latencies):.2f}")
            print(f"  Median: {statistics.median(latencies):.2f}")
            print(f"  95th Percentile: {sorted(latencies)[int(len(latencies) * 0.95)]:.2f}")
            print(f"  Max: {max(latencies):.2f}")
            print(f"  Min: {min(latencies):.2f}")
            
        # スループット
        messages_per_second = len(self.results['publishes']) / total_duration
        print(f"\nThroughput:")
        print(f"  Messages/second: {messages_per_second:.2f}")
        
        # エラー分析
        if self.results['errors']:
            print(f"\nErrors:")
            error_types = {}
            for error in self.results['errors']:
                error_type = error.get('operation', 'unknown')
                error_types[error_type] = error_types.get(error_type, 0) + 1
                
            for error_type, count in error_types.items():
                print(f"  {error_type}: {count}")
                
        # 結果をJSONファイルに保存
        report_filename = f"mqtt_load_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        report_data = {
            'config': self.config,
            'duration': total_duration,
            'summary': {
                'successful_connections': successful_connections,
                'failed_connections': failed_connections,
                'successful_publishes': successful_publishes,
                'failed_publishes': failed_publishes,
                'messages_per_second': messages_per_second
            },
            'detailed_results': self.results
        }
        
        async with aiofiles.open(report_filename, 'w') as f:
            await f.write(json.dumps(report_data, indent=2))
            
        print(f"\nDetailed report saved to: {report_filename}")

# コマンドライン実行
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='MQTT Load Testing Tool')
    parser.add_argument('--broker', default='localhost', help='MQTT broker hostname')
    parser.add_argument('--port', type=int, default=1883, help='MQTT broker port')
    parser.add_argument('--clients', type=int, default=100, help='Number of concurrent clients')
    parser.add_argument('--duration', type=int, default=60, help='Test duration in seconds')
    parser.add_argument('--rate', type=int, default=10, help='Messages per second')
    parser.add_argument('--topic', default='test/load', help='Publish topic')
    
    args = parser.parse_args()
    
    config = {
        'broker_host': args.broker,
        'broker_port': args.port,
        'num_clients': args.clients,
        'duration_seconds': args.duration,
        'messages_per_second': args.rate,
        'publish_topic': args.topic,
        'subscribe_topics': [args.topic],
        'data_types': ['sensor', 'status', 'alert']
    }
    
    tester = MQTTLoadTester(config)
    asyncio.run(tester.run_load_test())
```

## 10.5 一般的な問題と解決策

### 10.5.1 接続問題のトラブルシューティング

```python
import socket
import ssl
import time
from enum import Enum

class ConnectionIssueType(Enum):
    NETWORK_UNREACHABLE = "network_unreachable"
    CONNECTION_REFUSED = "connection_refused"
    SSL_HANDSHAKE_FAILED = "ssl_handshake_failed"
    AUTHENTICATION_FAILED = "authentication_failed"
    TIMEOUT = "timeout"
    PROTOCOL_VERSION_MISMATCH = "protocol_version_mismatch"

class MQTTConnectionDiagnostics:
    def __init__(self, broker_host, broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        
    def diagnose_connection_issues(self):
        """接続問題の診断"""
        print(f"Diagnosing connection to {self.broker_host}:{self.broker_port}")
        
        results = {
            'network_connectivity': self.test_network_connectivity(),
            'port_accessibility': self.test_port_accessibility(),
            'ssl_capability': self.test_ssl_capability(),
            'mqtt_response': self.test_mqtt_response(),
            'dns_resolution': self.test_dns_resolution()
        }
        
        # 総合診断結果
        self.generate_diagnosis_report(results)
        return results
        
    def test_network_connectivity(self):
        """ネットワーク接続テスト"""
        print("Testing network connectivity...")
        
        try:
            # ICMP ping (Pythonでは制限があるため、TCP接続でテスト)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((self.broker_host, self.broker_port))
            sock.close()
            
            if result == 0:
                return {'status': 'success', 'message': 'Network is reachable'}
            else:
                return {'status': 'failed', 'message': f'Network unreachable (error: {result})'}
                
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def test_port_accessibility(self):
        """ポートアクセシビリティテスト"""
        print("Testing port accessibility...")
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            
            start_time = time.time()
            result = sock.connect_ex((self.broker_host, self.broker_port))
            connect_time = time.time() - start_time
            
            sock.close()
            
            if result == 0:
                return {
                    'status': 'success', 
                    'message': f'Port {self.broker_port} is accessible',
                    'connect_time': connect_time
                }
            else:
                return {
                    'status': 'failed',
                    'message': f'Port {self.broker_port} is not accessible (error: {result})'
                }
                
        except socket.timeout:
            return {'status': 'failed', 'message': 'Connection timeout'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def test_ssl_capability(self):
        """SSL/TLS機能テスト"""
        if self.broker_port not in [8883, 443]:
            return {'status': 'skipped', 'message': 'SSL test skipped for non-SSL port'}
            
        print("Testing SSL/TLS capability...")
        
        try:
            context = ssl.create_default_context()
            
            with socket.create_connection((self.broker_host, self.broker_port), timeout=10) as sock:
                with context.wrap_socket(sock, server_hostname=self.broker_host) as ssock:
                    cert = ssock.getpeercert()
                    
                    return {
                        'status': 'success',
                        'message': 'SSL/TLS connection successful',
                        'certificate_info': {
                            'subject': dict(x[0] for x in cert['subject']),
                            'issuer': dict(x[0] for x in cert['issuer']),
                            'version': cert['version'],
                            'not_after': cert['notAfter']
                        }
                    }
                    
        except ssl.SSLError as e:
            return {'status': 'failed', 'message': f'SSL handshake failed: {e}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def test_mqtt_response(self):
        """MQTT固有のレスポンステスト"""
        print("Testing MQTT protocol response...")
        
        try:
            import paho.mqtt.client as mqtt
            
            test_result = {'status': 'unknown', 'message': ''}
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    test_result['status'] = 'success'
                    test_result['message'] = 'MQTT connection successful'
                    test_result['session_present'] = flags['session_present']
                else:
                    test_result['status'] = 'failed'
                    test_result['message'] = f'MQTT connection failed (code: {rc})'
                    test_result['return_code'] = rc
                    
                client.disconnect()
                
            def on_disconnect(client, userdata, rc):
                pass
                
            client = mqtt.Client(client_id="diagnostic_test")
            client.on_connect = on_connect
            client.on_disconnect = on_disconnect
            
            client.connect(self.broker_host, self.broker_port, 10)
            client.loop_start()
            
            # 接続結果を待機
            timeout = 15
            start_time = time.time()
            
            while test_result['status'] == 'unknown' and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            client.loop_stop()
            
            if test_result['status'] == 'unknown':
                test_result['status'] = 'timeout'
                test_result['message'] = 'MQTT connection timed out'
                
            return test_result
            
        except ImportError:
            return {'status': 'skipped', 'message': 'paho-mqtt library not available'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def test_dns_resolution(self):
        """DNS解決テスト"""
        print("Testing DNS resolution...")
        
        try:
            start_time = time.time()
            ip_addresses = socket.getaddrinfo(self.broker_host, self.broker_port)
            resolution_time = time.time() - start_time
            
            resolved_ips = list(set([addr[4][0] for addr in ip_addresses]))
            
            return {
                'status': 'success',
                'message': f'DNS resolution successful',
                'resolved_ips': resolved_ips,
                'resolution_time': resolution_time
            }
            
        except socket.gaierror as e:
            return {'status': 'failed', 'message': f'DNS resolution failed: {e}'}
        except Exception as e:
            return {'status': 'error', 'message': str(e)}
            
    def generate_diagnosis_report(self, results):
        """診断レポートの生成"""
        print("\n" + "="*60)
        print("CONNECTION DIAGNOSIS REPORT")
        print("="*60)
        
        overall_status = "HEALTHY"
        issues = []
        
        for test_name, result in results.items():
            status_symbol = "✓" if result['status'] == 'success' else "✗" if result['status'] == 'failed' else "?"
            print(f"{status_symbol} {test_name.replace('_', ' ').title()}: {result['message']}")
            
            if result['status'] == 'failed':
                overall_status = "ISSUES_DETECTED"
                issues.append(test_name)
            elif result['status'] == 'error':
                overall_status = "ERRORS_OCCURRED"
                issues.append(test_name)
                
        print(f"\nOverall Status: {overall_status}")
        
        if issues:
            print("\nRecommended Actions:")
            self.provide_recommendations(issues, results)
            
    def provide_recommendations(self, issues, results):
        """推奨アクションの提供"""
        recommendations = {
            'network_connectivity': [
                "1. Check network connectivity (ping, traceroute)",
                "2. Verify firewall rules",
                "3. Check proxy settings if applicable"
            ],
            'port_accessibility': [
                "1. Verify broker is running and listening on specified port",
                "2. Check firewall rules for the specific port",
                "3. Ensure no other service is using the port"
            ],
            'ssl_capability': [
                "1. Verify SSL certificate is valid and not expired",
                "2. Check certificate chain and CA certificates",
                "3. Ensure SSL/TLS version compatibility"
            ],
            'mqtt_response': [
                "1. Check MQTT broker logs for connection errors",
                "2. Verify authentication credentials",
                "3. Check MQTT protocol version compatibility",
                "4. Review broker configuration"
            ],
            'dns_resolution': [
                "1. Check DNS server configuration",
                "2. Try using IP address instead of hostname",
                "3. Verify /etc/hosts file entries"
            ]
        }
        
        for issue in issues:
            if issue in recommendations:
                print(f"\n{issue.replace('_', ' ').title()} Issues:")
                for rec in recommendations[issue]:
                    print(f"  {rec}")

# 使用例
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python mqtt_diagnostics.py <broker_host> [port]")
        sys.exit(1)
        
    broker_host = sys.argv[1]
    broker_port = int(sys.argv[2]) if len(sys.argv) > 2 else 1883
    
    diagnostics = MQTTConnectionDiagnostics(broker_host, broker_port)
    results = diagnostics.diagnose_connection_issues()
```

### 10.5.2 パフォーマンス問題の特定と解決

```python
class MQTTPerformanceAnalyzer:
    def __init__(self):
        self.metrics = {
            'connection_times': [],
            'publish_latencies': [],
            'throughput_samples': [],
            'memory_usage': [],
            'error_counts': defaultdict(int)
        }
        
    def analyze_broker_performance(self, broker_host, duration=300):
        """ブローカーパフォーマンス分析"""
        print(f"Analyzing broker performance for {duration} seconds...")
        
        # 複数の角度からパフォーマンス測定
        tasks = [
            self.measure_connection_performance(broker_host),
            self.measure_publish_performance(broker_host),
            self.measure_throughput(broker_host),
            self.monitor_resource_usage()
        ]
        
        # 並行実行
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            futures = [executor.submit(task) for task in tasks]
            concurrent.futures.wait(futures, timeout=duration)
            
        # 結果分析
        self.generate_performance_report()
        
    def measure_connection_performance(self, broker_host):
        """接続パフォーマンス測定"""
        for i in range(50):  # 50回の接続テスト
            start_time = time.time()
            
            try:
                client = mqtt.Client(f"perf_test_{i}")
                client.connect(broker_host, 1883, 60)
                client.loop_start()
                
                # 接続確認
                connected = False
                timeout = 5
                wait_start = time.time()
                
                while not connected and (time.time() - wait_start) < timeout:
                    if client.is_connected():
                        connected = True
                        break
                    time.sleep(0.01)
                    
                connection_time = time.time() - start_time
                
                if connected:
                    self.metrics['connection_times'].append(connection_time)
                else:
                    self.metrics['error_counts']['connection_timeout'] += 1
                    
                client.loop_stop()
                client.disconnect()
                
            except Exception as e:
                self.metrics['error_counts'][f'connection_error_{type(e).__name__}'] += 1
                
            time.sleep(0.1)  # レート制限
            
    def measure_publish_performance(self, broker_host):
        """発行パフォーマンス測定"""
        client = mqtt.Client("perf_publisher")
        
        def on_publish(client, userdata, mid):
            end_time = time.time()
            if mid in userdata['pending_publishes']:
                start_time = userdata['pending_publishes'][mid]
                latency = end_time - start_time
                self.metrics['publish_latencies'].append(latency)
                del userdata['pending_publishes'][mid]
                
        client.user_data_set({'pending_publishes': {}})
        client.on_publish = on_publish
        
        try:
            client.connect(broker_host, 1883, 60)
            client.loop_start()
            
            for i in range(1000):  # 1000メッセージのテスト
                start_time = time.time()
                message = json.dumps({
                    'timestamp': start_time,
                    'sequence': i,
                    'data': 'performance_test_payload'
                })
                
                result = client.publish('test/performance', message, qos=1)
                client._userdata['pending_publishes'][result.mid] = start_time
                
                time.sleep(0.01)  # 100 msg/sec rate
                
        except Exception as e:
            self.metrics['error_counts'][f'publish_error_{type(e).__name__}'] += 1
        finally:
            client.loop_stop()
            client.disconnect()
            
    def generate_performance_report(self):
        """パフォーマンスレポート生成"""
        print("\n" + "="*60)
        print("MQTT PERFORMANCE ANALYSIS REPORT")
        print("="*60)
        
        # 接続パフォーマンス
        if self.metrics['connection_times']:
            conn_times = self.metrics['connection_times']
            print(f"\nConnection Performance:")
            print(f"  Average: {statistics.mean(conn_times)*1000:.2f} ms")
            print(f"  Median: {statistics.median(conn_times)*1000:.2f} ms")
            print(f"  95th percentile: {sorted(conn_times)[int(len(conn_times)*0.95)]*1000:.2f} ms")
            print(f"  Max: {max(conn_times)*1000:.2f} ms")
            
        # 発行パフォーマンス
        if self.metrics['publish_latencies']:
            pub_latencies = self.metrics['publish_latencies']
            print(f"\nPublish Performance:")
            print(f"  Average latency: {statistics.mean(pub_latencies)*1000:.2f} ms")
            print(f"  Median latency: {statistics.median(pub_latencies)*1000:.2f} ms")
            print(f"  95th percentile: {sorted(pub_latencies)[int(len(pub_latencies)*0.95)]*1000:.2f} ms")
            
        # エラー統計
        if self.metrics['error_counts']:
            print(f"\nError Statistics:")
            for error_type, count in self.metrics['error_counts'].items():
                print(f"  {error_type}: {count}")
                
        # パフォーマンス推奨事項
        self.provide_performance_recommendations()
        
    def provide_performance_recommendations(self):
        """パフォーマンス改善推奨事項"""
        print(f"\nPerformance Recommendations:")
        
        # 接続時間が長い場合
        if self.metrics['connection_times'] and statistics.mean(self.metrics['connection_times']) > 1.0:
            print("  ⚠️  Slow connection times detected:")
            print("    - Check network latency to broker")
            print("    - Review broker connection limits")
            print("    - Consider connection pooling")
            
        # 発行レイテンシが高い場合
        if self.metrics['publish_latencies'] and statistics.mean(self.metrics['publish_latencies']) > 0.1:
            print("  ⚠️  High publish latency detected:")
            print("    - Check broker CPU and memory usage")
            print("    - Review QoS settings (consider QoS 0 for high volume)")
            print("    - Check message size and consider compression")
            
        # エラー率が高い場合
        total_operations = len(self.metrics['connection_times']) + len(self.metrics['publish_latencies'])
        total_errors = sum(self.metrics['error_counts'].values())
        
        if total_operations > 0 and (total_errors / total_operations) > 0.05:
            print("  ⚠️  High error rate detected:")
            print("    - Check broker logs for errors")
            print("    - Review network stability")
            print("    - Verify broker resource limits")
```

## 参考リンク

- [Prometheus MQTT Exporter](https://github.com/hikhvar/mqtt2prometheus)
- [Grafana MQTT Dashboard Templates](https://grafana.com/grafana/dashboards/?search=mqtt)
- [ELK Stack for IoT Logging](https://www.elastic.co/what-is/elk-stack)
- [MQTT Broker Performance Tuning](https://www.hivemq.com/blog/mqtt-performance-tuning/)
- [AWS IoT Core Metrics and Logs](https://docs.aws.amazon.com/iot/latest/developerguide/monitoring_overview.html)

---

これで、MQTTドキュメントシリーズの全10章が完成しました。初心者向けの基礎から上級者向けの監視・トラブルシューティングまで、包括的にカバーしています。