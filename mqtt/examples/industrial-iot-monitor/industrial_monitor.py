#!/usr/bin/env python3
"""
Industrial IoT Monitor - 産業用IoTモニタリングシステム
製造ラインの機器監視、予知保全、リアルタイム分析を行うMQTTシステム
"""

import paho.mqtt.client as mqtt
import json
import time
import sqlite3
import threading
import statistics
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum
from pathlib import Path

import pandas as pd
import numpy as np
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
from rich.layout import Layout

console = Console()

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

class MachineStatus(Enum):
    RUNNING = "running"
    IDLE = "idle"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    OFFLINE = "offline"

@dataclass
class SensorData:
    machine_id: str
    sensor_type: str
    value: float
    unit: str
    timestamp: datetime
    quality: float = 1.0  # データ品質 0-1

@dataclass
class Machine:
    machine_id: str
    machine_type: str
    line_id: str
    status: MachineStatus = MachineStatus.OFFLINE
    last_seen: Optional[datetime] = None
    sensor_data: Dict[str, List[SensorData]] = field(default_factory=dict)
    alerts: List[Dict[str, Any]] = field(default_factory=list)
    performance_metrics: Dict[str, float] = field(default_factory=dict)

class IndustrialIoTMonitor:
    """産業用IoTモニタリングシステム"""
    
    def __init__(self, broker_host: str = "localhost", port: int = 1883):
        self.broker_host = broker_host
        self.port = port
        
        # データベース初期化
        self.db_path = "industrial_iot.db"
        self.init_database()
        
        # 機器管理
        self.machines: Dict[str, Machine] = {}
        self.production_lines: Dict[str, List[str]] = {
            "line_a": [],
            "line_b": [],
            "line_c": []
        }
        
        # アラート設定
        self.alert_thresholds = {
            "temperature": {"warning": 80.0, "critical": 95.0},
            "vibration": {"warning": 2.0, "critical": 5.0},
            "pressure": {"warning": 150.0, "critical": 200.0},
            "current": {"warning": 80.0, "critical": 100.0}
        }
        
        # 統計データ
        self.stats = {
            "messages_processed": 0,
            "alerts_generated": 0,
            "machines_online": 0,
            "total_downtime": 0
        }
        
        # MQTT設定
        self.client = mqtt.Client(client_id="industrial_monitor")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        
        self.connected = threading.Event()
        
        # バックグラウンドタスク
        self.running = True
        self.start_background_tasks()
    
    def init_database(self):
        """データベースの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # センサーデータテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sensor_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    sensor_type TEXT NOT NULL,
                    value REAL NOT NULL,
                    unit TEXT NOT NULL,
                    quality REAL DEFAULT 1.0,
                    timestamp TEXT NOT NULL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # アラートテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS alerts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    alert_level TEXT NOT NULL,
                    message TEXT NOT NULL,
                    sensor_type TEXT,
                    value REAL,
                    threshold REAL,
                    acknowledged BOOLEAN DEFAULT FALSE,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # 機器状態履歴テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS machine_status_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    machine_id TEXT NOT NULL,
                    status TEXT NOT NULL,
                    duration_minutes REAL,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            console.print("🏭 Industrial IoT Monitor connected", style="bold green")
            self.connected.set()
            
            # 産業用トピックを購読
            topics = [
                ("factory/+/+/sensors/+", 0),      # センサーデータ
                ("factory/+/+/status", 1),         # 機器状態
                ("factory/+/+/commands", 2),       # 制御コマンド
                ("factory/+/+/maintenance", 1),    # 保全情報
                ("factory/alerts/+", 1),           # アラート
                ("factory/production/+", 0)        # 生産データ
            ]
            
            for topic, qos in topics:
                client.subscribe(topic, qos)
                console.print(f"📡 Subscribed: {topic}", style="blue")
        else:
            console.print(f"❌ Connection failed: {rc}", style="red")
    
    def on_message(self, client, userdata, msg):
        """メッセージ処理"""
        try:
            self.stats["messages_processed"] += 1
            
            topic_parts = msg.topic.split('/')
            payload = json.loads(msg.payload.decode())
            
            if len(topic_parts) >= 4:
                _, line_id, machine_id, message_type = topic_parts[:4]
                
                # メッセージタイプ別処理
                if message_type == "sensors":
                    self.handle_sensor_data(line_id, machine_id, topic_parts[4], payload)
                elif message_type == "status":
                    self.handle_status_update(line_id, machine_id, payload)
                elif message_type == "commands":
                    self.handle_command(line_id, machine_id, payload)
                elif message_type == "maintenance":
                    self.handle_maintenance_data(line_id, machine_id, payload)
                
            elif msg.topic.startswith("factory/alerts/"):
                self.handle_factory_alert(topic_parts[2], payload)
            elif msg.topic.startswith("factory/production/"):
                self.handle_production_data(topic_parts[2], payload)
                
        except json.JSONDecodeError:
            console.print(f"⚠️  Invalid JSON: {msg.topic}", style="yellow")
        except Exception as e:
            console.print(f"❌ Message processing error: {e}", style="red")
    
    def handle_sensor_data(self, line_id: str, machine_id: str, sensor_type: str, payload: Dict[str, Any]):
        """センサーデータの処理"""
        try:
            # 機器情報を取得または作成
            full_machine_id = f"{line_id}_{machine_id}"
            if full_machine_id not in self.machines:
                self.machines[full_machine_id] = Machine(
                    machine_id=full_machine_id,
                    machine_type=payload.get("machine_type", "unknown"),
                    line_id=line_id
                )
                
                # 生産ラインに追加
                if line_id in self.production_lines:
                    if full_machine_id not in self.production_lines[line_id]:
                        self.production_lines[line_id].append(full_machine_id)
            
            machine = self.machines[full_machine_id]
            machine.last_seen = datetime.now()
            machine.status = MachineStatus.RUNNING
            
            # センサーデータを作成
            sensor_data = SensorData(
                machine_id=full_machine_id,
                sensor_type=sensor_type,
                value=float(payload.get("value", 0)),
                unit=payload.get("unit", ""),
                timestamp=datetime.fromisoformat(payload.get("timestamp", datetime.now().isoformat())),
                quality=float(payload.get("quality", 1.0))
            )
            
            # データを保存
            if sensor_type not in machine.sensor_data:
                machine.sensor_data[sensor_type] = []
            
            machine.sensor_data[sensor_type].append(sensor_data)
            
            # 最新1000件のみ保持
            if len(machine.sensor_data[sensor_type]) > 1000:
                machine.sensor_data[sensor_type] = machine.sensor_data[sensor_type][-1000:]
            
            # データベースに保存
            self.save_sensor_data_to_db(sensor_data)
            
            # 異常検知
            self.check_sensor_alerts(machine, sensor_data)
            
            # パフォーマンス計算
            self.calculate_performance_metrics(machine, sensor_type)
            
        except Exception as e:
            console.print(f"❌ Sensor data error: {e}", style="red")
    
    def handle_status_update(self, line_id: str, machine_id: str, payload: Dict[str, Any]):
        """機器状態更新の処理"""
        full_machine_id = f"{line_id}_{machine_id}"
        
        if full_machine_id in self.machines:
            machine = self.machines[full_machine_id]
            old_status = machine.status
            
            try:
                new_status = MachineStatus(payload.get("status", "offline"))
                machine.status = new_status
                machine.last_seen = datetime.now()
                
                # 状態変更をログ
                if old_status != new_status:
                    console.print(f"🔄 {full_machine_id}: {old_status.value} → {new_status.value}", 
                                style="cyan")
                    
                    # データベースに状態履歴を保存
                    self.save_status_change_to_db(full_machine_id, new_status.value)
                    
                    # アラート生成
                    if new_status == MachineStatus.ERROR:
                        self.generate_alert(
                            full_machine_id, 
                            AlertLevel.CRITICAL,
                            f"Machine entered ERROR state: {payload.get('error_message', 'Unknown error')}"
                        )
                    
            except ValueError:
                console.print(f"⚠️  Invalid status: {payload.get('status')}", style="yellow")
    
    def handle_command(self, line_id: str, machine_id: str, payload: Dict[str, Any]):
        """制御コマンドの処理"""
        full_machine_id = f"{line_id}_{machine_id}"
        command = payload.get("command")
        
        console.print(f"⚙️  Command for {full_machine_id}: {command}", style="magenta")
        
        # コマンド実行のシミュレート
        if command == "start":
            self.send_machine_command(full_machine_id, "start_production")
        elif command == "stop":
            self.send_machine_command(full_machine_id, "stop_production")
        elif command == "maintenance":
            self.schedule_maintenance(full_machine_id, payload.get("maintenance_type"))
        elif command == "reset_alerts":
            self.reset_machine_alerts(full_machine_id)
    
    def handle_maintenance_data(self, line_id: str, machine_id: str, payload: Dict[str, Any]):
        """保全データの処理"""
        full_machine_id = f"{line_id}_{machine_id}"
        maintenance_type = payload.get("type")
        
        console.print(f"🔧 Maintenance for {full_machine_id}: {maintenance_type}", style="yellow")
        
        if full_machine_id in self.machines:
            machine = self.machines[full_machine_id]
            machine.status = MachineStatus.MAINTENANCE
            
            # 保全情報をアラートとして記録
            self.generate_alert(
                full_machine_id,
                AlertLevel.INFO,
                f"Maintenance started: {maintenance_type}"
            )
    
    def check_sensor_alerts(self, machine: Machine, sensor_data: SensorData):
        """センサーアラートチェック"""
        sensor_type = sensor_data.sensor_type
        value = sensor_data.value
        
        if sensor_type in self.alert_thresholds:
            thresholds = self.alert_thresholds[sensor_type]
            
            if value >= thresholds["critical"]:
                self.generate_alert(
                    machine.machine_id,
                    AlertLevel.CRITICAL,
                    f"{sensor_type.title()} critical: {value} {sensor_data.unit}",
                    sensor_type=sensor_type,
                    value=value,
                    threshold=thresholds["critical"]
                )
            elif value >= thresholds["warning"]:
                self.generate_alert(
                    machine.machine_id,
                    AlertLevel.WARNING,
                    f"{sensor_type.title()} high: {value} {sensor_data.unit}",
                    sensor_type=sensor_type,
                    value=value,
                    threshold=thresholds["warning"]
                )
    
    def generate_alert(self, machine_id: str, level: AlertLevel, message: str,
                      sensor_type: Optional[str] = None, value: Optional[float] = None,
                      threshold: Optional[float] = None):
        """アラート生成"""
        alert = {
            "machine_id": machine_id,
            "level": level.value,
            "message": message,
            "sensor_type": sensor_type,
            "value": value,
            "threshold": threshold,
            "timestamp": datetime.now(),
            "acknowledged": False
        }
        
        # 機器のアラートリストに追加
        if machine_id in self.machines:
            self.machines[machine_id].alerts.append(alert)
            
            # 最新100件のみ保持
            if len(self.machines[machine_id].alerts) > 100:
                self.machines[machine_id].alerts = self.machines[machine_id].alerts[-100:]
        
        # データベースに保存
        self.save_alert_to_db(alert)
        
        # 統計更新
        self.stats["alerts_generated"] += 1
        
        # アラートレベルに応じた処理
        if level == AlertLevel.CRITICAL:
            console.print(f"🚨 CRITICAL ALERT: {machine_id} - {message}", style="bold red")
            # 緊急時の自動対応
            self.handle_critical_alert(machine_id, message)
        elif level == AlertLevel.WARNING:
            console.print(f"⚠️  WARNING: {machine_id} - {message}", style="yellow")
        
        # MQTTでアラートを配信
        self.publish_alert(alert)
    
    def handle_critical_alert(self, machine_id: str, message: str):
        """重大アラートの自動対応"""
        # 緊急停止コマンドを送信
        emergency_command = {
            "command": "emergency_stop",
            "reason": message,
            "timestamp": datetime.now().isoformat(),
            "auto_generated": True
        }
        
        line_parts = machine_id.split('_')
        if len(line_parts) >= 2:
            line_id, machine_name = line_parts[0], '_'.join(line_parts[1:])
            topic = f"factory/{line_id}/{machine_name}/emergency"
            
            self.client.publish(topic, json.dumps(emergency_command), qos=2)
            console.print(f"🛑 Emergency stop sent to {machine_id}", style="bold red")
    
    def calculate_performance_metrics(self, machine: Machine, sensor_type: str):
        """性能指標の計算"""
        if sensor_type not in machine.sensor_data:
            return
        
        recent_data = machine.sensor_data[sensor_type][-100:]  # 最新100件
        
        if len(recent_data) >= 10:
            values = [d.value for d in recent_data]
            
            # 統計値を計算
            machine.performance_metrics.update({
                f"{sensor_type}_mean": statistics.mean(values),
                f"{sensor_type}_std": statistics.stdev(values) if len(values) > 1 else 0,
                f"{sensor_type}_min": min(values),
                f"{sensor_type}_max": max(values),
                f"{sensor_type}_trend": self.calculate_trend(values)
            })
    
    def calculate_trend(self, values: List[float]) -> float:
        """トレンド計算（線形回帰の傾き）"""
        if len(values) < 2:
            return 0.0
        
        x = list(range(len(values)))
        n = len(values)
        
        x_mean = sum(x) / n
        y_mean = sum(values) / n
        
        numerator = sum((x[i] - x_mean) * (values[i] - y_mean) for i in range(n))
        denominator = sum((x[i] - x_mean) ** 2 for i in range(n))
        
        return numerator / denominator if denominator != 0 else 0.0
    
    def save_sensor_data_to_db(self, sensor_data: SensorData):
        """センサーデータをデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO sensor_data 
                    (machine_id, sensor_type, value, unit, quality, timestamp)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    sensor_data.machine_id,
                    sensor_data.sensor_type,
                    sensor_data.value,
                    sensor_data.unit,
                    sensor_data.quality,
                    sensor_data.timestamp.isoformat()
                ))
                conn.commit()
        except Exception as e:
            console.print(f"❌ DB save error: {e}", style="red")
    
    def save_alert_to_db(self, alert: Dict[str, Any]):
        """アラートをデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO alerts 
                    (machine_id, alert_level, message, sensor_type, value, threshold)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    alert["machine_id"],
                    alert["level"],
                    alert["message"],
                    alert["sensor_type"],
                    alert["value"],
                    alert["threshold"]
                ))
                conn.commit()
        except Exception as e:
            console.print(f"❌ Alert save error: {e}", style="red")
    
    def save_status_change_to_db(self, machine_id: str, status: str):
        """状態変更をデータベースに保存"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO machine_status_history (machine_id, status)
                    VALUES (?, ?)
                ''', (machine_id, status))
                conn.commit()
        except Exception as e:
            console.print(f"❌ Status save error: {e}", style="red")
    
    def publish_alert(self, alert: Dict[str, Any]):
        """アラートをMQTTで配信"""
        topic = f"factory/alerts/{alert['level']}"
        payload = {
            "machine_id": alert["machine_id"],
            "level": alert["level"],
            "message": alert["message"],
            "timestamp": alert["timestamp"].isoformat(),
            "sensor_type": alert["sensor_type"],
            "value": alert["value"],
            "threshold": alert["threshold"]
        }
        
        self.client.publish(topic, json.dumps(payload, default=str), qos=1)
    
    def send_machine_command(self, machine_id: str, command: str):
        """機器にコマンドを送信"""
        line_parts = machine_id.split('_')
        if len(line_parts) >= 2:
            line_id, machine_name = line_parts[0], '_'.join(line_parts[1:])
            topic = f"factory/{line_id}/{machine_name}/commands/response"
            
            response = {
                "command": command,
                "status": "executed",
                "timestamp": datetime.now().isoformat()
            }
            
            self.client.publish(topic, json.dumps(response), qos=1)
    
    def get_dashboard_layout(self) -> Layout:
        """ダッシュボードレイアウトを作成"""
        layout = Layout()
        
        layout.split_column(
            Layout(self.get_stats_panel(), name="stats", size=8),
            Layout(name="main")
        )
        
        layout["main"].split_row(
            Layout(self.get_machines_table(), name="machines"),
            Layout(self.get_alerts_table(), name="alerts")
        )
        
        return layout
    
    def get_stats_panel(self) -> Panel:
        """統計情報パネル"""
        self.stats["machines_online"] = len([m for m in self.machines.values() 
                                            if m.status != MachineStatus.OFFLINE])
        
        stats_text = f"""
📊 Messages Processed: {self.stats['messages_processed']}
🏭 Machines Online: {self.stats['machines_online']} / {len(self.machines)}
🚨 Alerts Generated: {self.stats['alerts_generated']}
⏰ System Uptime: {self.get_uptime()}
        """.strip()
        
        return Panel(stats_text, title="System Statistics", border_style="blue")
    
    def get_machines_table(self) -> Table:
        """機器状況テーブル"""
        table = Table(title="Machine Status")
        table.add_column("Machine ID", style="cyan")
        table.add_column("Line", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Last Seen", style="yellow")
        table.add_column("Alerts", style="red")
        
        for machine in sorted(self.machines.values(), key=lambda m: m.machine_id):
            status_style = {
                MachineStatus.RUNNING: "green",
                MachineStatus.IDLE: "yellow", 
                MachineStatus.MAINTENANCE: "blue",
                MachineStatus.ERROR: "red",
                MachineStatus.OFFLINE: "dim"
            }.get(machine.status, "white")
            
            last_seen = machine.last_seen.strftime("%H:%M:%S") if machine.last_seen else "Never"
            alert_count = len([a for a in machine.alerts if not a["acknowledged"]])
            alert_text = f"{alert_count} active" if alert_count > 0 else "None"
            
            table.add_row(
                machine.machine_id,
                machine.line_id,
                f"[{status_style}]{machine.status.value}[/]",
                last_seen,
                alert_text
            )
        
        return table
    
    def get_alerts_table(self) -> Table:
        """アラートテーブル"""
        table = Table(title="Recent Alerts")
        table.add_column("Time", style="blue")
        table.add_column("Machine", style="cyan")
        table.add_column("Level", style="yellow")
        table.add_column("Message", style="white")
        
        # 全アラートを収集して時刻順にソート
        all_alerts = []
        for machine in self.machines.values():
            for alert in machine.alerts[-5:]:  # 最新5件
                all_alerts.append(alert)
        
        all_alerts.sort(key=lambda a: a["timestamp"], reverse=True)
        
        for alert in all_alerts[:10]:  # 最新10件表示
            level_style = {
                "critical": "bold red",
                "warning": "yellow",
                "info": "blue"
            }.get(alert["level"], "white")
            
            time_str = alert["timestamp"].strftime("%H:%M:%S")
            
            table.add_row(
                time_str,
                alert["machine_id"],
                f"[{level_style}]{alert['level'].upper()}[/]",
                alert["message"][:50] + "..." if len(alert["message"]) > 50 else alert["message"]
            )
        
        return table
    
    def get_uptime(self) -> str:
        """システム稼働時間を取得"""
        if not hasattr(self, 'start_time'):
            self.start_time = datetime.now()
        
        uptime = datetime.now() - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, _ = divmod(remainder, 60)
        
        return f"{hours:02d}:{minutes:02d}"
    
    def start_background_tasks(self):
        """バックグラウンドタスクを開始"""
        def health_check_loop():
            while self.running:
                time.sleep(30)  # 30秒間隔
                self.perform_health_check()
        
        def cleanup_loop():
            while self.running:
                time.sleep(300)  # 5分間隔
                self.cleanup_old_data()
        
        threading.Thread(target=health_check_loop, daemon=True).start()
        threading.Thread(target=cleanup_loop, daemon=True).start()
    
    def perform_health_check(self):
        """機器のヘルスチェック"""
        current_time = datetime.now()
        
        for machine in self.machines.values():
            if machine.last_seen:
                time_since_last_seen = current_time - machine.last_seen
                
                # 5分間応答がない場合はオフラインに
                if time_since_last_seen > timedelta(minutes=5):
                    if machine.status != MachineStatus.OFFLINE:
                        machine.status = MachineStatus.OFFLINE
                        self.generate_alert(
                            machine.machine_id,
                            AlertLevel.WARNING,
                            f"Machine went offline (last seen: {machine.last_seen.strftime('%H:%M:%S')})"
                        )
    
    def cleanup_old_data(self):
        """古いデータのクリーンアップ"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 7日以上古いセンサーデータを削除
                cutoff_date = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute('''
                    DELETE FROM sensor_data WHERE timestamp < ?
                ''', (cutoff_date,))
                
                # 30日以上古いアラートを削除
                cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
                cursor.execute('''
                    DELETE FROM alerts WHERE created_at < ?
                ''', (cutoff_date,))
                
                conn.commit()
                
        except Exception as e:
            console.print(f"❌ Cleanup error: {e}", style="red")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            console.print("⚠️  Unexpected disconnection", style="yellow")
        self.connected.clear()
    
    def connect(self) -> bool:
        try:
            self.client.connect(self.broker_host, self.port, 60)
            self.client.loop_start()
            return self.connected.wait(timeout=10)
        except Exception as e:
            console.print(f"❌ Connection error: {e}", style="red")
            return False
    
    def start_monitoring(self):
        """監視開始"""
        with Live(self.get_dashboard_layout(), refresh_per_second=1) as live:
            try:
                while True:
                    time.sleep(1)
                    live.update(self.get_dashboard_layout())
            except KeyboardInterrupt:
                console.print("\n👋 Monitoring stopped", style="yellow")
    
    def disconnect(self):
        self.running = False
        if self.connected.is_set():
            self.client.loop_stop()
            self.client.disconnect()

def main():
    """メイン実行関数"""
    console.print(Panel.fit(
        "🏭 Industrial IoT Monitor\n\n"
        "機能：\n"
        "• 製造ライン機器のリアルタイム監視\n"
        "• 予知保全とアラート管理\n"
        "• パフォーマンス分析\n"
        "• 自動緊急対応\n\n"
        "Language: Python 3\n"
        "Libraries: paho-mqtt, pandas, rich",
        title="Industrial IoT Monitoring System",
        border_style="blue"
    ))
    
    monitor = IndustrialIoTMonitor()
    
    if not monitor.connect():
        console.print("❌ Failed to connect to MQTT broker", style="bold red")
        return
    
    try:
        monitor.start_monitoring()
    finally:
        monitor.disconnect()
        console.print("✨ Industrial IoT Monitor shut down", style="bold green")

if __name__ == "__main__":
    main()