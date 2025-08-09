# セキュリティとベストプラクティス

## 6.1 MQTTセキュリティの脅威モデル

IoTシステムにおけるMQTTは、多様なセキュリティ脅威にさらされています。2025年現在の主要な脅威を理解することが重要です。

### 6.1.1 主要な脅威

| 脅威カテゴリ | 具体的な攻撃 | 影響 | 対策レベル |
|-------------|-------------|------|-----------|
| **盗聴** | パケットキャプチャ、中間者攻撃 | データ漏洩 | 高 |
| **なりすまし** | 偽のクライアント/ブローカー | データ改竄、システム乗っ取り | 高 |
| **DoS攻撃** | メッセージフラッド、接続フラッド | サービス停止 | 中 |
| **Topic Hijacking** | 不正なトピック購読/発行 | データ窃取、システム制御 | 高 |
| **Replay攻撃** | 過去のメッセージ再送 | 不正操作の実行 | 中 |
| **Session Hijacking** | セッション乗っ取り | システムへの不正アクセス | 高 |

### 6.1.2 2025年の新しい脅威

#### IoT Botnets
```
攻撃シナリオ:
1. 脆弱なIoTデバイスに侵入
2. MQTTブローカーへの認証情報を窃取
3. 大量のデバイスを制御下に置く
4. DDoS攻撃やデータ窃取に利用
```

#### AI/ML-Based Attacks
```
機械学習を使用した攻撃:
- パターン分析による認証情報の推測
- トラフィック分析による機密データの特定
- 行動分析による正当ユーザーのなりすまし
```

## 6.2 トランスポートレベルセキュリティ

### 6.2.1 TLS/SSL実装

**基本的なTLS接続:**
```javascript
const mqtt = require('mqtt');
const fs = require('fs');

const client = mqtt.connect('mqtts://secure-broker.example.com:8883', {
    // TLS設定
    protocol: 'mqtts',
    rejectUnauthorized: true,  // 証明書検証を有効
    
    // CA証明書（ルート証明書）
    ca: fs.readFileSync('./ca-certificate.pem'),
    
    // クライアント証明書認証（オプション）
    cert: fs.readFileSync('./client-certificate.pem'),
    key: fs.readFileSync('./client-private-key.pem'),
    
    // TLSバージョンの指定
    secureProtocol: 'TLSv1_2_method'
});
```

**Python実装例:**
```python
import ssl
import paho.mqtt.client as mqtt

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        print("Secure connection established")
    else:
        print(f"Connection failed: {rc}")

client = mqtt.Client()
client.on_connect = on_connect

# TLS設定
context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
context.check_hostname = False  # 必要に応じて
context.verify_mode = ssl.CERT_REQUIRED

# CA証明書の読み込み
context.load_verify_locations("ca-certificate.pem")

# クライアント証明書（相互認証）
context.load_cert_chain("client-certificate.pem", "client-private-key.pem")

client.tls_set_context(context)

# セキュアポートで接続
client.connect("secure-broker.example.com", 8883, 60)
```

### 6.2.2 証明書管理のベストプラクティス

#### 証明書階層の設計

```
Root CA (オフライン保管)
    ├── Intermediate CA (ブローカー用)
    │   ├── Broker Certificate
    │   └── Broker Certificate (バックアップ)
    └── Intermediate CA (デバイス用)
        ├── Device Certificate 1
        ├── Device Certificate 2
        └── ...
```

#### 証明書ローテーション自動化

```python
import datetime
import subprocess
from cryptography import x509
from cryptography.hazmat.primitives import hashes

class CertificateManager:
    def __init__(self, cert_path, key_path, ca_path):
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        
    def check_expiration(self, days_ahead=30):
        """証明書の期限チェック"""
        with open(self.cert_path, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read())
            
        expiry_date = cert.not_valid_after
        warning_date = datetime.datetime.now() + datetime.timedelta(days=days_ahead)
        
        if expiry_date <= warning_date:
            return True, expiry_date
        return False, expiry_date
        
    def renew_certificate(self):
        """証明書の更新"""
        # Let's Encrypt ACMEクライアントを使用
        try:
            subprocess.run([
                'certbot', 'renew',
                '--cert-name', 'mqtt-broker',
                '--force-renewal'
            ], check=True)
            
            # MQTTブローカーの再起動
            self.restart_broker()
            return True
        except subprocess.CalledProcessError as e:
            print(f"Certificate renewal failed: {e}")
            return False
            
    def restart_broker(self):
        """ブローカーの再起動"""
        subprocess.run(['systemctl', 'restart', 'mosquitto'])
```

