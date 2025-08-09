#!/usr/bin/env python3
"""
Smart Home System - MQTT Controller (Python Version)
スマートホームシステムのメインコントローラー
"""

import paho.mqtt.client as mqtt
import json
import time
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel

# ロギング設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

console = Console()

@dataclass
class Device:
    """スマートデバイスの情報を格納するデータクラス"""
    device_id: str
    device_type: str
    room: str
    status: str = "unknown"
    last_seen: Optional[datetime] = None
    data: Optional[Dict[str, Any]] = None

class SmartHomeController:
    """スマートホームシステムのメインコントローラー"""
    
    def __init__(self, broker_host: str = "localhost", broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        
        # デバイス管理
        self.devices: Dict[str, Device] = {}
        self.automation_rules: List[Dict[str, Any]] = []
        
        # MQTT設定
        self.client = mqtt.Client(client_id="smart_home_controller")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        # 接続状態管理
        self.connected = threading.Event()
        
        # デフォルトの自動化ルールを追加
        self.setup_default_automation_rules()
    
    def setup_default_automation_rules(self):
        """デフォルトの自動化ルールを設定"""
        # モーションセンサーに反応して照明をオン
        motion_rule = {
            "name": "Motion Light Control",
            "trigger_topic": "home/+/motion/detected",
            "condition": lambda data: data.get("detected", False),
            "actions": [
                {
                    "topic_template": "home/{room}/light/command",
                    "payload": {"state": "on", "brightness": 80}
                }
            ]
        }
        
        # 高温アラートでエアコン制御
        temperature_rule = {
            "name": "Temperature Control",
            "trigger_topic": "home/+/temperature/value",
            "condition": lambda data: data.get("temperature", 0) > 28,
            "actions": [
                {
                    "topic_template": "home/{room}/ac/command",
                    "payload": {"state": "on", "mode": "cool", "temperature": 24}
                }
            ]
        }
        
        self.automation_rules.extend([motion_rule, temperature_rule])
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT接続時のコールバック"""
        if rc == 0:
            logger.info("✅ Connected to MQTT broker")
            self.connected.set()
            
            # 全デバイストピックを購読
            topics = [
                ("home/+/+/+", 0),  # 全デバイスデータ
                ("devices/+/status", 1),  # デバイス状態
                ("alerts/+/+", 1),  # アラート
            ]
            
            for topic, qos in topics:
                client.subscribe(topic, qos)
                logger.info(f"📡 Subscribed to: {topic}")
        else:
            logger.error(f"❌ Failed to connect: {rc}")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            logger.debug(f"📨 Received: {topic} - {payload}")
            
            # トピックをパースしてデバイス情報を抽出
            topic_parts = topic.split('/')
            
            if topic.startswith("home/"):
                self.handle_device_message(topic_parts, payload)
            elif topic.startswith("devices/"):
                self.handle_device_status(topic_parts, payload)
            elif topic.startswith("alerts/"):
                self.handle_alert_message(topic_parts, payload)
                
            # 自動化ルールをチェック
            self.check_automation_rules(topic, payload)
            
        except json.JSONDecodeError:
            logger.warning(f"Invalid JSON in message: {msg.payload}")
        except Exception as e:
            logger.error(f"Error processing message: {e}")
    
    def handle_device_message(self, topic_parts: List[str], payload: Dict[str, Any]):
        """デバイスからのメッセージを処理"""
        if len(topic_parts) >= 4:
            _, room, device_type, metric = topic_parts[:4]
            device_id = f"{room}_{device_type}"
            
            # デバイス情報を更新
            if device_id not in self.devices:
                self.devices[device_id] = Device(
                    device_id=device_id,
                    device_type=device_type,
                    room=room
                )
            
            device = self.devices[device_id]
            device.last_seen = datetime.now()
            device.status = "online"
            
            if device.data is None:
                device.data = {}
            
            # メトリクス別の処理
            if metric == "temperature":
                device.data["temperature"] = payload.get("value", payload)
            elif metric == "humidity":
                device.data["humidity"] = payload.get("value", payload)
            elif metric == "motion":
                device.data["motion_detected"] = payload.get("detected", False)
            elif metric == "light":
                device.data.update(payload)
            else:
                device.data[metric] = payload
    
    def handle_device_status(self, topic_parts: List[str], payload: Dict[str, Any]):
        """デバイスステータス更新を処理"""
        if len(topic_parts) >= 3:
            device_id = topic_parts[1]
            status = payload.get("status", "unknown")
            
            if device_id in self.devices:
                self.devices[device_id].status = status
                logger.info(f"🔄 Device {device_id} status: {status}")
    
    def handle_alert_message(self, topic_parts: List[str], payload: Dict[str, Any]):
        """アラートメッセージを処理"""
        alert_type = topic_parts[1] if len(topic_parts) > 1 else "unknown"
        logger.warning(f"🚨 Alert [{alert_type}]: {payload}")
        
        # 緊急時プロトコル
        if alert_type == "fire":
            self.trigger_emergency_protocol("fire")
        elif alert_type == "security":
            self.trigger_emergency_protocol("security")
    
    def check_automation_rules(self, topic: str, payload: Dict[str, Any]):
        """自動化ルールをチェックして実行"""
        for rule in self.automation_rules:
            if self.topic_matches_pattern(topic, rule["trigger_topic"]):
                if rule["condition"](payload):
                    logger.info(f"🤖 Executing automation rule: {rule['name']}")
                    self.execute_rule_actions(rule["actions"], topic, payload)
    
    def topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """トピックがパターンにマッチするかチェック"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(topic_parts) != len(pattern_parts):
            return False
        
        for t, p in zip(topic_parts, pattern_parts):
            if p != '+' and p != '#' and p != t:
                return False
        
        return True
    
    def execute_rule_actions(self, actions: List[Dict[str, Any]], trigger_topic: str, trigger_payload: Dict[str, Any]):
        """自動化ルールのアクションを実行"""
        # トリガートピックから部屋を抽出
        topic_parts = trigger_topic.split('/')
        room = topic_parts[1] if len(topic_parts) > 1 else "unknown"
        
        for action in actions:
            try:
                # トピックテンプレートの変数を置換
                topic = action["topic_template"].replace("{room}", room)
                payload = json.dumps(action["payload"])
                
                result = self.client.publish(topic, payload, qos=1)
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    logger.info(f"✅ Automation action sent: {topic}")
                else:
                    logger.error(f"❌ Failed to send automation action: {result.rc}")
                    
            except Exception as e:
                logger.error(f"Error executing action: {e}")
    
    def trigger_emergency_protocol(self, alert_type: str):
        """緊急時プロトコルを実行"""
        logger.critical(f"🚨 EMERGENCY PROTOCOL ACTIVATED: {alert_type}")
        
        if alert_type == "fire":
            # 全照明を点灯
            for device in self.devices.values():
                if device.device_type == "light":
                    topic = f"home/{device.room}/light/command"
                    payload = json.dumps({"state": "on", "brightness": 100})
                    self.client.publish(topic, payload, qos=1)
            
            # 緊急用電源以外を停止
            self.publish_broadcast_command("plug", {"state": "off", "exclude": ["emergency"]})
            
        elif alert_type == "security":
            # 全ライトを点灯（防犯対策）
            self.publish_broadcast_command("light", {"state": "on", "brightness": 100})
    
    def publish_broadcast_command(self, device_type: str, command: Dict[str, Any]):
        """特定デバイスタイプに一斉コマンド送信"""
        topic = f"broadcast/{device_type}/command"
        payload = json.dumps(command)
        self.client.publish(topic, payload, qos=1)
        logger.info(f"📢 Broadcast command sent to {device_type}: {command}")
    
    def on_disconnect(self, client, userdata, rc):
        """MQTT切断時のコールバック"""
        if rc != 0:
            logger.warning(f"⚠️ Unexpected disconnection: {rc}")
        else:
            logger.info("🔌 Disconnected from broker")
        self.connected.clear()
    
    def connect(self) -> bool:
        """ブローカーに接続"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            if self.connected.wait(timeout=10):
                return True
            else:
                logger.error("Connection timeout")
                return False
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """ブローカーから切断"""
        self.client.loop_stop()
        self.client.disconnect()
    
    def get_system_status(self) -> Table:
        """システム状態を表形式で取得"""
        table = Table(title="Smart Home System Status")
        
        table.add_column("Device ID", style="cyan")
        table.add_column("Type", style="magenta")
        table.add_column("Room", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Last Seen", style="blue")
        table.add_column("Data", style="white")
        
        for device in self.devices.values():
            last_seen = device.last_seen.strftime("%H:%M:%S") if device.last_seen else "Never"
            data_str = json.dumps(device.data, indent=None) if device.data else "No data"
            
            table.add_row(
                device.device_id,
                device.device_type,
                device.room,
                device.status,
                last_seen,
                data_str[:50] + "..." if len(data_str) > 50 else data_str
            )
        
        return table
    
    def start_monitoring(self):
        """リアルタイム監視を開始"""
        logger.info("🖥️  Starting system monitoring...")
        
        try:
            with Live(self.get_system_status(), refresh_per_second=1) as live:
                while True:
                    time.sleep(1)
                    live.update(self.get_system_status())
        except KeyboardInterrupt:
            console.print("\n👋 Monitoring stopped by user", style="yellow")
    
    def send_test_data(self):
        """テストデータを送信"""
        test_devices = [
            {"room": "living_room", "type": "temperature", "data": {"value": 23.5, "unit": "C"}},
            {"room": "kitchen", "type": "motion", "data": {"detected": True, "timestamp": time.time()}},
            {"room": "bedroom", "type": "light", "data": {"state": "off", "brightness": 0}},
        ]
        
        for device in test_devices:
            topic = f"home/{device['room']}/{device['type']}/value"
            payload = json.dumps(device['data'])
            self.client.publish(topic, payload, qos=1)
            logger.info(f"📤 Test data sent: {topic}")

def main():
    """メイン実行関数"""
    console.print(Panel.fit(
        "🏠 Smart Home System Controller\n\n"
        "Language: Python 3\n"
        "Library: paho-mqtt\n"
        "Features: Device Management, Automation, Emergency Protocols",
        title="MQTT Smart Home Controller",
        border_style="blue"
    ))
    
    controller = SmartHomeController()
    
    if not controller.connect():
        console.print("❌ Failed to connect to MQTT broker", style="bold red")
        return
    
    # 少し待ってからテストデータ送信
    time.sleep(2)
    controller.send_test_data()
    
    try:
        # リアルタイム監視開始
        controller.start_monitoring()
    except KeyboardInterrupt:
        pass
    finally:
        controller.disconnect()
        console.print("✨ Smart Home Controller shut down gracefully", style="bold green")

if __name__ == "__main__":
    main()