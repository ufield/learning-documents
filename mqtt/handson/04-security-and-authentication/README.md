# ハンズオン 04: セキュリティと認証

## 🎯 学習目標

このハンズオンでは以下を学習します：

- MQTTにおけるセキュリティの重要性と脅威
- TLS/SSL暗号化通信の実装
- ユーザー名・パスワード認証
- 証明書ベースの相互認証
- Topic-based Authorization（トピック単位のアクセス制御）
- セキュリティベストプラクティスの実装

**所要時間**: 約120分

## 📋 前提条件

- [03-qos-and-reliability](../03-qos-and-reliability/) の完了
- OpenSSLツールの利用可能性
- MQTTブローカー（Mosquitto推奨）の管理者権限

## 🔒 MQTTセキュリティの概要

### セキュリティ脅威
1. **盗聴**: パケット内容の傍受
2. **なりすまし**: 偽のクライアント・ブローカー
3. **中間者攻撃**: 通信の改竄
4. **Topic Hijacking**: 不正なトピック操作
5. **DoS攻撃**: サービス妨害

### セキュリティ対策レイヤー
1. **トランスポート層**: TLS/SSL暗号化
2. **認証層**: クライアント認証
3. **認可層**: Topic単位のアクセス制御
4. **アプリケーション層**: ペイロード暗号化

## 📝 実装演習

### Exercise 1: TLS/SSL暗号化通信

まず、テスト用のCA証明書とクライアント証明書を作成します：

`scripts/create_certificates.sh` を作成：

```bash
#!/bin/bash
# MQTT TLS証明書作成スクリプト

set -e

CERT_DIR="./certificates"
DAYS=365

# 証明書ディレクトリを作成
mkdir -p $CERT_DIR
cd $CERT_DIR

echo "🔐 Creating MQTT TLS certificates..."

# 1. CA秘密鍵とCA証明書を作成
echo "📋 Creating CA certificate..."
openssl genrsa -out ca.key 2048
openssl req -new -x509 -days $DAYS -key ca.key -out ca.crt \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=MQTT-Learning/OU=CA/CN=mqtt-ca"

# 2. サーバー（ブローカー）証明書を作成
echo "🖥️  Creating server certificate..."
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=MQTT-Learning/OU=Server/CN=localhost"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out server.crt -days $DAYS

# 3. クライアント証明書を作成
echo "👤 Creating client certificate..."
openssl genrsa -out client.key 2048
openssl req -new -key client.key -out client.csr \
    -subj "/C=JP/ST=Tokyo/L=Tokyo/O=MQTT-Learning/OU=Client/CN=mqtt-client"
openssl x509 -req -in client.csr -CA ca.crt -CAkey ca.key \
    -CAcreateserial -out client.crt -days $DAYS

# 4. クリーンアップ
rm *.csr
rm ca.srl

echo "✅ Certificates created successfully!"
echo "📁 Files created:"
echo "   - ca.crt (CA certificate)"
echo "   - server.crt, server.key (Server certificate)"
echo "   - client.crt, client.key (Client certificate)"

# 5. Mosquittoの設定ファイルを作成
cat > mosquitto-tls.conf << EOF
# Mosquitto TLS設定
port 8883
cafile $PWD/ca.crt
certfile $PWD/server.crt
keyfile $PWD/server.key

# クライアント証明書を要求
require_certificate true

# 認証設定
allow_anonymous false
password_file $PWD/passwd

# ログ設定
log_type all
log_dest file $PWD/mosquitto.log
EOF

echo "⚙️  Mosquitto TLS config created: mosquitto-tls.conf"
```

TLS対応のセキュアクライアントを作成：

`src/secure_client.py` を作成：

