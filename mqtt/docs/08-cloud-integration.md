# クラウドサービスとの統合

## 8.1 AWS IoT Core との統合

AWS IoT Core は世界最大規模のマネージドMQTTサービスの一つで、2025年現在も継続的に機能拡張が行われています。

### 8.1.1 基本セットアップ

#### Thing（デバイス）の作成と証明書設定

```bash
# AWS CLI を使用したThing作成
aws iot create-thing --thing-name "temperature-sensor-001"

# 証明書とキーペアの作成
aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile cert.pem \
    --private-key-outfile private.key \
    --public-key-outfile public.key

# ポリシーの作成
cat > iot-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Connect"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish",
        "iot:Receive"
      ],
      "Resource": [
        "arn:aws:iot:region:account:topic/sensors/*",
        "arn:aws:iot:region:account:topic/commands/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iot:Subscribe"
      ],
      "Resource": [
        "arn:aws:iot:region:account:topicfilter/sensors/*",
        "arn:aws:iot:region:account:topicfilter/commands/*"
      ]
    }
  ]
}
EOF

aws iot create-policy \
    --policy-name "SensorDevicePolicy" \
    --policy-document file://iot-policy.json

# 証明書にポリシーをアタッチ
aws iot attach-policy \
    --policy-name "SensorDevicePolicy" \
    --target "certificate-arn"
```

#### Python デバイス実装

```python
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
import json
import time
import threading
from datetime import datetime
from typing import Dict, Any, Callable, Optional
import random

class AWSIoTDevice:
    def __init__(self, thing_name: str, endpoint: str, cert_path: str, key_path: str, 
                 ca_path: str = "./AmazonRootCA1.pem"):
        self.thing_name = thing_name
        self.endpoint = endpoint
        self.cert_path = cert_path
        self.key_path = key_path
        self.ca_path = ca_path
        
        # AWS IoT MQTT クライアント初期化
        self.client = AWSIoTMQTTClient(thing_name)
        self.client.configureEndpoint(endpoint, 8883)
        self.client.configureCredentials(ca_path, key_path, cert_path)
        
        # 接続設定
        self.client.configureAutoReconnectBackoffTime(1, 32, 20)
        self.client.configureOfflinePublishQueueing(-1)  # Infinite offline publishing
        self.client.configureDrainingFrequency(2)  # Draining frequency in Hz
        self.client.configureConnectDisconnectTimeout(10)  # 10 sec
        self.client.configureMQTTOperationTimeout(5)  # 5 sec
        
        self.connected = False
        
    def connect(self) -> bool:
        """AWS IoT Core に接続"""
        try:
            result = self.client.connect()
            if result:
                self.connected = True
                print(f"Connected to AWS IoT Core: {self.thing_name}")
                return True
            else:
                print("Connection failed")
                return False
        except Exception as error:
            print(f"Connection error: {error}")
            return False
    
    def disconnect(self):
        """接続を切断"""
        if self.connected:
            self.client.disconnect()
            self.connected = False
            print("Disconnected from AWS IoT Core")
    
    def publish_sensor_data(self, sensor_type: str, value: float, metadata: Dict[str, Any] = None) -> bool:
        """センサーデータをパブリッシュ"""
        if not self.connected:
            print("Not connected to AWS IoT Core")
            return False
            
        topic = f"sensors/{self.thing_name}/{sensor_type}"
        message = {
            "deviceId": self.thing_name,
            "sensorType": sensor_type,
            "value": value,
            "timestamp": datetime.now().isoformat(),
            "metadata": metadata or {}
        }
        
        try:
            self.client.publish(topic, json.dumps(message), 1)  # QoS 1
            print(f"Published to {topic}: {message}")
            return True
        except Exception as e:
            print(f"Failed to publish sensor data: {e}")
            return False
    
    def subscribe_to_commands(self, callback: Callable[[str, Dict[str, Any]], None]):
        """コマンドトピックを購読"""
        topic = f"commands/{self.thing_name}/+"
        
        def command_callback(client, userdata, message):
            try:
                payload = json.loads(message.payload.decode())
                command = message.topic.split('/')[-1]
                callback(command, payload)
            except Exception as error:
                print(f"Failed to parse command: {error}")
        
        self.client.subscribe(topic, 1, command_callback)
        print(f"Subscribed to commands: {topic}")
    
    def update_device_shadow(self, state: Dict[str, Any]) -> bool:
        """デバイスシャドウを更新"""
        if not self.connected:
            return False
            
        shadow_topic = f"$aws/things/{self.thing_name}/shadow/update"
        shadow_message = {
            "state": {
                "reported": state
            }
        }
        
        try:
            self.client.publish(shadow_topic, json.dumps(shadow_message), 1)
            print(f"Device shadow updated: {state}")
            return True
        except Exception as e:
            print(f"Failed to update device shadow: {e}")
            return False
    
    def subscribe_shadow_updates(self, callback: Callable[[str, Dict[str, Any]], None]):
        """シャドウ更新を購読"""
        accepted_topic = f"$aws/things/{self.thing_name}/shadow/update/accepted"
        delta_topic = f"$aws/things/{self.thing_name}/shadow/update/delta"
        
        def shadow_accepted_callback(client, userdata, message):
            try:
                payload = json.loads(message.payload.decode())
                callback('accepted', payload)
            except Exception as e:
                print(f"Failed to parse shadow accepted message: {e}")
        
        def shadow_delta_callback(client, userdata, message):
            try:
                payload = json.loads(message.payload.decode())
                callback('delta', payload)
            except Exception as e:
                print(f"Failed to parse shadow delta message: {e}")
        
        self.client.subscribe(accepted_topic, 1, shadow_accepted_callback)
        self.client.subscribe(delta_topic, 1, shadow_delta_callback)
        print(f"Subscribed to shadow updates")

# 使用例
def main():
    device = AWSIoTDevice(
        thing_name='temperature-sensor-001',
        endpoint='your-endpoint.iot.us-east-1.amazonaws.com',
        cert_path='./certificate.pem.crt',
        key_path='./private.pem.key'
    )
    
    if not device.connect():
        print("Failed to connect to AWS IoT Core")
        return
    
    # コマンド受信設定
    def command_handler(command: str, message: Dict[str, Any]):
        print(f"Received command {command}: {message}")
        
        if command == 'calibrate':
            print('Executing calibration...')
            # キャリブレーション実行
        elif command == 'set_interval':
            interval = message.get('interval', 30)
            print(f'Setting interval to {interval} seconds')
            # サンプリング間隔変更
    
    device.subscribe_to_commands(command_handler)
    
    # シャドウ更新監視
    def shadow_handler(update_type: str, message: Dict[str, Any]):
        if update_type == 'delta' and 'state' in message:
            print(f'Shadow delta received: {message["state"]}')
            # 設定変更を適用
            device.update_device_shadow(message['state'])
        elif update_type == 'accepted':
            print('Shadow update accepted')
    
    device.subscribe_shadow_updates(shadow_handler)
    
    # 定期的なセンサーデータ送信
    def send_sensor_data():
        while device.connected:
            temperature = 20 + random.random() * 10
            humidity = 40 + random.random() * 20
            
            device.publish_sensor_data('temperature', temperature, {
                'unit': 'celsius',
                'accuracy': '±0.5°C'
            })
            
            device.publish_sensor_data('humidity', humidity, {
                'unit': 'percent',
                'accuracy': '±2%'
            })
            
            time.sleep(30)
    
    # センサーデータ送信を別スレッドで開始
    sensor_thread = threading.Thread(target=send_sensor_data, daemon=True)
    sensor_thread.start()
    
    try:
        # メインループ
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        device.disconnect()

if __name__ == "__main__":
    main()
```

