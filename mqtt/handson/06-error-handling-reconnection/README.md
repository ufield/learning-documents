# ハンズオン 06: エラーハンドリングと自動再接続

## 🎯 学習目標

このハンズオンでは堅牢なMQTTアプリケーションの構築について学習します：

- 包括的なエラーハンドリング戦略の実装
- 自動再接続メカニズムの設計と実装
- ネットワーク障害からの復旧処理
- バックオフ戦略と指数的遅延
- メッセージの確実な配信保証
- 状態管理と復旧処理

**所要時間**: 約90分

## 📋 前提条件

- [05-security-implementation](../05-security-implementation/) の完了
- ネットワーク通信とエラーハンドリングの基本理解
- Python例外処理の知識

## 🛡 エラーハンドリング戦略

### エラーの分類

```
┌─────────────────────────────────────────────────────────┐
│                    MQTT エラー分類                      │
├─────────────────────────────────────────────────────────┤
│ 1. 接続エラー                                           │
│    • ネットワーク切断                                   │
│    • ブローカー停止                                     │
│    • 認証失敗                                           │
│                                                         │
│ 2. 通信エラー                                           │
│    • パケット損失                                       │
│    • タイムアウト                                       │
│    • QoS配信失敗                                        │
│                                                         │
│ 3. アプリケーションエラー                               │
│    • メッセージフォーマット不正                         │
│    • ディスク容量不足                                   │
│    • メモリ不足                                         │
└─────────────────────────────────────────────────────────┘
```

## 📝 実装演習

### Exercise 1: 高度なエラーハンドリング

