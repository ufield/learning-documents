# ハンズオン 02: Publish/Subscribe の基本

## 🎯 学習目標

このハンズオンでは以下を学習します：

- MQTTのPublish/Subscribe（Pub/Sub）パターンの理解
- メッセージの送信（Publish）方法
- メッセージの受信（Subscribe）方法  
- トピックとワイルドカードの使用方法
- 複数クライアント間での通信

**所要時間**: 約60分

## 📋 前提条件

- [01-setup-and-basic-connection](../01-setup-and-basic-connection/) の完了
- MQTTブローカーが起動していること

## 🎭 Pub/Subパターンの理解

従来の通信方式（リクエスト-レスポンス）と異なり、MQTTのPub/Subパターンでは：

```
Publisher → [Topic] → Broker → [Topic] → Subscriber(s)
```

- **Publisher**: メッセージを送信する側
- **Subscriber**: メッセージを受信する側  
- **Topic**: メッセージのルーティング先
- **Broker**: メッセージの仲介役

## 📝 実装演習

### Exercise 1: 基本的なPublish/Subscribe

#### シンプルなPublisher作成

`src/publisher.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import threading
from rich.console import Console
from rich.text import Text
from typing import Union, Dict, Any, Optional
from datetime import datetime

console = Console()

class MQTTPublisher:
    def __init__(self, broker_url: str = 'localhost', port: int = 1883):
        self.broker_url = broker_url
        self.port = port
        self.client = mqtt.Client(
            client_id=f"publisher-{int(time.time())}",
            clean_session=True
        )
        
        self.connected = threading.Event()
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            console.print("📡 Publisher connected to broker", style="bold green")
            self.connected.set()
        else:
            console.print(f"❌ Publisher connection failed: {rc}", style="bold red")
    
    def on_publish(self, client, userdata, mid):
        console.print("✅ Message published successfully", style="green")
    
    def on_disconnect(self, client, userdata, rc):
        console.print("👋 Publisher disconnected", style="yellow")
        self.connected.clear()
    
    def connect(self) -> bool:
        try:
            self.client.connect(self.broker_url, self.port, 60)
            self.client.loop_start()
            
            # 接続完了を待機
            if self.connected.wait(timeout=10):
                return True
            else:
                console.print("❌ Connection timeout", style="bold red")
                return False
        except Exception as e:
            console.print(f"❌ Connection error: {e}", style="bold red")
            return False
    
    def publish(self, topic: str, message: Union[str, Dict[str, Any]], 
                qos: int = 0, retain: bool = False) -> bool:
        """メッセージを送信"""
        if not self.connected.is_set():
            console.print("❌ Not connected to broker", style="bold red")
            return False
        
        # メッセージを文字列に変換
        if isinstance(message, dict):
            payload = json.dumps(message, ensure_ascii=False)
        else:
            payload = str(message)
        
        console.print(f"📤 Publishing to topic: {topic}", style="bold blue")
        console.print(f"   Message: {payload}", style="dim")
        console.print(f"   QoS: {qos}", style="dim")
        
        try:
            result = self.client.publish(topic, payload, qos, retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                result.wait_for_publish()  # 送信完了を待機
                return True
            else:
                console.print(f"❌ Publish failed: {result.rc}", style="bold red")
                return False
        except Exception as e:
            console.print(f"❌ Publish error: {e}", style="bold red")
            return False
    
    def disconnect(self):
        if self.connected.is_set():
            self.client.loop_stop()
            self.client.disconnect()

# 使用例
def demonstrate_publishing():
    publisher = MQTTPublisher()
    
    if not publisher.connect():
        console.print("❌ Failed to connect", style="bold red")
        return
    
    try:
        # シンプルなテキストメッセージ
        publisher.publish('sensors/temperature', '23.5')
        time.sleep(1)
        
        # JSONメッセージ
        sensor_data = {
            'sensor_id': 'temp-001',
            'temperature': 23.5,
            'humidity': 45.2,
            'timestamp': datetime.now().isoformat()
        }
        publisher.publish('sensors/data', sensor_data)
        time.sleep(1)
        
        # QoS 1でのメッセージ送信
        publisher.publish('alerts/high-temperature', 
                         'Temperature exceeded threshold!', 
                         qos=1)
        time.sleep(1)
        
        # Retainedメッセージ
        publisher.publish('sensors/temp-001/status', 'online', 
                         qos=1, retain=True)
        time.sleep(1)
        
    except Exception as error:
        console.print(f"Publishing failed: {error}", style="bold red")
    finally:
        publisher.disconnect()

if __name__ == "__main__":
    demonstrate_publishing()
```

