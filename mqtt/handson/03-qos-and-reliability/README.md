# ハンズオン 03: QoSとメッセージ信頼性

## 🎯 学習目標

このハンズオンでは以下を学習します：

- QoS (Quality of Service) レベルの理解と実装
- メッセージの信頼性保証の仕組み
- Persistent Session（永続セッション）の活用
- エラーハンドリングとメッセージ重複処理
- 実際のIoTシナリオでのQoS選択

**所要時間**: 約90分

## 📋 前提条件

- [02-publish-subscribe](../02-publish-subscribe/) の完了
- Python環境とpaho-mqttライブラリの設定
- MQTTブローカーが起動していること

## 🎭 QoSレベルの理解

### QoS 0: At most once（最大1回配信）
- 最も軽量、「Fire and Forget」方式
- センサーデータなど頻繁なデータに適用

### QoS 1: At least once（最低1回配信）
- 配信保証あり、重複の可能性
- アラートや重要な通知に適用

### QoS 2: Exactly once（正確に1回配信）
- 最高の信頼性、4ウェイハンドシェイク
- 制御コマンドや財務データに適用

## 📝 実装演習

### Exercise 1: QoS別メッセージ送信テスト

`src/qos_publisher.py` を作成：

```python
#!/usr/bin/env python3
"""
QoS別メッセージ送信テスト
異なるQoSレベルでのメッセージ配信テスト
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Dict, List

console = Console()

class QoSPublisher:
    def __init__(self, broker_host: str = "localhost", port: int = 1883):
        self.broker_host = broker_host
        self.port = port
        
        # 送信結果の追跡
        self.publish_results: Dict[int, Dict] = {}
        self.message_counter = 0
        
        # MQTTクライアント設定
        self.client = mqtt.Client(
            client_id=f"qos_publisher_{int(time.time())}",
            clean_session=True  # まずはClean Sessionから開始
        )
        
        self.connected = threading.Event()
        self.setup_callbacks()
    
    def setup_callbacks(self):
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            console.print("✅ QoS Publisher connected", style="bold green")
            self.connected.set()
        else:
            console.print(f"❌ Connection failed: {rc}", style="bold red")
    
    def on_publish(self, client, userdata, mid):
        """メッセージ送信完了時のコールバック"""
        if mid in self.publish_results:
            self.publish_results[mid]["status"] = "confirmed"
            self.publish_results[mid]["confirmed_at"] = datetime.now()
            
            result = self.publish_results[mid]
            console.print(f"✅ Message {mid} confirmed (QoS {result['qos']})", style="green")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            console.print("⚠️ Unexpected disconnection", style="yellow")
        self.connected.clear()
    
    def connect(self) -> bool:
        try:
            self.client.connect(self.broker_host, self.port, 60)
            self.client.loop_start()
            return self.connected.wait(timeout=10)
        except Exception as e:
            console.print(f"❌ Connection error: {e}", style="bold red")
            return False
    
    def publish_with_qos(self, topic: str, message: str, qos: int, 
                         message_type: str = "test") -> int:
        """指定されたQoSでメッセージを送信"""
        if not self.connected.is_set():
            console.print("❌ Not connected", style="bold red")
            return -1
        
        self.message_counter += 1
        
        # メッセージペイロードを準備
        payload = {
            "message_id": self.message_counter,
            "content": message,
            "message_type": message_type,
            "qos": qos,
            "timestamp": datetime.now().isoformat(),
            "sender": "qos_publisher"
        }
        
        result = self.client.publish(topic, json.dumps(payload), qos)
        
        # 送信結果を記録
        self.publish_results[result.mid] = {
            "message_id": self.message_counter,
            "topic": topic,
            "qos": qos,
            "message_type": message_type,
            "sent_at": datetime.now(),
            "status": "sent",
            "confirmed_at": None
        }
        
        console.print(
            f"📤 Sent message {self.message_counter} (MID: {result.mid}) "
            f"to {topic} with QoS {qos}",
            style="blue"
        )
        
        return result.mid
    
    def run_qos_comparison_test(self):
        """QoSレベル比較テストを実行"""
        console.print(Panel.fit(
            "QoS レベル比較テスト開始\n"
            "各QoSレベルでメッセージを送信し、配信特性を比較します",
            title="QoS Comparison Test",
            border_style="cyan"
        ))
        
        test_scenarios = [
            # センサーデータ（QoS 0）
            {
                "topic": "sensors/temperature",
                "qos": 0,
                "message": "23.5°C",
                "type": "sensor_data",
                "description": "温度センサーデータ（頻繁、軽量）"
            },
            # アラート（QoS 1）
            {
                "topic": "alerts/temperature_high",
                "qos": 1,
                "message": "Temperature exceeded threshold!",
                "type": "alert",
                "description": "温度アラート（確実な配信が必要）"
            },
            # 制御コマンド（QoS 2）
            {
                "topic": "actuators/valve/control",
                "qos": 2,
                "message": "CLOSE_VALVE",
                "type": "control_command",
                "description": "バルブ制御コマンド（重複実行不可）"
            }
        ]
        
        mids = []
        for scenario in test_scenarios:
            console.print(f"\n📋 {scenario['description']}")
            mid = self.publish_with_qos(
                scenario["topic"],
                scenario["message"], 
                scenario["qos"],
                scenario["type"]
            )
            mids.append(mid)
            time.sleep(1)  # 少し間隔を空ける
        
        # 結果の確認を待機
        console.print("\n⏳ Waiting for confirmations...")
        time.sleep(5)
        
        # 結果レポート
        self.display_results_report()
    
    def display_results_report(self):
        """送信結果レポートを表示"""
        table = Table(title="QoS Test Results")
        table.add_column("Message ID", style="cyan")
        table.add_column("Topic", style="magenta")
        table.add_column("QoS", style="yellow")
        table.add_column("Type", style="green")
        table.add_column("Status", style="red")
        table.add_column("Latency", style="blue")
        
        for mid, result in self.publish_results.items():
            if result["confirmed_at"]:
                latency = (result["confirmed_at"] - result["sent_at"]).total_seconds()
                latency_str = f"{latency:.3f}s"
                status = "✅ Confirmed"
            else:
                latency_str = "N/A"
                status = "⏳ Pending" if result["qos"] > 0 else "📤 Sent (QoS 0)"
            
            table.add_row(
                str(result["message_id"]),
                result["topic"],
                str(result["qos"]),
                result["message_type"],
                status,
                latency_str
            )
        
        console.print(table)
    
    def test_persistent_session(self):
        """Persistent Sessionのテスト"""
        console.print(Panel.fit(
            "Persistent Session テスト\n"
            "セッション保持によるメッセージ配信テスト",
            title="Persistent Session Test",
            border_style="yellow"
        ))
        
        # Clean Sessionを無効にして再接続
        self.client.loop_stop()
        self.client.disconnect()
        
        # Persistent Sessionクライアントを作成
        persistent_client = mqtt.Client(
            client_id="persistent_test_client",  # 固定クライアントID
            clean_session=False  # セッション保持
        )
        
        def on_connect_persistent(client, userdata, flags, rc):
            if rc == 0:
                session_present = flags.get('session_present', False)
                console.print(f"✅ Persistent client connected", style="bold green")
                console.print(f"📋 Session present: {session_present}", style="cyan")
                
                # 重要なトピックを購読（QoS 1）
                client.subscribe("important/messages", qos=1)
                console.print("📡 Subscribed to important/messages with QoS 1", style="blue")
            
        persistent_client.on_connect = on_connect_persistent
        persistent_client.connect(self.broker_host, self.port, 60)
        persistent_client.loop_start()
        
        time.sleep(2)
        
        # テストメッセージを送信
        test_messages = [
            "Important message 1 - while connected",
            "Important message 2 - while connected"
        ]
        
        for i, msg in enumerate(test_messages, 1):
            self.publish_with_qos("important/messages", msg, 1, "persistent_test")
            time.sleep(1)
        
        console.print("💤 Disconnecting persistent client...", style="yellow")
        persistent_client.loop_stop()
        persistent_client.disconnect()
        time.sleep(2)
        
        # 切断中にメッセージを送信
        offline_messages = [
            "Important message 3 - while offline",
            "Important message 4 - while offline"
        ]
        
        console.print("📤 Sending messages while client is offline...", style="blue")
        for msg in offline_messages:
            self.publish_with_qos("important/messages", msg, 1, "offline_test")
            time.sleep(1)
        
        time.sleep(2)
        
        # 再接続
        console.print("🔌 Reconnecting persistent client...", style="green")
        persistent_client.connect(self.broker_host, self.port, 60)
        persistent_client.loop_start()
        
        time.sleep(5)  # オフライン中のメッセージ受信を待機
        
        persistent_client.loop_stop()
        persistent_client.disconnect()
        
        console.print("✅ Persistent session test completed", style="bold green")
    
    def disconnect(self):
        if self.connected.is_set():
            self.client.loop_stop()
            self.client.disconnect()

def main():
    """メイン実行関数"""
    console.print(Panel.fit(
        "🔬 MQTT QoS & Reliability Test Suite\n\n"
        "このテストでは以下を検証します：\n"
        "• QoS 0, 1, 2の配信特性\n"
        "• Persistent Sessionの動作\n"
        "• メッセージ確認とレイテンシ\n\n"
        "Language: Python 3\n"
        "Library: paho-mqtt",
        title="QoS Test Suite",
        border_style="blue"
    ))
    
    publisher = QoSPublisher()
    
    if not publisher.connect():
        console.print("❌ Failed to connect to MQTT broker", style="bold red")
        return
    
    try:
        # QoS比較テスト
        publisher.run_qos_comparison_test()
        
        time.sleep(3)
        
        # Persistent Sessionテスト
        publisher.test_persistent_session()
        
    except KeyboardInterrupt:
        console.print("\n👋 Test interrupted by user", style="yellow")
    finally:
        publisher.disconnect()
        console.print("✨ QoS test suite completed", style="bold green")

if __name__ == "__main__":
    main()
```