`src/robust_mqtt_client.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import random
import threading
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from enum import Enum
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
import queue
import socket
from contextlib import contextmanager

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConnectionState(Enum):
    """接続状態の列挙型"""
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    RECONNECTING = "reconnecting"
    ERROR = "error"

class ErrorType(Enum):
    """エラータイプの列挙型"""
    NETWORK_ERROR = "network_error"
    AUTHENTICATION_ERROR = "authentication_error"
    TIMEOUT_ERROR = "timeout_error"
    PROTOCOL_ERROR = "protocol_error"
    APPLICATION_ERROR = "application_error"

class RetryPolicy:
    """リトライポリシークラス"""
    
    def __init__(self, 
                 max_retries: int = 5,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 exponential_base: float = 2.0,
                 jitter: bool = True):
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
        self.retry_count = 0
    
    def get_delay(self) -> float:
        """次のリトライまでの遅延時間を計算"""
        if self.retry_count >= self.max_retries:
            return -1  # リトライ回数上限
        
        # 指数的バックオフ
        delay = self.base_delay * (self.exponential_base ** self.retry_count)
        delay = min(delay, self.max_delay)
        
        # ジッター追加（同時接続による輻輳を避ける）
        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)
        
        return delay
    
    def reset(self):
        """リトライカウンターをリセット"""
        self.retry_count = 0
    
    def increment(self):
        """リトライカウンターを増加"""
        self.retry_count += 1

class CircuitBreaker:
    """サーキットブレーカーパターン実装"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 30.0,
                 expected_exception: type = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = 'CLOSED'  # CLOSED, OPEN, HALF_OPEN
        self._lock = threading.Lock()
    
    @contextmanager
    def __call__(self, fallback=None):
        """サーキットブレーカーのコンテキストマネージャー"""
        with self._lock:
            if self.state == 'OPEN':
                if self._should_attempt_reset():
                    self.state = 'HALF_OPEN'
                else:
                    if fallback:
                        yield fallback
                        return
                    else:
                        raise Exception("サーキットブレーカーが開いています")
        
        try:
            yield None
            self._on_success()
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """リセットを試行すべきかどうか"""
        if self.last_failure_time is None:
            return False
        return time.time() - self.last_failure_time >= self.recovery_timeout
    
    def _on_success(self):
        """成功時の処理"""
        with self._lock:
            self.failure_count = 0
            self.state = 'CLOSED'
    
    def _on_failure(self):
        """失敗時の処理"""
        with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.failure_threshold:
                self.state = 'OPEN'

class MessageBuffer:
    """メッセージバッファークラス"""
    
    def __init__(self, max_size: int = 1000):
        self.max_size = max_size
        self.buffer = queue.Queue(maxsize=max_size)
        self.failed_messages = []
    
    def add_message(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
        """メッセージをバッファーに追加"""
        message = {
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'timestamp': time.time()
        }
        
        try:
            self.buffer.put_nowait(message)
            return True
        except queue.Full:
            console.print("⚠️  メッセージバッファーが満杯です", style="yellow")
            # 古いメッセージを削除して新しいメッセージを追加
            try:
                self.buffer.get_nowait()  # 最も古いメッセージを削除
                self.buffer.put_nowait(message)
                return True
            except queue.Empty:
                return False
    
    def get_message(self) -> Optional[Dict[str, Any]]:
        """バッファーからメッセージを取得"""
        try:
            return self.buffer.get_nowait()
        except queue.Empty:
            return None
    
    def is_empty(self) -> bool:
        """バッファーが空かどうか"""
        return self.buffer.empty()
    
    def size(self) -> int:
        """バッファー内のメッセージ数"""
        return self.buffer.qsize()

class RobustMQTTClient:
    """堅牢なMQTTクライアント実装"""
    
    def __init__(self, 
                 broker_host: str = 'localhost',
                 broker_port: int = 1883,
                 client_id: str = None,
                 username: str = None,
                 password: str = None):
        
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.username = username
        self.password = password
        
        # クライアントID生成
        self.client_id = client_id or f"robust-client-{int(time.time())}"
        
        # 状態管理
        self.state = ConnectionState.DISCONNECTED
        self.last_error = None
        self.connection_time = None
        self.disconnection_time = None
        
        # エラーハンドリング設定
        self.retry_policy = RetryPolicy()
        self.circuit_breaker = CircuitBreaker()
        self.message_buffer = MessageBuffer()
        
        # 統計情報
        self.stats = {
            'connection_attempts': 0,
            'successful_connections': 0,
            'disconnections': 0,
            'messages_sent': 0,
            'messages_received': 0,
            'errors': {},
            'last_activity': None
        }
        
        # イベントハンドラー
        self.event_handlers = {
            'on_connect': [],
            'on_disconnect': [],
            'on_message': [],
            'on_error': [],
            'on_reconnect': []
        }
        
        # スレッド管理
        self.reconnect_thread = None
        self.buffer_flush_thread = None
        self.health_check_thread = None
        self._stop_threads = threading.Event()
        self._lock = threading.Lock()
        
        # MQTTクライアント初期化
        self.client = None
        self.initialize_client()
    
    def initialize_client(self):
        """MQTTクライアントの初期化"""
        self.client = mqtt.Client(client_id=self.client_id, clean_session=False)
        
        # 認証設定
        if self.username and self.password:
            self.client.username_pw_set(self.username, self.password)
        
        # イベントハンドラー設定
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        self.client.on_message = self._on_message
        self.client.on_publish = self._on_publish
        self.client.on_subscribe = self._on_subscribe
        self.client.on_log = self._on_log
    
    def add_event_handler(self, event: str, handler: Callable):
        """イベントハンドラーを追加"""
        if event in self.event_handlers:
            self.event_handlers[event].append(handler)
    
    def _trigger_event(self, event: str, *args, **kwargs):
        """イベントをトリガー"""
        for handler in self.event_handlers.get(event, []):
            try:
                handler(*args, **kwargs)
            except Exception as e:
                logger.error(f"イベントハンドラーでエラー: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        with self._lock:
            self.stats['connection_attempts'] += 1
            
            if rc == 0:
                self.state = ConnectionState.CONNECTED
                self.connection_time = time.time()
                self.stats['successful_connections'] += 1
                self.retry_policy.reset()
                
                console.print("✅ MQTTブローカーに接続しました", style="bold green")
                
                # バッファーされたメッセージの送信開始
                self._start_buffer_flush_thread()
                
                # ヘルスチェック開始
                self._start_health_check_thread()
                
                self._trigger_event('on_connect', client, userdata, flags, rc)
                
            else:
                self.state = ConnectionState.ERROR
                error_msg = self._get_connect_error_message(rc)
                self._handle_error(ErrorType.AUTHENTICATION_ERROR, error_msg)
    
    def _on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        with self._lock:
            self.state = ConnectionState.DISCONNECTED
            self.disconnection_time = time.time()
            self.stats['disconnections'] += 1
            
            if rc != 0:
                console.print(f"⚠️  予期しない切断が発生しました (rc={rc})", style="yellow")
                self._handle_error(ErrorType.NETWORK_ERROR, f"予期しない切断 (rc={rc})")
                self._start_reconnect_thread()
            else:
                console.print("👋 MQTTブローカーから切断しました", style="blue")
            
            self._trigger_event('on_disconnect', client, userdata, rc)
    
    def _on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        with self._lock:
            self.stats['messages_received'] += 1
            self.stats['last_activity'] = time.time()
        
        try:
            topic = msg.topic
            payload = msg.payload.decode('utf-8')
            qos = msg.qos
            retain = msg.retain
            
            console.print(f"📬 メッセージ受信: {topic}", style="cyan")
            self._trigger_event('on_message', topic, payload, qos, retain)
            
        except Exception as e:
            self._handle_error(ErrorType.APPLICATION_ERROR, f"メッセージ処理エラー: {e}")
    
    def _on_publish(self, client, userdata, mid):
        """メッセージ送信完了時のコールバック"""
        with self._lock:
            self.stats['messages_sent'] += 1
            self.stats['last_activity'] = time.time()
    
    def _on_subscribe(self, client, userdata, mid, granted_qos):
        """購読完了時のコールバック"""
        console.print(f"✅ 購読完了 (QoS: {granted_qos})", style="green")
    
    def _on_log(self, client, userdata, level, buf):
        """ログ出力時のコールバック"""
        logger.debug(f"MQTT Log: {buf}")
    
    def _get_connect_error_message(self, rc: int) -> str:
        """接続エラーメッセージを取得"""
        error_messages = {
            1: "不正なプロトコルバージョン",
            2: "無効なクライアントID",
            3: "ブローカーが利用できません",
            4: "認証エラー（ユーザー名またはパスワードが無効）",
            5: "認証が拒否されました"
        }
        return error_messages.get(rc, f"不明なエラー (rc={rc})")
    
    def _handle_error(self, error_type: ErrorType, message: str):
        """エラーハンドリング"""
        self.last_error = {
            'type': error_type,
            'message': message,
            'timestamp': time.time()
        }
        
        # 統計更新
        error_key = error_type.value
        self.stats['errors'][error_key] = self.stats['errors'].get(error_key, 0) + 1
        
        console.print(f"❌ {error_type.value}: {message}", style="bold red")
        logger.error(f"{error_type.value}: {message}")
        
        self._trigger_event('on_error', error_type, message)
    
    def connect(self, blocking: bool = True, timeout: float = 10.0) -> bool:
        """ブローカーに接続"""
        console.print(f"🔌 {self.broker_host}:{self.broker_port} に接続中...", style="blue")
        
        with self._lock:
            if self.state == ConnectionState.CONNECTED:
                console.print("✅ 既に接続されています", style="green")
                return True
            
            self.state = ConnectionState.CONNECTING
        
        try:
            with self.circuit_breaker():
                self.client.connect(self.broker_host, self.broker_port, 60)
                
                if blocking:
                    # ノンブロッキングループ開始
                    self.client.loop_start()
                    
                    # 接続完了まで待機
                    start_time = time.time()
                    while self.state == ConnectionState.CONNECTING:
                        if time.time() - start_time > timeout:
                            self._handle_error(ErrorType.TIMEOUT_ERROR, "接続タイムアウト")
                            return False
                        time.sleep(0.1)
                    
                    return self.state == ConnectionState.CONNECTED
                else:
                    # ブロッキングループ
                    self.client.loop_forever()
                    return True
                    
        except socket.error as e:
            self._handle_error(ErrorType.NETWORK_ERROR, f"ネットワークエラー: {e}")
            return False
        except Exception as e:
            self._handle_error(ErrorType.PROTOCOL_ERROR, f"接続エラー: {e}")
            return False
    
    def disconnect(self):
        """ブローカーから切断"""
        console.print("👋 切断中...", style="yellow")
        
        # スレッド停止
        self._stop_threads.set()
        
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            self.reconnect_thread.join(timeout=5)
        
        if self.buffer_flush_thread and self.buffer_flush_thread.is_alive():
            self.buffer_flush_thread.join(timeout=5)
        
        if self.health_check_thread and self.health_check_thread.is_alive():
            self.health_check_thread.join(timeout=5)
        
        # MQTT切断
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
        
        with self._lock:
            self.state = ConnectionState.DISCONNECTED
    
    def publish(self, topic: str, payload: str, qos: int = 0, retain: bool = False) -> bool:
        """メッセージを公開"""
        if self.state != ConnectionState.CONNECTED:
            console.print("⚠️  接続されていません。メッセージをバッファーします", style="yellow")
            return self.message_buffer.add_message(topic, payload, qos, retain)
        
        try:
            result = self.client.publish(topic, payload, qos, retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                console.print(f"📤 メッセージ送信: {topic}", style="green")
                return True
            else:
                self._handle_error(ErrorType.PROTOCOL_ERROR, f"送信エラー (rc={result.rc})")
                # バッファーに追加
                self.message_buffer.add_message(topic, payload, qos, retain)
                return False
                
        except Exception as e:
            self._handle_error(ErrorType.APPLICATION_ERROR, f"送信例外: {e}")
            self.message_buffer.add_message(topic, payload, qos, retain)
            return False
    
    def subscribe(self, topic: str, qos: int = 0) -> bool:
        """トピックに購読"""
        if self.state != ConnectionState.CONNECTED:
            console.print("❌ 接続されていません", style="bold red")
            return False
        
        try:
            result = self.client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                console.print(f"📥 購読開始: {topic}", style="green")
                return True
            else:
                self._handle_error(ErrorType.PROTOCOL_ERROR, f"購読エラー (rc={result[0]})")
                return False
                
        except Exception as e:
            self._handle_error(ErrorType.APPLICATION_ERROR, f"購読例外: {e}")
            return False
    
    def _start_reconnect_thread(self):
        """再接続スレッドを開始"""
        if self.reconnect_thread and self.reconnect_thread.is_alive():
            return
        
        self.reconnect_thread = threading.Thread(target=self._reconnect_loop, daemon=True)
        self.reconnect_thread.start()
    
    def _reconnect_loop(self):
        """自動再接続ループ"""
        console.print("🔄 自動再接続を開始します", style="yellow")
        
        while not self._stop_threads.is_set() and self.state != ConnectionState.CONNECTED:
            delay = self.retry_policy.get_delay()
            
            if delay < 0:
                console.print("❌ 最大リトライ回数に達しました", style="bold red")
                break
            
            console.print(f"⏱️  {delay:.1f}秒後に再接続を試行します", style="dim")
            
            if self._stop_threads.wait(delay):
                break  # 停止シグナルを受信
            
            with self._lock:
                self.state = ConnectionState.RECONNECTING
            
            self.retry_policy.increment()
            
            console.print(f"🔄 再接続試行 {self.retry_policy.retry_count}/{self.retry_policy.max_retries}", style="blue")
            
            # クライアントを再初期化
            self.initialize_client()
            
            if self.connect(blocking=True, timeout=10):
                console.print("✅ 再接続成功", style="bold green")
                self._trigger_event('on_reconnect')
                break
            else:
                console.print("❌ 再接続失敗", style="red")
    
    def _start_buffer_flush_thread(self):
        """バッファーフラッシュスレッドを開始"""
        if self.buffer_flush_thread and self.buffer_flush_thread.is_alive():
            return
        
        self.buffer_flush_thread = threading.Thread(target=self._buffer_flush_loop, daemon=True)
        self.buffer_flush_thread.start()
    
    def _buffer_flush_loop(self):
        """バッファーフラッシュループ"""
        while not self._stop_threads.is_set():
            if self.state == ConnectionState.CONNECTED and not self.message_buffer.is_empty():
                console.print(f"📦 バッファーメッセージを送信中 ({self.message_buffer.size()}件)", style="blue")
                
                while not self.message_buffer.is_empty():
                    message = self.message_buffer.get_message()
                    if message:
                        try:
                            result = self.client.publish(
                                message['topic'],
                                message['payload'],
                                message['qos'],
                                message['retain']
                            )
                            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                                console.print(f"✅ バッファーメッセージ送信完了: {message['topic']}", style="green")
                            else:
                                # 送信失敗時は再度バッファーに戻す
                                console.print(f"❌ バッファーメッセージ送信失敗: {message['topic']}", style="red")
                                break
                        except Exception as e:
                            logger.error(f"バッファーフラッシュエラー: {e}")
                            break
            
            self._stop_threads.wait(5)  # 5秒間隔でチェック
    
    def _start_health_check_thread(self):
        """ヘルスチェックスレッドを開始"""
        if self.health_check_thread and self.health_check_thread.is_alive():
            return
        
        self.health_check_thread = threading.Thread(target=self._health_check_loop, daemon=True)
        self.health_check_thread.start()
    
    def _health_check_loop(self):
        """ヘルスチェックループ"""
        while not self._stop_threads.is_set():
            if self.state == ConnectionState.CONNECTED:
                # Keep-aliveメッセージ送信
                try:
                    # PINGメッセージはpaho-mqttが自動送信するため、
                    # ここではアプリケーション固有のヘルスチェックを実行
                    current_time = time.time()
                    if self.stats['last_activity']:
                        inactive_time = current_time - self.stats['last_activity']
                        if inactive_time > 300:  # 5分間非アクティブ
                            console.print("⚠️  長時間非アクティブです", style="yellow")
                    
                except Exception as e:
                    logger.error(f"ヘルスチェックエラー: {e}")
            
            self._stop_threads.wait(30)  # 30秒間隔でチェック
    
    def get_connection_info(self) -> Dict[str, Any]:
        """接続情報を取得"""
        with self._lock:
            uptime = None
            if self.connection_time:
                uptime = time.time() - self.connection_time
            
            return {
                'state': self.state.value,
                'broker_host': self.broker_host,
                'broker_port': self.broker_port,
                'client_id': self.client_id,
                'uptime': uptime,
                'connection_time': self.connection_time,
                'disconnection_time': self.disconnection_time,
                'last_error': self.last_error,
                'retry_count': self.retry_policy.retry_count,
                'circuit_breaker_state': self.circuit_breaker.state,
                'buffer_size': self.message_buffer.size()
            }
    
    def get_statistics(self) -> Dict[str, Any]:
        """統計情報を取得"""
        with self._lock:
            return self.stats.copy()
    
    def display_status(self):
        """ステータス表示"""
        info = self.get_connection_info()
        stats = self.get_statistics()
        
        # 接続情報テーブル
        connection_table = Table(title="接続情報")
        connection_table.add_column("項目", style="cyan")
        connection_table.add_column("値", style="green")
        
        connection_table.add_row("状態", info['state'])
        connection_table.add_row("ブローカー", f"{info['broker_host']}:{info['broker_port']}")
        connection_table.add_row("クライアントID", info['client_id'])
        
        if info['uptime']:
            connection_table.add_row("稼働時間", f"{info['uptime']:.1f}秒")
        
        connection_table.add_row("リトライ回数", str(info['retry_count']))
        connection_table.add_row("サーキットブレーカー", info['circuit_breaker_state'])
        connection_table.add_row("バッファーサイズ", str(info['buffer_size']))
        
        # 統計情報テーブル
        stats_table = Table(title="統計情報")
        stats_table.add_column("項目", style="cyan")
        stats_table.add_column("値", style="yellow")
        
        stats_table.add_row("接続試行回数", str(stats['connection_attempts']))
        stats_table.add_row("成功接続回数", str(stats['successful_connections']))
        stats_table.add_row("切断回数", str(stats['disconnections']))
        stats_table.add_row("送信メッセージ数", str(stats['messages_sent']))
        stats_table.add_row("受信メッセージ数", str(stats['messages_received']))
        
        console.print(connection_table)
        console.print()
        console.print(stats_table)
        
        # エラー情報
        if stats['errors']:
            error_table = Table(title="エラー統計")
            error_table.add_column("エラータイプ", style="red")
            error_table.add_column("発生回数", style="yellow")
            
            for error_type, count in stats['errors'].items():
                error_table.add_row(error_type, str(count))
            
            console.print()
            console.print(error_table)

# 使用例とデモンストレーション
def demonstrate_error_handling():
    """エラーハンドリングのデモンストレーション"""
    console.print("🛡️  堅牢なMQTTクライアントデモ", style="bold blue")
    
    client = RobustMQTTClient(
        broker_host='localhost',
        broker_port=1883,
        client_id='robust-demo-client'
    )
    
    # イベントハンドラー追加
    def on_message_handler(topic, payload, qos, retain):
        console.print(f"📨 カスタムハンドラー: {topic} -> {payload}", style="magenta")
    
    def on_error_handler(error_type, message):
        console.print(f"🚨 カスタムエラーハンドラー: {error_type.value} - {message}", style="red")
    
    def on_reconnect_handler():
        console.print("🔄 カスタム再接続ハンドラーが呼ばれました", style="green")
    
    client.add_event_handler('on_message', on_message_handler)
    client.add_event_handler('on_error', on_error_handler)
    client.add_event_handler('on_reconnect', on_reconnect_handler)
    
    try:
        # 接続
        if client.connect():
            console.print("✅ 接続成功", style="bold green")
            
            # 購読
            client.subscribe('test/error-handling/+')
            
            # ステータス表示
            console.print("\n📊 初期ステータス:")
            client.display_status()
            
            # メッセージ送信テスト
            console.print("\n📤 メッセージ送信テスト:")
            for i in range(5):
                client.publish(f'test/error-handling/message-{i}', f'テストメッセージ {i}')
                time.sleep(1)
            
            # 不正なトピックでのテスト（エラーハンドリング）
            console.print("\n⚠️  エラーハンドリングテスト:")
            client.publish('invalid/topic/!@#$%', 'エラーテストメッセージ')
            
            # 少し待機
            console.print("\n⏱️  10秒間動作監視中...")
            time.sleep(10)
            
            # 最終ステータス
            console.print("\n📊 最終ステータス:")
            client.display_status()
            
        else:
            console.print("❌ 接続失敗", style="bold red")
            
    except KeyboardInterrupt:
        console.print("\n⚠️  ユーザーによる中断", style="yellow")
    except Exception as e:
        console.print(f"❌ 予期しないエラー: {e}", style="bold red")
    finally:
        client.disconnect()
        console.print("👋 デモンストレーション完了", style="blue")

if __name__ == "__main__":
    demonstrate_error_handling()
```