#### シンプルなSubscriber作成

`src/subscriber.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import threading
import signal
import sys
from rich.console import Console
from rich.panel import Panel
from typing import Callable, Optional, List, Dict, Any
from datetime import datetime

console = Console()

class MQTTSubscriber:
    """MQTT Subscriber クラス"""
    
    def __init__(self, broker_url: str = 'localhost', port: int = 1883):
        self.broker_url = broker_url
        self.port = port
        self.client = mqtt.Client(
            client_id=f"subscriber-{int(time.time())}",
            clean_session=True
        )
        
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.message_count = 0
        self.connected = threading.Event()
        
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """イベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_subscribe = self.on_subscribe
        self.client.on_unsubscribe = self.on_unsubscribe
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print("📡 Subscriber connected to broker", style="bold green")
            self.connected.set()
        else:
            console.print(f"❌ Subscriber connection failed: {rc}", style="bold red")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        self.handle_message(msg.topic, msg.payload, msg)
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        """購読成功時のコールバック"""
        console.print("✅ Successfully subscribed:", style="green")
        for qos in granted_qos:
            console.print(f"   QoS: {qos}", style="dim")
    
    def on_unsubscribe(self, client, userdata, mid):
        """購読解除時のコールバック"""
        console.print("✅ Successfully unsubscribed", style="green")
    
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        console.print(f"👋 Subscriber disconnected (received {self.message_count} messages)", style="yellow")
        self.connected.clear()
    
    def handle_message(self, topic: str, payload: bytes, packet):
        """メッセージ処理"""
        self.message_count += 1
        message_str = payload.decode('utf-8')
        
        console.print(f"\n📬 Message received (#{self.message_count})", style="bold cyan")
        console.print(f"   Topic: {topic}", style="blue")
        console.print(f"   QoS: {packet.qos}", style="blue")
        console.print(f"   Retain: {packet.retain}", style="blue")
        console.print(f"   Payload: {message_str}", style="blue")
        
        # JSONメッセージの場合はパースして表示
        try:
            json_data = json.loads(message_str)
            console.print("   Parsed JSON:", style="magenta")
            console.print(json.dumps(json_data, indent=4, ensure_ascii=False), style="dim")
        except (json.JSONDecodeError, ValueError):
            # JSON以外のメッセージの場合は無視
            pass
        
        # カスタム処理のデモ
        self.process_message_by_topic(topic, message_str)
    
    def process_message_by_topic(self, topic: str, message: str):
        """トピック別メッセージ処理"""
        if topic.startswith('sensors/temperature'):
            try:
                temp = float(message)
                if temp > 30:
                    console.print("🔥 High temperature alert!", style="bold red")
                elif temp < 10:
                    console.print("🧊 Low temperature alert!", style="bold blue")
            except ValueError:
                pass
        elif topic.startswith('alerts/'):
            console.print("⚠️  Alert received - escalating to monitoring system", style="bold yellow")
    
    def connect(self) -> bool:
        """ブローカーに接続"""
        try:
            self.client.connect(self.broker_url, self.port, 60)
            self.client.loop_start()
            
            # 接続完了を待機
            if self.connected.wait(timeout=10):
                return True
            else:
                console.print("❌ Connection timeout", style="bold red")
                return False
        except Exception as e:
            console.print(f"❌ Connection error: {e}", style="bold red")
            return False
    
    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """トピックに購読"""
        if not self.connected.is_set():
            console.print("❌ Not connected to broker", style="bold red")
            return False
        
        console.print(f"📥 Subscribing to topic: {topic}", style="bold blue")
        console.print(f"   QoS: {qos}", style="dim")
        
        try:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                self.subscriptions[topic] = {'qos': qos}
                return True
            else:
                console.print(f"❌ Subscribe failed: {result[0]}", style="bold red")
                return False
        except Exception as e:
            console.print(f"❌ Subscribe error: {e}", style="bold red")
            return False
    
    def unsubscribe(self, topic: str) -> bool:
        """トピックの購読を解除"""
        console.print(f"📤 Unsubscribing from topic: {topic}", style="yellow")
        
        try:
            result = self.client.unsubscribe(topic)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                if topic in self.subscriptions:
                    del self.subscriptions[topic]
                return True
            else:
                console.print(f"❌ Unsubscribe failed: {result[0]}", style="bold red")
                return False
        except Exception as e:
            console.print(f"❌ Unsubscribe error: {e}", style="bold red")
            return False
    
    def disconnect(self):
        """ブローカーから切断"""
        if self.connected.is_set():
            self.client.loop_stop()
            self.client.disconnect()
    
    def get_stats(self) -> Dict[str, Any]:
        """統計情報を取得"""
        return {
            'message_count': self.message_count,
            'subscriptions': list(self.subscriptions.keys())
        }

# 使用例
def demonstrate_subscribing():
    """Subscriber動作デモ"""
    subscriber = MQTTSubscriber()
    
    # シグナルハンドラーの設定
    def signal_handler(signum, frame):
        console.print("\n👋 Shutting down gracefully...", style="yellow")
        subscriber.disconnect()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    # 接続
    if not subscriber.connect():
        console.print("❌ Failed to connect", style="bold red")
        return
    
    # 接続完了まで少し待機
    time.sleep(1)
    
    try:
        # 複数のトピックに購読
        subscriber.subscribe('sensors/temperature')
        subscriber.subscribe('sensors/data')
        subscriber.subscribe('alerts/+')  # ワイルドカード使用
        subscriber.subscribe('sensors/+/status', qos=1)
        
        console.print("\n🎧 Listening for messages... (Press Ctrl+C to stop)", style="bold green")
        
        # メッセージを待機（60秒間）
        try:
            time.sleep(60)
        except KeyboardInterrupt:
            pass
        
    except Exception as error:
        console.print(f"Subscribing failed: {error}", style="bold red")
    finally:
        stats = subscriber.get_stats()
        console.print("\n📊 Session Statistics:", style="cyan")
        console.print(f"   Messages received: {stats['message_count']}")
        console.print(f"   Subscriptions: {', '.join(stats['subscriptions'])}")
        
        subscriber.disconnect()

if __name__ == "__main__":
    demonstrate_subscribing()
```

