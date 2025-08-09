# ハンズオン 08: クラウド連携

## 🎯 学習目標

このハンズオンでは主要クラウドサービスとのMQTT連携について学習します：

- AWS IoT Core との連携実装
- Azure IoT Hub での双方向通信
- Google Cloud IoT Core の活用
- クラウドストレージとの連携
- リアルタイムデータ分析パイプライン構築
- マルチクラウド対応アーキテクチャ
- セキュリティベストプラクティス

**所要時間**: 約150分

## 📋 前提条件

- [07-mqtt5-advanced-features](../07-mqtt5-advanced-features/) の完了
- 各クラウドサービスのアカウント（学習用）
- デバイス証明書の基本理解
- JSON形式でのデータ構造理解

## ☁️ クラウドIoTアーキテクチャ

### 典型的なクラウドIoTシステム構成

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   IoT Devices   │───▶│  MQTT Broker    │───▶│  Cloud Services │
│                 │    │  (Cloud)        │    │                 │
│ • Sensors       │    │                 │    │ • Data Storage  │
│ • Actuators     │    │ • AWS IoT Core  │    │ • Analytics     │
│ • Gateways      │    │ • Azure IoT Hub │    │ • ML/AI         │
│                 │    │ • Google Cloud  │    │ • Dashboards    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                ▲
                                │
┌─────────────────┐            │
│ Edge Computing  │────────────┘
│                 │
│ • Local MQTT    │
│ • Data Filtering│
│ • Offline Cache │
└─────────────────┘
```

## 📝 実装演習

### Exercise 1: AWS IoT Core 連携

`src/aws_iot_integration.py` を作成：

```python
import boto3
import json
import time
import ssl
import socket
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Callable, List
import paho.mqtt.client as mqtt
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import track
import uuid
import threading
from pathlib import Path

console = Console()