## 6.3 認証と認可

### 6.3.1 Username/Password認証

**Mosquittoでのユーザー管理:**
```bash
# パスワードファイルの作成
mosquitto_passwd -c /etc/mosquitto/passwd device001
# Password: [入力]

# 追加ユーザー
mosquitto_passwd /etc/mosquitto/passwd device002

# 設定ファイル更新
echo "password_file /etc/mosquitto/passwd" >> /etc/mosquitto/mosquitto.conf
echo "allow_anonymous false" >> /etc/mosquitto/mosquitto.conf
```

**動的ユーザー管理API:**
```python
import hashlib
import secrets
from typing import Dict, Optional

class MQTTUserManager:
    def __init__(self, password_file_path: str):
        self.password_file = password_file_path
        self.users: Dict[str, str] = {}
        self.load_users()
        
    def load_users(self):
        """既存ユーザーの読み込み"""
        try:
            with open(self.password_file, 'r') as f:
                for line in f:
                    if ':' in line:
                        username, password_hash = line.strip().split(':', 1)
                        self.users[username] = password_hash
        except FileNotFoundError:
            pass
            
    def add_user(self, username: str, password: str) -> bool:
        """新規ユーザー追加"""
        if username in self.users:
            return False
            
        # Mosquitto形式のハッシュ生成
        salt = secrets.token_bytes(12)
        password_hash = self._generate_hash(password, salt)
        
        self.users[username] = password_hash
        self.save_users()
        return True
        
    def _generate_hash(self, password: str, salt: bytes) -> str:
        """Mosquitto互換のハッシュ生成"""
        import base64
        
        # PBKDF2を使用（Mosquitto 2.0+）
        from hashlib import pbkdf2_hmac
        hash_bytes = pbkdf2_hmac('sha512', password.encode(), salt, 101)
        
        # Base64エンコード
        salt_b64 = base64.b64encode(salt).decode()
        hash_b64 = base64.b64encode(hash_bytes).decode()
        
        return f"$7${salt_b64}${hash_b64}"
        
    def revoke_user(self, username: str) -> bool:
        """ユーザーの削除"""
        if username in self.users:
            del self.users[username]
            self.save_users()
            return True
        return False
        
    def save_users(self):
        """ユーザー情報の保存"""
        with open(self.password_file, 'w') as f:
            for username, password_hash in self.users.items():
                f.write(f"{username}:{password_hash}\n")
```

### 6.3.2 OAuth 2.0 / JWT認証

**JWT Token認証実装:**
```javascript
const jwt = require('jsonwebtoken');
const mqtt = require('mqtt');

class JWTMQTTClient {
    constructor(brokerUrl, clientCredentials) {
        this.brokerUrl = brokerUrl;
        this.clientId = clientCredentials.clientId;
        this.clientSecret = clientCredentials.clientSecret;
        this.tokenEndpoint = clientCredentials.tokenEndpoint;
        this.accessToken = null;
        this.client = null;
    }
    
    async getAccessToken() {
        const response = await fetch(this.tokenEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
            },
            body: `grant_type=client_credentials&client_id=${this.clientId}&client_secret=${this.clientSecret}`
        });
        
        const data = await response.json();
        this.accessToken = data.access_token;
        return this.accessToken;
    }
    
    async connect() {
        if (!this.accessToken) {
            await this.getAccessToken();
        }
        
        return new Promise((resolve, reject) => {
            this.client = mqtt.connect(this.brokerUrl, {
                username: 'oauth2',
                password: this.accessToken,
                clientId: this.clientId
            });
            
            this.client.on('connect', () => {
                console.log('Connected with JWT authentication');
                resolve();
            });
            
            this.client.on('error', (err) => {
                if (err.message.includes('authentication')) {
                    // トークン期限切れの可能性
                    this.refreshTokenAndReconnect();
                } else {
                    reject(err);
                }
            });
        });
    }
    
    async refreshTokenAndReconnect() {
        try {
            await this.getAccessToken();
            this.client.end();
            await this.connect();
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
    }
}

// 使用例
const client = new JWTMQTTClient('mqtts://broker.example.com:8883', {
    clientId: 'iot-device-001',
    clientSecret: 'your-client-secret',
    tokenEndpoint: 'https://auth.example.com/oauth2/token'
});

await client.connect();
```