### Exercise 2: ワイルドカードの実践

`src/wildcard_demo.py` を作成：

```python
import paho.mqtt.client as mqtt
import time
import random
from rich.console import Console
from typing import List, Dict
from datetime import datetime

console = Console()

class WildcardDemo:
    """MQTT ワイルドカードデモクラス"""
    
    def __init__(self):
        self.client = mqtt.Client(client_id='wildcard-demo')
        
        self.test_topics = [
            'home/livingroom/temperature',
            'home/livingroom/humidity',
            'home/bedroom/temperature', 
            'home/bedroom/light',
            'home/kitchen/temperature',
            'office/room1/temperature',
            'office/room1/humidity',
            'factory/line1/sensor1/temperature',
            'factory/line1/sensor2/pressure'
        ]
        
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """イベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print("📡 Wildcard demo client connected", style="bold green")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        topic = msg.topic
        message = msg.payload.decode('utf-8')
        qos = msg.qos
        console.print(f"📬 [{qos}] {topic}: {message}", style="cyan")
    
    def connect(self) -> bool:
        """ブローカーに接続"""
        try:
            self.client.connect('localhost', 1883, 60)
            self.client.loop_start()
            time.sleep(1)  # 接続完了まで待機
            return True
        except Exception as e:
            console.print(f"❌ Connection error: {e}", style="bold red")
            return False
    
    def publish(self, topic: str, message: str) -> bool:
        """メッセージを公開"""
        try:
            result = self.client.publish(topic, message)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            console.print(f"❌ Publish error: {e}", style="bold red")
            return False
    
    def demonstrate_wildcards(self):
        """ワイルドカード実演"""
        console.print("🎯 MQTT Wildcard Demonstration\n", style="bold yellow")
        
        # テストデータの公開
        console.print("📤 Publishing test messages...", style="blue")
        for topic in self.test_topics:
            value = f"{random.uniform(10, 40):.1f}"
            self.publish(topic, value)
        
        time.sleep(2)
        
        # ワイルドカードパターンの実験
        wildcard_patterns = [
            {
                'pattern': 'home/+/temperature',
                'description': '家の全ての部屋の温度'
            },
            {
                'pattern': 'home/livingroom/+', 
                'description': 'リビングルームの全てのセンサー'
            },
            {
                'pattern': '+/+/temperature',
                'description': '全ての建物の全ての部屋の温度'
            },
            {
                'pattern': 'factory/#',
                'description': '工場の全てのデータ'
            },
            {
                'pattern': '+/+/+',
                'description': '3階層のトピック全て'
            }
        ]
        
        for pattern_info in wildcard_patterns:
            self.demonstrate_pattern(pattern_info)
            time.sleep(3)
    
    def demonstrate_pattern(self, pattern_info: Dict[str, str]):
        """特定パターンの実演"""
        pattern = pattern_info['pattern']
        description = pattern_info['description']
        
        console.print(f"\n🔍 Testing pattern: {pattern}", style="bold yellow")
        console.print(f"   Description: {description}", style="dim")
        
        # パターンに購読
        try:
            result = self.client.subscribe(pattern)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                console.print("✅ Subscribed. Publishing messages...", style="green")
            else:
                console.print(f"❌ Subscribe failed: {result[0]}", style="bold red")
                return
        except Exception as e:
            console.print(f"❌ Subscribe error: {e}", style="bold red")
            return
        
        # マッチするメッセージを再公開
        match_count = 0
        for topic in self.test_topics:
            if self.topic_matches(topic, pattern):
                match_count += 1
                value = f"{random.uniform(10, 40):.1f}"
                self.publish(topic, f"{value} (matched)")
        
        console.print(f"📊 Pattern matched {match_count} topics", style="blue")
        
        # 少し待機してから購読解除
        time.sleep(1)
        
        # 購読解除
        try:
            result = self.client.unsubscribe(pattern)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                console.print("📤 Unsubscribed from pattern", style="dim")
        except Exception as e:
            console.print(f"❌ Unsubscribe error: {e}", style="bold red")
    
    def topic_matches(self, topic: str, pattern: str) -> bool:
        """トピックがパターンにマッチするかチェック"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        # マルチレベルワイルドカード (#) の処理
        if '#' in pattern:
            hash_index = pattern_parts.index('#')
            # '#'より前の部分がマッチするかチェック
            return all(
                pattern_parts[i] == topic_parts[i] or pattern_parts[i] == '+'
                for i in range(min(hash_index, len(topic_parts)))
                if i < len(pattern_parts) and i < len(topic_parts)
            )
        
        # 階層数が違う場合は不一致
        if len(topic_parts) != len(pattern_parts):
            return False
        
        # シングルレベルワイルドカード (+) の処理
        return all(
            pattern_parts[i] == topic_parts[i] or pattern_parts[i] == '+'
            for i in range(len(topic_parts))
        )
    
    def disconnect(self):
        """切断"""
        self.client.loop_stop()
        self.client.disconnect()
        console.print("\n👋 Wildcard demo completed", style="yellow")

# 実行関数
def main():
    """メイン関数"""
    demo = WildcardDemo()
    
    if not demo.connect():
        console.print("❌ Failed to connect to broker", style="bold red")
        return
    
    try:
        demo.demonstrate_wildcards()
    except KeyboardInterrupt:
        console.print("\n⚠️  Demo interrupted by user", style="yellow")
    except Exception as error:
        console.print(f"❌ Demo failed: {error}", style="bold red")
    finally:
        demo.disconnect()

if __name__ == "__main__":
    main()
```

