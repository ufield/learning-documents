# ハンズオン 10: 監視ダッシュボード

## 🎯 学習目標

このハンズオンでは包括的なMQTT監視ダッシュボードの構築について学習します：

- リアルタイム監視ダッシュボードの実装
- メトリクス収集と可視化
- アラート機能とスレッショルド監視
- 履歴データ分析とトレンド表示
- デバイス状態管理とヘルスチェック
- パフォーマンス監視と最適化
- カスタムダッシュボードの構築

**所要時間**: 約180分

## 📋 前提条件

- [08-cloud-integration](../08-cloud-integration/) の完了
- Web開発の基本知識（HTML/CSS/JavaScript）
- データベース操作の基本理解
- グラフ描画ライブラリの基本知識

## 📊 監視アーキテクチャ

### 包括的な監視システム構成

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IoT Devices   │───▶│ MQTT Collectors │───▶│   Time Series   │
│                 │    │                 │    │    Database     │
│ • Sensors       │    │ • Message Count │    │                 │
│ • Actuators     │    │ • QoS Metrics   │    │ • InfluxDB      │
│ • Gateways      │    │ • Latency       │    │ • TimescaleDB   │
│                 │    │ • Error Rates   │    │ • Prometheus    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲                        ▲
                                │                        │
┌─────────────────┐            │                        ▼
│  MQTT Brokers   │────────────┘              ┌─────────────────┐
│                 │                           │  Web Dashboard  │
│ • Mosquitto     │                           │                 │
│ • AWS IoT       │                           │ • Real-time     │
│ • Azure IoT Hub │                           │ • Historical    │
└─────────────────┘                           │ • Alerts        │
                                              │ • Analytics     │
                                              └─────────────────┘
```

## 📝 実装演習

### Exercise 1: メトリクス収集システム

`src/mqtt_metrics_collector.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from collections import defaultdict, deque
import sqlite3
from dataclasses import dataclass, asdict
import statistics
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live
from rich.layout import Layout
from rich.text import Text

console = Console()

@dataclass
class MQTTMetrics:
    """MQTT メトリクスデータクラス"""
    timestamp: float
    broker_host: str
    topic: str
    message_count: int
    total_bytes: int
    qos_0_count: int
    qos_1_count: int
    qos_2_count: int
    average_latency: float
    error_count: int
    connection_count: int
    subscription_count: int

@dataclass 
class DeviceStatus:
    """デバイス状態データクラス"""
    device_id: str
    last_seen: float
    status: str  # online, offline, warning
    message_count: int
    error_count: int
    battery_level: Optional[float]
    signal_strength: Optional[float]