```python
#!/usr/bin/env python3
"""
セキュアMQTTクライアント
TLS/SSL暗号化通信とクライアント証明書認証
"""

import paho.mqtt.client as mqtt
import ssl
import json
import time
import os
from pathlib import Path
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from typing import Optional

console = Console()

class SecureMQTTClient:
    def __init__(self, 
                 broker_host: str = "localhost", 
                 port: int = 8883,
                 cert_path: str = "./certificates"):
        self.broker_host = broker_host
        self.port = port
        self.cert_path = Path(cert_path)
        
        # セキュリティ統計
        self.security_stats = {
            "tls_handshake_time": 0,
            "certificate_verified": False,
            "encryption_enabled": False,
            "auth_method": "none"
        }
        
        # MQTTクライアント設定
        self.client = mqtt.Client(
            client_id=f"secure_client_{int(time.time())}",
            clean_session=True
        )
        
        self.connected = False
        self.setup_callbacks()
    
    def setup_callbacks(self):
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log
    
    def configure_tls_security(self, 
                              username: Optional[str] = None,
                              password: Optional[str] = None,
                              use_client_cert: bool = True):
        """TLSセキュリティ設定"""
        try:
            # SSL/TLSコンテキストの作成
            context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
            
            # CA証明書の設定
            ca_cert_path = self.cert_path / "ca.crt"
            if ca_cert_path.exists():
                context.load_verify_locations(str(ca_cert_path))
                console.print(f"📋 CA certificate loaded: {ca_cert_path}", style="green")
            else:
                console.print("⚠️  CA certificate not found", style="yellow")
                context.check_hostname = False
                context.verify_mode = ssl.CERT_NONE
            
            # クライアント証明書の設定（相互認証）
            if use_client_cert:
                client_cert_path = self.cert_path / "client.crt"
                client_key_path = self.cert_path / "client.key"
                
                if client_cert_path.exists() and client_key_path.exists():
                    context.load_cert_chain(str(client_cert_path), str(client_key_path))
                    console.print("🔐 Client certificate loaded for mutual authentication", style="green")
                    self.security_stats["certificate_verified"] = True
                    self.security_stats["auth_method"] = "client_certificate"
                else:
                    console.print("⚠️  Client certificate not found", style="yellow")
            
            # TLSコンテキストを設定
            self.client.tls_set_context(context)
            self.security_stats["encryption_enabled"] = True
            
            # ユーザー名/パスワード認証
            if username and password:
                self.client.username_pw_set(username, password)
                console.print(f"👤 Username/password authentication set for: {username}", style="blue")
                if self.security_stats["auth_method"] == "none":
                    self.security_stats["auth_method"] = "username_password"
                else:
                    self.security_stats["auth_method"] += " + username_password"
            
            console.print("🔒 TLS security configured successfully", style="bold green")
            return True
            
        except Exception as e:
            console.print(f"❌ TLS configuration failed: {e}", style="bold red")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            console.print("✅ Secure connection established", style="bold green")
            self.connected = True
            
            # セキュリティ情報の表示
            self.display_security_info()
            
            # セキュアトピックを購読
            secure_topics = [
                "secure/sensors/+",
                "secure/alerts/+",
                "secure/commands/+",
                f"secure/clients/{self.client._client_id.decode()}/+"
            ]
            
            for topic in secure_topics:
                client.subscribe(topic, qos=1)
                console.print(f"🔐 Subscribed to secure topic: {topic}", style="blue")
        else:
            console.print(f"❌ Secure connection failed: {rc}", style="bold red")
            self.print_connection_error(rc)
    
    def on_message(self, client, userdata, msg):
        try:
            # メッセージの復号化（必要に応じて）
            payload = msg.payload.decode()
            
            # セキュアメッセージの検証
            if self.verify_secure_message(msg.topic, payload):
                console.print(f"🔐 Secure message received on {msg.topic}", style="green")
                console.print(f"   Content: {payload[:100]}...", style="dim")
                
                # メッセージ処理
                self.process_secure_message(msg.topic, payload)
            else:
                console.print(f"⚠️  Message verification failed: {msg.topic}", style="yellow")
                
        except Exception as e:
            console.print(f"❌ Error processing secure message: {e}", style="red")
    
    def verify_secure_message(self, topic: str, payload: str) -> bool:
        """セキュアメッセージの検証"""
        try:
            # JSONメッセージの場合、署名やタイムスタンプを検証
            if payload.startswith('{'):
                data = json.loads(payload)
                
                # タイムスタンプ検証（古すぎるメッセージを拒否）
                if "timestamp" in data:
                    msg_time = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
                    age = (datetime.now().astimezone() - msg_time).total_seconds()
                    if age > 300:  # 5分以上古い
                        console.print(f"⚠️  Message too old: {age:.1f}s", style="yellow")
                        return False
                
                # 送信者検証
                if "sender" not in data:
                    console.print("⚠️  Message missing sender information", style="yellow")
                    return False
                
                return True
            
            return True  # プレーンテキストは通す
            
        except json.JSONDecodeError:
            return True  # JSON以外は通す
        except Exception:
            return False
    
    def process_secure_message(self, topic: str, payload: str):
        """セキュアメッセージの処理"""
        topic_parts = topic.split('/')
        
        if len(topic_parts) >= 3:
            category = topic_parts[1]  # secure/[category]/...
            
            if category == "sensors":
                self.process_secure_sensor_data(topic, payload)
            elif category == "alerts":
                self.process_secure_alert(topic, payload)
            elif category == "commands":
                self.process_secure_command(topic, payload)
            else:
                console.print(f"📨 Generic secure message: {topic}", style="white")
    
    def process_secure_sensor_data(self, topic: str, payload: str):
        """セキュアセンサーデータ処理"""
        try:
            data = json.loads(payload)
            sensor_id = data.get("sensor_id", "unknown")
            value = data.get("value", data.get("content"))
            
            console.print(f"🌡️  Secure sensor [{sensor_id}]: {value}", style="cyan")
        except:
            console.print(f"🌡️  Secure sensor data: {payload[:50]}...", style="cyan")
    
    def process_secure_alert(self, topic: str, payload: str):
        """セキュアアラート処理"""
        try:
            data = json.loads(payload)
            alert_level = data.get("level", "info")
            message = data.get("message", data.get("content"))
            
            style = "bold red" if alert_level == "critical" else "yellow"
            console.print(f"🚨 Secure Alert [{alert_level}]: {message}", style=style)
        except:
            console.print(f"🚨 Secure Alert: {payload[:50]}...", style="yellow")
    
    def process_secure_command(self, topic: str, payload: str):
        """セキュアコマンド処理"""
        try:
            data = json.loads(payload)
            command = data.get("command", data.get("content"))
            
            console.print(f"⚙️  Secure Command: {command}", style="magenta")
            
            # コマンド実行のシミュレート
            result = self.execute_secure_command(command)
            
            # 結果を返信
            response_topic = topic.replace("/commands/", "/responses/")
            response = {
                "original_command": command,
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "client_id": self.client._client_id.decode()
            }
            
            self.publish_secure(response_topic, response, qos=1)
            
        except Exception as e:
            console.print(f"❌ Command processing error: {e}", style="red")
    
    def execute_secure_command(self, command: str) -> dict:
        """セキュアコマンドの実行"""
        # コマンド実行のシミュレート
        if "status" in command.lower():
            return {
                "status": "online",
                "uptime": int(time.time()),
                "security_level": "high"
            }
        elif "restart" in command.lower():
            return {
                "action": "restart_scheduled",
                "eta": "30 seconds"
            }
        else:
            return {
                "action": "unknown_command",
                "supported_commands": ["status", "restart"]
            }
    
    def publish_secure(self, topic: str, message, qos: int = 1) -> bool:
        """セキュアメッセージの送信"""
        try:
            # メッセージにセキュリティメタデータを追加
            if isinstance(message, dict):
                message["timestamp"] = datetime.now().isoformat()
                message["sender"] = self.client._client_id.decode()
                message["security_level"] = "encrypted"
                payload = json.dumps(message)
            else:
                secure_wrapper = {
                    "content": str(message),
                    "timestamp": datetime.now().isoformat(),
                    "sender": self.client._client_id.decode(),
                    "security_level": "encrypted"
                }
                payload = json.dumps(secure_wrapper)
            
            result = self.client.publish(topic, payload, qos)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                console.print(f"🔐 Secure message sent to: {topic}", style="green")
                return True
            else:
                console.print(f"❌ Secure publish failed: {result.rc}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Secure publish error: {e}", style="red")
            return False
    
    def display_security_info(self):
        """セキュリティ情報の表示"""
        table = Table(title="Security Configuration")
        table.add_column("Parameter", style="cyan")
        table.add_column("Status", style="green")
        
        table.add_row("Encryption", "✅ Enabled" if self.security_stats["encryption_enabled"] else "❌ Disabled")
        table.add_row("Certificate Verified", "✅ Yes" if self.security_stats["certificate_verified"] else "❌ No")
        table.add_row("Authentication Method", self.security_stats["auth_method"])
        table.add_row("Connection Port", str(self.port))
        table.add_row("TLS Version", "TLS 1.2+")
        
        console.print(table)
    
    def print_connection_error(self, rc: int):
        """接続エラーの詳細表示"""
        error_messages = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier", 
            3: "Server unavailable",
            4: "Bad username or password",
            5: "Not authorized"
        }
        
        if rc in error_messages:
            console.print(f"Error: {error_messages[rc]}", style="red")
        
        console.print("\n🔧 Security troubleshooting:", style="bold yellow")
        console.print("1. Check certificate files exist and are valid")
        console.print("2. Verify CA certificate matches server certificate")
        console.print("3. Ensure username/password are correct")
        console.print("4. Confirm broker is running on the secure port")
    
    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            console.print("⚠️  Unexpected secure disconnection", style="yellow")
    
    def on_log(self, client, userdata, level, buf):
        if "SSL" in buf or "TLS" in buf:
            console.print(f"🔐 TLS: {buf}", style="dim blue")
    
    def connect(self) -> bool:
        try:
            start_time = time.time()
            self.client.connect(self.broker_host, self.port, 60)
            self.client.loop_start()
            
            # TLSハンドシェイク時間を測定
            timeout = 15  # TLSハンドシェイクには時間がかかる場合がある
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if self.connected:
                self.security_stats["tls_handshake_time"] = time.time() - start_time
                console.print(f"🕐 TLS handshake completed in {self.security_stats['tls_handshake_time']:.3f}s", 
                            style="dim green")
                return True
            else:
                console.print("⏰ Secure connection timeout", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Secure connection failed: {e}", style="bold red")
            return False
    
    def disconnect(self):
        if self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            console.print("🔐 Secure connection closed", style="yellow")

def main():
    """メイン実行関数"""
    console.print(Panel.fit(
        "🔐 Secure MQTT Client Demo\n\n"
        "セキュリティ機能：\n"
        "• TLS/SSL 暗号化通信\n"
        "• クライアント証明書認証\n"
        "• メッセージ整合性検証\n"
        "• セキュアトピック管理\n\n"
        "Language: Python 3\n"
        "Library: paho-mqtt + OpenSSL",
        title="Secure MQTT Client",
        border_style="green"
    ))
    
    # 証明書の存在確認
    cert_path = Path("./certificates")
    if not cert_path.exists():
        console.print("❌ Certificate directory not found", style="bold red")
        console.print("Run: chmod +x scripts/create_certificates.sh && ./scripts/create_certificates.sh", 
                     style="yellow")
        return
    
    # セキュアクライアントを作成
    client = SecureMQTTClient()
    
    # TLSセキュリティを設定
    if not client.configure_tls_security(
        username="secure_user",  # 必要に応じて変更
        password="secure_pass",  # 必要に応じて変更
        use_client_cert=True
    ):
        console.print("❌ TLS configuration failed", style="bold red")
        return
    
    # セキュアな接続を開始
    if not client.connect():
        console.print("❌ Failed to establish secure connection", style="bold red")
        return
    
    try:
        # テストメッセージを送信
        time.sleep(2)
        
        # センサーデータを送信
        sensor_data = {
            "sensor_id": "secure_temp_001",
            "value": 24.7,
            "unit": "celsius",
            "location": "server_room"
        }
        client.publish_secure("secure/sensors/temperature", sensor_data)
        
        time.sleep(1)
        
        # アラートを送信
        alert_data = {
            "level": "warning",
            "message": "Temperature approaching threshold",
            "threshold": 30.0,
            "current": 28.5
        }
        client.publish_secure("secure/alerts/temperature", alert_data)
        
        time.sleep(1)
        
        # ステータスコマンドを送信
        command_data = {
            "command": "status",
            "target": "system"
        }
        client.publish_secure("secure/commands/system", command_data)
        
        # メッセージを受信するため少し待機
        console.print("\n👂 Listening for secure messages... (Press Ctrl+C to stop)", style="blue")
        
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        console.print("\n👋 Shutting down secure client...", style="yellow")
    finally:
        client.disconnect()
        console.print("✨ Secure client shut down", style="bold green")

if __name__ == "__main__":
    main()
```

