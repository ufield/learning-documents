# ハンズオン 07: MQTT 5.0 高度な機能

## 🎯 学習目標

このハンズオンではMQTT 5.0の高度な機能について学習します：

- MQTT 5.0の新機能と改善点の理解
- User Properties（ユーザープロパティ）の実装
- Request Response Pattern（リクエスト・レスポンスパターン）
- Topic Alias（トピックエイリアス）の活用
- Subscription Identifier（購読識別子）の使用
- Flow Control（フロー制御）とReceive Maximum
- Clean Start とSession Expiry Interval
- Reason Codes とエラーハンドリング

**所要時間**: 約120分

## 📋 前提条件

- [06-error-handling-reconnection](../06-error-handling-reconnection/) の完了
- MQTT 5.0対応ブローカーの準備（Eclipse Mosquitto 1.6+推奨）
- MQTT 3.1.1との違いの理解

## 🚀 MQTT 5.0 の主要な新機能

### 新機能概要

```
┌─────────────────────────────────────────────────────────┐
│                    MQTT 5.0 新機能                     │
├─────────────────────────────────────────────────────────┤
│ 1. Enhanced Authentication                             │
│    • SASL/SCRAM認証                                    │
│    • 多段階認証                                        │
│                                                         │
│ 2. User Properties                                      │
│    • カスタムヘッダー                                   │
│    • アプリケーション固有データ                         │
│                                                         │
│ 3. Topic Alias                                          │
│    • トピック名の短縮                                   │
│    • 帯域幅の節約                                       │
│                                                         │
│ 4. Request-Response                                     │
│    • 同期通信パターン                                   │
│    • Response Topic                                     │
│                                                         │
│ 5. Flow Control                                         │
│    • 受信制限                                           │
│    • バックプレッシャー                                 │
│                                                         │
│ 6. Enhanced Session Management                          │
│    • Clean Start flag                                   │
│    • Session Expiry Interval                            │
│                                                         │
│ 7. Improved Error Handling                              │
│    • Reason Codes                                       │
│    • Reason Strings                                     │
└─────────────────────────────────────────────────────────┘
```

## 📝 実装演習

### Exercise 1: User Properties と Enhanced Messaging

`src/mqtt5_user_properties.py` を作成：