### 6.3.3 X.509証明書認証

**クライアント証明書生成スクリプト:**
```bash
#!/bin/bash
# IoTデバイス用証明書生成スクリプト

DEVICE_ID=$1
if [ -z "$DEVICE_ID" ]; then
    echo "Usage: $0 <device_id>"
    exit 1
fi

# デバイス用秘密鍵生成
openssl genrsa -out ${DEVICE_ID}.key 2048

# 証明書署名要求（CSR）生成
openssl req -new \
    -key ${DEVICE_ID}.key \
    -out ${DEVICE_ID}.csr \
    -subj "/CN=${DEVICE_ID}/O=MyIoTCompany/C=JP"

# CA署名で証明書生成
openssl x509 -req \
    -in ${DEVICE_ID}.csr \
    -CA ca.crt \
    -CAkey ca.key \
    -CAcreateserial \
    -out ${DEVICE_ID}.crt \
    -days 365 \
    -extensions v3_req \
    -extfile <(echo -e "basicConstraints=CA:FALSE\nkeyUsage=digitalSignature,keyEncipherment\nsubjectAltName=DNS:${DEVICE_ID}")

echo "Certificate generated for device: ${DEVICE_ID}"
```

**証明書ベース認証の実装:**
```python
import ssl
import paho.mqtt.client as mqtt
from cryptography import x509
from cryptography.hazmat.primitives import serialization

class X509MQTTClient:
    def __init__(self, broker_host, broker_port, cert_file, key_file, ca_file):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.cert_file = cert_file
        self.key_file = key_file
        self.ca_file = ca_file
        
        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("Certificate authentication successful")
            # 証明書からデバイスIDを取得してトピック設定
            device_id = self.extract_device_id()
            client.subscribe(f"devices/{device_id}/commands")
        else:
            print(f"Authentication failed: {rc}")
            
    def extract_device_id(self):
        """証明書からデバイスIDを抽出"""
        with open(self.cert_file, 'rb') as f:
            cert = x509.load_pem_x509_certificate(f.read())
            
        # Common Nameからデバイス ID取得
        for attribute in cert.subject:
            if attribute.oid == x509.NameOID.COMMON_NAME:
                return attribute.value
        return "unknown"
        
    def connect_secure(self):
        # SSL/TLS設定
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.load_verify_locations(self.ca_file)
        context.load_cert_chain(self.cert_file, self.key_file)
        
        self.client.tls_set_context(context)
        self.client.connect(self.broker_host, self.broker_port, 60)
        self.client.loop_forever()
        
    def on_message(self, client, userdata, msg):
        print(f"Received command: {msg.payload.decode()}")
```

## 6.4 アクセス制御とトピック認可

### 6.4.1 ACL（Access Control List）設計

**階層的トピック設計:**
```
organization/location/device_type/device_id/metric

例:
acme/tokyo/sensor/temp001/temperature
acme/tokyo/sensor/temp001/humidity
acme/tokyo/actuator/valve001/status
acme/tokyo/actuator/valve001/commands
```

**Mosquitto ACL設定:**
```
# /etc/mosquitto/acl.conf

# 管理者グループ
user admin
topic readwrite #

# センサーデバイス（読み書き制限）
pattern readwrite acme/+/sensor/%c/#
pattern read acme/+/actuator/+/status

# アクチュエーターデバイス
pattern readwrite acme/+/actuator/%c/#
pattern read acme/+/sensor/+/temperature

# アプリケーション（全体監視）
user monitoring_app
topic read acme/+/+/+/temperature
topic read acme/+/+/+/status

# デバイス固有のアクセス
user temp001
topic readwrite acme/tokyo/sensor/temp001/#

user valve001  
topic readwrite acme/tokyo/actuator/valve001/#
```