### 8.1.2 IoT Rules Engine 活用

```python
# Boto3を使用したIoT Rules Engineの設定
import boto3
import json

def create_temperature_alert_rule():
    """温度アラートルールの作成"""
    iot_client = boto3.client('iot')
    
    rule_payload = {
        'sql': '''
            SELECT 
                deviceId,
                sensorType,
                value as temperature,
                timestamp,
                'HIGH_TEMPERATURE' as alertType
            FROM 'sensors/+/temperature' 
            WHERE value > 35
        ''',
        'actions': [
            {
                'lambda': {
                    'functionArn': 'arn:aws:lambda:region:account:function:ProcessHighTemperature'
                }
            },
            {
                'sns': {
                    'targetArn': 'arn:aws:sns:region:account:temperature-alerts',
                    'messageFormat': 'JSON'
                }
            },
            {
                'dynamoDBv2': {
                    'tableName': 'TemperatureAlerts',
                    'roleArn': 'arn:aws:iam::account:role/IoTRuleRole',
                    'putItem': {
                        'deviceId': {
                            'S': '${deviceId}'
                        },
                        'timestamp': {
                            'S': '${timestamp}'
                        },
                        'temperature': {
                            'N': '${temperature}'
                        },
                        'alertType': {
                            'S': '${alertType}'
                        }
                    }
                }
            }
        ],
        'ruleDisabled': False,
        'awsIotSqlVersion': '2016-03-23'
    }
    
    try:
        response = iot_client.create_topic_rule(
            ruleName='TemperatureAlertRule',
            topicRulePayload=rule_payload
        )
        print("IoT Rule created successfully")
        return response
    except Exception as e:
        print(f"Failed to create IoT rule: {e}")
        return None

# CloudFormation テンプレート（YAML形式）
cloudformation_template = '''
AWSTemplateFormatVersion: '2010-09-09'
Description: 'MQTT Temperature Alert Rule'

Resources:
  TemperatureAlertRule:
    Type: AWS::IoT::TopicRule
    Properties:
      RuleName: TemperatureAlertRule
      TopicRulePayload:
        Sql: |
          SELECT 
            deviceId,
            sensorType,
            value as temperature,
            timestamp,
            'HIGH_TEMPERATURE' as alertType
          FROM 'sensors/+/temperature' 
          WHERE value > 35
        Actions:
          - Lambda:
              FunctionArn: !Sub 'arn:aws:lambda:${AWS::Region}:${AWS::AccountId}:function:ProcessHighTemperature'
          - Sns:
              TargetArn: !Sub 'arn:aws:sns:${AWS::Region}:${AWS::AccountId}:temperature-alerts'
              MessageFormat: JSON
          - DynamoDBv2:
              TableName: TemperatureAlerts
              RoleArn: !Sub 'arn:aws:iam::${AWS::AccountId}:role/IoTRuleRole'
              PutItem:
                deviceId:
                  S: '${deviceId}'
                timestamp:
                  S: '${timestamp}'
                temperature:
                  N: '${temperature}'
                alertType:
                  S: '${alertType}'
        RuleDisabled: false
        AwsIotSqlVersion: '2016-03-23'

Outputs:
  RuleName:
    Description: 'Name of the created IoT rule'
    Value: !Ref TemperatureAlertRule
    Export:
      Name: !Sub '${AWS::StackName}-RuleName'
'''

# 使用例
if __name__ == "__main__":
    create_temperature_alert_rule()
```

### 8.1.3 Device Shadow との連携

```python
import json
import boto3
from botocore.exceptions import ClientError

class AWSIoTShadowManager:
    def __init__(self, region_name='us-east-1'):
        self.iot_data_client = boto3.client('iot-data', region_name=region_name)
        
    def get_thing_shadow(self, thing_name):
        """デバイスシャドウの取得"""
        try:
            response = self.iot_data_client.get_thing_shadow(thingName=thing_name)
            shadow_data = json.loads(response['payload'].read())
            return shadow_data
        except ClientError as e:
            print(f"Failed to get shadow for {thing_name}: {e}")
            return None
            
    def update_thing_shadow(self, thing_name, desired_state=None, reported_state=None):
        """デバイスシャドウの更新"""
        shadow_update = {"state": {}}
        
        if desired_state:
            shadow_update["state"]["desired"] = desired_state
        if reported_state:
            shadow_update["state"]["reported"] = reported_state
            
        try:
            response = self.iot_data_client.update_thing_shadow(
                thingName=thing_name,
                payload=json.dumps(shadow_update)
            )
            return json.loads(response['payload'].read())
        except ClientError as e:
            print(f"Failed to update shadow for {thing_name}: {e}")
            return None
            
    def set_device_configuration(self, thing_name, config):
        """デバイス設定の更新"""
        return self.update_thing_shadow(thing_name, desired_state=config)
        
    def get_device_status(self, thing_name):
        """デバイス状態の取得"""
        shadow = self.get_thing_shadow(thing_name)
        if shadow and 'state' in shadow and 'reported' in shadow['state']:
            return shadow['state']['reported']
        return None

# 使用例：デバイス設定管理
shadow_manager = AWSIoTShadowManager()

# デバイス設定の更新
new_config = {
    "sampling_interval": 60,
    "temperature_threshold": 30,
    "reporting_enabled": True,
    "sensor_calibration": {
        "temperature_offset": 0.5,
        "humidity_offset": -1.2
    }
}

result = shadow_manager.set_device_configuration('temperature-sensor-001', new_config)
print("Configuration update result:", result)

# デバイス状態の確認
current_status = shadow_manager.get_device_status('temperature-sensor-001')
print("Current device status:", current_status)
```

## 8.2 Azure IoT Hub との統合

### 8.2.1 接続文字列とSAS認証