```python
import paho.mqtt.client as mqtt
import paho.mqtt.properties as properties
import paho.mqtt.reasoncodes as reasoncodes
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.json import JSON

console = Console()

class MQTT5UserPropertiesClient:
    """MQTT 5.0 User Properties対応クライアント"""
    
    def __init__(self, client_id: str = None, broker_host: str = 'localhost', broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = client_id or f"mqtt5-client-{int(time.time())}"
        
        # MQTT 5.0クライアント作成
        self.client = mqtt.Client(
            client_id=self.client_id,
            protocol=mqtt.MQTTv5,  # MQTT 5.0を指定
            clean_session=None  # MQTT 5.0では使用しない
        )
        
        # 接続プロパティ設定
        self.connect_properties = properties.Properties(properties.PacketTypes.CONNECT)
        self.connect_properties.SessionExpiryInterval = 300  # 5分
        self.connect_properties.ReceiveMaximum = 10
        self.connect_properties.MaximumPacketSize = 1024 * 1024  # 1MB
        self.connect_properties.TopicAliasMaximum = 10
        
        # ユーザープロパティ追加
        self.connect_properties.UserProperty = [
            ("client_type", "advanced_mqtt5_client"),
            ("version", "1.0.0"),
            ("capabilities", "user_properties,topic_alias,request_response")
        ]
        
        self.is_connected = False
        self.topic_aliases = {}  # トピック名 -> エイリアス番号
        self.alias_counter = 1
        
        self.setup_callbacks()
    
    def setup_callbacks(self):
        """コールバック関数の設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, reasonCode, properties=None):
        """接続時のコールバック（MQTT 5.0版）"""
        if reasonCode.is_failure:
            console.print(f"❌ 接続失敗: {reasonCode}", style="bold red")
            if properties and hasattr(properties, 'ReasonString'):
                console.print(f"   理由: {properties.ReasonString}", style="red")
            return
        
        console.print("✅ MQTT 5.0 ブローカーに接続成功", style="bold green")
        self.is_connected = True
        
        # サーバーから返されたプロパティを表示
        if properties:
            console.print("📋 サーバーから受信したプロパティ:", style="blue")
            
            if hasattr(properties, 'SessionExpiryInterval'):
                console.print(f"   Session Expiry: {properties.SessionExpiryInterval}秒")
            
            if hasattr(properties, 'ReceiveMaximum'):
                console.print(f"   Receive Maximum: {properties.ReceiveMaximum}")
            
            if hasattr(properties, 'TopicAliasMaximum'):
                console.print(f"   Topic Alias Maximum: {properties.TopicAliasMaximum}")
            
            if hasattr(properties, 'UserProperty'):
                console.print("   User Properties:")
                for key, value in properties.UserProperty:
                    console.print(f"     {key}: {value}")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック（MQTT 5.0版）"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        props = msg.properties
        
        console.print(f"📬 メッセージ受信", style="bold cyan")
        console.print(f"   Topic: {topic}", style="blue")
        console.print(f"   QoS: {msg.qos}", style="blue")
        console.print(f"   Retain: {msg.retain}", style="blue")
        
        # MQTT 5.0固有のプロパティを表示
        if props:
            self._display_message_properties(props)
        
        # ペイロードを表示
        try:
            # JSONとして解析を試行
            json_data = json.loads(payload)
            console.print("   Payload (JSON):", style="green")
            console.print(JSON.from_data(json_data))
        except json.JSONDecodeError:
            console.print(f"   Payload: {payload}", style="green")
        
        console.print()  # 空行
    
    def on_publish(self, client, userdata, mid, reasonCode=None, properties=None):
        """メッセージ送信完了時のコールバック（MQTT 5.0版）"""
        if reasonCode and reasonCode.is_failure:
            console.print(f"❌ 送信失敗: {reasonCode}", style="red")
        else:
            console.print(f"✅ メッセージ送信完了 (MID: {mid})", style="green")
    
    def on_subscribe(self, client, userdata, mid, reasonCodes, properties=None):
        """購読完了時のコールバック（MQTT 5.0版）"""
        console.print("✅ 購読完了", style="green")
        for i, code in enumerate(reasonCodes):
            if code.is_failure:
                console.print(f"   購読 {i+1}: 失敗 ({code})", style="red")
            else:
                console.print(f"   購読 {i+1}: 成功 (QoS: {code.value})", style="green")
    
    def on_disconnect(self, client, userdata, reasonCode, properties=None):
        """切断時のコールバック（MQTT 5.0版）"""
        self.is_connected = False
        if reasonCode.is_failure:
            console.print(f"⚠️  予期しない切断: {reasonCode}", style="yellow")
        else:
            console.print("👋 正常に切断しました", style="blue")
    
    def _display_message_properties(self, props):
        """メッセージプロパティの表示"""
        console.print("   MQTT 5.0 Properties:", style="magenta")
        
        if hasattr(props, 'PayloadFormatIndicator'):
            format_type = "UTF-8 String" if props.PayloadFormatIndicator == 1 else "Binary"
            console.print(f"     Payload Format: {format_type}")
        
        if hasattr(props, 'MessageExpiryInterval'):
            console.print(f"     Message Expiry: {props.MessageExpiryInterval}秒")
        
        if hasattr(props, 'TopicAlias'):
            console.print(f"     Topic Alias: {props.TopicAlias}")
        
        if hasattr(props, 'ResponseTopic'):
            console.print(f"     Response Topic: {props.ResponseTopic}")
        
        if hasattr(props, 'CorrelationData'):
            console.print(f"     Correlation Data: {props.CorrelationData}")
        
        if hasattr(props, 'UserProperty'):
            console.print("     User Properties:")
            for key, value in props.UserProperty:
                console.print(f"       {key}: {value}")
        
        if hasattr(props, 'ContentType'):
            console.print(f"     Content Type: {props.ContentType}")
    
    def connect(self) -> bool:
        """ブローカーに接続"""
        console.print(f"🔌 MQTT 5.0 ブローカー接続中: {self.broker_host}:{self.broker_port}", style="blue")
        
        try:
            # Clean Startフラグを設定（MQTT 5.0の新機能）
            self.client.connect(
                host=self.broker_host,
                port=self.broker_port,
                keepalive=60,
                properties=self.connect_properties,
                clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY  # 初回のみクリーンスタート
            )
            
            self.client.loop_start()
            
            # 接続完了まで待機
            timeout = 10
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            return self.is_connected
            
        except Exception as e:
            console.print(f"❌ 接続エラー: {e}", style="bold red")
            return False
    
    def publish_with_user_properties(self,
                                   topic: str,
                                   payload: Any,
                                   qos: int = 1,
                                   retain: bool = False,
                                   user_properties: List[Tuple[str, str]] = None,
                                   content_type: str = None,
                                   message_expiry: int = None,
                                   response_topic: str = None,
                                   correlation_data: bytes = None,
                                   use_topic_alias: bool = False) -> bool:
        """User Properties付きメッセージ送信"""
        
        if not self.is_connected:
            console.print("❌ ブローカーに接続されていません", style="bold red")
            return False
        
        # Publishプロパティを作成
        publish_props = properties.Properties(properties.PacketTypes.PUBLISH)
        
        # ペイロードフォーマットを設定
        if isinstance(payload, (dict, list)):
            payload_str = json.dumps(payload, ensure_ascii=False)
            publish_props.PayloadFormatIndicator = 1  # UTF-8 String
        else:
            payload_str = str(payload)
            publish_props.PayloadFormatIndicator = 1
        
        # User Propertiesを設定
        if user_properties:
            publish_props.UserProperty = user_properties
        
        # Content Typeを設定
        if content_type:
            publish_props.ContentType = content_type
        
        # Message Expiry Intervalを設定
        if message_expiry:
            publish_props.MessageExpiryInterval = message_expiry
        
        # Response Topicを設定（Request-Response用）
        if response_topic:
            publish_props.ResponseTopic = response_topic
        
        # Correlation Dataを設定
        if correlation_data:
            publish_props.CorrelationData = correlation_data
        
        # Topic Aliasを使用
        actual_topic = topic
        if use_topic_alias:
            if topic in self.topic_aliases:
                # 既存のエイリアスを使用
                publish_props.TopicAlias = self.topic_aliases[topic]
                actual_topic = ""  # エイリアス使用時はトピック名を空にできる
            else:
                # 新しいエイリアスを作成
                if self.alias_counter <= 10:  # TopicAliasMaximumの範囲内
                    alias_num = self.alias_counter
                    self.topic_aliases[topic] = alias_num
                    publish_props.TopicAlias = alias_num
                    self.alias_counter += 1
                    console.print(f"🏷️  新しいTopic Alias作成: {topic} -> {alias_num}", style="yellow")
        
        try:
            # メッセージ送信
            console.print(f"📤 MQTT 5.0メッセージ送信: {topic}", style="blue")
            if user_properties:
                console.print("   User Properties:", style="dim")
                for key, value in user_properties:
                    console.print(f"     {key}: {value}", style="dim")
            
            result = self.client.publish(
                topic=actual_topic,
                payload=payload_str,
                qos=qos,
                retain=retain,
                properties=publish_props
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                return True
            else:
                console.print(f"❌ 送信失敗: {result.rc}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ 送信例外: {e}", style="bold red")
            return False
    
    def subscribe_with_options(self,
                             subscriptions: List[Tuple[str, int]],
                             subscription_identifier: int = None,
                             user_properties: List[Tuple[str, str]] = None) -> bool:
        """Subscription Options付き購読"""
        
        if not self.is_connected:
            console.print("❌ ブローカーに接続されていません", style="bold red")
            return False
        
        # Subscribeプロパティを作成
        subscribe_props = properties.Properties(properties.PacketTypes.SUBSCRIBE)
        
        # Subscription Identifierを設定
        if subscription_identifier:
            subscribe_props.SubscriptionIdentifier = subscription_identifier
        
        # User Propertiesを設定
        if user_properties:
            subscribe_props.UserProperty = user_properties
        
        try:
            console.print("📥 MQTT 5.0 購読開始:", style="blue")
            for topic, qos in subscriptions:
                console.print(f"   {topic} (QoS: {qos})", style="dim")
            
            if subscription_identifier:
                console.print(f"   Subscription ID: {subscription_identifier}", style="dim")
            
            result = self.client.subscribe(
                subscriptions,
                properties=subscribe_props
            )
            
            return result[0] == mqtt.MQTT_ERR_SUCCESS
            
        except Exception as e:
            console.print(f"❌ 購読例外: {e}", style="bold red")
            return False
    
    def disconnect(self, reason_code=None, reason_string: str = None, user_properties: List[Tuple[str, str]] = None):
        """切断（MQTT 5.0対応）"""
        if not self.is_connected:
            return
        
        # Disconnectプロパティを作成
        disconnect_props = properties.Properties(properties.PacketTypes.DISCONNECT)
        
        if reason_string:
            disconnect_props.ReasonString = reason_string
        
        if user_properties:
            disconnect_props.UserProperty = user_properties
        
        console.print("👋 MQTT 5.0 クライアント切断中...", style="yellow")
        
        try:
            self.client.disconnect(
                reasoncode=reason_code or reasoncodes.ReasonCodes(reasoncodes.PacketTypes.DISCONNECT, "Normal disconnection"),
                properties=disconnect_props
            )
            self.client.loop_stop()
        except Exception as e:
            console.print(f"❌ 切断エラー: {e}", style="red")

# Exercise 2: Request-Response Pattern
class MQTT5RequestResponseClient:
    """MQTT 5.0 Request-Response パターンの実装"""
    
    def __init__(self, client_id: str = None):
        self.client_id = client_id or f"req-resp-{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv5)
        
        # レスポンス待機用
        self.pending_requests = {}  # correlation_id -> callback
        self.response_topic = f"response/{self.client_id}"
        
        self.setup_callbacks()
    
    def setup_callbacks(self):
        """コールバック設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, reasonCode, properties=None):
        """接続時のコールバック"""
        if not reasonCode.is_failure:
            console.print("✅ Request-Response クライアント接続完了", style="green")
            # 自分のレスポンストピックに購読
            client.subscribe(self.response_topic)
        else:
            console.print(f"❌ 接続失敗: {reasonCode}", style="red")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信（レスポンス処理）"""
        props = msg.properties
        
        # Correlation Dataを確認
        if hasattr(props, 'CorrelationData'):
            correlation_id = props.CorrelationData.decode('utf-8')
            
            if correlation_id in self.pending_requests:
                # 対応するリクエストのコールバックを実行
                callback = self.pending_requests[correlation_id]
                payload = msg.payload.decode('utf-8')
                
                try:
                    response_data = json.loads(payload)
                except json.JSONDecodeError:
                    response_data = payload
                
                # コールバック実行
                callback(response_data, props)
                
                # 完了したリクエストを削除
                del self.pending_requests[correlation_id]
                
                console.print(f"✅ レスポンス受信完了: {correlation_id}", style="green")
            else:
                console.print(f"⚠️  不明なCorrelation ID: {correlation_id}", style="yellow")
        else:
            console.print("📬 通常メッセージ受信", style="cyan")
            console.print(f"   Topic: {msg.topic}")
            console.print(f"   Payload: {msg.payload.decode('utf-8')}")
    
    def connect(self, broker_host: str = 'localhost', broker_port: int = 1883) -> bool:
        """ブローカーに接続"""
        try:
            self.client.connect(broker_host, broker_port, 60)
            self.client.loop_start()
            
            # 接続完了まで待機
            time.sleep(2)
            return True
        except Exception as e:
            console.print(f"❌ 接続エラー: {e}", style="red")
            return False
    
    def send_request(self,
                    request_topic: str,
                    request_data: Any,
                    callback,
                    timeout: int = 30,
                    user_properties: List[Tuple[str, str]] = None) -> str:
        """リクエスト送信"""
        
        # Correlation IDを生成
        correlation_id = str(uuid.uuid4())
        
        # リクエストプロパティを設定
        request_props = properties.Properties(properties.PacketTypes.PUBLISH)
        request_props.ResponseTopic = self.response_topic
        request_props.CorrelationData = correlation_id.encode('utf-8')
        
        if user_properties:
            request_props.UserProperty = user_properties
        
        # ペイロード準備
        if isinstance(request_data, (dict, list)):
            payload = json.dumps(request_data, ensure_ascii=False)
            request_props.ContentType = "application/json"
        else:
            payload = str(request_data)
            request_props.ContentType = "text/plain"
        
        # リクエストを登録
        self.pending_requests[correlation_id] = callback
        
        try:
            console.print(f"📤 リクエスト送信: {request_topic}", style="blue")
            console.print(f"   Correlation ID: {correlation_id}", style="dim")
            console.print(f"   Response Topic: {self.response_topic}", style="dim")
            
            result = self.client.publish(
                topic=request_topic,
                payload=payload,
                qos=1,
                properties=request_props
            )
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                # タイムアウト処理を設定
                def timeout_handler():
                    time.sleep(timeout)
                    if correlation_id in self.pending_requests:
                        del self.pending_requests[correlation_id]
                        console.print(f"⏰ リクエストタイムアウト: {correlation_id}", style="yellow")
                
                import threading
                threading.Thread(target=timeout_handler, daemon=True).start()
                
                return correlation_id
            else:
                # 失敗した場合はリクエストを削除
                if correlation_id in self.pending_requests:
                    del self.pending_requests[correlation_id]
                console.print(f"❌ リクエスト送信失敗: {result.rc}", style="red")
                return None
                
        except Exception as e:
            if correlation_id in self.pending_requests:
                del self.pending_requests[correlation_id]
            console.print(f"❌ リクエスト送信例外: {e}", style="red")
            return None
    
    def disconnect(self):
        """切断"""
        self.client.loop_stop()
        self.client.disconnect()

# デモンストレーション関数
def demonstrate_user_properties():
    """User Properties デモンストレーション"""
    console.print("🏷️  MQTT 5.0 User Properties デモ", style="bold blue")
    
    client = MQTT5UserPropertiesClient()
    
    if not client.connect():
        console.print("❌ 接続に失敗しました", style="bold red")
        return
    
    # 購読（Subscription Identifierと User Properties付き）
    client.subscribe_with_options(
        subscriptions=[("test/mqtt5/demo", 1)],
        subscription_identifier=100,
        user_properties=[
            ("subscriber_type", "demo_client"),
            ("features", "user_properties,subscription_id")
        ]
    )
    
    time.sleep(1)  # 購読完了待ち
    
    try:
        # 様々なUser Properties付きメッセージを送信
        console.print("\n📤 User Properties付きメッセージ送信テスト:", style="bold blue")
        
        # 1. 基本的なUser Properties
        client.publish_with_user_properties(
            topic="test/mqtt5/demo",
            payload={"message": "Hello MQTT 5.0!", "timestamp": time.time()},
            user_properties=[
                ("sender", "demo_publisher"),
                ("priority", "high"),
                ("category", "demo")
            ],
            content_type="application/json",
            message_expiry=300
        )
        
        time.sleep(2)
        
        # 2. Topic Alias を使用
        console.print("\n🏷️  Topic Alias使用例:", style="bold yellow")
        client.publish_with_user_properties(
            topic="test/mqtt5/demo",
            payload={"message": "Topic Aliasテスト", "alias_test": True},
            user_properties=[("test_type", "topic_alias")],
            use_topic_alias=True
        )
        
        time.sleep(2)
        
        # 3. 同じトピックに再度送信（エイリアス再利用）
        client.publish_with_user_properties(
            topic="test/mqtt5/demo",
            payload={"message": "エイリアス再利用", "reuse": True},
            user_properties=[("test_type", "alias_reuse")],
            use_topic_alias=True
        )
        
        time.sleep(2)
        
        # 4. Request-Response パターンのデモ
        console.print("\n🔄 Request-Response パターンデモ:", style="bold green")
        
        response_client = MQTT5RequestResponseClient()
        if response_client.connect():
            def response_handler(response_data, props):
                console.print("📨 レスポンス受信:", style="green")
                console.print(f"   Data: {response_data}")
                if hasattr(props, 'UserProperty'):
                    console.print("   User Properties:")
                    for key, value in props.UserProperty:
                        console.print(f"     {key}: {value}")
            
            # リクエスト送信
            correlation_id = response_client.send_request(
                request_topic="test/mqtt5/request",
                request_data={"query": "get_server_status", "client_id": response_client.client_id},
                callback=response_handler,
                user_properties=[
                    ("request_type", "status_query"),
                    ("client_version", "1.0.0")
                ]
            )
            
            if correlation_id:
                console.print(f"✅ リクエスト送信完了: {correlation_id}", style="green")
                
                # 模擬レスポンス送信（実際のサーバー応答をシミュレート）
                time.sleep(1)
                mock_response_props = properties.Properties(properties.PacketTypes.PUBLISH)
                mock_response_props.CorrelationData = correlation_id.encode('utf-8')
                mock_response_props.UserProperty = [
                    ("response_type", "status_response"),
                    ("server_version", "2.0.0"),
                    ("status", "healthy")
                ]
                
                response_data = {
                    "server_status": "online",
                    "uptime": 12345,
                    "active_clients": 42
                }
                
                client.client.publish(
                    response_client.response_topic,
                    json.dumps(response_data),
                    qos=1,
                    properties=mock_response_props
                )
                
                console.print("✅ 模擬レスポンス送信完了", style="green")
            
            time.sleep(3)  # レスポンス受信待ち
            response_client.disconnect()
        
        console.print("\n⏱️  10秒間メッセージ監視中...", style="dim")
        time.sleep(10)
        
    except KeyboardInterrupt:
        console.print("\n⚠️  デモ中断", style="yellow")
    finally:
        client.disconnect(
            reason_string="Demo completed",
            user_properties=[("disconnect_reason", "demo_end")]
        )
        console.print("✅ User Properties デモ完了", style="bold green")

def demonstrate_flow_control():
    """Flow Control デモンストレーション"""
    console.print("🌊 MQTT 5.0 Flow Control デモ", style="bold blue")
    
    # Receive Maximum を小さく設定したクライアント
    client = mqtt.Client(client_id="flow-control-demo", protocol=mqtt.MQTTv5)
    
    # 接続プロパティでReceive Maximumを設定
    connect_props = properties.Properties(properties.PacketTypes.CONNECT)
    connect_props.ReceiveMaximum = 3  # 同時に処理できるQoS1/2メッセージを3つに制限
    
    def on_connect(client, userdata, flags, reasonCode, properties):
        if not reasonCode.is_failure:
            console.print("✅ Flow Control クライアント接続完了", style="green")
            console.print(f"   Receive Maximum: {connect_props.ReceiveMaximum}", style="dim")
        else:
            console.print(f"❌ 接続失敗: {reasonCode}", style="red")
    
    def on_message(client, userdata, msg):
        console.print(f"📬 メッセージ受信: {msg.topic} (QoS: {msg.qos})", style="cyan")
        # メッセージ処理に時間をかけることで、フロー制御の効果を確認
        time.sleep(2)
        console.print(f"✅ メッセージ処理完了: {msg.topic}", style="green")
    
    client.on_connect = on_connect
    client.on_message = on_message
    
    try:
        client.connect('localhost', 1883, 60, properties=connect_props)
        client.loop_start()
        
        time.sleep(2)  # 接続完了待ち
        
        # テストトピックに購読
        client.subscribe("test/flow-control/+", qos=1)
        
        # 別のクライアントで大量のメッセージを送信
        publisher = mqtt.Client(client_id="flow-control-publisher", protocol=mqtt.MQTTv5)
        publisher.connect('localhost', 1883, 60)
        publisher.loop_start()
        
        console.print("\n📤 大量メッセージ送信中（Flow Controlの効果を確認）...", style="blue")
        
        for i in range(10):
            message = f"Flow Control Test Message #{i+1}"
            result = publisher.publish(f"test/flow-control/msg-{i+1}", message, qos=1)
            console.print(f"   送信: Message #{i+1}", style="dim")
            time.sleep(0.5)  # 短い間隔で送信
        
        console.print("\n⏱️  20秒間メッセージ処理を監視中...", style="dim")
        time.sleep(20)
        
        publisher.loop_stop()
        publisher.disconnect()
        
    except KeyboardInterrupt:
        console.print("\n⚠️  Flow Control デモ中断", style="yellow")
    finally:
        client.loop_stop()
        client.disconnect()
        console.print("✅ Flow Control デモ完了", style="bold green")

# メイン実行
def main():
    """メイン実行関数"""
    console.print("🚀 MQTT 5.0 Advanced Features Demo", style="bold blue")
    
    demos = [
        ("User Properties & Topic Alias", demonstrate_user_properties),
        ("Flow Control", demonstrate_flow_control)
    ]
    
    for i, (name, demo_func) in enumerate(demos):
        console.print(f"\n{'='*60}", style="dim")
        console.print(f"Demo {i+1}/{len(demos)}: {name}", style="bold yellow")
        console.print('='*60, style="dim")
        
        try:
            demo_func()
        except KeyboardInterrupt:
            console.print(f"\n⚠️  {name} デモが中断されました", style="yellow")
            break
        except Exception as e:
            console.print(f"❌ {name} デモでエラー: {e}", style="red")
        
        if i < len(demos) - 1:
            console.print("\n⏳ 次のデモまで5秒待機...", style="dim")
            time.sleep(5)
    
    console.print("\n🎉 全てのMQTT 5.0デモが完了しました！", style="bold green")

if __name__ == "__main__":
    main()
```