### 6.4.2 動的ACL管理

```python
import json
import sqlite3
from typing import List, Dict, Optional

class DynamicACLManager:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
        
    def init_database(self):
        """データベーステーブルの初期化"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS acl_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                topic_pattern TEXT NOT NULL,
                permission TEXT CHECK(permission IN ('read', 'write', 'readwrite')),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                UNIQUE(username, topic_pattern)
            )
        ''')
        
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_username ON acl_rules(username);
        ''')
        
        conn.commit()
        conn.close()
        
    def add_rule(self, username: str, topic_pattern: str, permission: str, expires_at: Optional[str] = None) -> bool:
        """ACL ルールの追加"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO acl_rules 
                (username, topic_pattern, permission, expires_at)
                VALUES (?, ?, ?, ?)
            ''', (username, topic_pattern, permission, expires_at))
            
            conn.commit()
            self.generate_acl_file()  # ACLファイル再生成
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()
            
    def revoke_rule(self, username: str, topic_pattern: str = None) -> bool:
        """ACL ルールの削除"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            if topic_pattern:
                cursor.execute('''
                    DELETE FROM acl_rules 
                    WHERE username = ? AND topic_pattern = ?
                ''', (username, topic_pattern))
            else:
                # ユーザーの全ルール削除
                cursor.execute('''
                    DELETE FROM acl_rules WHERE username = ?
                ''', (username,))
                
            conn.commit()
            self.generate_acl_file()
            return True
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            return False
        finally:
            conn.close()
            
    def generate_acl_file(self):
        """Mosquitto ACLファイルの生成"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 期限切れルールの削除
        cursor.execute('''
            DELETE FROM acl_rules 
            WHERE expires_at IS NOT NULL AND expires_at < datetime('now')
        ''')
        
        # 有効なルールの取得
        cursor.execute('''
            SELECT username, topic_pattern, permission
            FROM acl_rules
            WHERE expires_at IS NULL OR expires_at > datetime('now')
            ORDER BY username, topic_pattern
        ''')
        
        rules = cursor.fetchall()
        
        # ACLファイル生成
        with open('/etc/mosquitto/dynamic.acl', 'w') as f:
            current_user = None
            for username, topic_pattern, permission in rules:
                if username != current_user:
                    f.write(f"\nuser {username}\n")
                    current_user = username
                f.write(f"topic {permission} {topic_pattern}\n")
                
        conn.close()
        
        # Mosquitto設定リロード
        import subprocess
        subprocess.run(['mosquitto_pub', '-h', 'localhost', '-t', '$SYS/broker/config/reload', '-m', ''])

# 使用例
acl_manager = DynamicACLManager('/var/lib/mosquitto/acl.db')

# センサーデバイスのルール追加
acl_manager.add_rule('sensor001', 'data/sensors/sensor001/#', 'readwrite')
acl_manager.add_rule('sensor001', 'config/sensors/sensor001', 'read')

# 一時的な管理者権限（1時間）
from datetime import datetime, timedelta
expires = datetime.now() + timedelta(hours=1)
acl_manager.add_rule('temp_admin', '#', 'readwrite', expires.isoformat())
```

## 6.5 ペイロード暗号化

### 6.5.1 AES暗号化実装