### Exercise 2: メッセージ重複処理とエラーハンドリング

`src/reliable_subscriber.py` を作成：

```python
#!/usr/bin/env python3
"""
信頼性の高いMQTTサブスクライバー
メッセージ重複処理とエラーハンドリングの実装
"""

import paho.mqtt.client as mqtt
import json
import time
import hashlib
import threading
from datetime import datetime, timedelta
from typing import Dict, Set, Callable, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dataclasses import dataclass, field

console = Console()

@dataclass
class MessageRecord:
    """メッセージ記録用データクラス"""
    message_id: str
    topic: str
    payload: str
    received_at: datetime
    qos: int
    processed: bool = False
    processing_result: str = field(default="")

class ReliableSubscriber:
    def __init__(self, broker_host: str = "localhost", port: int = 1883):
        self.broker_host = broker_host
        self.port = port
        
        # 重複チェック用
        self.processed_messages: Set[str] = set()
        self.message_history: Dict[str, MessageRecord] = {}
        
        # 統計情報
        self.stats = {
            "total_received": 0,
            "duplicates_detected": 0,
            "processing_errors": 0,
            "successfully_processed": 0
        }
        
        # エラーリトライ設定
        self.max_retries = 3
        self.retry_delay = 2.0
        
        # MQTTクライアント設定
        self.client = mqtt.Client(
            client_id=f"reliable_subscriber_{int(time.time())}",
            clean_session=False  # セッション保持
        )
        
        self.connected = threading.Event()
        self.setup_callbacks()
        
        # 定期クリーンアップ
        self.start_cleanup_timer()
    
    def setup_callbacks(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_subscribe = self.on_subscribe
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            console.print("✅ Reliable Subscriber connected", style="bold green")
            session_present = flags.get('session_present', False)
            console.print(f"📋 Session present: {session_present}", style="cyan")
            self.connected.set()
            
            # 様々なQoSレベルでトピックを購読
            subscriptions = [
                ("sensors/+", 0),          # センサーデータ（QoS 0）
                ("alerts/+", 1),           # アラート（QoS 1）
                ("actuators/+/+", 2),      # 制御コマンド（QoS 2）
                ("important/messages", 1), # 重要メッセージ（QoS 1）
            ]
            
            for topic, qos in subscriptions:
                client.subscribe(topic, qos)
        else:
            console.print(f"❌ Connection failed: {rc}", style="bold red")
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        console.print(f"📡 Subscription confirmed (MID: {mid}, QoS: {granted_qos})", style="blue")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信処理（重複チェックとエラーハンドリング付き）"""
        try:
            self.stats["total_received"] += 1
            
            # メッセージの一意識別子を生成
            message_id = self.generate_message_id(msg)
            
            # 重複チェック
            if message_id in self.processed_messages:
                self.stats["duplicates_detected"] += 1
                console.print(f"🔄 Duplicate message detected: {message_id}", style="yellow")
                return
            
            # メッセージ記録
            record = MessageRecord(
                message_id=message_id,
                topic=msg.topic,
                payload=msg.payload.decode(),
                received_at=datetime.now(),
                qos=msg.qos
            )
            
            self.message_history[message_id] = record
            
            # メッセージ処理
            success = self.process_message_with_retry(msg, record)
            
            if success:
                # 処理成功時のみ重複チェックに追加
                self.processed_messages.add(message_id)
                record.processed = True
                self.stats["successfully_processed"] += 1
            else:
                self.stats["processing_errors"] += 1
            
        except Exception as e:
            console.print(f"❌ Error in message handler: {e}", style="bold red")
            self.stats["processing_errors"] += 1
    
    def generate_message_id(self, msg) -> str:
        """メッセージの一意識別子を生成"""
        try:
            # JSONメッセージの場合、message_idフィールドをチェック
            payload = json.loads(msg.payload.decode())
            if "message_id" in payload:
                return f"{msg.topic}:{payload['message_id']}"
        except json.JSONDecodeError:
            pass
        
        # フォールバック：トピック、ペイロード、QoSからハッシュ生成
        content = f"{msg.topic}:{msg.payload.decode()}:{msg.qos}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def process_message_with_retry(self, msg, record: MessageRecord) -> bool:
        """リトライ機能付きメッセージ処理"""
        for attempt in range(self.max_retries):
            try:
                success = self.process_message(msg, record)
                if success:
                    if attempt > 0:
                        console.print(f"✅ Message processed successfully on attempt {attempt + 1}", style="green")
                    return True
                else:
                    raise Exception("Processing returned False")
                    
            except Exception as e:
                error_msg = f"Attempt {attempt + 1} failed: {e}"
                record.processing_result += f"{error_msg}; "
                
                console.print(f"⚠️ {error_msg}", style="yellow")
                
                if attempt < self.max_retries - 1:
                    console.print(f"🔄 Retrying in {self.retry_delay}s...", style="blue")
                    time.sleep(self.retry_delay)
                else:
                    console.print(f"❌ All {self.max_retries} attempts failed", style="bold red")
        
        return False
    
    def process_message(self, msg, record: MessageRecord) -> bool:
        """実際のメッセージ処理ロジック"""
        topic_parts = msg.topic.split('/')
        
        # トピック別処理
        if topic_parts[0] == "sensors":
            return self.process_sensor_data(msg, record)
        elif topic_parts[0] == "alerts":
            return self.process_alert(msg, record)
        elif topic_parts[0] == "actuators":
            return self.process_actuator_command(msg, record)
        elif msg.topic == "important/messages":
            return self.process_important_message(msg, record)
        else:
            return self.process_generic_message(msg, record)
    
    def process_sensor_data(self, msg, record: MessageRecord) -> bool:
        """センサーデータ処理"""
        try:
            data = json.loads(msg.payload.decode())
            sensor_type = msg.topic.split('/')[1]
            
            console.print(f"🌡️ Sensor data [{sensor_type}]: {data.get('content', data)}", style="cyan")
            
            # センサーデータをDBに保存する処理をシミュレート
            time.sleep(0.1)  # DB書き込み時間をシミュレート
            
            record.processing_result = f"Sensor data stored for {sensor_type}"
            return True
            
        except Exception as e:
            raise Exception(f"Sensor processing error: {e}")
    
    def process_alert(self, msg, record: MessageRecord) -> bool:
        """アラート処理"""
        try:
            data = json.loads(msg.payload.decode())
            alert_type = msg.topic.split('/')[1]
            
            console.print(f"🚨 ALERT [{alert_type}]: {data.get('content', data)}", style="bold red")
            
            # アラート処理（通知送信等）をシミュレート
            time.sleep(0.2)
            
            # 重要なアラートの場合、処理失敗をシミュレート（テスト用）
            if "high" in alert_type and record.message_id.endswith('3'):
                raise Exception("Simulated alert processing failure")
            
            record.processing_result = f"Alert processed for {alert_type}"
            return True
            
        except Exception as e:
            raise Exception(f"Alert processing error: {e}")
    
    def process_actuator_command(self, msg, record: MessageRecord) -> bool:
        """アクチュエータ制御コマンド処理"""
        try:
            data = json.loads(msg.payload.decode())
            device_type = msg.topic.split('/')[1]
            
            console.print(f"🔧 Actuator command [{device_type}]: {data.get('content', data)}", style="magenta")
            
            # 制御コマンド実行をシミュレート
            time.sleep(0.3)
            
            # QoS 2のメッセージは重複実行を避けるため、より厳密にチェック
            if msg.qos == 2:
                console.print(f"🔒 QoS 2 command executed exactly once", style="bold green")
            
            record.processing_result = f"Actuator command executed for {device_type}"
            return True
            
        except Exception as e:
            raise Exception(f"Actuator processing error: {e}")
    
    def process_important_message(self, msg, record: MessageRecord) -> bool:
        """重要メッセージ処理"""
        try:
            data = json.loads(msg.payload.decode())
            
            console.print(f"📢 Important: {data.get('content', data)}", style="bold yellow")
            
            # 重要メッセージの処理をシミュレート
            time.sleep(0.15)
            
            record.processing_result = "Important message processed"
            return True
            
        except Exception as e:
            raise Exception(f"Important message processing error: {e}")
    
    def process_generic_message(self, msg, record: MessageRecord) -> bool:
        """汎用メッセージ処理"""
        console.print(f"📨 Generic message on {msg.topic}: {msg.payload.decode()[:100]}", style="white")
        record.processing_result = "Generic message processed"
        return True
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            console.print("⚠️ Unexpected disconnection", style="yellow")
        self.connected.clear()
    
    def connect(self) -> bool:
        try:
            self.client.connect(self.broker_host, self.port, 60)
            self.client.loop_start()
            return self.connected.wait(timeout=10)
        except Exception as e:
            console.print(f"❌ Connection error: {e}", style="bold red")
            return False
    
    def display_statistics(self):
        """統計情報を表示"""
        table = Table(title="Message Processing Statistics")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="yellow")
        table.add_column("Percentage", style="green")
        
        total = self.stats["total_received"]
        if total > 0:
            for key, value in self.stats.items():
                percentage = f"{(value/total)*100:.1f}%" if total > 0 else "0%"
                table.add_row(key.replace("_", " ").title(), str(value), percentage)
        
        console.print(table)
    
    def cleanup_old_records(self):
        """古いメッセージ記録をクリーンアップ"""
        cutoff_time = datetime.now() - timedelta(minutes=10)
        
        old_ids = [
            msg_id for msg_id, record in self.message_history.items()
            if record.received_at < cutoff_time and record.processed
        ]
        
        for msg_id in old_ids:
            del self.message_history[msg_id]
            self.processed_messages.discard(msg_id)
        
        if old_ids:
            console.print(f"🧹 Cleaned up {len(old_ids)} old message records", style="dim")
    
    def start_cleanup_timer(self):
        """定期クリーンアップタイマーを開始"""
        def cleanup_loop():
            while True:
                time.sleep(300)  # 5分間隔
                self.cleanup_old_records()
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def disconnect(self):
        if self.connected.is_set():
            self.client.loop_stop()
            self.client.disconnect()

def main():
    """メイン実行関数"""
    console.print(Panel.fit(
        "🛡️ MQTT Reliable Subscriber\n\n"
        "機能：\n"
        "• メッセージ重複検出・除去\n"
        "• エラーハンドリングとリトライ\n"
        "• Persistent Session対応\n"
        "• 統計情報とモニタリング\n\n"
        "Language: Python 3\n"
        "Library: paho-mqtt",
        title="Reliable MQTT Subscriber",
        border_style="green"
    ))
    
    subscriber = ReliableSubscriber()
    
    if not subscriber.connect():
        console.print("❌ Failed to connect to MQTT broker", style="bold red")
        return
    
    try:
        console.print("👂 Listening for messages... (Press Ctrl+C to stop)", style="blue")
        
        # 定期的に統計情報を表示
        while True:
            time.sleep(30)
            subscriber.display_statistics()
            
    except KeyboardInterrupt:
        console.print("\n👋 Shutting down gracefully...", style="yellow")
        subscriber.display_statistics()
    finally:
        subscriber.disconnect()
        console.print("✨ Reliable subscriber shut down", style="bold green")

if __name__ == "__main__":
    main()
```