### Exercise 2: Session Management と Clean Start

`src/mqtt5_session_management.py` を作成：

```python
import paho.mqtt.client as mqtt
import paho.mqtt.properties as properties
import time
import json
from typing import Optional, List, Tuple
from rich.console import Console
from rich.table import Table

console = Console()

class MQTT5SessionManager:
    """MQTT 5.0 セッション管理クラス"""
    
    def __init__(self, client_id: str, broker_host: str = 'localhost', broker_port: int = 1883):
        self.client_id = client_id
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.session_present = False
        
    def connect_with_clean_start(self, 
                                clean_start: bool = True,
                                session_expiry_interval: int = 0,
                                user_properties: List[Tuple[str, str]] = None) -> mqtt.Client:
        """Clean StartとSession Expiry設定での接続"""
        
        client = mqtt.Client(client_id=self.client_id, protocol=mqtt.MQTTv5)
        
        # 接続プロパティを設定
        connect_props = properties.Properties(properties.PacketTypes.CONNECT)
        connect_props.SessionExpiryInterval = session_expiry_interval
        
        if user_properties:
            connect_props.UserProperty = user_properties
        
        def on_connect(client, userdata, flags, reasonCode, properties):
            if not reasonCode.is_failure:
                # Session Present フラグを確認
                session_present = flags.get('session present', False)
                self.session_present = session_present
                
                console.print("✅ MQTT 5.0 接続成功", style="bold green")
                console.print(f"   Clean Start: {clean_start}", style="blue")
                console.print(f"   Session Present: {session_present}", style="blue")
                console.print(f"   Session Expiry: {session_expiry_interval}秒", style="blue")
                
                if properties and hasattr(properties, 'SessionExpiryInterval'):
                    console.print(f"   Server Session Expiry: {properties.SessionExpiryInterval}秒", style="dim")
            else:
                console.print(f"❌ 接続失敗: {reasonCode}", style="red")
        
        client.on_connect = on_connect
        
        try:
            clean_start_flag = mqtt.MQTT_CLEAN_START_FIRST_ONLY if clean_start else False
            
            client.connect(
                host=self.broker_host,
                port=self.broker_port,
                keepalive=60,
                properties=connect_props,
                clean_start=clean_start_flag
            )
            
            client.loop_start()
            time.sleep(2)  # 接続完了待ち
            
            return client
            
        except Exception as e:
            console.print(f"❌ 接続エラー: {e}", style="red")
            return None

def demonstrate_session_management():
    """セッション管理のデモンストレーション"""
    console.print("📊 MQTT 5.0 Session Management デモ", style="bold blue")
    
    session_manager = MQTT5SessionManager("session-demo-client")
    
    # フェーズ1: Clean Start = True でセッション作成
    console.print("\n🔹 Phase 1: Clean Startでセッション作成", style="bold yellow")
    
    client1 = session_manager.connect_with_clean_start(
        clean_start=True,
        session_expiry_interval=60,  # 60秒でセッション期限切れ
        user_properties=[("phase", "session_creation")]
    )
    
    if client1:
        # 購読を作成（セッションに保存される）
        console.print("📥 購読を作成中...", style="blue")
        client1.subscribe("test/session/messages", qos=1)
        client1.subscribe("test/session/alerts", qos=2)
        
        time.sleep(2)
        
        # 切断（セッションは保持される）
        console.print("👋 切断中（セッション保持）...", style="yellow")
        client1.loop_stop()
        client1.disconnect()
        
        time.sleep(3)
    
    # フェーズ2: Clean Start = False で再接続
    console.print("\n🔹 Phase 2: Clean Start=Falseで再接続", style="bold yellow")
    
    client2 = session_manager.connect_with_clean_start(
        clean_start=False,  # セッションを再開
        session_expiry_interval=120,  # セッション期限を延長
        user_properties=[("phase", "session_resume")]
    )
    
    if client2:
        message_count = 0
        
        def on_message(client, userdata, msg):
            nonlocal message_count
            message_count += 1
            console.print(f"📬 セッション復旧後メッセージ #{message_count}: {msg.topic}", style="green")
        
        client2.on_message = on_message
        
        # セッションが復旧していれば、以前の購読が有効なはず
        if session_manager.session_present:
            console.print("✅ セッション復旧確認済み - 以前の購読が有効", style="green")
        else:
            console.print("⚠️  新しいセッション - 以前の購読は無効", style="yellow")
        
        # テストメッセージを送信
        publisher = mqtt.Client(protocol=mqtt.MQTTv5)
        publisher.connect('localhost', 1883, 60)
        publisher.loop_start()
        
        console.print("📤 テストメッセージ送信中...", style="blue")
        publisher.publish("test/session/messages", "Session Test Message 1", qos=1)
        publisher.publish("test/session/alerts", "Session Alert Test", qos=2)
        
        time.sleep(3)  # メッセージ受信待ち
        
        publisher.loop_stop()
        publisher.disconnect()
        
        # フェーズ3: セッション期限切れテスト
        console.print("\n🔹 Phase 3: セッション期限切れテスト", style="bold yellow")
        console.print("⏰ 70秒待機してセッション期限切れを確認...", style="dim")
        
        # 切断
        client2.loop_stop()
        client2.disconnect()
        
        # セッション期限切れを待つ（デモ用に短縮）
        time.sleep(10)  # 実際は60秒+ waiting time
        
        # フェーズ4: セッション期限切れ後の再接続
        console.print("\n🔹 Phase 4: セッション期限切れ後の再接続", style="bold yellow")
        
        client3 = session_manager.connect_with_clean_start(
            clean_start=False,
            session_expiry_interval=60,
            user_properties=[("phase", "expired_session_test")]
        )
        
        if client3:
            if not session_manager.session_present:
                console.print("✅ 期待通りセッション期限切れ確認", style="green")
                console.print("   新しいセッションが開始されました", style="dim")
            else:
                console.print("⚠️  セッションがまだ有効です", style="yellow")
            
            time.sleep(2)
            client3.loop_stop()
            client3.disconnect()

def demonstrate_enhanced_auth():
    """Enhanced Authentication のデモ（基本例）"""
    console.print("🔐 Enhanced Authentication デモ", style="bold blue")
    
    # 注意: 実際のEnhanced Authenticationには対応ブローカーとより複雑な実装が必要
    console.print("ℹ️  Enhanced Authentication は高度な機能です", style="dim")
    console.print("   実際の実装にはSASL/SCRAM対応ブローカーが必要です", style="dim")
    
    client = mqtt.Client(client_id="enhanced-auth-demo", protocol=mqtt.MQTTv5)
    
    # 認証プロパティの設定例
    connect_props = properties.Properties(properties.PacketTypes.CONNECT)
    
    # User Propertyで認証情報を送信（実際のEnhanced Authとは異なる簡易例）
    connect_props.UserProperty = [
        ("auth_method", "demo_auth"),
        ("auth_version", "1.0"),
        ("client_type", "enhanced_demo")
    ]
    
    def on_connect(client, userdata, flags, reasonCode, properties):
        if not reasonCode.is_failure:
            console.print("✅ Enhanced Auth デモ接続成功", style="green")
            
            if properties and hasattr(properties, 'UserProperty'):
                console.print("📋 サーバーからの認証レスポンス:")
                for key, value in properties.UserProperty:
                    console.print(f"   {key}: {value}")
        else:
            console.print(f"❌ 認証失敗: {reasonCode}", style="red")
    
    client.on_connect = on_connect
    
    try:
        console.print("🔐 Enhanced Auth接続試行中...", style="blue")
        client.connect('localhost', 1883, 60, properties=connect_props)
        client.loop_start()
        
        time.sleep(3)
        
        client.loop_stop()
        client.disconnect()
        
    except Exception as e:
        console.print(f"❌ Enhanced Auth エラー: {e}", style="red")
    
    console.print("✅ Enhanced Auth デモ完了", style="green")

def main():
    """メイン実行関数"""
    console.print("🎛️  MQTT 5.0 Session Management & Enhanced Auth Demo", style="bold blue")
    
    try:
        # Session Management デモ
        demonstrate_session_management()
        
        console.print("\n" + "="*60, style="dim")
        console.print("⏳ 次のデモまで3秒待機...", style="dim")
        time.sleep(3)
        
        # Enhanced Authentication デモ
        demonstrate_enhanced_auth()
        
    except KeyboardInterrupt:
        console.print("\n⚠️  デモ中断", style="yellow")
    except Exception as e:
        console.print(f"❌ デモエラー: {e}", style="red")
    
    console.print("\n🎉 Session Management デモ完了！", style="bold green")

if __name__ == "__main__":
    main()
```