```python
from azure.iot.device import IoTHubDeviceClient, Message, MethodResponse
import json
import asyncio
import time
import threading
from datetime import datetime
from typing import Dict, Any, Callable
import psutil
import random

class AzureIoTDevice:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string
        self.client = IoTHubDeviceClient.create_from_connection_string(connection_string)
        self.connected = False
        self.setup_event_handlers()
    
    def setup_event_handlers(self):
        """イベントハンドラーの設定"""
        
        # C2D (Cloud-to-Device) メッセージ受信ハンドラー
        async def message_handler(message):
            print('C2D Message received:')
            print(f'- Data: {message.data.decode()}')
            print(f'- Properties: {message.custom_properties}')
            
            # メッセージ処理完了通知
            try:
                await self.client.complete_message(message)
                print('Message completed')
            except Exception as e:
                print(f'Failed to complete message: {e}')
        
        self.client.on_message_received = message_handler
        
        # Direct Methods のハンドラー設定
        async def reboot_method_handler(method_request):
            print('Reboot method called')
            print(f'Payload: {method_request.payload}')
            
            # リブート処理のシミュレーション
            await asyncio.sleep(2)
            
            method_response = MethodResponse.create_from_method_request(
                method_request, 200, "Reboot completed"
            )
            await self.client.send_method_response(method_response)
        
        async def get_status_method_handler(method_request):
            status = {
                'uptime': time.time() - psutil.boot_time(),
                'memory': dict(psutil.virtual_memory()._asdict()),
                'cpu_percent': psutil.cpu_percent(),
                'timestamp': datetime.now().isoformat()
            }
            
            method_response = MethodResponse.create_from_method_request(
                method_request, 200, status
            )
            await self.client.send_method_response(method_response)
        
        # Direct Methods の登録
        self.client.on_method_request_received = self.create_method_dispatcher({
            'reboot': reboot_method_handler,
            'getStatus': get_status_method_handler
        })
    
    def create_method_dispatcher(self, method_handlers: Dict[str, Callable]):
        """Direct Method のディスパッチャー作成"""
        async def method_dispatcher(method_request):
            method_name = method_request.name
            if method_name in method_handlers:
                await method_handlers[method_name](method_request)
            else:
                print(f'Unknown method: {method_name}')
                method_response = MethodResponse.create_from_method_request(
                    method_request, 404, f"Method {method_name} not found"
                )
                await self.client.send_method_response(method_response)
        
        return method_dispatcher
    
    async def connect(self):
        """Azure IoT Hub に接続"""
        try:
            await self.client.connect()
            self.connected = True
            print('Connected to Azure IoT Hub')
        except Exception as e:
            print(f'Connection error: {e}')
            raise
    
    async def disconnect(self):
        """接続を切断"""
        if self.connected:
            await self.client.disconnect()
            self.connected = False
            print('Disconnected from Azure IoT Hub')
    
    async def send_telemetry(self, data: Dict[str, Any]):
        """テレメトリデータを送信"""
        message = Message(json.dumps(data))
        
        # メッセージプロパティの設定
        message.custom_properties['temperatureAlert'] = 'true' if data.get('temperature', 0) > 30 else 'false'
        message.custom_properties['deviceType'] = 'sensor'
        message.custom_properties['timestamp'] = datetime.now().isoformat()
        
        try:
            await self.client.send_message(message)
            print(f'Telemetry sent: {data}')
        except Exception as e:
            print(f'Failed to send telemetry: {e}')
            raise
    
    async def update_reported_properties(self, properties: Dict[str, Any]):
        """Reported Properties を更新"""
        try:
            await self.client.patch_twin_reported_properties(properties)
            print(f'Reported properties updated: {properties}')
        except Exception as e:
            print(f'Failed to update reported properties: {e}')
            raise
    
    async def subscribe_to_desired_properties(self, callback: Callable[[Dict[str, Any]], None]):
        """Desired Properties の変更を監視"""
        def twin_patch_handler(twin_patch):
            print(f'Desired properties update: {twin_patch}')
            # コールバックを非同期で実行
            asyncio.create_task(callback(twin_patch))
        
        self.client.on_twin_desired_properties_patch_received = twin_patch_handler

# 使用例
async def main():
    # 接続文字列（Azure ポータルから取得）
    connection_string = 'HostName=your-hub.azure-devices.net;DeviceId=your-device;SharedAccessKey=your-key'
    
    device = AzureIoTDevice(connection_string)
    await device.connect()
    
    # Desired Properties の監視
    async def desired_properties_handler(delta):
        # 設定変更をReported Propertiesに反映
        await device.update_reported_properties(delta)
    
    await device.subscribe_to_desired_properties(desired_properties_handler)
    
    # 定期的なテレメトリ送信タスク
    async def send_telemetry_loop():
        while device.connected:
            telemetry_data = {
                'temperature': 20 + random.random() * 15,
                'humidity': 40 + random.random() * 30,
                'pressure': 1000 + random.random() * 100,
                'timestamp': datetime.now().isoformat()
            }
            
            try:
                await device.send_telemetry(telemetry_data)
            except Exception as error:
                print(f'Failed to send telemetry: {error}')
            
            await asyncio.sleep(10)
    
    # デバイス状態の定期更新タスク
    async def update_properties_loop():
        while device.connected:
            reported_properties = {
                'connectivity': 'connected',
                'lastSeen': datetime.now().isoformat(),
                'batteryLevel': random.randint(0, 100),
                'cpuUsage': psutil.cpu_percent(),
                'memoryUsage': psutil.virtual_memory().percent
            }
            
            try:
                await device.update_reported_properties(reported_properties)
            except Exception as error:
                print(f'Failed to update properties: {error}')
            
            await asyncio.sleep(60)
    
    # バックグラウンドタスクを開始
    telemetry_task = asyncio.create_task(send_telemetry_loop())
    properties_task = asyncio.create_task(update_properties_loop())
    
    try:
        # メインループ
        await asyncio.gather(telemetry_task, properties_task)
    except KeyboardInterrupt:
        print("\nShutting down...")
        telemetry_task.cancel()
        properties_task.cancel()
    finally:
        await device.disconnect()

if __name__ == "__main__":
    asyncio.run(main())
```

### 8.2.2 IoT Edge との連携

```yaml
# IoT Edge 設定 (config.yaml)
hostname: "my-iot-edge-device"

connect:
  management_uri: "unix:///var/run/iotedge/mgmt.sock"
  workload_uri: "unix:///var/run/iotedge/workload.sock"

listen:
  management_uri: "fd://iotedge.mgmt.socket"
  workload_uri: "fd://iotedge.socket"

homedir: "/var/lib/iotedge"

moby_runtime:
  uri: "unix:///var/run/docker.sock"
  network: azure-iot-edge

provisioning:
  source: "manual"
  device_connection_string: "HostName=your-hub.azure-devices.net;DeviceId=your-edge-device;SharedAccessKey=your-key"

certificates:
  device_ca_cert: "/etc/iotedge/device-ca-cert.pem"
  device_ca_pk: "/etc/iotedge/device-ca-pk.pem"
  trusted_ca_certs: "/etc/iotedge/trusted-ca-certs.pem"
```