### Exercise 3: チャットアプリケーション

`src/chat_application.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import sys
import threading
import signal
from datetime import datetime
from rich.console import Console
from rich.prompt import Prompt
from typing import Optional

console = Console()

class MQTTChatApp:
    """MQTT チャットアプリケーション"""
    
    def __init__(self, username: str):
        self.username = username
        self.is_connected = False
        self.running = True
        
        # Last Will Testament設定
        will_message = json.dumps({
            'type': 'user_disconnect',
            'username': username,
            'timestamp': datetime.now().isoformat()
        })
        
        self.client = mqtt.Client(
            client_id=f"chat-{username}-{int(datetime.now().timestamp())}",
            clean_session=True
        )
        
        # Last Will Testament設定
        self.client.will_set(
            topic='chat/system',
            payload=will_message,
            qos=1
        )
        
        self.setup_mqtt_handlers()
        self.setup_signal_handlers()
    
    def setup_mqtt_handlers(self):
        """MQTTイベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def setup_signal_handlers(self):
        """シグナルハンドラーの設定"""
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, signum, frame):
        """シグナルハンドラー"""
        console.print("\n👋 Received exit signal. Leaving chat...", style="yellow")
        self.quit()
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            self.is_connected = True
            console.print(f"🎉 Welcome to MQTT Chat, {self.username}!", style="bold green")
            console.print("💡 Commands: /help, /users, /quit", style="dim")
            console.print("📝 Type your message and press Enter to send\n", style="dim")
            
            # チャットルームに参加
            self.subscribe_to_chat()
            self.announce_join()
        else:
            console.print(f"❌ Connection failed: {rc}", style="bold red")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        self.handle_message(msg.topic, msg.payload, msg)
    
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        if rc != 0:
            console.print("⚠️  Unexpected disconnect", style="yellow")
        self.is_connected = False
    
    def subscribe_to_chat(self):
        """チャットトピックに購読"""
        try:
            self.client.subscribe('chat/messages', qos=1)
            self.client.subscribe('chat/system', qos=1)
            self.client.subscribe(f'chat/private/{self.username}', qos=1)
        except Exception as e:
            console.print(f"Failed to subscribe to chat topics: {e}", style="bold red")
    
    def handle_message(self, topic: str, payload: bytes, packet):
        """メッセージ処理"""
        try:
            data = json.loads(payload.decode('utf-8'))
            
            # 自分のメッセージは表示しない
            if data.get('username') == self.username:
                return
            
            if topic == 'chat/messages':
                console.print(f"💬 {data['username']}: {data['message']}", style="cyan")
            elif topic == 'chat/system':
                self.handle_system_message(data)
            elif topic.startswith('chat/private/'):
                console.print(f"🔒 [Private] {data['username']}: {data['message']}", style="magenta")
                
        except (json.JSONDecodeError, KeyError) as e:
            # JSON以外のメッセージまたは不正なフォーマットは無視
            pass
    
    def handle_system_message(self, data: dict):
        """システムメッセージ処理"""
        msg_type = data.get('type')
        username = data.get('username')
        
        if msg_type == 'user_join':
            console.print(f"👋 {username} joined the chat", style="green")
        elif msg_type == 'user_disconnect':
            console.print(f"👋 {username} left the chat", style="yellow")
        elif msg_type == 'user_list':
            users = data.get('users', [])
            console.print(f"👥 Online users: {', '.join(users)}", style="blue")
    
    def handle_command(self, command: str):
        """コマンド処理"""
        parts = command.split()
        if not parts:
            return
            
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == '/help':
            console.print("📖 Available commands:", style="blue")
            console.print("  /help - Show this help")
            console.print("  /users - List online users")
            console.print("  /private <username> <message> - Send private message")
            console.print("  /quit - Leave the chat")
            
        elif cmd == '/users':
            self.request_user_list()
            
        elif cmd == '/private':
            if len(args) < 2:
                console.print("❌ Usage: /private <username> <message>", style="red")
            else:
                target_user = args[0]
                message = ' '.join(args[1:])
                self.send_private_message(target_user, message)
                
        elif cmd == '/quit':
            self.quit()
            
        else:
            console.print(f"❌ Unknown command: {cmd}", style="red")
            console.print("💡 Type /help for available commands", style="dim")
    
    def send_message(self, message: str):
        """パブリックメッセージ送信"""
        message_data = {
            'username': self.username,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.client.publish('chat/messages', json.dumps(message_data), qos=1)
        except Exception as e:
            console.print(f"Failed to send message: {e}", style="bold red")
    
    def send_private_message(self, target_user: str, message: str):
        """プライベートメッセージ送信"""
        message_data = {
            'username': self.username,
            'message': message,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.client.publish(f'chat/private/{target_user}', json.dumps(message_data), qos=1)
            console.print(f"🔒 [Private to {target_user}]: {message}", style="magenta")
        except Exception as e:
            console.print(f"Failed to send private message: {e}", style="bold red")
    
    def announce_join(self):
        """チャット参加を通知"""
        join_data = {
            'type': 'user_join',
            'username': self.username,
            'timestamp': datetime.now().isoformat()
        }
        
        try:
            self.client.publish('chat/system', json.dumps(join_data), qos=1)
        except Exception as e:
            console.print(f"Failed to announce join: {e}", style="bold red")
    
    def request_user_list(self):
        """ユーザーリスト要求"""
        # 実際のアプリケーションでは、サーバー側でユーザーリストを管理する必要があります
        console.print("👥 User list functionality would require server-side implementation", style="dim")
    
    def run(self):
        """チャットアプリケーション実行"""
        try:
            # MQTTブローカーに接続
            self.client.connect('localhost', 1883, 60)
            self.client.loop_start()
            
            # 接続完了まで待機
            import time
            time.sleep(2)
            
            if not self.is_connected:
                console.print("❌ Failed to connect to MQTT broker", style="bold red")
                return
            
            # メインループ
            while self.running and self.is_connected:
                try:
                    user_input = Prompt.ask(f"[bold blue]{self.username}[/bold blue]", default="")
                    
                    if not user_input:
                        continue
                        
                    if user_input.startswith('/'):
                        self.handle_command(user_input)
                    else:
                        self.send_message(user_input)
                        
                except KeyboardInterrupt:
                    console.print("\n👋 Keyboard interrupt received", style="yellow")
                    break
                except EOFError:
                    break
                    
        except Exception as e:
            console.print(f"❌ Chat error: {e}", style="bold red")
        finally:
            self.quit()
    
    def quit(self):
        """チャット終了"""
        if not self.running:
            return
            
        self.running = False
        console.print("\n👋 Leaving chat...", style="yellow")
        
        if self.is_connected:
            # 切断通知送信
            disconnect_data = {
                'type': 'user_disconnect',
                'username': self.username,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                self.client.publish('chat/system', json.dumps(disconnect_data), qos=1)
            except:
                pass  # エラーは無視
        
        # MQTT切断
        self.client.loop_stop()
        self.client.disconnect()
        
        console.print("✨ Chat session ended", style="green")
        sys.exit(0)

def main():
    """メイン関数"""
    if len(sys.argv) != 2:
        console.print("❌ Please provide a username", style="bold red")
        console.print("Usage: python chat_application.py <username>", style="blue")
        sys.exit(1)
    
    username = sys.argv[1]
    
    if not username or len(username.strip()) == 0:
        console.print("❌ Username cannot be empty", style="bold red")
        sys.exit(1)
    
    # チャットアプリケーション開始
    chat_app = MQTTChatApp(username.strip())
    chat_app.run()

if __name__ == "__main__":
    main()
```