### Exercise 3: 統合テストスクリプト

`src/qos_integration_test.py` を作成：

```python
#!/usr/bin/env python3
"""
QoSとReliability統合テスト
パブリッシャーとサブスクライバーの協調動作テスト
"""

import subprocess
import sys
import time
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

def run_integration_test():
    console.print(Panel.fit(
        "🧪 MQTT QoS Integration Test\n\n"
        "このテストでは以下を実行します：\n"
        "1. Reliable Subscriberを起動\n"
        "2. QoS Publisherでテストメッセージ送信\n"
        "3. メッセージ配信と処理を確認\n"
        "4. 統計結果の表示",
        title="Integration Test Suite",
        border_style="blue"
    ))
    
    try:
        # Reliable Subscriberをバックグラウンドで起動
        console.print("🚀 Starting Reliable Subscriber...", style="blue")
        subscriber_process = subprocess.Popen([
            sys.executable, "reliable_subscriber.py"
        ])
        
        # 少し待機
        time.sleep(3)
        
        # QoS Publisherでテスト実行
        console.print("📤 Running QoS Publisher tests...", style="green")
        publisher_process = subprocess.run([
            sys.executable, "qos_publisher.py"
        ])
        
        # テスト完了まで少し待機
        time.sleep(5)
        
        console.print("✅ Integration test completed", style="bold green")
        
    except KeyboardInterrupt:
        console.print("\n👋 Test interrupted", style="yellow")
    finally:
        # プロセスをクリーンアップ
        if 'subscriber_process' in locals():
            subscriber_process.terminate()
            subscriber_process.wait()
        
        console.print("🧹 Cleanup completed", style="dim")

if __name__ == "__main__":
    run_integration_test()
```