```javascript
const crypto = require('crypto');

class PayloadEncryption {
    constructor(encryptionKey) {
        this.algorithm = 'aes-256-gcm';
        this.key = Buffer.from(encryptionKey, 'hex');
    }
    
    encrypt(plaintext) {
        const iv = crypto.randomBytes(16);
        const cipher = crypto.createCipher(this.algorithm, this.key, iv);
        
        let encrypted = cipher.update(plaintext, 'utf8', 'hex');
        encrypted += cipher.final('hex');
        
        const authTag = cipher.getAuthTag();
        
        return {
            encrypted: encrypted,
            iv: iv.toString('hex'),
            authTag: authTag.toString('hex')
        };
    }
    
    decrypt(encryptedData) {
        const decipher = crypto.createDecipher(
            this.algorithm, 
            this.key, 
            Buffer.from(encryptedData.iv, 'hex')
        );
        
        decipher.setAuthTag(Buffer.from(encryptedData.authTag, 'hex'));
        
        let decrypted = decipher.update(encryptedData.encrypted, 'hex', 'utf8');
        decrypted += decipher.final('utf8');
        
        return decrypted;
    }
}

// 使用例
const encryption = new PayloadEncryption('your-256-bit-key-in-hex');

// センサーデータ暗号化
const sensorData = JSON.stringify({
    temperature: 23.5,
    humidity: 45.2,
    timestamp: Date.now()
});

const encryptedPayload = encryption.encrypt(sensorData);

client.publish('sensors/encrypted/data', JSON.stringify(encryptedPayload), {
    qos: 1
});

// 受信側での復号化
client.on('message', (topic, message) => {
    if (topic.includes('/encrypted/')) {
        const encryptedData = JSON.parse(message.toString());
        const decryptedData = encryption.decrypt(encryptedData);
        const sensorData = JSON.parse(decryptedData);
        console.log('Decrypted data:', sensorData);
    }
});
```

### 6.5.2 End-to-End暗号化

```python
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os
import json

class E2EEncryption:
    def __init__(self, password: str):
        """パスワードベースの暗号化キー生成"""
        salt = os.urandom(16)
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        self.cipher = Fernet(key)
        self.salt = salt
        
    def encrypt_message(self, message: dict) -> str:
        """メッセージの暗号化"""
        plaintext = json.dumps(message)
        encrypted = self.cipher.encrypt(plaintext.encode())
        
        # salt + encrypted dataのフォーマット
        payload = {
            'salt': base64.b64encode(self.salt).decode(),
            'data': base64.b64encode(encrypted).decode(),
            'version': '1.0'
        }
        
        return json.dumps(payload)
        
    def decrypt_message(self, encrypted_payload: str) -> dict:
        """メッセージの復号化"""
        payload = json.loads(encrypted_payload)
        
        if payload['version'] != '1.0':
            raise ValueError("Unsupported encryption version")
            
        encrypted_data = base64.b64decode(payload['data'])
        decrypted = self.cipher.decrypt(encrypted_data)
        
        return json.loads(decrypted.decode())

# デバイス間暗号化通信の実装
class SecureMQTTDevice:
    def __init__(self, device_id: str, shared_secret: str, mqtt_client):
        self.device_id = device_id
        self.encryption = E2EEncryption(shared_secret)
        self.client = mqtt_client
        
    def send_secure_message(self, target_device: str, message: dict):
        """暗号化メッセージ送信"""
        encrypted_payload = self.encryption.encrypt_message({
            'from': self.device_id,
            'to': target_device,
            'timestamp': int(time.time()),
            'data': message
        })
        
        topic = f'secure/{target_device}/inbox'
        self.client.publish(topic, encrypted_payload, qos=1)
        
    def handle_secure_message(self, topic: str, encrypted_payload: str):
        """暗号化メッセージ受信処理"""
        try:
            decrypted_message = self.encryption.decrypt_message(encrypted_payload)
            
            # メッセージ検証
            if decrypted_message['to'] != self.device_id:
                print("Message not intended for this device")
                return
                
            # タイムスタンプ検証（リプレイ攻撃防止）
            message_time = decrypted_message['timestamp']
            current_time = int(time.time())
            
            if abs(current_time - message_time) > 300:  # 5分以内
                print("Message timestamp too old, possible replay attack")
                return
                
            # メッセージ処理
            self.process_message(decrypted_message)
            
        except Exception as e:
            print(f"Failed to decrypt message: {e}")
            
    def process_message(self, message: dict):
        """復号化済みメッセージの処理"""
        print(f"Secure message from {message['from']}: {message['data']}")
```

## 6.6 セキュリティ監視とログ

### 6.6.1 セキュリティイベント監視