**カスタムIoT Edgeモジュール:**

```python
# modules/mqtt-bridge/app.py
from azure.iot.device import IoTHubModuleClient, Message
import paho.mqtt.client as mqtt
import asyncio
import json
import signal
import sys
from datetime import datetime
from typing import Dict, Any, Optional

class MQTTBridgeModule:
    def __init__(self):
        self.module_client: Optional[IoTHubModuleClient] = None
        self.local_mqtt_client: Optional[mqtt.Client] = None
        self.bridge_config = {
            'local_broker': 'mqtt://localhost:1883',
            'topic_mapping': {
                'local/sensors/+/data': 'cloud/sensors/{deviceId}/telemetry',
                'cloud/commands/+': 'local/commands/{deviceId}'
            }
        }
        self.running = True
    
    async def initialize(self):
        """モジュールの初期化"""
        try:
            # IoT Edge Module Client の初期化
            self.module_client = IoTHubModuleClient.create_from_edge_environment()
            await self.module_client.connect()
            
            print('IoT Edge module connected')
            
            # ローカルMQTTブローカーへの接続
            self.setup_local_mqtt_client()
            
            # クラウドからのメッセージ受信設定
            self.module_client.on_message_received = self.handle_cloud_message
            
            # Module Twin の設定
            await self.setup_module_twin()
            
        except Exception as e:
            print(f'Failed to initialize module: {e}')
            raise
    
    def setup_local_mqtt_client(self):
        """ローカルMQTTクライアントの設定"""
        broker_url = self.bridge_config['local_broker'].replace('mqtt://', '')
        host, port = (broker_url.split(':') + ['1883'])[:2]
        port = int(port)
        
        self.local_mqtt_client = mqtt.Client(client_id="iot-edge-bridge")
        
        def on_connect(client, userdata, flags, rc):
            if rc == 0:
                print('Connected to local MQTT broker')
                self.setup_local_subscriptions()
            else:
                print(f'Failed to connect to local MQTT broker: {rc}')
        
        def on_message(client, userdata, message):
            asyncio.create_task(self.handle_local_message(message.topic, message.payload))
        
        self.local_mqtt_client.on_connect = on_connect
        self.local_mqtt_client.on_message = on_message
        
        self.local_mqtt_client.connect(host, port, 60)
        self.local_mqtt_client.loop_start()
    
    def setup_local_subscriptions(self):
        """ローカルMQTTトピックの購読"""
        for local_topic in self.bridge_config['topic_mapping'].keys():
            if local_topic.startswith('local/'):
                result = self.local_mqtt_client.subscribe(local_topic, qos=1)
                if result[0] == mqtt.MQTT_ERR_SUCCESS:
                    print(f'Subscribed to local topic: {local_topic}')
                else:
                    print(f'Failed to subscribe to {local_topic}')
    
    async def handle_local_message(self, topic: str, payload: bytes):
        """ローカルメッセージをクラウドに転送"""
        try:
            device_id = self.extract_device_id(topic)
            cloud_topic = self.map_to_cloud_topic(topic, device_id)
            
            if cloud_topic:
                # Azure IoT メッセージを作成
                output_message = Message(payload)
                output_message.custom_properties['source'] = 'local-mqtt'
                output_message.custom_properties['originalTopic'] = topic
                output_message.custom_properties['deviceId'] = device_id
                output_message.custom_properties['timestamp'] = datetime.now().isoformat()
                
                # クラウドに送信
                await self.module_client.send_message_to_output(
                    output_message, 'upstreamOutput'
                )
                print(f'Bridged message from {topic} to cloud')
                
        except Exception as e:
            print(f'Error handling local message: {e}')
    
    async def handle_cloud_message(self, message):
        """クラウドメッセージをローカルに転送"""
        try:
            print(f'Received cloud message')
            
            # メッセージプロパティから情報取得
            device_id = message.custom_properties.get('deviceId')
            target_topic = message.custom_properties.get('targetTopic')
            
            if device_id and target_topic:
                local_topic = target_topic.replace('{deviceId}', device_id)
                
                # ローカルMQTTブローカーにパブリッシュ
                result = self.local_mqtt_client.publish(
                    local_topic, 
                    message.data, 
                    qos=1
                )
                
                if result.rc == mqtt.MQTT_ERR_SUCCESS:
                    print(f'Bridged message from cloud to {local_topic}')
                else:
                    print(f'Failed to publish to local topic: {result.rc}')
            
            # メッセージ完了通知
            await self.module_client.complete_message(message)
            
        except Exception as e:
            print(f'Error handling cloud message: {e}')
    
    async def setup_module_twin(self):
        """Module Twin の設定"""
        try:
            # Desired Properties の監視
            def twin_patch_handler(twin_patch):
                print(f'Module twin desired properties update: {twin_patch}')
                self.update_bridge_config(twin_patch)
            
            self.module_client.on_twin_desired_properties_patch_received = twin_patch_handler
            
            # Reported Properties の更新
            reported_properties = {
                'status': 'running',
                'lastStartTime': datetime.now().isoformat(),
                'version': '1.0.0',
                'bridgeConfig': self.bridge_config
            }
            
            await self.module_client.patch_twin_reported_properties(reported_properties)
            print('Module twin reported properties updated')
            
        except Exception as e:
            print(f'Failed to setup module twin: {e}')
    
    def update_bridge_config(self, delta: Dict[str, Any]):
        """ブリッジ設定の更新"""
        if 'topicMapping' in delta:
            self.bridge_config['topic_mapping'].update(delta['topicMapping'])
            print('Updated topic mapping configuration')
            # 新しいトピックマッピングで購読を再設定
            self.setup_local_subscriptions()
    
    def extract_device_id(self, topic: str) -> str:
        """トピックからデバイスIDを抽出"""
        parts = topic.split('/')
        return parts[2] if len(parts) > 2 else 'unknown'
    
    def map_to_cloud_topic(self, local_topic: str, device_id: str) -> Optional[str]:
        """ローカルトピックをクラウドトピックにマッピング"""
        # ワイルドカード部分を置換してマッチング
        for pattern, cloud_template in self.bridge_config['topic_mapping'].items():
            if self.topic_matches_pattern(local_topic, pattern):
                return cloud_template.replace('{deviceId}', device_id)
        return None
    
    def topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """トピックがパターンにマッチするかチェック"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(topic_parts) != len(pattern_parts):
            return False
        
        for t_part, p_part in zip(topic_parts, pattern_parts):
            if p_part != '+' and p_part != t_part:
                return False
        
        return True
    
    async def shutdown(self):
        """モジュールのシャットダウン"""
        print('Shutting down MQTT Bridge Module...')
        self.running = False
        
        if self.local_mqtt_client:
            self.local_mqtt_client.loop_stop()
            self.local_mqtt_client.disconnect()
        
        if self.module_client:
            await self.module_client.disconnect()
        
        print('MQTT Bridge Module shut down')

# メイン実行関数
async def main():
    bridge_module = MQTTBridgeModule()
    
    # シグナルハンドラーの設定
    def signal_handler(signum, frame):
        print(f'Signal {signum} received, shutting down gracefully')
        asyncio.create_task(bridge_module.shutdown())
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    try:
        await bridge_module.initialize()
        print('MQTT Bridge Module started')
        
        # メインループ
        while bridge_module.running:
            await asyncio.sleep(1)
            
    except Exception as e:
        print(f'Module startup failed: {e}')
        sys.exit(1)
    finally:
        await bridge_module.shutdown()

if __name__ == '__main__':
    asyncio.run(main())
```