## 🎯 練習問題

### 問題1: 基本的なPub/Sub
1. ターミナルを2つ開いて、一方でSubscriber、もう一方でPublisherを実行してください
2. 様々なトピックとメッセージでやり取りを確認してください

### 問題2: ワイルドカードの理解
1. `wildcard_demo.py`を実行して、各パターンの動作を確認してください
2. 独自のワイルドカードパターンを作成してテストしてください

### 問題3: チャットアプリケーション
1. 複数のターミナルで異なるユーザー名でチャットアプリを起動してください（`python chat_application.py <username>`）
2. メッセージのやり取りと各種コマンドを試してください
3. プライベートメッセージ機能を確認してください

### 問題4: カスタム実装
温度センサーの監視システムを作成してください：
- Publisher: 5秒間隔で温度データ（15-35度のランダム値）を送信
- Subscriber: 30度以上で警告、10度以下でアラート表示
- Topic: `sensors/building1/room{1-3}/temperature`

## ✅ 確認チェックリスト

- [ ] PublisherとSubscriberの基本動作を理解した
- [ ] 様々なデータ形式（文字列、JSON）でメッセージを送受信できた
- [ ] QoSレベルの違いを理解した
- [ ] Retainedメッセージの動作を確認した
- [ ] ワイルドカード（+と#）の使い方を理解した
- [ ] 複数クライアント間でのリアルタイム通信を実現できた
- [ ] Last Will Testamentの動作を確認した

## 📊 理解度チェック

以下の質問に答えられるか確認してください：

1. `home/+/temperature`と`home/#`の違いは何ですか？
2. Retainedメッセージはいつ使用しますか？
3. QoS 0とQoS 1の違いは何ですか？
4. Last Will Testamentはどのような場面で有効ですか？

## 🔧 トラブルシューティング

### メッセージが届かない
- トピック名のタイプミスを確認
- Subscriberが正しく購読しているか確認
- ブローカーのログを確認

### 重複メッセージ
- Clean Sessionの設定を確認
- QoS 1での重複は正常な動作

### チャットで文字化け
- UTF-8エンコーディングを確認
- JSONの形式を確認

---

**次のステップ**: [03-qos-and-reliability](../03-qos-and-reliability/) でメッセージの信頼性について詳しく学習しましょう！