class MQTTMetricsCollector:
    """MQTT メトリクス収集クラス"""
    
    def __init__(self, db_path: str = "mqtt_metrics.db"):
        self.db_path = db_path
        self.metrics_buffer = deque(maxlen=1000)
        self.device_statuses = {}
        self.topic_statistics = defaultdict(lambda: {
            'message_count': 0,
            'total_bytes': 0,
            'last_message_time': 0,
            'qos_distribution': {'0': 0, '1': 0, '2': 0},
            'error_count': 0
        })
        
        # リアルタイム統計用
        self.realtime_stats = {
            'messages_per_minute': deque(maxlen=60),
            'bytes_per_minute': deque(maxlen=60),
            'latency_samples': deque(maxlen=100),
            'error_rate': deque(maxlen=60)
        }
        
        # 監視クライアント
        self.monitor_client = mqtt.Client(client_id="metrics-collector")
        self.monitor_client.on_connect = self.on_connect
        self.monitor_client.on_message = self.on_message
        self.monitor_client.on_disconnect = self.on_disconnect
        
        self.is_running = False
        self.init_database()
    
    def init_database(self):
        """データベース初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS mqtt_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    broker_host TEXT NOT NULL,
                    topic TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    total_bytes INTEGER DEFAULT 0,
                    qos_0_count INTEGER DEFAULT 0,
                    qos_1_count INTEGER DEFAULT 0,
                    qos_2_count INTEGER DEFAULT 0,
                    average_latency REAL DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    connection_count INTEGER DEFAULT 0,
                    subscription_count INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS device_status (
                    device_id TEXT PRIMARY KEY,
                    last_seen REAL NOT NULL,
                    status TEXT NOT NULL,
                    message_count INTEGER DEFAULT 0,
                    error_count INTEGER DEFAULT 0,
                    battery_level REAL,
                    signal_strength REAL,
                    updated_at REAL NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS alert_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp REAL NOT NULL,
                    alert_type TEXT NOT NULL,
                    severity TEXT NOT NULL,
                    source TEXT NOT NULL,
                    message TEXT NOT NULL,
                    resolved BOOLEAN DEFAULT FALSE,
                    resolved_at REAL
                )
            """)
            
            conn.commit()
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print("✅ メトリクス収集クライアント接続完了", style="green")
            # 全てのトピックを監視（ワイルドカード使用）
            client.subscribe("#", qos=0)
            client.subscribe("$SYS/#", qos=0)  # ブローカー統計情報
        else:
            console.print(f"❌ メトリクス収集クライアント接続失敗: {rc}", style="red")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック（メトリクス収集）"""
        current_time = time.time()
        topic = msg.topic
        payload = msg.payload
        qos = msg.qos
        
        # システムトピック（$SYS）の処理
        if topic.startswith("$SYS/"):
            self._process_system_message(topic, payload)
            return
        
        # 通常のメッセージ統計を更新
        stats = self.topic_statistics[topic]
        stats['message_count'] += 1
        stats['total_bytes'] += len(payload)
        stats['last_message_time'] = current_time
        stats['qos_distribution'][str(qos)] += 1
        
        # デバイス状態の更新
        self._update_device_status(topic, payload, current_time)
        
        # リアルタイム統計の更新
        self._update_realtime_stats(len(payload))
        
        # 異常検知
        self._detect_anomalies(topic, payload, current_time)
    
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        if rc != 0:
            console.print("⚠️  メトリクス収集クライアントが予期せず切断されました", style="yellow")
    
    def _process_system_message(self, topic: str, payload: bytes):
        """$SYSシステムメッセージの処理"""
        try:
            value = payload.decode('utf-8')
            
            # よく使われる$SYSトピックの処理例
            if topic.endswith("/clients/connected"):
                console.print(f"📊 接続クライアント数: {value}", style="blue")
            elif topic.endswith("/messages/received"):
                console.print(f"📥 受信メッセージ総数: {value}", style="blue") 
            elif topic.endswith("/messages/sent"):
                console.print(f"📤 送信メッセージ総数: {value}", style="blue")
            elif topic.endswith("/subscriptions/count"):
                console.print(f"📝 購読数: {value}", style="blue")
                
        except UnicodeDecodeError:
            pass  # バイナリデータは無視
    
    def _update_device_status(self, topic: str, payload: bytes, timestamp: float):
        """デバイス状態の更新"""
        # トピックからデバイスIDを抽出（例: device/sensor-001/data）
        parts = topic.split('/')
        if len(parts) >= 2 and parts[0] == 'device':
            device_id = parts[1]
            
            try:
                # JSONペイロードの場合、追加情報を抽出
                data = json.loads(payload.decode('utf-8'))
                battery_level = data.get('battery_level')
                signal_strength = data.get('signal_strength')
                error_info = data.get('error')
                
            except (json.JSONDecodeError, UnicodeDecodeError):
                battery_level = None
                signal_strength = None
                error_info = None
            
            # デバイス状態を更新
            if device_id in self.device_statuses:
                device = self.device_statuses[device_id]
                device.last_seen = timestamp
                device.message_count += 1
                if error_info:
                    device.error_count += 1
                    device.status = "warning"
                else:
                    device.status = "online"
            else:
                self.device_statuses[device_id] = DeviceStatus(
                    device_id=device_id,
                    last_seen=timestamp,
                    status="online",
                    message_count=1,
                    error_count=1 if error_info else 0,
                    battery_level=battery_level,
                    signal_strength=signal_strength
                )
            
            # バッテリーレベルとシグナル強度を更新
            if battery_level is not None:
                self.device_statuses[device_id].battery_level = battery_level
            if signal_strength is not None:
                self.device_statuses[device_id].signal_strength = signal_strength
    
    def _update_realtime_stats(self, message_size: int):
        """リアルタイム統計の更新"""
        current_time = time.time()
        
        # 分ごとの統計を更新（60秒分の移動平均）
        self.realtime_stats['messages_per_minute'].append({
            'timestamp': current_time,
            'count': 1
        })
        
        self.realtime_stats['bytes_per_minute'].append({
            'timestamp': current_time,
            'bytes': message_size
        })
    
    def _detect_anomalies(self, topic: str, payload: bytes, timestamp: float):
        """異常検知"""
        stats = self.topic_statistics[topic]
        
        # メッセージ頻度の異常検知
        if stats['last_message_time'] > 0:
            interval = timestamp - stats['last_message_time']
            
            # 30秒以上メッセージが来ない場合
            if interval > 30:
                self._create_alert(
                    alert_type="message_gap",
                    severity="warning",
                    source=topic,
                    message=f"メッセージ間隔が異常: {interval:.1f}秒"
                )
        
        # メッセージサイズの異常検知
        if len(payload) > 10000:  # 10KB以上
            self._create_alert(
                alert_type="large_message",
                severity="warning", 
                source=topic,
                message=f"大きなメッセージ: {len(payload)} bytes"
            )
    
    def _create_alert(self, alert_type: str, severity: str, source: str, message: str):
        """アラート作成"""
        timestamp = time.time()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO alert_history (timestamp, alert_type, severity, source, message)
                VALUES (?, ?, ?, ?, ?)
            """, (timestamp, alert_type, severity, source, message))
            conn.commit()
        
        # コンソールにもアラート表示
        severity_colors = {
            'info': 'blue',
            'warning': 'yellow', 
            'critical': 'red'
        }
        color = severity_colors.get(severity, 'white')
        console.print(f"🚨 [{severity.upper()}] {message} (source: {source})", style=color)
    
    def start_collection(self, broker_host: str = 'localhost', broker_port: int = 1883):
        """メトリクス収集開始"""
        console.print("📊 MQTT メトリクス収集を開始します", style="bold blue")
        
        try:
            self.monitor_client.connect(broker_host, broker_port, 60)
            self.monitor_client.loop_start()
            self.is_running = True
            
            # 定期的なメトリクス保存スレッド
            save_thread = threading.Thread(target=self._periodic_save, daemon=True)
            save_thread.start()
            
            # デバイス状態監視スレッド
            status_thread = threading.Thread(target=self._device_status_monitor, daemon=True)
            status_thread.start()
            
            return True
            
        except Exception as e:
            console.print(f"❌ メトリクス収集開始エラー: {e}", style="red")
            return False
    
    def _periodic_save(self):
        """定期的なメトリクス保存"""
        while self.is_running:
            try:
                # 5分ごとにメトリクスをデータベースに保存
                time.sleep(300)
                self._save_metrics()
            except Exception as e:
                console.print(f"❌ メトリクス保存エラー: {e}", style="red")
    
    def _device_status_monitor(self):
        """デバイス状態監視"""
        while self.is_running:
            try:
                current_time = time.time()
                offline_threshold = 120  # 2分
                
                for device_id, device in self.device_statuses.items():
                    # オフラインデバイスの検出
                    if current_time - device.last_seen > offline_threshold:
                        if device.status != "offline":
                            device.status = "offline"
                            self._create_alert(
                                alert_type="device_offline",
                                severity="warning",
                                source=device_id,
                                message=f"デバイスがオフライン: {device_id}"
                            )
                    
                    # バッテリー低下アラート
                    if device.battery_level is not None and device.battery_level < 20:
                        self._create_alert(
                            alert_type="low_battery",
                            severity="critical",
                            source=device_id,
                            message=f"バッテリー低下: {device.battery_level}%"
                        )
                
                time.sleep(30)  # 30秒ごとにチェック
                
            except Exception as e:
                console.print(f"❌ デバイス状態監視エラー: {e}", style="red")
    
    def _save_metrics(self):
        """メトリクスのデータベース保存"""
        current_time = time.time()
        
        with sqlite3.connect(self.db_path) as conn:
            for topic, stats in self.topic_statistics.items():
                metrics = MQTTMetrics(
                    timestamp=current_time,
                    broker_host='localhost',  # 設定から取得
                    topic=topic,
                    message_count=stats['message_count'],
                    total_bytes=stats['total_bytes'],
                    qos_0_count=stats['qos_distribution']['0'],
                    qos_1_count=stats['qos_distribution']['1'], 
                    qos_2_count=stats['qos_distribution']['2'],
                    average_latency=0,  # 後で実装
                    error_count=stats['error_count'],
                    connection_count=0,  # $SYSから取得
                    subscription_count=0  # $SYSから取得
                )
                
                conn.execute("""
                    INSERT INTO mqtt_metrics (
                        timestamp, broker_host, topic, message_count, total_bytes,
                        qos_0_count, qos_1_count, qos_2_count, average_latency,
                        error_count, connection_count, subscription_count
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    metrics.timestamp, metrics.broker_host, metrics.topic,
                    metrics.message_count, metrics.total_bytes,
                    metrics.qos_0_count, metrics.qos_1_count, metrics.qos_2_count,
                    metrics.average_latency, metrics.error_count,
                    metrics.connection_count, metrics.subscription_count
                ))
            
            # デバイス状態も保存
            for device in self.device_statuses.values():
                conn.execute("""
                    INSERT OR REPLACE INTO device_status (
                        device_id, last_seen, status, message_count, error_count,
                        battery_level, signal_strength, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    device.device_id, device.last_seen, device.status,
                    device.message_count, device.error_count,
                    device.battery_level, device.signal_strength, current_time
                ))
            
            conn.commit()
        
        console.print("💾 メトリクスをデータベースに保存しました", style="green")
    
    def get_realtime_dashboard_data(self) -> Dict[str, Any]:
        """リアルタイムダッシュボード用データを取得"""
        current_time = time.time()
        
        # 最近1分間のメッセージ数を計算
        recent_messages = [
            msg for msg in self.realtime_stats['messages_per_minute']
            if current_time - msg['timestamp'] < 60
        ]
        messages_per_minute = len(recent_messages)
        
        # 最近1分間のバイト数を計算
        recent_bytes = [
            msg['bytes'] for msg in self.realtime_stats['bytes_per_minute']
            if current_time - msg['timestamp'] < 60
        ]
        bytes_per_minute = sum(recent_bytes)
        
        # トップアクティブトピック
        sorted_topics = sorted(
            self.topic_statistics.items(),
            key=lambda x: x[1]['message_count'],
            reverse=True
        )[:5]
        
        # デバイス状態サマリー
        device_summary = {
            'online': sum(1 for d in self.device_statuses.values() if d.status == 'online'),
            'offline': sum(1 for d in self.device_statuses.values() if d.status == 'offline'),
            'warning': sum(1 for d in self.device_statuses.values() if d.status == 'warning')
        }
        
        return {
            'timestamp': current_time,
            'messages_per_minute': messages_per_minute,
            'bytes_per_minute': bytes_per_minute,
            'total_topics': len(self.topic_statistics),
            'active_devices': len(self.device_statuses),
            'top_topics': sorted_topics,
            'device_summary': device_summary,
            'recent_alerts_count': self._get_recent_alerts_count()
        }
    
    def _get_recent_alerts_count(self) -> int:
        """直近のアラート数を取得"""
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT COUNT(*) FROM alert_history 
                WHERE timestamp > ? AND resolved = FALSE
            """, (one_hour_ago,))
            return cursor.fetchone()[0]
    
    def stop_collection(self):
        """メトリクス収集停止"""
        self.is_running = False
        self.monitor_client.loop_stop()
        self.monitor_client.disconnect()
        console.print("⏹️  メトリクス収集を停止しました", style="yellow")

# Exercise 2: リアルタイムダッシュボード
class MQTTDashboard:
    """MQTT監視ダッシュボード"""
    
    def __init__(self, metrics_collector: MQTTMetricsCollector):
        self.metrics_collector = metrics_collector
        self.layout = Layout()
        self.setup_layout()
    
    def setup_layout(self):
        """ダッシュボードレイアウト設定"""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body", ratio=1),
            Layout(name="footer", size=3)
        )
        
        self.layout["body"].split_row(
            Layout(name="left"),
            Layout(name="right")
        )
        
        self.layout["left"].split(
            Layout(name="metrics", ratio=2),
            Layout(name="devices", ratio=1)
        )
        
        self.layout["right"].split(
            Layout(name="topics", ratio=1),
            Layout(name="alerts", ratio=1)
        )
    
    def update_dashboard(self):
        """ダッシュボード更新"""
        data = self.metrics_collector.get_realtime_dashboard_data()
        
        # ヘッダー
        header_text = Text.assemble(
            ("🔍 MQTT Real-time Monitoring Dashboard", "bold blue"),
            f" | Last Update: {datetime.fromtimestamp(data['timestamp']).strftime('%H:%M:%S')}"
        )
        self.layout["header"].update(Panel(header_text, style="blue"))
        
        # メトリクス表示
        metrics_table = Table(title="📊 Key Metrics")
        metrics_table.add_column("Metric", style="cyan")
        metrics_table.add_column("Value", style="green")
        
        metrics_table.add_row("Messages/min", str(data['messages_per_minute']))
        metrics_table.add_row("Bytes/min", f"{data['bytes_per_minute']:,}")
        metrics_table.add_row("Active Topics", str(data['total_topics']))
        metrics_table.add_row("Active Devices", str(data['active_devices']))
        
        self.layout["metrics"].update(Panel(metrics_table, title="Real-time Metrics"))
        
        # デバイス状態
        device_table = Table(title="🔌 Device Status")
        device_table.add_column("Status", style="cyan")
        device_table.add_column("Count", style="green")
        
        device_summary = data['device_summary']
        device_table.add_row("Online", str(device_summary['online']))
        device_table.add_row("Offline", str(device_summary['offline']))
        device_table.add_row("Warning", str(device_summary['warning']))
        
        self.layout["devices"].update(Panel(device_table, title="Device Summary"))
        
        # トップトピック
        topics_table = Table(title="📈 Top Active Topics")
        topics_table.add_column("Topic", style="cyan")
        topics_table.add_column("Messages", style="green")
        topics_table.add_column("Bytes", style="yellow")
        
        for topic, stats in data['top_topics']:
            topics_table.add_row(
                topic[:30] + "..." if len(topic) > 30 else topic,
                str(stats['message_count']),
                f"{stats['total_bytes']:,}"
            )
        
        self.layout["topics"].update(Panel(topics_table, title="Topic Statistics"))
        
        # アラート
        alerts_text = Text.assemble(
            f"🚨 Recent Alerts: {data['recent_alerts_count']}",
            style="red" if data['recent_alerts_count'] > 0 else "green"
        )
        self.layout["alerts"].update(Panel(alerts_text, title="Alert Status"))
        
        # フッター
        footer_text = Text.assemble(
            "Press Ctrl+C to exit | ",
            ("Dashboard refreshes every 5 seconds", "dim")
        )
        self.layout["footer"].update(Panel(footer_text, style="dim"))
    
    def run_dashboard(self):
        """ダッシュボード実行"""
        console.print("🖥️  リアルタイムダッシュボードを開始します", style="bold green")
        
        with Live(self.layout, refresh_per_second=0.5, screen=True):
            try:
                while True:
                    self.update_dashboard()
                    time.sleep(5)
            except KeyboardInterrupt:
                console.print("\n👋 ダッシュボードを終了します", style="yellow")

# Exercise 3: Web ダッシュボード
class MQTTWebDashboard:
    """WebベースのMQTT監視ダッシュボード"""
    
    def __init__(self, metrics_collector: MQTTMetricsCollector, port: int = 8080):
        self.metrics_collector = metrics_collector
        self.port = port
        
        try:
            from flask import Flask, render_template, jsonify
            from flask_socketio import SocketIO
            
            self.app = Flask(__name__)
            self.app.config['SECRET_KEY'] = 'mqtt-dashboard-secret'
            self.socketio = SocketIO(self.app, cors_allowed_origins="*")
            
            self.setup_routes()
            console.print("✅ Web ダッシュボード初期化完了", style="green")
            
        except ImportError:
            console.print("⚠️  Flask と Flask-SocketIO が必要です", style="yellow")
            console.print("   pip install Flask Flask-SocketIO", style="dim")
            self.app = None
    
    def setup_routes(self):
        """Webルートの設定"""
        @self.app.route('/')
        def dashboard():
            return self.get_dashboard_html()
        
        @self.app.route('/api/metrics')
        def api_metrics():
            data = self.metrics_collector.get_realtime_dashboard_data()
            return jsonify(data)
        
        @self.app.route('/api/historical/<int:hours>')
        def api_historical(hours):
            return jsonify(self._get_historical_data(hours))
        
        @self.socketio.on('connect')
        def handle_connect():
            console.print("📱 WebSocket クライアント接続", style="blue")
        
        @self.socketio.on('disconnect')
        def handle_disconnect():
            console.print("📱 WebSocket クライアント切断", style="dim")
    
    def get_dashboard_html(self) -> str:
        """ダッシュボード HTML を生成"""
        html_template = """