## 8.3 Google Cloud IoT Platform

**注意**: Google Cloud IoT Core は2023年8月16日にサービス終了しました。以下は代替アーキテクチャの例です。

### 8.3.1 Cloud Pub/Sub + Cloud Run アーキテクチャ

```python
# Cloud Run で動作するMQTTプロキシサービス
from flask import Flask, request, jsonify
from google.cloud import pubsub_v1
from google.cloud import firestore
import paho.mqtt.client as mqtt
import json
import os
import threading
import time
from datetime import datetime
from typing import Dict, Any

class GoogleCloudMQTTProxy:
    def __init__(self):
        self.app = Flask(__name__)
        self.publisher = pubsub_v1.PublisherClient()
        self.firestore_client = firestore.Client()
        self.mqtt_client = None
        self.project_id = os.environ.get('PROJECT_ID')
        
        self.setup_flask_routes()
        self.connect_to_mqtt_broker()
    
    def setup_flask_routes(self):
        """Flask ルートの設定"""
        
        @self.app.route('/devices/<device_id>/register', methods=['POST'])
        def register_device(device_id):
            try:
                config = request.get_json()
                self.register_device(device_id, config)
                return jsonify({'success': True, 'deviceId': device_id})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/devices/<device_id>/commands', methods=['POST'])
        def send_command(device_id):
            try:
                command = request.get_json()
                self.send_device_command(device_id, command)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @self.app.route('/health', methods=['GET'])
        def health_check():
            return jsonify({
                'status': 'healthy',
                'timestamp': datetime.now().isoformat(),
                'mqtt_connected': self.mqtt_client.is_connected() if self.mqtt_client else False
            })
        
        @self.app.route('/devices', methods=['GET'])
        def list_devices():
            try:
                devices_ref = self.firestore_client.collection('devices')
                devices = []
                for doc in devices_ref.stream():
                    device_data = doc.to_dict()
                    device_data['id'] = doc.id
                    devices.append(device_data)
                return jsonify({'devices': devices})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def connect_to_mqtt_broker(self):
        """MQTTブローカーへの接続"""
        try:
            # マネージドMQTTサービス（EMQX Cloud、HiveMQ Cloud等）への接続
            broker_url = os.environ.get('MQTT_BROKER_URL', 'localhost')
            username = os.environ.get('MQTT_USERNAME')
            password = os.environ.get('MQTT_PASSWORD')
            port = int(os.environ.get('MQTT_PORT', '1883'))
            
            client_id = f"gcp-proxy-{int(time.time())}"
            self.mqtt_client = mqtt.Client(client_id=client_id)
            
            if username and password:
                self.mqtt_client.username_pw_set(username, password)
            
            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    print('Connected to MQTT broker')
                    self.setup_mqtt_subscriptions()
                else:
                    print(f'Failed to connect to MQTT broker: {rc}')
            
            def on_message(client, userdata, message):
                self.handle_mqtt_message(message.topic, message.payload)
            
            def on_disconnect(client, userdata, rc):
                print(f'Disconnected from MQTT broker: {rc}')
            
            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_message = on_message
            self.mqtt_client.on_disconnect = on_disconnect
            
            self.mqtt_client.connect(broker_url, port, 60)
            
            # MQTTクライアントを別スレッドで実行
            mqtt_thread = threading.Thread(target=self.mqtt_client.loop_forever, daemon=True)
            mqtt_thread.start()
            
        except Exception as e:
            print(f'Failed to connect to MQTT broker: {e}')
    
    def setup_mqtt_subscriptions(self):
        """MQTT購読の設定"""
        subscriptions = [
            ('devices/+/telemetry', 1),
            ('devices/+/state', 1), 
            ('devices/+/events/+', 1)
        ]
        
        for topic, qos in subscriptions:
            result = self.mqtt_client.subscribe(topic, qos)
            if result[0] == mqtt.MQTT_ERR_SUCCESS:
                print(f'Subscribed to: {topic}')
            else:
                print(f'Failed to subscribe to: {topic}')
    
    def handle_mqtt_message(self, topic: str, message: bytes):
        """MQTTメッセージの処理"""
        try:
            topic_parts = topic.split('/')
            if len(topic_parts) < 3:
                return
            
            device_id = topic_parts[1]
            message_type = topic_parts[2]
            
            data = json.loads(message.decode())
            
            # Cloud Pub/Sub にメッセージ転送
            pubsub_topic = f'projects/{self.project_id}/topics/iot-{message_type}'
            
            message_data = {
                'deviceId': device_id,
                'messageType': message_type,
                'data': data,
                'timestamp': datetime.now().isoformat(),
                'originalTopic': topic
            }
            
            # Pub/Sub にパブリッシュ
            topic_path = self.publisher.topic_path(self.project_id, f'iot-{message_type}')
            message_json = json.dumps(message_data)
            message_bytes = message_json.encode('utf-8')
            
            future = self.publisher.publish(topic_path, message_bytes)
            future.result()  # 送信完了を待機
            
            print(f'Message forwarded to Pub/Sub: {topic}')
            
        except Exception as e:
            print(f'Error handling MQTT message: {e}')
    
    def register_device(self, device_id: str, config: Dict[str, Any]):
        """デバイス登録"""
        try:
            device_data = {
                **config,
                'registeredAt': datetime.now().isoformat(),
                'status': 'registered',
                'lastSeen': None
            }
            
            doc_ref = self.firestore_client.collection('devices').document(device_id)
            doc_ref.set(device_data)
            
            print(f'Device registered: {device_id}')
            
        except Exception as e:
            print(f'Failed to register device {device_id}: {e}')
            raise
    
    def send_device_command(self, device_id: str, command: Dict[str, Any]):
        """デバイスコマンド送信"""
        try:
            topic = f'devices/{device_id}/commands'
            command_json = json.dumps(command)
            
            result = self.mqtt_client.publish(topic, command_json, qos=1)
            
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                print(f'Command sent to {device_id}: {command}')
            else:
                raise Exception(f'Failed to publish command: {result.rc}')
            
        except Exception as e:
            print(f'Failed to send command to {device_id}: {e}')
            raise
    
    def start(self):
        """サービス開始"""
        port = int(os.environ.get('PORT', 8080))
        
        print(f'Starting MQTT Proxy on port {port}')
        print(f'Project ID: {self.project_id}')
        
        self.app.run(
            host='0.0.0.0',
            port=port,
            debug=os.environ.get('FLASK_ENV') == 'development'
        )

# サービス起動
if __name__ == '__main__':
    proxy = GoogleCloudMQTTProxy()
    proxy.start()
```