### Exercise 2: ネットワーク障害シミュレーター

`src/network_failure_simulator.py` を作成：

```python
import paho.mqtt.client as mqtt
import time
import random
import threading
import psutil
import subprocess
from typing import List, Dict, Any
from rich.console import Console
from rich.progress import Progress, track
from rich.panel import Panel
import os
import signal

console = Console()

class NetworkFailureSimulator:
    """ネットワーク障害シミュレータークラス"""
    
    def __init__(self):
        self.is_blocking = False
        self.blocked_hosts = set()
        self.original_rules = []
        self.scenarios = self.define_scenarios()
    
    def define_scenarios(self) -> List[Dict[str, Any]]:
        """障害シナリオの定義"""
        return [
            {
                'name': 'ネットワーク完全切断',
                'description': 'すべてのネットワーク通信を5秒間遮断',
                'duration': 5,
                'action': self.simulate_complete_network_failure
            },
            {
                'name': '間欠的接続障害',
                'description': '1秒間隔でON/OFFを繰り返す不安定な接続',
                'duration': 10,
                'action': self.simulate_intermittent_failure
            },
            {
                'name': '高レイテンシー',
                'description': 'ネットワーク遅延を500ms追加',
                'duration': 8,
                'action': self.simulate_high_latency
            },
            {
                'name': 'パケット損失',
                'description': '30%のパケット損失を発生',
                'duration': 6,
                'action': self.simulate_packet_loss
            }
        ]
    
    def simulate_complete_network_failure(self, duration: int):
        """完全なネットワーク障害をシミュレート"""
        console.print("🚫 ネットワーク完全切断を開始", style="bold red")
        
        # iptablesでMQTTポートを遮断（Linux/macOSの場合）
        try:
            if os.name == 'posix':  # Unix系OS
                subprocess.run(['sudo', 'iptables', '-A', 'OUTPUT', '-p', 'tcp', '--dport', '1883', '-j', 'DROP'], 
                             check=False, capture_output=True)
                subprocess.run(['sudo', 'iptables', '-A', 'INPUT', '-p', 'tcp', '--sport', '1883', '-j', 'DROP'], 
                             check=False, capture_output=True)
        except Exception as e:
            console.print(f"⚠️  iptables設定エラー: {e}", style="yellow")
        
        time.sleep(duration)
        
        # ルールを削除して復旧
        try:
            if os.name == 'posix':
                subprocess.run(['sudo', 'iptables', '-D', 'OUTPUT', '-p', 'tcp', '--dport', '1883', '-j', 'DROP'], 
                             check=False, capture_output=True)
                subprocess.run(['sudo', 'iptables', '-D', 'INPUT', '-p', 'tcp', '--sport', '1883', '-j', 'DROP'], 
                             check=False, capture_output=True)
        except Exception as e:
            console.print(f"⚠️  iptables復旧エラー: {e}", style="yellow")
        
        console.print("✅ ネットワーク接続を復旧", style="bold green")
    
    def simulate_intermittent_failure(self, duration: int):
        """間欠的な接続障害をシミュレート"""
        console.print("⚡ 間欠的接続障害を開始", style="bold yellow")
        
        start_time = time.time()
        blocking = False
        
        while time.time() - start_time < duration:
            if blocking:
                console.print("🔌 接続復旧", style="green")
                # 接続を復旧
                try:
                    if os.name == 'posix':
                        subprocess.run(['sudo', 'iptables', '-D', 'OUTPUT', '-p', 'tcp', '--dport', '1883', '-j', 'DROP'], 
                                     check=False, capture_output=True)
                except:
                    pass
                blocking = False
            else:
                console.print("🚫 接続遮断", style="red")
                # 接続を遮断
                try:
                    if os.name == 'posix':
                        subprocess.run(['sudo', 'iptables', '-A', 'OUTPUT', '-p', 'tcp', '--dport', '1883', '-j', 'DROP'], 
                                     check=False, capture_output=True)
                except:
                    pass
                blocking = True
            
            time.sleep(1)
        
        # 最終的に接続を復旧
        if blocking:
            try:
                if os.name == 'posix':
                    subprocess.run(['sudo', 'iptables', '-D', 'OUTPUT', '-p', 'tcp', '--dport', '1883', '-j', 'DROP'], 
                                 check=False, capture_output=True)
            except:
                pass
        
        console.print("✅ 間欠的障害を終了", style="bold green")
    
    def simulate_high_latency(self, duration: int):
        """高レイテンシーをシミュレート"""
        console.print("🐌 高レイテンシーを開始", style="bold blue")
        
        # tc (traffic control)を使用してレイテンシーを追加
        try:
            if os.name == 'posix':
                subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', 'lo', 'root', 'netem', 'delay', '500ms'], 
                             check=False, capture_output=True)
        except Exception as e:
            console.print(f"⚠️  tc設定エラー: {e}", style="yellow")
        
        time.sleep(duration)
        
        # レイテンシー設定を削除
        try:
            if os.name == 'posix':
                subprocess.run(['sudo', 'tc', 'qdisc', 'del', 'dev', 'lo', 'root'], 
                             check=False, capture_output=True)
        except Exception as e:
            console.print(f"⚠️  tc復旧エラー: {e}", style="yellow")
        
        console.print("✅ 高レイテンシーを終了", style="bold green")
    
    def simulate_packet_loss(self, duration: int):
        """パケット損失をシミュレート"""
        console.print("📦 パケット損失を開始 (30%)", style="bold magenta")
        
        # tcでパケット損失を設定
        try:
            if os.name == 'posix':
                subprocess.run(['sudo', 'tc', 'qdisc', 'add', 'dev', 'lo', 'root', 'netem', 'loss', '30%'], 
                             check=False, capture_output=True)
        except Exception as e:
            console.print(f"⚠️  tc設定エラー: {e}", style="yellow")
        
        time.sleep(duration)
        
        # パケット損失設定を削除
        try:
            if os.name == 'posix':
                subprocess.run(['sudo', 'tc', 'qdisc', 'del', 'dev', 'lo', 'root'], 
                             check=False, capture_output=True)
        except Exception as e:
            console.print(f"⚠️  tc復旧エラー: {e}", style="yellow")
        
        console.print("✅ パケット損失を終了", style="bold green")
    
    def run_scenario(self, scenario_index: int):
        """指定されたシナリオを実行"""
        if 0 <= scenario_index < len(self.scenarios):
            scenario = self.scenarios[scenario_index]
            
            console.print(f"\n🎬 シナリオ実行: {scenario['name']}", style="bold cyan")
            console.print(f"   説明: {scenario['description']}", style="dim")
            console.print(f"   継続時間: {scenario['duration']}秒", style="dim")
            
            try:
                scenario['action'](scenario['duration'])
            except Exception as e:
                console.print(f"❌ シナリオ実行エラー: {e}", style="bold red")
            
            console.print(f"✅ シナリオ完了: {scenario['name']}", style="bold green")
        else:
            console.print("❌ 無効なシナリオインデックス", style="bold red")
    
    def list_scenarios(self):
        """利用可能なシナリオ一覧を表示"""
        console.print("\n📋 利用可能な障害シナリオ:", style="bold blue")
        
        for i, scenario in enumerate(self.scenarios):
            console.print(f"  {i+1}. {scenario['name']}")
            console.print(f"     {scenario['description']}")
            console.print(f"     継続時間: {scenario['duration']}秒")
            console.print()
    
    def cleanup(self):
        """クリーンアップ処理"""
        console.print("🧹 ネットワーク設定をクリーンアップ中...", style="yellow")
        
        # すべてのiptablesルールを削除
        try:
            if os.name == 'posix':
                subprocess.run(['sudo', 'iptables', '-F'], check=False, capture_output=True)
                subprocess.run(['sudo', 'tc', 'qdisc', 'del', 'dev', 'lo', 'root'], check=False, capture_output=True)
        except:
            pass
        
        console.print("✅ クリーンアップ完了", style="green")

class ResilienceTest:
    """レジリエンステストクラス"""
    
    def __init__(self, robust_client):
        self.client = robust_client
        self.simulator = NetworkFailureSimulator()
        self.test_results = []
    
    def run_comprehensive_test(self):
        """包括的なレジリエンステスト"""
        console.print("🧪 レジリエンス総合テストを開始", style="bold blue")
        
        # テスト前の接続確認
        if not self.client.connect():
            console.print("❌ 初期接続に失敗", style="bold red")
            return
        
        self.client.subscribe('test/resilience/+')
        
        # 各シナリオをテスト
        for i, scenario in enumerate(self.simulator.scenarios):
            console.print(f"\n🔬 テスト {i+1}/{len(self.simulator.scenarios)}: {scenario['name']}", 
                         style="bold yellow")
            
            # テスト開始前の状態記録
            start_stats = self.client.get_statistics()
            start_time = time.time()
            
            # バックグラウンドでメッセージ送信
            message_thread = threading.Thread(
                target=self._send_test_messages,
                args=(scenario['duration'] + 5,),  # シナリオより少し長く
                daemon=True
            )
            message_thread.start()
            
            # 少し待ってから障害を発生
            time.sleep(2)
            
            # 障害シナリオ実行
            self.simulator.run_scenario(i)
            
            # 復旧待ち
            time.sleep(3)
            
            # メッセージ送信スレッドの終了を待機
            message_thread.join(timeout=10)
            
            # テスト結果記録
            end_stats = self.client.get_statistics()
            end_time = time.time()
            
            test_result = {
                'scenario': scenario['name'],
                'duration': end_time - start_time,
                'messages_sent_before': start_stats['messages_sent'],
                'messages_sent_after': end_stats['messages_sent'],
                'errors_before': sum(start_stats['errors'].values()) if start_stats['errors'] else 0,
                'errors_after': sum(end_stats['errors'].values()) if end_stats['errors'] else 0,
                'connection_state': self.client.get_connection_info()['state']
            }
            
            self.test_results.append(test_result)
            
            console.print(f"✅ テスト完了: {scenario['name']}", style="green")
            self.client.display_status()
        
        # テスト結果サマリー
        self._display_test_results()
        
        # クリーンアップ
        self.simulator.cleanup()
        self.client.disconnect()
    
    def _send_test_messages(self, duration: int):
        """テストメッセージを定期送信"""
        start_time = time.time()
        message_count = 0
        
        while time.time() - start_time < duration:
            message = f"テストメッセージ #{message_count} - {time.time()}"
            success = self.client.publish('test/resilience/messages', message)
            
            if success:
                console.print(f"📤 テストメッセージ送信 #{message_count}", style="dim")
            else:
                console.print(f"❌ テストメッセージ送信失敗 #{message_count}", style="dim red")
            
            message_count += 1
            time.sleep(1)
    
    def _display_test_results(self):
        """テスト結果を表示"""
        console.print("\n📊 レジリエンステスト結果サマリー", style="bold blue")
        
        from rich.table import Table
        
        table = Table(title="テスト結果")
        table.add_column("シナリオ", style="cyan")
        table.add_column("実行時間", style="yellow")
        table.add_column("送信メッセージ数", style="green")
        table.add_column("エラー発生数", style="red")
        table.add_column("最終接続状態", style="blue")
        
        for result in self.test_results:
            messages_sent = result['messages_sent_after'] - result['messages_sent_before']
            errors_occurred = result['errors_after'] - result['errors_before']
            
            table.add_row(
                result['scenario'],
                f"{result['duration']:.1f}秒",
                str(messages_sent),
                str(errors_occurred),
                result['connection_state']
            )
        
        console.print(table)

# 実行例とデモンストレーション
def main():
    """メイン実行関数"""
    console.print("🛡️  MQTT エラーハンドリング・レジリエンステスト", style="bold blue")
    
    # 堅牢なクライアント作成
    from robust_mqtt_client import RobustMQTTClient
    
    client = RobustMQTTClient(
        broker_host='localhost',
        broker_port=1883,
        client_id='resilience-test-client'
    )
    
    # レジリエンステスト実行
    test = ResilienceTest(client)
    
    try:
        test.run_comprehensive_test()
    except KeyboardInterrupt:
        console.print("\n⚠️  テスト中断", style="yellow")
    except Exception as e:
        console.print(f"❌ テストエラー: {e}", style="bold red")
    finally:
        test.simulator.cleanup()
        console.print("👋 テスト完了", style="blue")

if __name__ == "__main__":
    main()
```