<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>MQTT Monitoring Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.0/socket.io.js"></script>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            margin: 0; padding: 20px; 
            background-color: #f5f5f5;
        }
        .header { 
            text-align: center; 
            margin-bottom: 30px; 
            color: #333;
        }
        .container { 
            display: grid; 
            grid-template-columns: 1fr 1fr; 
            gap: 20px; 
            max-width: 1200px; 
            margin: 0 auto;
        }
        .card { 
            background: white; 
            padding: 20px; 
            border-radius: 8px; 
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        .metric-value { 
            font-size: 2em; 
            font-weight: bold; 
            color: #007acc;
        }
        .chart-container { 
            position: relative; 
            height: 300px; 
        }
        .device-status { 
            display: flex; 
            justify-content: space-around; 
            align-items: center;
        }
        .status-item { 
            text-align: center; 
        }
        .status-online { color: #28a745; }
        .status-offline { color: #dc3545; }
        .status-warning { color: #ffc107; }
        .alerts { 
            background-color: #fff3cd; 
            border: 1px solid #ffeaa7; 
            color: #856404;
        }
        .footer { 
            text-align: center; 
            margin-top: 30px; 
            color: #666; 
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🔍 MQTT Monitoring Dashboard</h1>
        <p>Real-time monitoring and analytics</p>
    </div>
    
    <div class="container">
        <div class="card">
            <h3>📊 Key Metrics</h3>
            <div>Messages/min: <span id="messages-per-min" class="metric-value">0</span></div>
            <div>Bytes/min: <span id="bytes-per-min" class="metric-value">0</span></div>
            <div>Active Topics: <span id="active-topics" class="metric-value">0</span></div>
        </div>
        
        <div class="card">
            <h3>🔌 Device Status</h3>
            <div class="device-status">
                <div class="status-item">
                    <div class="metric-value status-online" id="devices-online">0</div>
                    <div>Online</div>
                </div>
                <div class="status-item">
                    <div class="metric-value status-offline" id="devices-offline">0</div>
                    <div>Offline</div>
                </div>
                <div class="status-item">
                    <div class="metric-value status-warning" id="devices-warning">0</div>
                    <div>Warning</div>
                </div>
            </div>
        </div>
        
        <div class="card">
            <h3>📈 Message Volume</h3>
            <div class="chart-container">
                <canvas id="messageChart"></canvas>
            </div>
        </div>
        
        <div class="card">
            <h3>📈 Data Volume</h3>
            <div class="chart-container">
                <canvas id="dataChart"></canvas>
            </div>
        </div>
        
        <div class="card alerts">
            <h3>🚨 Recent Alerts</h3>
            <div id="alerts-count">Loading...</div>
            <div id="alerts-list"></div>
        </div>
        
        <div class="card">
            <h3>📊 Top Topics</h3>
            <div id="top-topics-list">Loading...</div>
        </div>
    </div>
    
    <div class="footer">
        <p>Last updated: <span id="last-update">Never</span></p>
        <p>Dashboard auto-refreshes every 5 seconds</p>
    </div>

    <script>
        const socket = io();
        
        // Chart setup
        const messageCtx = document.getElementById('messageChart').getContext('2d');
        const dataCtx = document.getElementById('dataChart').getContext('2d');
        
        const messageChart = new Chart(messageCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Messages/min',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        const dataChart = new Chart(dataCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'Bytes/min',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    tension: 0.1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // Data update function
        function updateDashboard() {
            fetch('/api/metrics')
                .then(response => response.json())
                .then(data => {
                    // Update metrics
                    document.getElementById('messages-per-min').textContent = data.messages_per_minute;
                    document.getElementById('bytes-per-min').textContent = data.bytes_per_minute.toLocaleString();
                    document.getElementById('active-topics').textContent = data.total_topics;
                    
                    // Update device status
                    document.getElementById('devices-online').textContent = data.device_summary.online;
                    document.getElementById('devices-offline').textContent = data.device_summary.offline;
                    document.getElementById('devices-warning').textContent = data.device_summary.warning;
                    
                    // Update charts
                    const currentTime = new Date(data.timestamp * 1000).toLocaleTimeString();
                    
                    messageChart.data.labels.push(currentTime);
                    messageChart.data.datasets[0].data.push(data.messages_per_minute);
                    
                    dataChart.data.labels.push(currentTime);
                    dataChart.data.datasets[0].data.push(data.bytes_per_minute);
                    
                    // Keep only last 20 data points
                    if (messageChart.data.labels.length > 20) {
                        messageChart.data.labels.shift();
                        messageChart.data.datasets[0].data.shift();
                        dataChart.data.labels.shift();
                        dataChart.data.datasets[0].data.shift();
                    }
                    
                    messageChart.update('none');
                    dataChart.update('none');
                    
                    // Update alerts
                    document.getElementById('alerts-count').textContent = 
                        `${data.recent_alerts_count} alerts in the last hour`;
                    
                    // Update top topics
                    const topicsHTML = data.top_topics.map(([topic, stats]) =>
                        `<div>${topic}: ${stats.message_count} messages</div>`
                    ).join('');
                    document.getElementById('top-topics-list').innerHTML = topicsHTML;
                    
                    // Update timestamp
                    document.getElementById('last-update').textContent = 
                        new Date().toLocaleTimeString();
                })
                .catch(error => console.error('Error updating dashboard:', error));
        }
        
        // Initial update and set interval
        updateDashboard();
        setInterval(updateDashboard, 5000);
    </script>
</body>
</html>
        """
        return html_template
    
    def _get_historical_data(self, hours: int) -> Dict[str, Any]:
        """過去データを取得"""
        end_time = time.time()
        start_time = end_time - (hours * 3600)
        
        with sqlite3.connect(self.metrics_collector.db_path) as conn:
            cursor = conn.execute("""
                SELECT timestamp, SUM(message_count), SUM(total_bytes)
                FROM mqtt_metrics 
                WHERE timestamp BETWEEN ? AND ?
                GROUP BY CAST(timestamp / 300 AS INTEGER)
                ORDER BY timestamp
            """, (start_time, end_time))
            
            historical_data = []
            for row in cursor.fetchall():
                historical_data.append({
                    'timestamp': row[0],
                    'message_count': row[1],
                    'total_bytes': row[2]
                })
        
        return {'data': historical_data, 'period_hours': hours}
    
    def run_web_dashboard(self):
        """Web ダッシュボード実行"""
        if not self.app:
            console.print("❌ Web ダッシュボードを開始できません", style="red")
            return
        
        console.print(f"🌐 Web ダッシュボードを開始します: http://localhost:{self.port}", style="bold green")
        
        # バックグラウンドでリアルタイム更新
        def emit_updates():
            while True:
                try:
                    data = self.metrics_collector.get_realtime_dashboard_data()
                    self.socketio.emit('update', data)
                    time.sleep(5)
                except Exception as e:
                    console.print(f"❌ WebSocket更新エラー: {e}", style="red")
        
        update_thread = threading.Thread(target=emit_updates, daemon=True)
        update_thread.start()
        
        self.socketio.run(self.app, host='0.0.0.0', port=self.port, debug=False)

# デモンストレーション
def demonstrate_mqtt_monitoring():
    """MQTT監視システムのデモンストレーション"""
    console.print("🔍 MQTT監視システム統合デモ", style="bold blue")
    
    # メトリクス収集器の初期化
    collector = MQTTMetricsCollector()
    
    # 監視開始
    if not collector.start_collection():
        console.print("❌ メトリクス収集の開始に失敗", style="red")
        return
    
    try:
        # ダッシュボードの選択
        console.print("\n📊 利用可能なダッシュボード:", style="bold yellow")
        console.print("1. コンソールダッシュボード (リアルタイム)")
        console.print("2. Webダッシュボード (ブラウザ)")
        console.print("3. メトリクス収集のみ")
        
        choice = console.input("\n選択してください (1-3): ")
        
        if choice == "1":
            # コンソールダッシュボード実行
            dashboard = MQTTDashboard(collector)
            dashboard.run_dashboard()
            
        elif choice == "2":
            # Webダッシュボード実行
            web_dashboard = MQTTWebDashboard(collector)
            web_dashboard.run_web_dashboard()
            
        else:
            # メトリクス収集のみ
            console.print("📊 メトリクス収集中... (Ctrl+C で終了)", style="green")
            
            while True:
                time.sleep(10)
                data = collector.get_realtime_dashboard_data()
                
                console.print(f"\n⏰ {datetime.now().strftime('%H:%M:%S')}")
                console.print(f"📊 Messages/min: {data['messages_per_minute']}")
                console.print(f"📊 Active devices: {data['active_devices']}")
                console.print(f"🚨 Recent alerts: {data['recent_alerts_count']}")
                
    except KeyboardInterrupt:
        console.print("\n⚠️  監視システムを終了中...", style="yellow")
    finally:
        collector.stop_collection()
        console.print("✅ 監視システムが正常に終了しました", style="green")

def create_demo_data_generator():
    """デモデータ生成器"""
    console.print("🔄 デモデータ生成器を開始します", style="bold blue")
    
    client = mqtt.Client(client_id="demo-data-generator")
    
    try:
        client.connect('localhost', 1883, 60)
        client.loop_start()
        
        import random
        
        device_ids = ['sensor-001', 'sensor-002', 'gateway-001', 'actuator-001']
        
        console.print("📤 デモデータ送信中... (Ctrl+C で停止)", style="green")
        
        while True:
            for device_id in device_ids:
                # センサーデータ
                sensor_data = {
                    'device_id': device_id,
                    'temperature': round(random.uniform(20, 30), 1),
                    'humidity': round(random.uniform(40, 80), 1),
                    'battery_level': round(random.uniform(20, 100), 1),
                    'signal_strength': round(random.uniform(-80, -20), 1),
                    'timestamp': time.time()
                }
                
                # 時々エラーを含める
                if random.random() < 0.1:  # 10%の確率
                    sensor_data['error'] = 'sensor_read_timeout'
                
                topic = f"device/{device_id}/data"
                payload = json.dumps(sensor_data)
                
                client.publish(topic, payload, qos=random.choice([0, 1]))
                
                # ステータス更新
                status_data = {
                    'device_id': device_id,
                    'status': 'online',
                    'uptime': random.randint(1000, 86400)
                }
                
                status_topic = f"device/{device_id}/status"
                client.publish(status_topic, json.dumps(status_data), qos=1)
            
            time.sleep(random.uniform(2, 8))  # 2-8秒間隔
            
    except KeyboardInterrupt:
        console.print("\n⏹️  デモデータ生成器を停止", style="yellow")
    finally:
        client.loop_stop()
        client.disconnect()

# メイン実行関数
def main():
    """メイン実行関数"""
    console.print("🖥️  MQTT Monitoring Dashboard Suite", style="bold blue")
    
    options = [
        ("Complete Monitoring System", demonstrate_mqtt_monitoring),
        ("Demo Data Generator", create_demo_data_generator)
    ]
    
    console.print("\n📋 利用可能なオプション:", style="bold yellow")
    for i, (name, _) in enumerate(options, 1):
        console.print(f"{i}. {name}")
    
    try:
        choice = console.input("\n選択してください (1-2): ")
        choice_idx = int(choice) - 1
        
        if 0 <= choice_idx < len(options):
            name, func = options[choice_idx]
            console.print(f"\n🚀 {name} を実行中...", style="bold green")
            func()
        else:
            console.print("❌ 無効な選択です", style="red")
            
    except (ValueError, IndexError):
        console.print("❌ 無効な入力です", style="red")
    except KeyboardInterrupt:
        console.print("\n👋 プログラムを終了します", style="yellow")
    
    console.print("\n🎉 MQTT監視ダッシュボードデモ完了！", style="bold green")

if __name__ == "__main__":
    main()
```

## 🎯 練習問題

### 問題1: 基本的な監視システム
1. `MQTTMetricsCollector` を使用してメトリクス収集を開始してください
2. リアルタイムダッシュボードでデータの可視化を確認してください
3. デモデータ生成器を実行して監視機能をテストしてください

### 問題2: カスタムアラート
1. 独自のアラート条件を追加してください（例：特定トピックの異常パターン）
2. アラート通知システムを実装してください（メール、Slack等）
3. アラートの自動復旧機能を実装してください

### 問題3: Webダッシュボード
1. Webダッシュボードを実行してブラウザで確認してください
2. 追加のチャートやウィジェットを実装してください
3. ユーザー認証機能を追加してください

### 問題4: 高度な分析機能
1. 時系列データの異常検知アルゴリズムを実装してください
2. デバイス性能の予測分析機能を追加してください
3. コスト分析とリソース最適化の提案機能を実装してください

## ✅ 確認チェックリスト

- [ ] メトリクス収集システムを実装した
- [ ] リアルタイムダッシュボードを構築した
- [ ] アラート機能とスレッショルド監視を実装した
- [ ] デバイス状態管理機能を実装した
- [ ] Webベースダッシュボードを構築した
- [ ] 履歴データの分析機能を実装した
- [ ] 異常検知機能を実装した
- [ ] パフォーマンス最適化を実装した

## 📊 理解度チェック

以下の質問に答えられるか確認してください：

1. 効果的なIoT監視システムに必要な要素は？
2. リアルタイム監視と履歴分析の使い分けは？
3. アラートの誤検知を減らす方法は？
4. スケーラブルな監視アーキテクチャの設計原則は？
5. 監視システムのコスト最適化の方法は？

## 🔧 トラブルシューティング

### メトリクス収集が開始されない
- MQTTブローカーの接続状況を確認
- データベースファイルの書き込み権限を確認
- ネットワーク接続とポート設定を確認

### ダッシュボードが表示されない
- 必要なライブラリのインストール状況を確認
- ポート番号の競合を確認
- ブラウザのJavaScript有効化を確認

### データが更新されない
- WebSocketの接続状況を確認
- データベースの更新タイミングを確認
- クライアント側のリフレッシュ間隔を確認

### パフォーマンス問題
- データベースのインデックス設定を確認
- メモリ使用量と最適化を確認
- 不要なデータのクリーンアップを実装

---

**🎉 お疲れさまでした！** 

これでMQTTハンズオンシリーズが完了です。基本的な接続から高度なクラウド連携、そして包括的な監視システムまで、実用的なMQTTシステムの構築方法を学習しました。これらの知識を活用して、実際のIoTプロジェクトに挑戦してください！