## 🎯 練習問題

### 問題1: User Properties の活用
1. `mqtt5_user_properties.py`を実行して、User Propertiesの動作を確認してください
2. 独自のUser Propertiesを追加してメッセージングシステムを拡張してください

### 問題2: Request-Response パターン
1. Request-Responseパターンを使用してRESTful APIライクなサービスを実装してください
2. タイムアウト機能とエラーハンドリングを含めてください

### 問題3: Session Management
1. `mqtt5_session_management.py`を実行してセッション管理を確認してください
2. 異なるSession Expiry Intervalでの動作を比較してください

### 問題4: Topic Alias の最適化
IoTデバイス用にTopic Aliasを活用した帯域幅効率化システムを実装してください：
- 長いトピック名の自動エイリアス化
- エイリアス管理の最適化
- 帯域幅節約効果の測定

## ✅ 確認チェックリスト

- [ ] MQTT 5.0の主要新機能を理解した
- [ ] User Propertiesを効果的に活用できた
- [ ] Request-Responseパターンを実装した
- [ ] Topic Aliasによる帯域幅節約を確認した
- [ ] Session ManagementとClean Startを理解した
- [ ] Flow Controlメカニズムを確認した
- [ ] Enhanced Authenticationの概念を理解した
- [ ] Reason Codesとエラーハンドリングを実装した

## 📊 理解度チェック

以下の質問に答えられるか確認してください：

1. User PropertiesとMQTT 3.1.1のペイロード埋め込みの違いは？
2. Topic Aliasはどのような場面で効果的ですか？
3. Clean StartとSession Expiry Intervalの関係は？
4. Request-ResponseパターンでのCorrelation Dataの役割は？
5. Flow ControlのReceive Maximumはどのような問題を解決しますか？

## 🔧 トラブルシューティング

### MQTT 5.0接続失敗
- ブローカーがMQTT 5.0に対応しているか確認
- プロトコルバージョンの指定を確認
- 接続プロパティの設定を確認

### User Properties が表示されない
- MQTT 5.0プロトコルの使用を確認
- プロパティオブジェクトの正しい設定を確認
- ブローカーの対応機能を確認

### Topic Alias が機能しない
- TopicAliasMaximumの設定を確認
- エイリアス番号の範囲を確認
- ブローカーの対応状況を確認

### Session が復旧しない
- Clean Startの設定を確認
- Session Expiry Intervalの値を確認
- ブローカーのセッション管理設定を確認

---

**次のステップ**: [08-cloud-integration](../08-cloud-integration/) でクラウドサービスとの連携について学習しましょう！