### 8.3.2 Cloud Functions でのメッセージ処理

```python
# Cloud Functions: Pub/Sub トリガー関数
from google.cloud import bigquery
from google.cloud import firestore
from google.cloud import pubsub_v1
import base64
import json
import functions_framework
from datetime import datetime
from typing import Dict, Any, List

# クライアントの初期化
bigquery_client = bigquery.Client()
firestore_client = firestore.Client()
publisher = pubsub_v1.PublisherClient()

@functions_framework.cloud_event
def process_telemetry(cloud_event):
    """
    Pub/Sub トリガー関数 - テレメトリデータ処理
    """
    try:
        # Pub/Sub メッセージのデコード
        message_data = base64.b64decode(cloud_event.data['message']['data']).decode()
        telemetry_data = json.loads(message_data)
        
        print(f'Processing telemetry: {telemetry_data}')
        
        device_id = telemetry_data.get('deviceId')
        data = telemetry_data.get('data', {})
        timestamp = telemetry_data.get('timestamp')
        
        if not device_id or not data:
            print('Invalid telemetry data: missing deviceId or data')
            return
        
        # BigQuery にテレメトリーデータ保存
        save_telemetry_to_bigquery(device_id, data, timestamp)
        
        # 閾値チェックとアラート処理
        check_thresholds_and_alert(device_id, data)
        
        # デバイス状態の更新
        update_device_status(device_id, timestamp)
        
        print(f'Telemetry processed for device: {device_id}')
        
    except Exception as error:
        print(f'Error processing telemetry: {error}')
        raise

def save_telemetry_to_bigquery(device_id: str, data: Dict[str, Any], timestamp: str):
    """
    テレメトリーデータをBigQueryに保存
    """
    try:
        dataset_ref = bigquery_client.dataset('iot_data')
        table_ref = dataset_ref.table('telemetry')
        table = bigquery_client.get_table(table_ref)
        
        row = {
            'device_id': device_id,
            'timestamp': timestamp,
            'temperature': data.get('temperature'),
            'humidity': data.get('humidity'),
            'pressure': data.get('pressure'),
            'raw_data': json.dumps(data),
            'processed_at': datetime.now().isoformat()
        }
        
        # データが None の場合は除外
        row = {k: v for k, v in row.items() if v is not None}
        
        errors = bigquery_client.insert_rows_json(table, [row])
        
        if errors:
            print(f'BigQuery insert errors: {errors}')
        else:
            print(f'Telemetry data saved to BigQuery for device: {device_id}')
            
    except Exception as e:
        print(f'Failed to save telemetry to BigQuery: {e}')
        raise

def check_thresholds_and_alert(device_id: str, data: Dict[str, Any]):
    """
    閾値チェックとアラート処理
    """
    try:
        # デバイス設定の取得
        device_ref = firestore_client.collection('devices').document(device_id)
        device_doc = device_ref.get()
        
        if not device_doc.exists:
            print(f'Device {device_id} not found in Firestore')
            return
        
        device_config = device_doc.to_dict()
        thresholds = device_config.get('thresholds', {})
        
        if not thresholds:
            print(f'No thresholds configured for device {device_id}')
            return
        
        # 閾値チェック
        alerts = []
        
        # 温度チェック
        temperature = data.get('temperature')
        if temperature and 'temperature' in thresholds:
            temp_threshold = thresholds['temperature']
            if temperature > temp_threshold.get('max', float('inf')):
                alerts.append({
                    'type': 'HIGH_TEMPERATURE',
                    'value': temperature,
                    'threshold': temp_threshold['max'],
                    'severity': 'critical'
                })
            elif temperature < temp_threshold.get('min', float('-inf')):
                alerts.append({
                    'type': 'LOW_TEMPERATURE',
                    'value': temperature,
                    'threshold': temp_threshold['min'],
                    'severity': 'warning'
                })
        
        # 湿度チェック
        humidity = data.get('humidity')
        if humidity and 'humidity' in thresholds:
            humidity_threshold = thresholds['humidity']
            if humidity > humidity_threshold.get('max', float('inf')):
                alerts.append({
                    'type': 'HIGH_HUMIDITY',
                    'value': humidity,
                    'threshold': humidity_threshold['max'],
                    'severity': 'warning'
                })
        
        # 圧力チェック
        pressure = data.get('pressure')
        if pressure and 'pressure' in thresholds:
            pressure_threshold = thresholds['pressure']
            if pressure > pressure_threshold.get('max', float('inf')):
                alerts.append({
                    'type': 'HIGH_PRESSURE',
                    'value': pressure,
                    'threshold': pressure_threshold['max'],
                    'severity': 'critical'
                })
        
        # アラート送信
        for alert in alerts:
            send_alert(device_id, alert)
            
    except Exception as e:
        print(f'Error checking thresholds for device {device_id}: {e}')
        raise

def send_alert(device_id: str, alert: Dict[str, Any]):
    """
    アラートをPub/Sub経由で送信
    """
    try:
        import os
        project_id = os.environ.get('GCP_PROJECT')
        topic_name = 'iot-alerts'
        topic_path = publisher.topic_path(project_id, topic_name)
        
        alert_message = {
            'deviceId': device_id,
            'alertType': alert['type'],
            'value': alert['value'],
            'threshold': alert['threshold'],
            'severity': alert.get('severity', 'warning'),
            'timestamp': datetime.now().isoformat()
        }
        
        message_json = json.dumps(alert_message)
        message_bytes = message_json.encode('utf-8')
        
        future = publisher.publish(topic_path, message_bytes)
        future.result()  # 送信完了を待機
        
        print(f'Alert sent for device {device_id}: {alert}')
        
        # Firestoreにもアラート履歴を保存
        save_alert_to_firestore(device_id, alert_message)
        
    except Exception as e:
        print(f'Failed to send alert for device {device_id}: {e}')
        raise

def save_alert_to_firestore(device_id: str, alert: Dict[str, Any]):
    """
    アラートをFirestoreに保存
    """
    try:
        alerts_ref = firestore_client.collection('alerts')
        alerts_ref.add({
            **alert,
            'acknowledged': False,
            'created_at': firestore.SERVER_TIMESTAMP
        })
        
        print(f'Alert saved to Firestore for device {device_id}')
        
    except Exception as e:
        print(f'Failed to save alert to Firestore: {e}')

def update_device_status(device_id: str, timestamp: str):
    """
    デバイス状態の更新
    """
    try:
        device_ref = firestore_client.collection('devices').document(device_id)
        device_ref.update({
            'lastSeen': timestamp,
            'status': 'online',
            'updated_at': firestore.SERVER_TIMESTAMP
        })
        
        print(f'Device status updated for {device_id}')
        
    except Exception as e:
        print(f'Failed to update device status for {device_id}: {e}')
        
# デバイス状態監視用Cloud Function
@functions_framework.cloud_event
def monitor_device_status(cloud_event):
    """
    定期実行でデバイスのオフライン検出
    """
    try:
        from datetime import datetime, timedelta
        
        # 10分以上応答がないデバイスをオフラインと判定
        offline_threshold = datetime.now() - timedelta(minutes=10)
        
        devices_ref = firestore_client.collection('devices')
        query = devices_ref.where('status', '==', 'online')
        
        for device_doc in query.stream():
            device_data = device_doc.to_dict()
            last_seen_str = device_data.get('lastSeen')
            
            if last_seen_str:
                last_seen = datetime.fromisoformat(last_seen_str.replace('Z', '+00:00'))
                
                if last_seen < offline_threshold:
                    # デバイスをオフライン状態に更新
                    device_doc.reference.update({
                        'status': 'offline',
                        'updated_at': firestore.SERVER_TIMESTAMP
                    })
                    
                    # オフラインアラートを送信
                    send_alert(device_doc.id, {
                        'type': 'DEVICE_OFFLINE',
                        'value': None,
                        'threshold': None,
                        'severity': 'warning'
                    })
                    
                    print(f'Device {device_doc.id} marked as offline')
        
    except Exception as e:
        print(f'Error monitoring device status: {e}')
        raise
```