## 📊 演習課題

### 課題 1: QoSレベルの使い分け
以下のシナリオで適切なQoSレベルを選択し、実装してください：

1. **工場の温度監視システム**
   - 毎秒の温度データ送信
   - 温度異常アラート
   - 冷却システム制御コマンド

2. **スマートホームシステム**
   - 照明の状態通知
   - セキュリティアラート
   - ドアロック制御

### 課題 2: メッセージ重複対策
QoS 1で発生する可能性がある重複メッセージに対して、以下を実装してください：

1. 冪等性のある処理ロジック
2. メッセージIDベースの重複検出
3. 重複統計の収集と表示

### 課題 3: 障害耐性テスト
以下の障害シナリオをテストし、システムの動作を確認してください：

1. ネットワーク瞬断時の動作
2. ブローカーの再起動
3. クライアントの異常終了

## 🎯 学習チェックポイント

- [ ] QoS 0, 1, 2の特性と使用場面を理解している
- [ ] Persistent Sessionの動作原理を理解している
- [ ] メッセージ重複検出と処理が実装できる
- [ ] エラーハンドリングとリトライ機能を実装できる
- [ ] 実際のIoTシナリオでの適切なQoS選択ができる

## 📚 参考資料

- [MQTT QoS Levels Explained - HiveMQ](https://www.hivemq.com/blog/mqtt-essentials-part-6-mqtt-quality-of-service-levels/)
- [MQTT Persistent Sessions - MQTT.org](https://mqtt.org/documentation/specifications/)
- [Paho MQTT Python Documentation](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)

---

**次のハンズオン**: [04-security-and-authentication](../04-security-and-authentication/) - セキュリティと認証