### Exercise 3: メッセージ配信保証システム

`src/delivery_guarantee.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import threading
import sqlite3
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set
from rich.console import Console
from rich.table import Table
from rich.progress import track
import uuid

console = Console()

class MessageState:
    """メッセージ状態管理"""
    PENDING = "pending"
    SENT = "sent"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    EXPIRED = "expired"

class DeliveryGuaranteeManager:
    """配信保証管理クラス"""
    
    def __init__(self, db_path: str = "message_delivery.db", max_retries: int = 3):
        self.db_path = db_path
        self.max_retries = max_retries
        self.pending_messages: Dict[str, Dict[str, Any]] = {}
        self.acknowledged_messages: Set[str] = set()
        
        # データベース初期化
        self.init_database()
        
        # タイマースレッド
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_running = True
        self.cleanup_thread.start()
    
    def init_database(self):
        """データベースの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS message_delivery (
                    message_id TEXT PRIMARY KEY,
                    topic TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    qos INTEGER NOT NULL,
                    retain BOOLEAN NOT NULL,
                    state TEXT NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    updated_at TIMESTAMP NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    max_retries INTEGER NOT NULL,
                    expires_at TIMESTAMP,
                    checksum TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS delivery_acknowledgment (
                    message_id TEXT PRIMARY KEY,
                    acknowledged_at TIMESTAMP NOT NULL,
                    client_id TEXT,
                    FOREIGN KEY (message_id) REFERENCES message_delivery (message_id)
                )
            """)
            
            conn.commit()
    
    def generate_message_id(self, topic: str, payload: str) -> str:
        """メッセージIDを生成"""
        unique_data = f"{topic}:{payload}:{time.time()}:{uuid.uuid4()}"
        return hashlib.sha256(unique_data.encode()).hexdigest()[:16]
    
    def calculate_checksum(self, payload: str) -> str:
        """ペイロードのチェックサムを計算"""
        return hashlib.md5(payload.encode()).hexdigest()
    
    def store_message(self, 
                     topic: str, 
                     payload: str, 
                     qos: int = 1, 
                     retain: bool = False,
                     ttl_seconds: int = 3600) -> str:
        """メッセージをストレージに保存"""
        message_id = self.generate_message_id(topic, payload)
        checksum = self.calculate_checksum(payload)
        created_at = datetime.now()
        expires_at = created_at + timedelta(seconds=ttl_seconds)
        
        message_data = {
            'message_id': message_id,
            'topic': topic,
            'payload': payload,
            'qos': qos,
            'retain': retain,
            'state': MessageState.PENDING,
            'created_at': created_at.isoformat(),
            'expires_at': expires_at.isoformat(),
            'retry_count': 0,
            'checksum': checksum
        }
        
        # データベースに保存
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO message_delivery 
                (message_id, topic, payload, qos, retain, state, created_at, updated_at, 
                 retry_count, max_retries, expires_at, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                message_id, topic, payload, qos, retain, MessageState.PENDING,
                created_at, created_at, 0, self.max_retries, expires_at, checksum
            ))
            conn.commit()
        
        # メモリにも保存
        self.pending_messages[message_id] = message_data
        
        console.print(f"💾 メッセージ保存完了: {message_id}", style="green")
        return message_id
    
    def mark_message_sent(self, message_id: str):
        """メッセージを送信済みとしてマーク"""
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE message_delivery 
                SET state = ?, updated_at = ?
                WHERE message_id = ?
            """, (MessageState.SENT, current_time, message_id))
            conn.commit()
        
        if message_id in self.pending_messages:
            self.pending_messages[message_id]['state'] = MessageState.SENT
            self.pending_messages[message_id]['updated_at'] = current_time.isoformat()
    
    def acknowledge_message(self, message_id: str, client_id: str = None):
        """メッセージの配信確認"""
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # メッセージ状態を更新
            conn.execute("""
                UPDATE message_delivery 
                SET state = ?, updated_at = ?
                WHERE message_id = ?
            """, (MessageState.ACKNOWLEDGED, current_time, message_id))
            
            # 確認記録を保存
            conn.execute("""
                INSERT OR REPLACE INTO delivery_acknowledgment 
                (message_id, acknowledged_at, client_id)
                VALUES (?, ?, ?)
            """, (message_id, current_time, client_id))
            
            conn.commit()
        
        # メモリから削除
        if message_id in self.pending_messages:
            del self.pending_messages[message_id]
        
        self.acknowledged_messages.add(message_id)
        console.print(f"✅ メッセージ配信確認: {message_id}", style="bold green")
    
    def mark_message_failed(self, message_id: str, reason: str = None):
        """メッセージを失敗としてマーク"""
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE message_delivery 
                SET state = ?, updated_at = ?
                WHERE message_id = ?
            """, (MessageState.FAILED, current_time, message_id))
            conn.commit()
        
        if message_id in self.pending_messages:
            self.pending_messages[message_id]['state'] = MessageState.FAILED
        
        console.print(f"❌ メッセージ配信失敗: {message_id} ({reason})", style="red")
    
    def increment_retry_count(self, message_id: str) -> bool:
        """リトライ回数を増加（上限チェック付き）"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT retry_count, max_retries FROM message_delivery 
                WHERE message_id = ?
            """, (message_id,))
            
            row = cursor.fetchone()
            if not row:
                return False
            
            retry_count, max_retries = row
            new_retry_count = retry_count + 1
            
            if new_retry_count > max_retries:
                # 最大リトライ回数に達した場合は失敗とマーク
                self.mark_message_failed(message_id, "最大リトライ回数超過")
                return False
            
            # リトライ回数を更新
            conn.execute("""
                UPDATE message_delivery 
                SET retry_count = ?, updated_at = ?
                WHERE message_id = ?
            """, (new_retry_count, datetime.now(), message_id))
            conn.commit()
        
        if message_id in self.pending_messages:
            self.pending_messages[message_id]['retry_count'] = new_retry_count
        
        return True
    
    def get_pending_messages(self) -> List[Dict[str, Any]]:
        """未配信メッセージを取得"""
        current_time = datetime.now()
        pending_messages = []
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT message_id, topic, payload, qos, retain, retry_count, expires_at, checksum
                FROM message_delivery
                WHERE state IN (?, ?) AND expires_at > ?
                ORDER BY created_at
            """, (MessageState.PENDING, MessageState.SENT, current_time))
            
            for row in cursor.fetchall():
                pending_messages.append({
                    'message_id': row[0],
                    'topic': row[1],
                    'payload': row[2],
                    'qos': row[3],
                    'retain': bool(row[4]),
                    'retry_count': row[5],
                    'expires_at': row[6],
                    'checksum': row[7]
                })
        
        return pending_messages
    
    def cleanup_expired_messages(self):
        """期限切れメッセージのクリーンアップ"""
        current_time = datetime.now()
        
        with sqlite3.connect(self.db_path) as conn:
            # 期限切れメッセージを取得
            cursor = conn.execute("""
                SELECT message_id FROM message_delivery
                WHERE expires_at < ? AND state != ?
            """, (current_time, MessageState.ACKNOWLEDGED))
            
            expired_ids = [row[0] for row in cursor.fetchall()]
            
            if expired_ids:
                # 状態を期限切れに更新
                placeholders = ','.join('?' for _ in expired_ids)
                conn.execute(f"""
                    UPDATE message_delivery 
                    SET state = ?, updated_at = ?
                    WHERE message_id IN ({placeholders})
                """, [MessageState.EXPIRED, current_time] + expired_ids)
                
                conn.commit()
                
                # メモリからも削除
                for msg_id in expired_ids:
                    if msg_id in self.pending_messages:
                        del self.pending_messages[msg_id]
                
                console.print(f"🗑️  期限切れメッセージをクリーンアップ: {len(expired_ids)}件", style="yellow")
    
    def _cleanup_loop(self):
        """定期クリーンアップループ"""
        while self.cleanup_running:
            try:
                self.cleanup_expired_messages()
                time.sleep(60)  # 1分間隔でクリーンアップ
            except Exception as e:
                console.print(f"❌ クリーンアップエラー: {e}", style="red")
                time.sleep(60)
    
    def get_delivery_statistics(self) -> Dict[str, Any]:
        """配信統計を取得"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT 
                    state,
                    COUNT(*) as count,
                    AVG(retry_count) as avg_retries
                FROM message_delivery
                GROUP BY state
            """)
            
            stats = {}
            for row in cursor.fetchall():
                state, count, avg_retries = row
                stats[state] = {
                    'count': count,
                    'avg_retries': avg_retries or 0
                }
            
            # 全体統計
            cursor = conn.execute("SELECT COUNT(*) FROM message_delivery")
            total_messages = cursor.fetchone()[0]
            
            cursor = conn.execute("""
                SELECT COUNT(*) FROM message_delivery 
                WHERE state = ?
            """, (MessageState.ACKNOWLEDGED,))
            success_count = cursor.fetchone()[0]
            
            success_rate = (success_count / total_messages * 100) if total_messages > 0 else 0
            
            return {
                'by_state': stats,
                'total_messages': total_messages,
                'success_rate': success_rate,
                'pending_count': len(self.pending_messages)
            }
    
    def display_statistics(self):
        """統計情報を表示"""
        stats = self.get_delivery_statistics()
        
        table = Table(title="メッセージ配信統計")
        table.add_column("状態", style="cyan")
        table.add_column("件数", style="yellow")
        table.add_column("平均リトライ回数", style="green")
        
        for state, data in stats['by_state'].items():
            table.add_row(
                state,
                str(data['count']),
                f"{data['avg_retries']:.1f}"
            )
        
        console.print(table)
        console.print(f"\n📊 総メッセージ数: {stats['total_messages']}")
        console.print(f"✅ 成功率: {stats['success_rate']:.1f}%")
        console.print(f"⏳ 未処理メッセージ: {stats['pending_count']}")
    
    def shutdown(self):
        """シャットダウン処理"""
        self.cleanup_running = False
        if self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=5)
        console.print("💾 配信保証マネージャーをシャットダウン", style="yellow")

class GuaranteedMQTTClient:
    """配信保証付きMQTTクライアント"""
    
    def __init__(self, broker_host: str = 'localhost', broker_port: int = 1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = mqtt.Client(client_id=f"guaranteed-client-{int(time.time())}")
        self.delivery_manager = DeliveryGuaranteeManager()
        
        # 送信待ちメッセージの定期処理
        self.retry_thread = threading.Thread(target=self._retry_loop, daemon=True)
        self.retry_running = True
        
        self.setup_mqtt_handlers()
    
    def setup_mqtt_handlers(self):
        """MQTTイベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_publish = self.on_publish
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print("✅ 配信保証クライアント接続完了", style="bold green")
            
            # 確認応答用トピックに購読
            client.subscribe("delivery/ack/+")
            
            # 未送信メッセージの再送を開始
            self.retry_thread.start()
        else:
            console.print(f"❌ 接続失敗: {rc}", style="bold red")
    
    def on_publish(self, client, userdata, mid):
        """メッセージ送信完了時のコールバック"""
        # MIDからメッセージIDを取得する仕組みが必要
        console.print(f"📤 メッセージ送信完了 (MID: {mid})", style="green")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        topic = msg.topic
        payload = msg.payload.decode('utf-8')
        
        if topic.startswith('delivery/ack/'):
            # 配信確認メッセージ
            message_id = topic.split('/')[-1]
            try:
                ack_data = json.loads(payload)
                client_id = ack_data.get('client_id')
                self.delivery_manager.acknowledge_message(message_id, client_id)
            except json.JSONDecodeError:
                console.print(f"⚠️  不正な確認メッセージフォーマット: {payload}", style="yellow")
        else:
            # 通常のメッセージ処理
            console.print(f"📬 メッセージ受信: {topic}", style="cyan")
    
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        if rc != 0:
            console.print("⚠️  予期しない切断", style="yellow")
    
    def connect(self) -> bool:
        """ブローカーに接続"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            console.print(f"❌ 接続エラー: {e}", style="bold red")
            return False
    
    def guaranteed_publish(self, 
                          topic: str, 
                          payload: str, 
                          qos: int = 1, 
                          retain: bool = False,
                          ttl_seconds: int = 3600) -> str:
        """配信保証付きメッセージ送信"""
        # メッセージを永続化
        message_id = self.delivery_manager.store_message(topic, payload, qos, retain, ttl_seconds)
        
        # 配信確認要求を含むメッセージを作成
        enhanced_payload = json.dumps({
            'message_id': message_id,
            'content': payload,
            'timestamp': time.time(),
            'requires_ack': True,
            'ack_topic': f'delivery/ack/{message_id}'
        })
        
        # メッセージ送信
        try:
            result = self.client.publish(topic, enhanced_payload, qos, retain)
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                self.delivery_manager.mark_message_sent(message_id)
                console.print(f"📤 配信保証メッセージ送信: {message_id}", style="green")
            else:
                console.print(f"❌ メッセージ送信失敗: {result.rc}", style="red")
                self.delivery_manager.mark_message_failed(message_id, f"MQTT送信エラー: {result.rc}")
                
        except Exception as e:
            console.print(f"❌ 送信例外: {e}", style="red")
            self.delivery_manager.mark_message_failed(message_id, str(e))
        
        return message_id
    
    def _retry_loop(self):
        """未配信メッセージのリトライループ"""
        while self.retry_running:
            try:
                pending_messages = self.delivery_manager.get_pending_messages()
                
                for msg in pending_messages:
                    message_id = msg['message_id']
                    
                    # リトライ回数チェック
                    if not self.delivery_manager.increment_retry_count(message_id):
                        continue  # 最大リトライ回数に達した
                    
                    console.print(f"🔄 メッセージ再送: {message_id} (試行 {msg['retry_count'] + 1})", 
                                style="yellow")
                    
                    # メッセージ再送
                    enhanced_payload = json.dumps({
                        'message_id': message_id,
                        'content': msg['payload'],
                        'timestamp': time.time(),
                        'requires_ack': True,
                        'ack_topic': f'delivery/ack/{message_id}',
                        'retry_count': msg['retry_count'] + 1
                    })
                    
                    try:
                        result = self.client.publish(msg['topic'], enhanced_payload, msg['qos'], msg['retain'])
                        if result.rc == mqtt.MQTT_ERR_SUCCESS:
                            self.delivery_manager.mark_message_sent(message_id)
                        else:
                            console.print(f"❌ 再送失敗: {message_id}", style="red")
                    except Exception as e:
                        console.print(f"❌ 再送例外: {e}", style="red")
                
                time.sleep(30)  # 30秒間隔でリトライ
                
            except Exception as e:
                console.print(f"❌ リトライループエラー: {e}", style="red")
                time.sleep(30)
    
    def disconnect(self):
        """切断処理"""
        self.retry_running = False
        if self.retry_thread.is_alive():
            self.retry_thread.join(timeout=5)
        
        self.client.loop_stop()
        self.client.disconnect()
        self.delivery_manager.shutdown()
        
        console.print("👋 配信保証クライアント切断完了", style="blue")

# デモンストレーション
def demonstrate_delivery_guarantee():
    """配信保証システムのデモンストレーション"""
    console.print("🛡️  メッセージ配信保証システムデモ", style="bold blue")
    
    client = GuaranteedMQTTClient()
    
    if not client.connect():
        console.print("❌ 接続に失敗しました", style="bold red")
        return
    
    time.sleep(2)  # 接続完了待ち
    
    try:
        # テストメッセージ送信
        console.print("📤 テストメッセージを送信中...", style="blue")
        
        message_ids = []
        for i in range(5):
            msg_id = client.guaranteed_publish(
                f'test/guaranteed/message-{i}',
                f'重要なメッセージ #{i} - 配信保証が必要',
                qos=1
            )
            message_ids.append(msg_id)
            time.sleep(1)
        
        # 統計表示
        console.print("\n📊 10秒後に統計を表示します...")
        time.sleep(10)
        
        client.delivery_manager.display_statistics()
        
        # 手動での配信確認（通常は受信側クライアントが行う）
        console.print("\n✅ 手動で配信確認をシミュレート...")
        for i, msg_id in enumerate(message_ids):
            if i < 3:  # 最初の3つだけ確認
                client.delivery_manager.acknowledge_message(msg_id, "test-receiver")
                time.sleep(0.5)
        
        # 最終統計表示
        console.print("\n📊 最終統計:")
        client.delivery_manager.display_statistics()
        
        console.print("\n⏱️  30秒間リトライ処理を観察...")
        time.sleep(30)
        
        console.print("\n📊 リトライ後統計:")
        client.delivery_manager.display_statistics()
        
    except KeyboardInterrupt:
        console.print("\n⚠️  デモンストレーション中断", style="yellow")
    except Exception as e:
        console.print(f"❌ デモエラー: {e}", style="bold red")
    finally:
        client.disconnect()
        console.print("✅ デモンストレーション完了", style="green")

if __name__ == "__main__":
    demonstrate_delivery_guarantee()
```