```python
import re
import json
from datetime import datetime
from collections import defaultdict
import threading
import time

class MQTTSecurityMonitor:
    def __init__(self):
        self.failed_attempts = defaultdict(list)
        self.suspicious_patterns = {
            'topic_enumeration': re.compile(r'[/#*+]{3,}'),
            'sql_injection': re.compile(r'(union|select|insert|delete|drop|script)', re.IGNORECASE),
            'command_injection': re.compile(r'[;&|`$]'),
            'large_payload': lambda x: len(x) > 65536  # 64KB
        }
        self.rate_limits = {
            'connection_per_ip': 10,  # per minute
            'publish_per_client': 100,  # per minute
            'subscribe_per_client': 20  # per minute
        }
        
    def monitor_authentication(self, client_ip: str, username: str, success: bool):
        """認証監視"""
        current_time = datetime.now()
        
        if not success:
            self.failed_attempts[client_ip].append(current_time)
            
            # 1分以内の失敗回数をチェック
            recent_failures = [
                t for t in self.failed_attempts[client_ip]
                if (current_time - t).seconds < 60
            ]
            
            if len(recent_failures) >= 5:
                self.trigger_alert('BRUTE_FORCE_ATTACK', {
                    'client_ip': client_ip,
                    'username': username,
                    'failure_count': len(recent_failures)
                })
                
                # IP一時ブロック
                self.block_ip_temporarily(client_ip)
        else:
            # 成功時は失敗履歴をクリア
            self.failed_attempts[client_ip].clear()
            
    def monitor_topic_access(self, client_id: str, topic: str, action: str):
        """トピックアクセス監視"""
        # 疑わしいトピックパターンの検査
        for pattern_name, pattern in self.suspicious_patterns.items():
            if isinstance(pattern, re.Pattern):
                if pattern.search(topic):
                    self.trigger_alert('SUSPICIOUS_TOPIC_PATTERN', {
                        'client_id': client_id,
                        'topic': topic,
                        'pattern': pattern_name,
                        'action': action
                    })
                    
    def monitor_payload(self, client_id: str, topic: str, payload: bytes):
        """ペイロード監視"""
        payload_str = payload.decode('utf-8', errors='ignore')
        
        # 大きなペイロードの検出
        if self.suspicious_patterns['large_payload'](payload):
            self.trigger_alert('LARGE_PAYLOAD', {
                'client_id': client_id,
                'topic': topic,
                'payload_size': len(payload)
            })
            
        # 疑わしいコンテンツの検出
        for pattern_name, pattern in self.suspicious_patterns.items():
            if isinstance(pattern, re.Pattern) and pattern.search(payload_str):
                self.trigger_alert('MALICIOUS_PAYLOAD', {
                    'client_id': client_id,
                    'topic': topic,
                    'pattern': pattern_name,
                    'payload_preview': payload_str[:200]
                })
                
    def trigger_alert(self, alert_type: str, details: dict):
        """セキュリティアラートの発生"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'type': alert_type,
            'severity': self.get_severity(alert_type),
            'details': details
        }
        
        print(f"SECURITY ALERT: {json.dumps(alert, indent=2)}")
        
        # 外部SIEM/ログシステムへ送信
        self.send_to_siem(alert)
        
    def get_severity(self, alert_type: str) -> str:
        """アラートの重要度判定"""
        severity_map = {
            'BRUTE_FORCE_ATTACK': 'HIGH',
            'SUSPICIOUS_TOPIC_PATTERN': 'MEDIUM',
            'MALICIOUS_PAYLOAD': 'HIGH',
            'LARGE_PAYLOAD': 'LOW'
        }
        return severity_map.get(alert_type, 'MEDIUM')
        
    def block_ip_temporarily(self, ip: str, duration: int = 300):
        """IP一時ブロック（5分間）"""
        # iptablesルールの追加
        import subprocess
        subprocess.run([
            'iptables', '-A', 'INPUT', 
            '-s', ip, '-p', 'tcp', '--dport', '1883', 
            '-j', 'DROP'
        ])
        
        # 指定時間後にブロック解除
        threading.Timer(duration, self.unblock_ip, args=[ip]).start()
        
    def unblock_ip(self, ip: str):
        """IPブロック解除"""
        import subprocess
        subprocess.run([
            'iptables', '-D', 'INPUT', 
            '-s', ip, '-p', 'tcp', '--dport', '1883', 
            '-j', 'DROP'
        ])
        
    def send_to_siem(self, alert: dict):
        """SIEM システムへアラート送信"""
        # Elasticsearch, Splunk, Azure Sentinel等への送信
        pass
```

### 6.6.2 ログ分析とフォレンジック

```python
import json
import gzip
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt

class MQTTLogAnalyzer:
    def __init__(self, log_file_path: str):
        self.log_file = log_file_path
        
    def parse_mosquitto_logs(self, start_date: datetime, end_date: datetime):
        """Mosquittoログの解析"""
        events = []
        
        with open(self.log_file, 'r') as f:
            for line in f:
                if 'Client' in line:
                    event = self.parse_log_line(line)
                    if event and start_date <= event['timestamp'] <= end_date:
                        events.append(event)
                        
        return pd.DataFrame(events)
        
    def parse_log_line(self, line: str) -> dict:
        """ログ行の解析"""
        # Mosquittoログフォーマット解析
        patterns = {
            'connection': r'(\d{10}): New connection from ([\d.]+) on port (\d+)',
            'authentication': r'(\d{10}): Client ([^\s]+) .*(disconnected|connected)',
            'publish': r'(\d{10}): Received PUBLISH from ([^\s]+) .* \((\d+) bytes\)',
            'subscribe': r'(\d{10}): Received SUBSCRIBE from ([^\s]+)'
        }
        
        for event_type, pattern in patterns.items():
            match = re.search(pattern, line)
            if match:
                return {
                    'timestamp': datetime.fromtimestamp(int(match.group(1))),
                    'event_type': event_type,
                    'details': match.groups()
                }
        return None
        
    def analyze_connection_patterns(self, df: pd.DataFrame):
        """接続パターン分析"""
        # 時間別接続数
        hourly_connections = df[df['event_type'] == 'connection'].groupby(
            df['timestamp'].dt.hour
        ).size()
        
        # 異常な接続パターンの検出
        avg_connections = hourly_connections.mean()
        std_connections = hourly_connections.std()
        anomalies = hourly_connections[
            hourly_connections > avg_connections + 3 * std_connections
        ]
        
        if not anomalies.empty:
            print("Anomalous connection patterns detected:")
            print(anomalies)
            
        return hourly_connections, anomalies
        
    def detect_data_exfiltration(self, df: pd.DataFrame):
        """データ漏洩の検出"""
        publish_events = df[df['event_type'] == 'publish']
        
        # 大量データ転送の検出
        large_transfers = publish_events[
            publish_events['details'].str[2].astype(int) > 10000  # 10KB以上
        ]
        
        # 異常な時間帯での活動
        night_activity = publish_events[
            (publish_events['timestamp'].dt.hour < 6) | 
            (publish_events['timestamp'].dt.hour > 22)
        ]
        
        return large_transfers, night_activity
        
    def generate_security_report(self, start_date: datetime, end_date: datetime):
        """セキュリティレポート生成"""
        df = self.parse_mosquitto_logs(start_date, end_date)
        
        report = {
            'period': f"{start_date} to {end_date}",
            'total_events': len(df),
            'unique_clients': df['details'].str[1].nunique(),
            'connection_analysis': self.analyze_connection_patterns(df),
            'data_exfiltration': self.detect_data_exfiltration(df)
        }
        
        # レポートの保存
        with open(f'security_report_{start_date.date()}.json', 'w') as f:
            json.dump(report, f, indent=2, default=str)
            
        return report
```

## 参考リンク

- [MQTT Security Fundamentals - HiveMQ](https://www.hivemq.com/mqtt-security-fundamentals/)
- [OWASP IoT Security Top 10](https://owasp.org/www-project-internet-of-things/)
- [TLS Best Practices for MQTT](https://docs.oasis-open.org/mqtt/mqtt/v5.0/os/mqtt-v5.0-os.html#_Toc3901227)
- [AWS IoT Core Security](https://docs.aws.amazon.com/iot/latest/developerguide/security.html)
- [Eclipse Mosquitto Security](https://mosquitto.org/documentation/security/)

---

**次の章**: [07-mqtt5-features.md](07-mqtt5-features.md) - MQTT 5.0の新機能