## 8.4 マルチクラウド戦略

### 8.4.1 クラウドアグノスティックMQTTクライアント

```python
import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from abc import ABC, abstractmethod
import random

# AWS IoT用のインポート
try:
    from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTClient
except ImportError:
    AWSIoTMQTTClient = None

# Azure IoT用のインポート
try:
    from azure.iot.device import IoTHubDeviceClient, Message
except ImportError:
    IoTHubDeviceClient = None
    Message = None

# 標準MQTTクライアント
import paho.mqtt.client as mqtt

class CloudProvider(ABC):
    """クラウドプロバイダーの抽象基底クラス"""
    
    @abstractmethod
    async def connect(self) -> bool:
        pass
    
    @abstractmethod
    async def disconnect(self):
        pass
    
    @abstractmethod
    async def publish_telemetry(self, data: Dict[str, Any]) -> bool:
        pass
    
    @abstractmethod
    def is_connected(self) -> bool:
        pass

class AWSProvider(CloudProvider):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[AWSIoTMQTTClient] = None
        self.connected = False
        
        if AWSIoTMQTTClient is None:
            raise ImportError("AWSIoTPythonSDK not available")
    
    async def connect(self) -> bool:
        try:
            self.client = AWSIoTMQTTClient(self.config['thingName'])
            self.client.configureEndpoint(self.config['endpoint'], 8883)
            self.client.configureCredentials(
                './AmazonRootCA1.pem',
                self.config['keyPath'],
                self.config['certPath']
            )
            
            result = self.client.connect()
            self.connected = result
            return result
        except Exception as e:
            print(f"AWS connection failed: {e}")
            return False
    
    async def disconnect(self):
        if self.client and self.connected:
            self.client.disconnect()
            self.connected = False
    
    async def publish_telemetry(self, data: Dict[str, Any]) -> bool:
        if not self.connected or not self.client:
            return False
        
        try:
            message = {
                **data,
                'timestamp': datetime.now().isoformat(),
                'source': 'multi-cloud-client'
            }
            
            result = self.client.publish('telemetry/data', json.dumps(message), 1)
            return result
        except Exception as e:
            print(f"AWS publish failed: {e}")
            return False
    
    def is_connected(self) -> bool:
        return self.connected

class AzureProvider(CloudProvider):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[IoTHubDeviceClient] = None
        self.connected = False
        
        if IoTHubDeviceClient is None:
            raise ImportError("azure-iot-device not available")
    
    async def connect(self) -> bool:
        try:
            self.client = IoTHubDeviceClient.create_from_connection_string(
                self.config['connectionString']
            )
            await self.client.connect()
            self.connected = True
            return True
        except Exception as e:
            print(f"Azure connection failed: {e}")
            return False
    
    async def disconnect(self):
        if self.client and self.connected:
            await self.client.disconnect()
            self.connected = False
    
    async def publish_telemetry(self, data: Dict[str, Any]) -> bool:
        if not self.connected or not self.client:
            return False
        
        try:
            message_data = {
                **data,
                'timestamp': datetime.now().isoformat(),
                'source': 'multi-cloud-client'
            }
            
            message = Message(json.dumps(message_data))
            message.custom_properties['deviceType'] = 'multi-cloud-sensor'
            
            await self.client.send_message(message)
            return True
        except Exception as e:
            print(f"Azure publish failed: {e}")
            return False
    
    def is_connected(self) -> bool:
        return self.connected

class GCPProvider(CloudProvider):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.client: Optional[mqtt.Client] = None
        self.connected = False
    
    async def connect(self) -> bool:
        try:
            self.client = mqtt.Client(client_id=f"gcp-client-{int(time.time())}")
            
            options = self.config.get('options', {})
            if 'username' in options and 'password' in options:
                self.client.username_pw_set(options['username'], options['password'])
            
            def on_connect(client, userdata, flags, rc):
                self.connected = (rc == 0)
            
            self.client.on_connect = on_connect
            
            broker_url = self.config['brokerUrl'].replace('mqtts://', '').replace('mqtt://', '')
            port = 8883 if self.config['brokerUrl'].startswith('mqtts://') else 1883
            
            self.client.connect(broker_url, port, 60)
            self.client.loop_start()
            
            # 接続完了を待機
            for _ in range(50):  # 5秒待機
                if self.connected:
                    return True
                await asyncio.sleep(0.1)
            
            return False
        except Exception as e:
            print(f"GCP connection failed: {e}")
            return False
    
    async def disconnect(self):
        if self.client and self.connected:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
    
    async def publish_telemetry(self, data: Dict[str, Any]) -> bool:
        if not self.connected or not self.client:
            return False
        
        try:
            message = {
                **data,
                'timestamp': datetime.now().isoformat(),
                'source': 'multi-cloud-client'
            }
            
            result = self.client.publish('devices/telemetry', json.dumps(message), qos=1)
            return result.rc == mqtt.MQTT_ERR_SUCCESS
        except Exception as e:
            print(f"GCP publish failed: {e}")
            return False
    
    def is_connected(self) -> bool:
        return self.connected

class MultiCloudMQTTClient:
    def __init__(self, configs: Dict[str, Dict[str, Any]]):
        self.configs = configs
        self.clients: Dict[str, CloudProvider] = {}
        self.active_client: Optional[Dict[str, Any]] = None
        self.fallback_order = ['aws', 'azure', 'gcp']
    
    async def initialize(self):
        """各クラウドプロバイダーへの接続を初期化"""
        for provider, config in self.configs.items():
            try:
                client = await self.create_client(provider, config)
                self.clients[provider] = client
                print(f"Initialized {provider} client")
            except Exception as error:
                print(f"Failed to initialize {provider} client: {error}")
        
        # プライマリクライアントの選択
        await self.select_active_client()
    
    async def create_client(self, provider: str, config: Dict[str, Any]) -> CloudProvider:
        """プロバイダー固有のクライアントを作成"""
        if provider == 'aws':
            return AWSProvider(config)
        elif provider == 'azure':
            return AzureProvider(config)
        elif provider == 'gcp':
            return GCPProvider(config)
        else:
            raise ValueError(f"Unknown provider: {provider}")
    
    async def select_active_client(self):
        """アクティブクライアントの選択"""
        for provider in self.fallback_order:
            if provider in self.clients:
                client = self.clients[provider]
                if await self.test_connection(client, provider):
                    self.active_client = {'provider': provider, 'client': client}
                    print(f"Active client set to: {provider}")
                    return
        
        if not self.active_client:
            raise Exception('No cloud provider available')
    
    async def test_connection(self, client: CloudProvider, provider: str) -> bool:
        """接続テスト"""
        try:
            if not client.is_connected():
                return await client.connect()
            return True
        except Exception:
            return False
    
    async def publish_telemetry(self, data: Dict[str, Any]):
        """テレメトリデータの送信"""
        if not self.active_client:
            raise Exception('No active client available')
        
        try:
            success = await self.active_client['client'].publish_telemetry(data)
            if success:
                print(f"Published to {self.active_client['provider']}: {data}")
            else:
                raise Exception("Publish failed")
        except Exception as error:
            print(f"Failed to publish to {self.active_client['provider']}: {error}")
            
            # フェイルオーバー実行
            await self.execute_failover()
            
            # リトライ
            if self.active_client:
                success = await self.active_client['client'].publish_telemetry(data)
                if success:
                    print(f"Retry successful to {self.active_client['provider']}: {data}")
                else:
                    raise Exception("Retry failed")
    
    async def execute_failover(self):
        """フェイルオーバーの実行"""
        print('Executing failover...')
        
        current_index = self.fallback_order.index(self.active_client['provider'])
        next_providers = self.fallback_order[current_index + 1:]
        
        for provider in next_providers:
            if provider in self.clients:
                client = self.clients[provider]
                if await self.test_connection(client, provider):
                    self.active_client = {'provider': provider, 'client': client}
                    print(f"Failover completed to: {provider}")
                    return
        
        # 全てのプロバイダーが利用不可
        self.active_client = None
        raise Exception('All cloud providers are unavailable')
    
    def get_current_provider(self) -> Optional[str]:
        """現在のプロバイダーを取得"""
        return self.active_client['provider'] if self.active_client else None
    
    async def get_status(self) -> Dict[str, Any]:
        """接続状態の取得"""
        status = {
            'activeProvider': self.get_current_provider(),
            'availableProviders': []
        }
        
        for provider, client in self.clients.items():
            is_connected = await self.test_connection(client, provider)
            status['availableProviders'].append({
                'provider': provider,
                'connected': is_connected
            })
        
        return status
    
    async def shutdown(self):
        """全クライアントの切断"""
        for client in self.clients.values():
            await client.disconnect()
        print("All clients disconnected")

# 使用例
async def main():
    multi_cloud_configs = {
        'aws': {
            'endpoint': 'your-endpoint.iot.us-east-1.amazonaws.com',
            'certPath': './aws-cert.pem',
            'keyPath': './aws-key.pem',
            'thingName': 'multi-cloud-device'
        },
        'azure': {
            'connectionString': 'HostName=your-hub.azure-devices.net;DeviceId=multi-cloud-device;SharedAccessKey=your-key'
        },
        'gcp': {
            'brokerUrl': 'mqtts://your-mqtt-proxy.run.app',
            'options': {
                'username': 'gcp-device',
                'password': 'device-token'
            }
        }
    }
    
    multi_cloud_client = MultiCloudMQTTClient(multi_cloud_configs)
    
    try:
        await multi_cloud_client.initialize()
        
        # テレメトリ送信タスク
        async def telemetry_loop():
            while True:
                telemetry_data = {
                    'temperature': 20 + random.random() * 15,
                    'humidity': 40 + random.random() * 30,
                    'deviceId': 'multi-cloud-sensor-001'
                }
                
                try:
                    await multi_cloud_client.publish_telemetry(telemetry_data)
                except Exception as error:
                    print(f'Failed to publish telemetry: {error}')
                
                await asyncio.sleep(30)
        
        # ステータス監視タスク
        async def status_loop():
            while True:
                status = await multi_cloud_client.get_status()
                print(f'Multi-cloud status: {status}')
                await asyncio.sleep(60)
        
        # タスクを並行実行
        await asyncio.gather(
            telemetry_loop(),
            status_loop()
        )
        
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        await multi_cloud_client.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

## 参考リンク

- [AWS IoT Core Developer Guide](https://docs.aws.amazon.com/iot/latest/developerguide/)
- [Azure IoT Hub Documentation](https://docs.microsoft.com/en-us/azure/iot-hub/)
- [Google Cloud Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [AWS IoT Device SDK v2](https://github.com/aws/aws-iot-device-sdk-js-v2)
- [Azure IoT SDK for Node.js](https://github.com/Azure/azure-iot-sdk-node)

---

**次の章**: [09-file-transfer.md](09-file-transfer.md) - ファイル転送とIoTデバイス管理