## 🎯 練習問題

### 問題1: 基本的なエラーハンドリング
1. `robust_mqtt_client.py`を実行して、堅牢なクライアントの動作を確認してください
2. MQTTブローカーを停止して自動再接続機能をテストしてください

### 問題2: ネットワーク障害シミュレーション
1. `network_failure_simulator.py`を実行して各障害シナリオをテストしてください
2. 各シナリオでクライアントがどのように復旧するかを観察してください

### 問題3: 配信保証システム
1. `delivery_guarantee.py`を実行して配信保証機能を確認してください
2. メッセージの永続化とリトライ機能をテストしてください

### 問題4: カスタム実装
独自のエラーハンドリング戦略を実装してください：
- 特定のエラータイプに対する個別の対応
- カスタムリトライポリシー
- アプリケーション固有の復旧処理

## ✅ 確認チェックリスト

- [ ] 包括的なエラーハンドリング戦略を理解した
- [ ] 自動再接続メカニズムを実装できた
- [ ] 指数的バックオフとジッターを実装した
- [ ] サーキットブレーカーパターンを理解した
- [ ] メッセージバッファリングを実装した
- [ ] 配信保証システムを構築した
- [ ] ネットワーク障害からの復旧を確認した

## 📊 理解度チェック

以下の質問に答えられるか確認してください：

1. 指数的バックオフにジッターを追加する理由は何ですか？
2. サーキットブレーカーパターンの利点は何ですか？
3. メッセージの配信保証を実現する方法は？
4. ネットワーク障害の分類とそれぞれの対処法は？

## 🔧 トラブルシューティング

### 自動再接続が機能しない
- リトライポリシーの設定を確認
- ネットワーク接続状況を確認
- エラーログを詳細に確認

### メッセージが重複配信される
- QoSレベルとClean Sessionの設定を確認
- 重複検出メカニズムの実装を確認

### 配信保証が機能しない
- データベースの初期化を確認
- 確認メッセージの形式を確認
- タイムアウト設定を確認

---

**次のステップ**: [07-mqtt5-advanced-features](../07-mqtt5-advanced-features/) でMQTT 5.0の高度な機能について学習しましょう！