class AWSIoTClient:
    """AWS IoT Core 統合クライアント"""
    
    def __init__(self,
                 endpoint: str,
                 root_ca_path: str,
                 certificate_path: str,
                 private_key_path: str,
                 thing_name: str,
                 region: str = 'us-west-2'):
        """
        AWS IoT Core クライアント初期化
        
        Args:
            endpoint: AWS IoT Core エンドポイント
            root_ca_path: Amazon Root CA証明書のパス
            certificate_path: デバイス証明書のパス
            private_key_path: デバイス秘密鍵のパス
            thing_name: Thing名（デバイス名）
            region: AWS リージョン
        """
        self.endpoint = endpoint
        self.root_ca_path = root_ca_path
        self.certificate_path = certificate_path
        self.private_key_path = private_key_path
        self.thing_name = thing_name
        self.region = region
        
        # MQTT クライアント設定
        self.client = mqtt.Client(client_id=thing_name)
        self.is_connected = False
        self.device_shadow_callbacks = {}
        
        # AWS SDK クライアント（管理用）
        self.iot_client = boto3.client('iot', region_name=region)
        self.iot_data_client = boto3.client('iot-data', region_name=region)
        
        self.setup_mqtt_client()
    
    def setup_mqtt_client(self):
        """MQTT クライアントのセットアップ"""
        # SSL/TLS 設定
        context = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_REQUIRED
        
        context.load_verify_locations(self.root_ca_path)
        context.load_cert_chain(self.certificate_path, self.private_key_path)
        
        self.client.tls_set_context(context=context)
        
        # コールバック設定
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            self.is_connected = True
            console.print("✅ AWS IoT Core に接続しました", style="bold green")
            console.print(f"   Thing Name: {self.thing_name}", style="blue")
            console.print(f"   Endpoint: {self.endpoint}", style="blue")
            
            # Device Shadow トピックに購読
            shadow_topics = [
                f"$aws/things/{self.thing_name}/shadow/update/accepted",
                f"$aws/things/{self.thing_name}/shadow/update/rejected",
                f"$aws/things/{self.thing_name}/shadow/get/accepted",
                f"$aws/things/{self.thing_name}/shadow/get/rejected",
                f"$aws/things/{self.thing_name}/shadow/update/delta"
            ]
            
            for topic in shadow_topics:
                client.subscribe(topic)
                console.print(f"📥 購読: {topic}", style="dim")
                
        else:
            console.print(f"❌ AWS IoT Core 接続失敗: {rc}", style="bold red")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        topic = msg.topic
        try:
            payload = json.loads(msg.payload.decode('utf-8'))
        except json.JSONDecodeError:
            payload = msg.payload.decode('utf-8')
        
        console.print(f"📬 AWS IoT メッセージ受信", style="cyan")
        console.print(f"   Topic: {topic}", style="blue")
        
        # Device Shadow メッセージの処理
        if '/shadow/' in topic:
            self._handle_shadow_message(topic, payload)
        else:
            console.print(f"   Payload: {payload}", style="green")
    
    def on_publish(self, client, userdata, mid):
        """メッセージ送信完了時のコールバック"""
        console.print(f"✅ AWS IoT メッセージ送信完了 (MID: {mid})", style="green")
    
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        self.is_connected = False
        if rc != 0:
            console.print("⚠️  AWS IoT Core から予期しない切断", style="yellow")
        else:
            console.print("👋 AWS IoT Core から切断しました", style="blue")
    
    def connect(self) -> bool:
        """AWS IoT Core に接続"""
        try:
            console.print(f"🔌 AWS IoT Core 接続中...", style="blue")
            self.client.connect(self.endpoint, 8883, 60)
            self.client.loop_start()
            
            # 接続完了まで待機
            timeout = 15
            start_time = time.time()
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.5)
            
            return self.is_connected
            
        except Exception as e:
            console.print(f"❌ AWS IoT Core 接続エラー: {e}", style="bold red")
            return False
    
    def publish_telemetry(self, data: Dict[str, Any], custom_topic: str = None) -> bool:
        """テレメトリデータを送信"""
        topic = custom_topic or f"device/{self.thing_name}/telemetry"
        
        # タイムスタンプを追加
        telemetry_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'thing_name': self.thing_name,
            'data': data
        }
        
        try:
            payload = json.dumps(telemetry_data)
            result = self.client.publish(topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                console.print(f"📤 テレメトリ送信: {topic}", style="green")
                return True
            else:
                console.print(f"❌ テレメトリ送信失敗: {result.rc}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ テレメトリ送信例外: {e}", style="red")
            return False
    
    def update_device_shadow(self, desired_state: Dict[str, Any], reported_state: Dict[str, Any] = None) -> bool:
        """Device Shadow を更新"""
        shadow_topic = f"$aws/things/{self.thing_name}/shadow/update"
        
        shadow_update = {
            'state': {}
        }
        
        if desired_state:
            shadow_update['state']['desired'] = desired_state
        
        if reported_state:
            shadow_update['state']['reported'] = reported_state
        
        try:
            payload = json.dumps(shadow_update)
            result = self.client.publish(shadow_topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                console.print("🌟 Device Shadow 更新送信完了", style="green")
                return True
            else:
                console.print(f"❌ Shadow 更新失敗: {result.rc}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Shadow 更新例外: {e}", style="red")
            return False
    
    def get_device_shadow(self) -> bool:
        """Device Shadow の現在の状態を取得"""
        shadow_topic = f"$aws/things/{self.thing_name}/shadow/get"
        
        try:
            result = self.client.publish(shadow_topic, "", qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            console.print(f"❌ Shadow 取得エラー: {e}", style="red")
            return False
    
    def _handle_shadow_message(self, topic: str, payload: Dict[str, Any]):
        """Device Shadow メッセージの処理"""
        console.print(f"🌟 Device Shadow メッセージ: {topic.split('/')[-1]}", style="magenta")
        
        if 'update/accepted' in topic:
            console.print("   Shadow 更新が受諾されました", style="green")
            if 'state' in payload and 'desired' in payload['state']:
                desired_state = payload['state']['desired']
                console.print(f"   Desired State: {desired_state}", style="blue")
        
        elif 'update/rejected' in topic:
            console.print("   Shadow 更新が拒否されました", style="red")
            if 'message' in payload:
                console.print(f"   Error: {payload['message']}", style="red")
        
        elif 'get/accepted' in topic:
            console.print("   Shadow 状態取得成功", style="green")
            if 'state' in payload:
                state = payload['state']
                if 'desired' in state:
                    console.print(f"   Desired: {state['desired']}", style="blue")
                if 'reported' in state:
                    console.print(f"   Reported: {state['reported']}", style="green")
        
        elif 'update/delta' in topic:
            console.print("   Shadow Delta 受信", style="yellow")
            if 'state' in payload:
                delta_state = payload['state']
                console.print(f"   Delta: {delta_state}", style="yellow")
                
                # Delta に基づいてデバイス状態を更新
                self._handle_shadow_delta(delta_state)
    
    def _handle_shadow_delta(self, delta_state: Dict[str, Any]):
        """Shadow Delta の処理（デバイス状態変更）"""
        console.print("🔄 Shadow Delta に基づいてデバイス状態を更新中...", style="yellow")
        
        # 実際のデバイス制御をシミュレート
        reported_state = {}
        for key, value in delta_state.items():
            console.print(f"   {key} を {value} に設定", style="dim")
            reported_state[key] = value
            time.sleep(0.5)  # デバイス制御の遅延をシミュレート
        
        # 実際の状態をShadowに報告
        self.update_device_shadow(desired_state=None, reported_state=reported_state)
    
    def subscribe_to_commands(self, callback: Callable[[str, Dict[str, Any]], None]):
        """コマンド受信用トピックに購読"""
        command_topic = f"device/{self.thing_name}/commands"
        
        def command_handler(client, userdata, msg):
            try:
                command_data = json.loads(msg.payload.decode('utf-8'))
                callback(msg.topic, command_data)
            except json.JSONDecodeError:
                console.print("❌ 無効なコマンドフォーマット", style="red")
        
        self.client.message_callback_add(command_topic, command_handler)
        self.client.subscribe(command_topic, qos=1)
        
        console.print(f"📥 コマンドトピックに購読: {command_topic}", style="blue")
    
    def publish_to_rule(self, rule_topic: str, data: Dict[str, Any]) -> bool:
        """AWS IoT Rules Engine 用のメッセージ送信"""
        message_data = {
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'source': self.thing_name,
            'data': data,
            'rule_trigger': True
        }
        
        try:
            payload = json.dumps(message_data)
            result = self.client.publish(rule_topic, payload, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                console.print(f"📋 Rules Engine トリガー送信: {rule_topic}", style="green")
                return True
            else:
                console.print(f"❌ Rules送信失敗: {result.rc}", style="red")
                return False
                
        except Exception as e:
            console.print(f"❌ Rules送信例外: {e}", style="red")
            return False
    
    def disconnect(self):
        """切断"""
        if self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()

class AWSIoTSimulator:
    """AWS IoT デバイスシミュレーター"""
    
    def __init__(self, aws_client: AWSIoTClient):
        self.aws_client = aws_client
        self.simulation_running = False
        self.sensor_data = {
            'temperature': 25.0,
            'humidity': 50.0,
            'pressure': 1013.25,
            'battery_level': 95.0
        }
    
    def start_sensor_simulation(self, interval: int = 10):
        """センサーデータシミュレーション開始"""
        self.simulation_running = True
        
        def simulation_loop():
            while self.simulation_running:
                # センサーデータを生成（ランダムな変動）
                import random
                
                self.sensor_data['temperature'] += random.uniform(-2, 2)
                self.sensor_data['humidity'] += random.uniform(-5, 5)
                self.sensor_data['pressure'] += random.uniform(-10, 10)
                self.sensor_data['battery_level'] = max(0, self.sensor_data['battery_level'] - 0.1)
                
                # データの範囲制限
                self.sensor_data['temperature'] = max(0, min(50, self.sensor_data['temperature']))
                self.sensor_data['humidity'] = max(0, min(100, self.sensor_data['humidity']))
                self.sensor_data['pressure'] = max(900, min(1100, self.sensor_data['pressure']))
                
                # テレメトリ送信
                self.aws_client.publish_telemetry(self.sensor_data)
                
                # Device Shadow の reported state を更新
                self.aws_client.update_device_shadow(
                    desired_state=None,
                    reported_state={
                        'sensor_status': 'online',
                        'last_reading': self.sensor_data,
                        'battery_level': self.sensor_data['battery_level']
                    }
                )
                
                # アラート条件チェック
                if self.sensor_data['temperature'] > 35:
                    self.aws_client.publish_to_rule(
                        "alerts/temperature",
                        {
                            'alert_type': 'high_temperature',
                            'value': self.sensor_data['temperature'],
                            'threshold': 35,
                            'severity': 'warning'
                        }
                    )
                
                if self.sensor_data['battery_level'] < 20:
                    self.aws_client.publish_to_rule(
                        "alerts/battery",
                        {
                            'alert_type': 'low_battery',
                            'value': self.sensor_data['battery_level'],
                            'threshold': 20,
                            'severity': 'critical'
                        }
                    )
                
                time.sleep(interval)
        
        thread = threading.Thread(target=simulation_loop, daemon=True)
        thread.start()
        console.print("🔄 センサーシミュレーション開始", style="green")
    
    def stop_sensor_simulation(self):
        """センサーシミュレーション停止"""
        self.simulation_running = False
        console.print("⏹️  センサーシミュレーション停止", style="yellow")

# デモンストレーション
def demonstrate_aws_iot():
    """AWS IoT Core デモンストレーション"""
    console.print("☁️ AWS IoT Core 統合デモ", style="bold blue")
    
    # 注意: 実際のAWS IoT Coreを使用する場合は、適切な証明書とエンドポイントが必要
    console.print("⚠️  このデモを実行するには以下が必要です:", style="yellow")
    console.print("   1. AWS IoT Core でのThing作成")
    console.print("   2. デバイス証明書の生成")
    console.print("   3. IAMポリシーの設定")
    console.print("   4. 証明書ファイルの配置")
    
    # 模擬的な設定（実際の実装では実際の値を使用）
    try:
        # デモ用の設定（実際の証明書パスに置き換えてください）
        aws_client = AWSIoTClient(
            endpoint="your-iot-endpoint.iot.us-west-2.amazonaws.com",  # 実際のエンドポイント
            root_ca_path="certs/AmazonRootCA1.pem",  # Amazon Root CA
            certificate_path="certs/device-certificate.pem.crt",  # デバイス証明書
            private_key_path="certs/device-private.pem.key",  # デバイス秘密鍵
            thing_name="demo-iot-device",
            region="us-west-2"
        )
        
        console.print("ℹ️  実際の接続はスキップします（証明書が必要）", style="dim")
        
        # コマンドハンドラーの設定例
        def handle_command(topic: str, command_data: Dict[str, Any]):
            console.print(f"📟 コマンド受信: {command_data}", style="magenta")
            
            command_type = command_data.get('command')
            if command_type == 'restart':
                console.print("🔄 デバイス再起動コマンド実行", style="yellow")
            elif command_type == 'update_config':
                config = command_data.get('config', {})
                console.print(f"⚙️  設定更新: {config}", style="blue")
        
        # 実際の使用例のコード構造を示す
        console.print("\n📋 AWS IoT Core 統合の主要機能:", style="bold green")
        console.print("   ✅ X.509証明書による認証")
        console.print("   ✅ Device Shadow による状態管理")
        console.print("   ✅ テレメトリデータの送信")
        console.print("   ✅ デバイスコマンドの受信")
        console.print("   ✅ AWS IoT Rules Engine連携")
        
        # 模擬的なデータフロー表示
        console.print("\n🔄 典型的なデータフロー:", style="bold blue")
        demo_data = {
            'temperature': 28.5,
            'humidity': 65.0,
            'location': {'lat': 35.6762, 'lon': 139.6503}
        }
        
        console.print(f"   📤 テレメトリ送信例: {demo_data}")
        console.print("   🌟 Device Shadow 状態更新")
        console.print("   📋 IoT Rules による後続処理")
        console.print("   💾 DynamoDB / S3 へのデータ保存")
        console.print("   📊 CloudWatch でのモニタリング")
        
    except Exception as e:
        console.print(f"⚠️  AWS IoT デモ設定エラー: {e}", style="yellow")
        console.print("   実際の環境では適切な認証情報を設定してください", style="dim")

# Exercise 2: Azure IoT Hub 連携
class AzureIoTHubClient:
    """Azure IoT Hub 統合クライアント"""
    
    def __init__(self, connection_string: str, device_id: str):
        """
        Azure IoT Hub クライアント初期化
        
        Args:
            connection_string: IoT Hub 接続文字列
            device_id: デバイスID
        """
        self.connection_string = connection_string
        self.device_id = device_id
        
        try:
            from azure.iot.device import IoTHubDeviceClient, Message
            self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)
            self.Message = Message
            console.print("✅ Azure IoT Hub クライアント初期化完了", style="green")
        except ImportError:
            console.print("⚠️  azure-iot-device ライブラリが必要です", style="yellow")
            console.print("   pip install azure-iot-device", style="dim")
            self.client = None
    
    async def connect_and_run(self):
        """Azure IoT Hub に接続してサンプル実行"""
        if not self.client:
            return
        
        try:
            await self.client.connect()
            console.print("✅ Azure IoT Hub に接続しました", style="bold green")
            
            # テレメトリ送信のデモ
            for i in range(5):
                telemetry_data = {
                    'deviceId': self.device_id,
                    'temperature': 20 + i * 2,
                    'humidity': 50 + i,
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                message = self.Message(json.dumps(telemetry_data))
                message.content_type = "application/json"
                message.content_encoding = "utf-8"
                message.custom_properties["temperatureAlert"] = "true" if telemetry_data['temperature'] > 25 else "false"
                
                await self.client.send_message(message)
                console.print(f"📤 Azure IoT Hub テレメトリ送信 #{i+1}", style="green")
                
                await asyncio.sleep(2)
            
        except Exception as e:
            console.print(f"❌ Azure IoT Hub エラー: {e}", style="red")
        finally:
            await self.client.disconnect()

def demonstrate_azure_iot():
    """Azure IoT Hub デモンストレーション"""
    console.print("☁️ Azure IoT Hub 統合デモ", style="bold blue")
    
    console.print("⚠️  このデモを実行するには以下が必要です:", style="yellow")
    console.print("   1. Azure IoT Hub の作成")
    console.print("   2. デバイスの登録")
    console.print("   3. 接続文字列の取得")
    console.print("   4. azure-iot-device ライブラリのインストール")
    
    # 模擬的なデモ実行
    console.print("\n📋 Azure IoT Hub 統合の主要機能:", style="bold green")
    console.print("   ✅ デバイス接続文字列による認証")
    console.print("   ✅ Device-to-Cloud メッセージ")
    console.print("   ✅ Cloud-to-Device メッセージ")
    console.print("   ✅ Device Twins による状態管理")
    console.print("   ✅ Direct Methods によるリモート制御")
    
    # 接続文字列の例（実際の値は使用しない）
    demo_connection_string = "HostName=your-iothub.azure-devices.net;DeviceId=demo-device;SharedAccessKey=your-key"
    
    try:
        azure_client = AzureIoTHubClient(demo_connection_string, "demo-device")
        console.print("ℹ️  実際の接続はスキップします（Azure接続文字列が必要）", style="dim")
        
        # 模擬的なデータフロー表示
        console.print("\n🔄 典型的なデータフロー:", style="bold blue")
        demo_telemetry = {
            'deviceId': 'demo-device',
            'temperature': 22.5,
            'humidity': 60.0,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        console.print(f"   📤 テレメトリ送信例: {demo_telemetry}")
        console.print("   🔄 Device Twin 状態同期")
        console.print("   📞 Direct Methods 実行")
        console.print("   💾 Azure Storage / Cosmos DB 保存")
        console.print("   📊 Azure Monitor でのモニタリング")
        
    except Exception as e:
        console.print(f"⚠️  Azure IoT デモ設定エラー: {e}", style="yellow")

# Exercise 3: Google Cloud IoT Core 連携
class GoogleCloudIoTClient:
    """Google Cloud IoT Core 統合クライアント"""
    
    def __init__(self, project_id: str, region: str, registry_id: str, device_id: str, private_key_path: str):
        """
        Google Cloud IoT Core クライアント初期化
        
        Args:
            project_id: Google Cloud プロジェクトID
            region: リージョン
            registry_id: デバイスレジストリID
            device_id: デバイスID
            private_key_path: 秘密鍵ファイルパス
        """
        self.project_id = project_id
        self.region = region
        self.registry_id = registry_id
        self.device_id = device_id
        self.private_key_path = private_key_path
        
        self.mqtt_bridge_hostname = 'mqtt.googleapis.com'
        self.mqtt_bridge_port = 8883
        
        console.print("✅ Google Cloud IoT Core クライアント初期化完了", style="green")
    
    def create_jwt(self, audience: str, private_key_path: str, algorithm: str = 'RS256') -> str:
        """JWT トークンを生成"""
        try:
            import jwt
            import datetime
            
            with open(private_key_path, 'r') as f:
                private_key = f.read()
            
            now = datetime.datetime.utcnow()
            
            payload = {
                'iat': now,
                'exp': now + datetime.timedelta(minutes=60),
                'aud': audience
            }
            
            return jwt.encode(payload, private_key, algorithm=algorithm)
            
        except ImportError:
            console.print("⚠️  PyJWT ライブラリが必要です", style="yellow")
            console.print("   pip install PyJWT[crypto]", style="dim")
            return None
        except Exception as e:
            console.print(f"❌ JWT生成エラー: {e}", style="red")
            return None
    
    def connect_and_publish(self):
        """Google Cloud IoT Core に接続してデータ送信"""
        # JWT トークンを生成
        audience = f"projects/{self.project_id}/locations/{self.region}"
        jwt_token = self.create_jwt(audience, self.private_key_path)
        
        if not jwt_token:
            console.print("❌ JWT トークン生成に失敗", style="red")
            return False
        
        # MQTTクライアント設定
        client = mqtt.Client(client_id=f"projects/{self.project_id}/locations/{self.region}/registries/{self.registry_id}/devices/{self.device_id}")
        
        # Google Cloud IoT Core は username に未使用、password に JWT を使用
        client.username_pw_set(username='unused', password=jwt_token)
        
        client.tls_set()
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                console.print("✅ Google Cloud IoT Core に接続しました", style="bold green")
            else:
                console.print(f"❌ 接続失敗: {rc}", style="red")
        
        def on_publish(client, userdata, mid):
            console.print(f"✅ メッセージ送信完了 (MID: {mid})", style="green")
        
        client.on_connect = on_connect
        client.on_publish = on_publish
        
        try:
            client.connect(self.mqtt_bridge_hostname, self.mqtt_bridge_port, 60)
            client.loop_start()
            
            time.sleep(2)  # 接続完了待ち
            
            # テレメトリトピック
            telemetry_topic = f"/devices/{self.device_id}/events"
            
            # サンプルデータ送信
            for i in range(3):
                telemetry_data = {
                    'device_id': self.device_id,
                    'sensor_reading': {
                        'temperature': 25.0 + i,
                        'humidity': 55.0 + i * 2
                    },
                    'timestamp': datetime.now(timezone.utc).isoformat()
                }
                
                payload = json.dumps(telemetry_data)
                client.publish(telemetry_topic, payload, qos=1)
                
                console.print(f"📤 Google Cloud テレメトリ送信 #{i+1}", style="green")
                time.sleep(3)
            
            time.sleep(2)
            client.loop_stop()
            client.disconnect()
            
            return True
            
        except Exception as e:
            console.print(f"❌ Google Cloud IoT 接続エラー: {e}", style="red")
            return False

def demonstrate_google_cloud_iot():
    """Google Cloud IoT Core デモンストレーション"""
    console.print("☁️ Google Cloud IoT Core 統合デモ", style="bold blue")
    
    console.print("⚠️  このデモを実行するには以下が必要です:", style="yellow")
    console.print("   1. Google Cloud IoT Core の有効化")
    console.print("   2. デバイスレジストリの作成")
    console.print("   3. デバイスの登録と公開鍵設定")
    console.print("   4. PyJWT[crypto] ライブラリのインストール")
    
    console.print("\n📋 Google Cloud IoT Core 統合の主要機能:", style="bold green")
    console.print("   ✅ JWT トークンによる認証")
    console.print("   ✅ MQTT Bridge 経由でのデータ送信")
    console.print("   ✅ Cloud Pub/Sub との連携")
    console.print("   ✅ Cloud Functions トリガー")
    console.print("   ✅ デバイス設定の管理")
    
    # 模擬的なデモ実行
    try:
        gcp_client = GoogleCloudIoTClient(
            project_id="your-project-id",
            region="us-central1", 
            registry_id="your-registry",
            device_id="demo-device",
            private_key_path="path/to/private_key.pem"
        )
        
        console.print("ℹ️  実際の接続はスキップします（認証情報が必要）", style="dim")
        
        # 模擬的なデータフロー表示
        console.print("\n🔄 典型的なデータフロー:", style="bold blue")
        demo_data = {
            'device_id': 'demo-device',
            'sensor_reading': {'temperature': 26.5, 'humidity': 58.0},
            'timestamp': datetime.now(timezone.utc).isoformat()
        }
        
        console.print(f"   📤 テレメトリ送信例: {demo_data}")
        console.print("   📮 Cloud Pub/Sub へのメッセージ配信")
        console.print("   ⚡ Cloud Functions での処理")
        console.print("   💾 BigQuery へのデータ蓄積")
        console.print("   📊 Data Studio でのダッシュボード")
        
    except Exception as e:
        console.print(f"⚠️  Google Cloud IoT デモ設定エラー: {e}", style="yellow")

# マルチクラウド対応クライアント
class MultiCloudIoTClient:
    """マルチクラウド対応 IoT クライアント"""
    
    def __init__(self):
        self.cloud_clients = {}
        self.active_clouds = []
        
    def add_aws_client(self, name: str, aws_client: AWSIoTClient):
        """AWS IoT クライアントを追加"""
        self.cloud_clients[name] = {
            'type': 'aws',
            'client': aws_client,
            'status': 'disconnected'
        }
    
    def add_azure_client(self, name: str, azure_client: AzureIoTHubClient):
        """Azure IoT Hub クライアントを追加"""
        self.cloud_clients[name] = {
            'type': 'azure',
            'client': azure_client,
            'status': 'disconnected'
        }
    
    def connect_all(self):
        """全てのクラウドに接続"""
        for name, config in self.cloud_clients.items():
            try:
                if config['type'] == 'aws':
                    if config['client'].connect():
                        config['status'] = 'connected'
                        self.active_clouds.append(name)
                        console.print(f"✅ {name} (AWS) 接続成功", style="green")
                
                elif config['type'] == 'azure':
                    # Azure は非同期のため、この例では接続済みとして扱う
                    config['status'] = 'connected'
                    self.active_clouds.append(name)
                    console.print(f"✅ {name} (Azure) 準備完了", style="green")
                    
            except Exception as e:
                console.print(f"❌ {name} 接続失敗: {e}", style="red")
    
    def broadcast_telemetry(self, data: Dict[str, Any]):
        """全てのクラウドにテレメトリを送信"""
        for name in self.active_clouds:
            config = self.cloud_clients[name]
            
            try:
                if config['type'] == 'aws' and config['status'] == 'connected':
                    config['client'].publish_telemetry(data)
                    console.print(f"📤 {name} テレメトリ送信完了", style="green")
                    
                elif config['type'] == 'azure' and config['status'] == 'connected':
                    console.print(f"📤 {name} テレメトリ送信準備完了", style="green")
                    
            except Exception as e:
                console.print(f"❌ {name} テレメトリ送信エラー: {e}", style="red")
    
    def get_status(self):
        """全クライアントの状態を取得"""
        status_table = Table(title="マルチクラウド接続状態")
        status_table.add_column("クラウド名", style="cyan")
        status_table.add_column("タイプ", style="blue")
        status_table.add_column("状態", style="green")
        
        for name, config in self.cloud_clients.items():
            status_style = "green" if config['status'] == 'connected' else "red"
            status_table.add_row(
                name,
                config['type'].upper(),
                config['status'],
                style=status_style if config['status'] == 'connected' else None
            )
        
        console.print(status_table)

def demonstrate_multi_cloud():
    """マルチクラウド統合デモンストレーション"""
    console.print("🌐 マルチクラウド IoT 統合デモ", style="bold blue")
    
    multi_client = MultiCloudIoTClient()
    
    console.print("📋 マルチクラウド統合の利点:", style="bold green")
    console.print("   ✅ クラウドベンダーロックインの回避")
    console.print("   ✅ 冗長性と可用性の向上")
    console.print("   ✅ 地域的な分散とレイテンシ最適化")
    console.print("   ✅ コスト最適化とサービス選択の柔軟性")
    console.print("   ✅ 災害対策とバックアップ")
    
    # 模擬的な設定を追加
    console.print("\n🔄 マルチクラウド構成例:", style="bold blue")
    console.print("   AWS: 主要データ処理とML/AI")
    console.print("   Azure: エンタープライズ統合とActive Directory連携") 
    console.print("   GCP: ビッグデータ分析とリアルタイム処理")
    
    # ステータス表示の例
    multi_client.cloud_clients = {
        'aws-primary': {'type': 'aws', 'status': 'connected'},
        'azure-backup': {'type': 'azure', 'status': 'connected'},
        'gcp-analytics': {'type': 'gcp', 'status': 'disconnected'}
    }
    
    console.print("\n📊 接続状態例:")
    multi_client.get_status()
    
    # データブロードキャストのデモ
    demo_data = {
        'device_id': 'multi-cloud-sensor',
        'temperature': 24.5,
        'humidity': 62.0,
        'location': 'Tokyo',
        'timestamp': datetime.now(timezone.utc).isoformat()
    }
    
    console.print(f"\n📡 ブロードキャストデータ例: {demo_data}")
    console.print("   各クラウドに同じデータを並列送信")
    console.print("   フェイルオーバーとロードバランシング")

# メイン実行関数
def main():
    """メイン実行関数"""
    console.print("☁️ Cloud Integration Comprehensive Demo", style="bold blue")
    
    demos = [
        ("AWS IoT Core Integration", demonstrate_aws_iot),
        ("Azure IoT Hub Integration", demonstrate_azure_iot),
        ("Google Cloud IoT Core Integration", demonstrate_google_cloud_iot),
        ("Multi-Cloud Architecture", demonstrate_multi_cloud)
    ]
    
    for i, (name, demo_func) in enumerate(demos):
        console.print(f"\n{'='*70}", style="dim")
        console.print(f"Demo {i+1}/{len(demos)}: {name}", style="bold yellow")
        console.print('='*70, style="dim")
        
        try:
            demo_func()
        except KeyboardInterrupt:
            console.print(f"\n⚠️  {name} デモが中断されました", style="yellow")
            break
        except Exception as e:
            console.print(f"❌ {name} デモでエラー: {e}", style="red")
        
        if i < len(demos) - 1:
            console.print("\n⏳ 次のデモまで3秒待機...", style="dim")
            time.sleep(3)
    
    console.print("\n🎉 全てのクラウド統合デモが完了しました！", style="bold green")
    
    # 総括
    console.print("\n📋 クラウド統合のベストプラクティス:", style="bold cyan")
    console.print("   1. 適切な認証とセキュリティの実装")
    console.print("   2. エラーハンドリングとリトライ機構")
    console.print("   3. データ形式の標準化")
    console.print("   4. モニタリングとログ記録")
    console.print("   5. コスト最適化")
    console.print("   6. 可用性と災害対策")

if __name__ == "__main__":
    main()
```

## 🎯 練習問題

### 問題1: AWS IoT Core 基本連携
1. AWS IoT Core でThingを作成し、X.509証明書を生成してください
2. `AWSIoTClient`を使用してデバイスからテレメトリデータを送信してください
3. Device Shadow を使用してデバイス状態を管理してください

### 問題2: Azure IoT Hub 双方向通信
1. Azure IoT Hub でデバイスを登録してください
2. Device-to-Cloud メッセージングを実装してください
3. Cloud-to-Device メッセージ受信機能を追加してください

### 問題3: Google Cloud IoT Core JWT認証
1. Google Cloud IoT Core でデバイスレジストリを作成してください
2. JWT認証を実装してテレメトリデータを送信してください
3. Cloud Pub/Sub と連携したデータパイプラインを構築してください

### 問題4: マルチクラウド対応システム
1. 複数のクラウドサービスに同時接続するシステムを実装してください
2. フェイルオーバー機構を追加してください
3. 各クラウドの特性を活かしたデータルーティングを実装してください

## ✅ 確認チェックリスト

- [ ] AWS IoT Core への接続と認証を実装した
- [ ] Device Shadow による状態管理を実装した
- [ ] Azure IoT Hub でのデバイス通信を実装した
- [ ] Google Cloud IoT Core でのJWT認証を理解した
- [ ] マルチクラウド対応アーキテクチャを設計した
- [ ] 各クラウドサービスの特徴を理解した
- [ ] セキュリティベストプラクティスを適用した
- [ ] エラーハンドリングと復旧機能を実装した

## 📊 理解度チェック

以下の質問に答えられるか確認してください：

1. AWS IoT Core、Azure IoT Hub、Google Cloud IoT Coreの主な違いは？
2. Device ShadowとDevice Twinsの役割の違いは？
3. X.509証明書認証とJWT認証の特徴の比較は？
4. マルチクラウド戦略のメリットとデメリットは？
5. クラウドIoTサービスでのコスト最適化の方法は？

## 🔧 トラブルシューティング

### AWS IoT Core 接続エラー
- 証明書ファイルのパスと権限を確認
- IAMポリシーの設定を確認
- エンドポイントURLの正確性を確認
- SSL/TLS設定を確認

### Azure IoT Hub 認証失敗
- 接続文字列の形式を確認
- デバイスの登録状態を確認
- Shared Access Keyの有効性を確認

### Google Cloud IoT Core JWT エラー
- 秘密鍵ファイルの形式を確認
- JWTの有効期限を確認
- プロジェクトIDとレジストリIDを確認
- Cloud IoT Core APIの有効化を確認

### ネットワーク接続問題
- ファイアウォール設定を確認
- ポート8883の開放を確認
- DNS解決を確認
- プロキシ設定を確認

---

**次のステップ**: [10-monitoring-dashboard](../10-monitoring-dashboard/) で監視ダッシュボードの構築について学習しましょう！