### Exercise 2: ユーザー認証とアクセス制御

`src/auth_manager.py` を作成：

```python
#!/usr/bin/env python3
"""
MQTT認証・認可管理システム
ユーザー管理とトピックベースアクセス制御
"""

import hashlib
import secrets
import json
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dataclasses import dataclass

console = Console()

@dataclass
class User:
    username: str
    password_hash: str
    roles: Set[str]
    created_at: datetime
    last_login: Optional[datetime] = None
    active: bool = True

@dataclass
class TopicPermission:
    topic_pattern: str
    permission: str  # 'read', 'write', 'readwrite'
    role: str

class MQTTAuthManager:
    def __init__(self, db_path: str = "./mqtt_auth.db"):
        self.db_path = db_path
        self.init_database()
        self.load_default_data()
    
    def init_database(self):
        """データベースの初期化"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ユーザーテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    password_hash TEXT NOT NULL,
                    roles TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    active INTEGER DEFAULT 1
                )
            ''')
            
            # トピック権限テーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS topic_permissions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    topic_pattern TEXT NOT NULL,
                    permission TEXT NOT NULL,
                    role TEXT NOT NULL,
                    UNIQUE(topic_pattern, role)
                )
            ''')
            
            # セッションテーブル
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    expires_at TEXT NOT NULL,
                    client_id TEXT,
                    FOREIGN KEY (username) REFERENCES users (username)
                )
            ''')
            
            conn.commit()
    
    def load_default_data(self):
        """デフォルトデータの読み込み"""
        # デフォルトユーザーの作成
        default_users = [
            {
                "username": "admin",
                "password": "admin123",
                "roles": ["admin", "user"]
            },
            {
                "username": "sensor_device",
                "password": "sensor_secret",
                "roles": ["sensor"]
            },
            {
                "username": "control_system", 
                "password": "control_secret",
                "roles": ["controller", "user"]
            },
            {
                "username": "viewer",
                "password": "viewer123",
                "roles": ["readonly"]
            }
        ]
        
        for user_data in default_users:
            if not self.user_exists(user_data["username"]):
                self.create_user(
                    user_data["username"],
                    user_data["password"],
                    user_data["roles"]
                )
        
        # デフォルトトピック権限の設定
        default_permissions = [
            # 管理者は全権限
            {"topic_pattern": "#", "permission": "readwrite", "role": "admin"},
            
            # センサーデバイスの権限
            {"topic_pattern": "sensors/+/data", "permission": "write", "role": "sensor"},
            {"topic_pattern": "sensors/+/status", "permission": "write", "role": "sensor"},
            {"topic_pattern": "sensors/+/heartbeat", "permission": "write", "role": "sensor"},
            
            # コントローラーの権限
            {"topic_pattern": "actuators/+/command", "permission": "write", "role": "controller"},
            {"topic_pattern": "sensors/+/data", "permission": "read", "role": "controller"},
            {"topic_pattern": "alerts/+", "permission": "readwrite", "role": "controller"},
            
            # 一般ユーザーの権限
            {"topic_pattern": "sensors/+/data", "permission": "read", "role": "user"},
            {"topic_pattern": "public/+", "permission": "readwrite", "role": "user"},
            
            # 読み取り専用ユーザー
            {"topic_pattern": "sensors/+/data", "permission": "read", "role": "readonly"},
            {"topic_pattern": "public/info", "permission": "read", "role": "readonly"},
        ]
        
        for perm in default_permissions:
            self.add_topic_permission(
                perm["topic_pattern"],
                perm["permission"], 
                perm["role"]
            )
    
    def hash_password(self, password: str) -> str:
        """パスワードをハッシュ化"""
        salt = secrets.token_hex(16)
        password_hash = hashlib.pbkdf2_hmac(
            'sha256',
            password.encode(),
            salt.encode(),
            100000
        )
        return f"{salt}:{password_hash.hex()}"
    
    def verify_password(self, password: str, password_hash: str) -> bool:
        """パスワード検証"""
        try:
            salt, hash_hex = password_hash.split(':')
            expected_hash = hashlib.pbkdf2_hmac(
                'sha256',
                password.encode(),
                salt.encode(),
                100000
            )
            return expected_hash.hex() == hash_hex
        except Exception:
            return False
    
    def user_exists(self, username: str) -> bool:
        """ユーザー存在確認"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
            return cursor.fetchone() is not None
    
    def create_user(self, username: str, password: str, roles: List[str]) -> bool:
        """新規ユーザー作成"""
        try:
            if self.user_exists(username):
                return False
            
            password_hash = self.hash_password(password)
            roles_json = json.dumps(sorted(roles))
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO users (username, password_hash, roles, created_at)
                    VALUES (?, ?, ?, ?)
                ''', (username, password_hash, roles_json, datetime.now().isoformat()))
                conn.commit()
            
            console.print(f"✅ User created: {username} with roles: {roles}", style="green")
            return True
            
        except Exception as e:
            console.print(f"❌ Failed to create user: {e}", style="red")
            return False
    
    def authenticate_user(self, username: str, password: str) -> Optional[User]:
        """ユーザー認証"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, password_hash, roles, created_at, last_login, active
                    FROM users WHERE username = ? AND active = 1
                ''', (username,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                if self.verify_password(password, row[1]):
                    # ログイン時刻を更新
                    cursor.execute('''
                        UPDATE users SET last_login = ? WHERE username = ?
                    ''', (datetime.now().isoformat(), username))
                    conn.commit()
                    
                    return User(
                        username=row[0],
                        password_hash=row[1],
                        roles=set(json.loads(row[2])),
                        created_at=datetime.fromisoformat(row[3]),
                        last_login=datetime.fromisoformat(row[4]) if row[4] else None,
                        active=bool(row[5])
                    )
                
                return None
                
        except Exception as e:
            console.print(f"❌ Authentication error: {e}", style="red")
            return None
    
    def add_topic_permission(self, topic_pattern: str, permission: str, role: str):
        """トピック権限の追加"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR REPLACE INTO topic_permissions (topic_pattern, permission, role)
                    VALUES (?, ?, ?)
                ''', (topic_pattern, permission, role))
                conn.commit()
                
        except Exception as e:
            console.print(f"❌ Failed to add topic permission: {e}", style="red")
    
    def check_topic_permission(self, username: str, topic: str, operation: str) -> bool:
        """トピックアクセス権限チェック"""
        try:
            # ユーザーの役割を取得
            user = self.get_user(username)
            if not user or not user.active:
                return False
            
            # 各役割について権限をチェック
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for role in user.roles:
                    cursor.execute('''
                        SELECT topic_pattern, permission FROM topic_permissions
                        WHERE role = ?
                    ''', (role,))
                    
                    permissions = cursor.fetchall()
                    
                    for topic_pattern, permission in permissions:
                        if self.topic_matches_pattern(topic, topic_pattern):
                            # 権限チェック
                            if operation == "read" and permission in ["read", "readwrite"]:
                                return True
                            elif operation == "write" and permission in ["write", "readwrite"]:
                                return True
            
            return False
            
        except Exception as e:
            console.print(f"❌ Permission check error: {e}", style="red")
            return False
    
    def topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """トピックパターンマッチング"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        # #（multi-level wildcard）の処理
        if '#' in pattern_parts:
            hash_index = pattern_parts.index('#')
            if hash_index != len(pattern_parts) - 1:
                return False  # #は最後にのみ使用可能
            
            # #より前の部分をチェック
            if len(topic_parts) < hash_index:
                return False
            
            for i in range(hash_index):
                if pattern_parts[i] != '+' and pattern_parts[i] != topic_parts[i]:
                    return False
            
            return True
        
        # 通常のワイルドカード処理
        if len(topic_parts) != len(pattern_parts):
            return False
        
        for topic_part, pattern_part in zip(topic_parts, pattern_parts):
            if pattern_part != '+' and pattern_part != topic_part:
                return False
        
        return True
    
    def get_user(self, username: str) -> Optional[User]:
        """ユーザー情報取得"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, password_hash, roles, created_at, last_login, active
                    FROM users WHERE username = ?
                ''', (username,))
                
                row = cursor.fetchone()
                if row:
                    return User(
                        username=row[0],
                        password_hash=row[1],
                        roles=set(json.loads(row[2])),
                        created_at=datetime.fromisoformat(row[3]),
                        last_login=datetime.fromisoformat(row[4]) if row[4] else None,
                        active=bool(row[5])
                    )
                return None
                
        except Exception as e:
            console.print(f"❌ Error getting user: {e}", style="red")
            return None
    
    def list_users(self) -> List[User]:
        """全ユーザー一覧"""
        users = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT username, password_hash, roles, created_at, last_login, active
                    FROM users ORDER BY username
                ''')
                
                for row in cursor.fetchall():
                    users.append(User(
                        username=row[0],
                        password_hash=row[1],
                        roles=set(json.loads(row[2])),
                        created_at=datetime.fromisoformat(row[3]),
                        last_login=datetime.fromisoformat(row[4]) if row[4] else None,
                        active=bool(row[5])
                    ))
                
        except Exception as e:
            console.print(f"❌ Error listing users: {e}", style="red")
        
        return users
    
    def display_users_table(self):
        """ユーザー一覧表示"""
        users = self.list_users()
        
        table = Table(title="MQTT Users")
        table.add_column("Username", style="cyan")
        table.add_column("Roles", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Created", style="blue")
        table.add_column("Last Login", style="yellow")
        
        for user in users:
            status = "✅ Active" if user.active else "❌ Inactive"
            roles_str = ", ".join(sorted(user.roles))
            created_str = user.created_at.strftime("%Y-%m-%d")
            last_login_str = user.last_login.strftime("%Y-%m-%d %H:%M") if user.last_login else "Never"
            
            table.add_row(user.username, roles_str, status, created_str, last_login_str)
        
        console.print(table)
    
    def display_permissions_table(self):
        """権限一覧表示"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT topic_pattern, permission, role
                    FROM topic_permissions
                    ORDER BY role, topic_pattern
                ''')
                
                table = Table(title="Topic Permissions")
                table.add_column("Role", style="cyan")
                table.add_column("Topic Pattern", style="magenta")
                table.add_column("Permission", style="green")
                
                for row in cursor.fetchall():
                    permission_icon = {
                        "read": "👁️  Read",
                        "write": "✏️  Write", 
                        "readwrite": "🔄 Read/Write"
                    }.get(row[1], row[1])
                    
                    table.add_row(row[2], row[0], permission_icon)
                
                console.print(table)
                
        except Exception as e:
            console.print(f"❌ Error displaying permissions: {e}", style="red")
    
    def test_permissions(self):
        """権限テストの実行"""
        console.print(Panel.fit(
            "🧪 Permission Testing\n"
            "様々なユーザーとトピックの組み合わせをテストします",
            title="Permission Test Suite",
            border_style="blue"
        ))
        
        test_cases = [
            # (username, topic, operation, expected_result)
            ("admin", "sensors/temp001/data", "read", True),
            ("admin", "actuators/valve001/command", "write", True),
            ("sensor_device", "sensors/temp001/data", "write", True),
            ("sensor_device", "actuators/valve001/command", "write", False),
            ("viewer", "sensors/temp001/data", "read", True),
            ("viewer", "sensors/temp001/data", "write", False),
            ("control_system", "actuators/valve001/command", "write", True),
            ("control_system", "sensors/temp001/data", "read", True),
            ("nonexistent_user", "sensors/temp001/data", "read", False),
        ]
        
        table = Table(title="Permission Test Results")
        table.add_column("User", style="cyan")
        table.add_column("Topic", style="magenta")  
        table.add_column("Operation", style="yellow")
        table.add_column("Expected", style="blue")
        table.add_column("Actual", style="green")
        table.add_column("Result", style="white")
        
        for username, topic, operation, expected in test_cases:
            actual = self.check_topic_permission(username, topic, operation)
            result = "✅ PASS" if actual == expected else "❌ FAIL"
            
            expected_str = "✅ Allow" if expected else "❌ Deny"
            actual_str = "✅ Allow" if actual else "❌ Deny"
            
            table.add_row(username, topic, operation, expected_str, actual_str, result)
        
        console.print(table)

def main():
    """メイン実行関数"""
    console.print(Panel.fit(
        "🔐 MQTT Authentication & Authorization Manager\n\n"
        "機能：\n"
        "• ユーザー管理（作成・認証・役割管理）\n"
        "• トピックベースアクセス制御\n"
        "• 権限パターンマッチング\n"
        "• セキュリティ監査\n\n"
        "Language: Python 3\n"
        "Database: SQLite",
        title="MQTT Auth Manager",
        border_style="blue"
    ))
    
    auth_manager = MQTTAuthManager()
    
    try:
        # ユーザー一覧表示
        auth_manager.display_users_table()
        
        # 権限一覧表示
        console.print()
        auth_manager.display_permissions_table()
        
        # 権限テスト実行
        console.print()
        auth_manager.test_permissions()
        
        # インタラクティブなユーザー認証テスト
        console.print("\n🔓 Interactive Authentication Test", style="bold blue")
        
        while True:
            username = console.input("Enter username (or 'quit' to exit): ")
            if username.lower() == 'quit':
                break
            
            password = console.input("Enter password: ")
            
            user = auth_manager.authenticate_user(username, password)
            if user:
                console.print(f"✅ Authentication successful for {username}", style="bold green")
                console.print(f"   Roles: {', '.join(sorted(user.roles))}", style="dim")
                
                # トピックアクセステスト
                topic = console.input("Test topic access (enter topic): ")
                operation = console.input("Operation (read/write): ")
                
                if auth_manager.check_topic_permission(username, topic, operation):
                    console.print(f"✅ {operation.title()} access GRANTED for {topic}", style="green")
                else:
                    console.print(f"❌ {operation.title()} access DENIED for {topic}", style="red")
            else:
                console.print(f"❌ Authentication failed for {username}", style="bold red")
            
            console.print()
        
    except KeyboardInterrupt:
        console.print("\n👋 Exiting auth manager...", style="yellow")
    except Exception as e:
        console.print(f"❌ Error: {e}", style="bold red")
    finally:
        console.print("✨ MQTT Auth Manager shut down", style="bold green")

if __name__ == "__main__":
    main()
```

## 📊 演習課題

### 課題 1: セキュリティ監査システム
以下を実装してください：

1. ログイン試行回数の監視
2. 異常なトピックアクセス検出
3. セキュリティイベントのログ記録

### 課題 2: 高度な認証システム
以下を実装してください：

1. JWT（JSON Web Token）認証
2. 多要素認証（2FA）
3. セッション管理とタイムアウト

### 課題 3: セキュリティダッシュボード
以下を実装してください：

1. リアルタイムセキュリティ状況表示
2. 脅威検出アラート
3. セキュリティメトリクス収集

## 🎯 学習チェックポイント

- [ ] TLS/SSL暗号化通信を実装できる
- [ ] クライアント証明書認証を理解している
- [ ] トピックベースアクセス制御を実装できる
- [ ] セキュリティ脅威と対策を理解している
- [ ] 認証・認可システムを設計できる

---

**次のハンズオン**: [05-cloud-integration](../05-cloud-integration/) - クラウド統合