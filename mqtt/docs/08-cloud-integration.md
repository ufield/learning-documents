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

#### Node.js デバイス実装

```javascript
const awsIot = require('aws-iot-device-sdk-v2');
const { mqtt, io, iot } = awsIot;

class AWSIoTDevice {
    constructor(options) {
        this.thingName = options.thingName;
        this.endpoint = options.endpoint;
        this.region = options.region;
        this.connection = null;
        
        // 証明書設定
        this.tlsContext = io.TlsContextOptions.create_client_with_mtls_from_path(
            options.certPath,    // certificate.pem.crt
            options.keyPath      // private.pem.key
        );
    }
    
    async connect() {
        const config = iot.AwsIotMqttConnectionConfigBuilder.new_mtls_builder_from_path(
            this.certPath,
            this.keyPath
        )
        .with_certificate_authority_from_path(null, './AmazonRootCA1.pem')
        .with_clean_session(false)
        .with_client_id(this.thingName)
        .with_endpoint(this.endpoint)
        .build();
        
        const client = new mqtt.MqttClient();
        this.connection = client.new_connection(config);
        
        this.connection.on('connect', () => {
            console.log(`Connected to AWS IoT Core: ${this.thingName}`);
        });
        
        this.connection.on('error', (error) => {
            console.error('Connection error:', error);
        });
        
        await this.connection.connect();
        return this.connection;
    }
    
    async publishSensorData(sensorType, value, metadata = {}) {
        const topic = `sensors/${this.thingName}/${sensorType}`;
        const message = {
            deviceId: this.thingName,
            sensorType: sensorType,
            value: value,
            timestamp: new Date().toISOString(),
            metadata: metadata
        };
        
        await this.connection.publish(topic, JSON.stringify(message), mqtt.QoS.AtLeastOnce);
        console.log(`Published to ${topic}:`, message);
    }
    
    async subscribeToCommands(callback) {
        const topic = `commands/${this.thingName}/+`;
        
        await this.connection.subscribe(topic, mqtt.QoS.AtLeastOnce, (topic, payload) => {
            try {
                const message = JSON.parse(payload.toString());
                const command = topic.split('/').pop();
                callback(command, message);
            } catch (error) {
                console.error('Failed to parse command:', error);
            }
        });
        
        console.log(`Subscribed to commands: ${topic}`);
    }
    
    async updateDeviceShadow(state) {
        const shadowTopic = `$aws/things/${this.thingName}/shadow/update`;
        const shadowMessage = {
            state: {
                reported: state
            }
        };
        
        await this.connection.publish(shadowTopic, JSON.stringify(shadowMessage), mqtt.QoS.AtLeastOnce);
        console.log('Device shadow updated:', state);
    }
    
    async subscribeShadowUpdates(callback) {
        const acceptedTopic = `$aws/things/${this.thingName}/shadow/update/accepted`;
        const deltasTopic = `$aws/things/${this.thingName}/shadow/update/delta`;
        
        // シャドウ更新成功通知
        await this.connection.subscribe(acceptedTopic, mqtt.QoS.AtLeastOnce, (topic, payload) => {
            const message = JSON.parse(payload.toString());
            callback('accepted', message);
        });
        
        // 差分検出通知
        await this.connection.subscribe(deltasTopic, mqtt.QoS.AtLeastOnce, (topic, payload) => {
            const message = JSON.parse(payload.toString());
            callback('delta', message);
        });
    }
}

// 使用例
async function main() {
    const device = new AWSIoTDevice({
        thingName: 'temperature-sensor-001',
        endpoint: 'your-endpoint.iot.us-east-1.amazonaws.com',
        region: 'us-east-1',
        certPath: './certificate.pem.crt',
        keyPath: './private.pem.key'
    });
    
    await device.connect();
    
    // コマンド受信設定
    await device.subscribeToCommands((command, message) => {
        console.log(`Received command ${command}:`, message);
        
        switch (command) {
            case 'calibrate':
                // キャリブレーション実行
                console.log('Executing calibration...');
                break;
            case 'set_interval':
                // サンプリング間隔変更
                console.log(`Setting interval to ${message.interval} seconds`);
                break;
        }
    });
    
    // シャドウ更新監視
    await device.subscribeShadowUpdates((type, message) => {
        if (type === 'delta') {
            console.log('Shadow delta received:', message.state);
            // 設定変更を適用
            device.updateDeviceShadow(message.state);
        }
    });
    
    // 定期的なセンサーデータ送信
    setInterval(async () => {
        const temperature = 20 + Math.random() * 10;
        const humidity = 40 + Math.random() * 20;
        
        await device.publishSensorData('temperature', temperature, {
            unit: 'celsius',
            accuracy: '±0.5°C'
        });
        
        await device.publishSensorData('humidity', humidity, {
            unit: 'percent',
            accuracy: '±2%'
        });
    }, 30000);
}

main().catch(console.error);
```

### 8.1.2 IoT Rules Engine 活用

```javascript
// CloudFormation テンプレートによるRules Engine設定
const ruleTemplate = {
    AWSTemplateFormatVersion: '2010-09-09',
    Resources: {
        TemperatureAlertRule: {
            Type: 'AWS::IoT::TopicRule',
            Properties: {
                RuleName: 'TemperatureAlertRule',
                TopicRulePayload: {
                    Sql: `
                        SELECT 
                            deviceId,
                            sensorType,
                            value as temperature,
                            timestamp,
                            'HIGH_TEMPERATURE' as alertType
                        FROM 'sensors/+/temperature' 
                        WHERE value > 35
                    `,
                    Actions: [
                        {
                            Lambda: {
                                FunctionArn: 'arn:aws:lambda:region:account:function:ProcessHighTemperature'
                            }
                        },
                        {
                            Sns: {
                                TargetArn: 'arn:aws:sns:region:account:temperature-alerts',
                                MessageFormat: 'JSON'
                            }
                        },
                        {
                            DynamoDBv2: {
                                TableName: 'TemperatureAlerts',
                                RoleArn: 'arn:aws:iam::account:role/IoTRuleRole',
                                PutItem: {
                                    'deviceId': {
                                        S: '${deviceId}'
                                    },
                                    'timestamp': {
                                        S: '${timestamp}'
                                    },
                                    'temperature': {
                                        N: '${temperature}'
                                    },
                                    'alertType': {
                                        S: '${alertType}'
                                    }
                                }
                            }
                        }
                    ]
                }
            }
        }
    }
};
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

```javascript
const { Client } = require('azure-iot-device');
const { Mqtt } = require('azure-iot-device-mqtt');

class AzureIoTDevice {
    constructor(connectionString) {
        this.connectionString = connectionString;
        this.client = Client.fromConnectionString(connectionString, Mqtt);
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.client.on('connect', () => {
            console.log('Connected to Azure IoT Hub');
        });
        
        this.client.on('error', (err) => {
            console.error('Connection error:', err);
        });
        
        this.client.on('disconnect', () => {
            console.log('Disconnected from Azure IoT Hub');
        });
        
        // C2D (Cloud-to-Device) メッセージ受信
        this.client.on('message', (message) => {
            console.log('C2D Message received:');
            console.log('- Data:', message.data.toString());
            console.log('- Properties:', message.properties);
            
            // メッセージ処理完了通知
            this.client.complete(message, (err) => {
                if (err) {
                    console.error('Failed to complete message:', err);
                } else {
                    console.log('Message completed');
                }
            });
        });
        
        // Direct Methods の受信
        this.client.onDeviceMethod('reboot', (request, response) => {
            console.log('Reboot method called');
            
            // リブート処理のシミュレーション
            setTimeout(() => {
                response.send(200, 'Reboot completed', (err) => {
                    if (err) {
                        console.error('Failed to send method response:', err);
                    }
                });
            }, 2000);
        });
        
        this.client.onDeviceMethod('getStatus', (request, response) => {
            const status = {
                uptime: process.uptime(),
                memory: process.memoryUsage(),
                timestamp: new Date().toISOString()
            };
            
            response.send(200, status, (err) => {
                if (err) {
                    console.error('Failed to send status response:', err);
                }
            });
        });
    }
    
    async connect() {
        return new Promise((resolve, reject) => {
            this.client.open((err) => {
                if (err) {
                    reject(err);
                } else {
                    resolve();
                }
            });
        });
    }
    
    async sendTelemetry(data) {
        const message = new Message(JSON.stringify(data));
        
        // メッセージプロパティの設定
        message.properties.add('temperatureAlert', data.temperature > 30 ? 'true' : 'false');
        message.properties.add('deviceType', 'sensor');
        
        return new Promise((resolve, reject) => {
            this.client.sendEvent(message, (err) => {
                if (err) {
                    reject(err);
                } else {
                    console.log('Telemetry sent:', data);
                    resolve();
                }
            });
        });
    }
    
    async updateReportedProperties(properties) {
        return new Promise((resolve, reject) => {
            this.client.getTwin((err, twin) => {
                if (err) {
                    reject(err);
                    return;
                }
                
                twin.properties.reported.update(properties, (err) => {
                    if (err) {
                        reject(err);
                    } else {
                        console.log('Reported properties updated:', properties);
                        resolve();
                    }
                });
            });
        });
    }
    
    subscribeToDesiredProperties(callback) {
        this.client.getTwin((err, twin) => {
            if (err) {
                console.error('Failed to get twin:', err);
                return;
            }
            
            twin.on('properties.desired', (delta) => {
                console.log('Desired properties update:', delta);
                callback(delta);
            });
        });
    }
}

// 使用例
const { Message } = require('azure-iot-device');

async function main() {
    // 接続文字列（Azure ポータルから取得）
    const connectionString = 'HostName=your-hub.azure-devices.net;DeviceId=your-device;SharedAccessKey=your-key';
    
    const device = new AzureIoTDevice(connectionString);
    await device.connect();
    
    // Desired Properties の監視
    device.subscribeToDesiredProperties(async (delta) => {
        // 設定変更をReported Propertiesに反映
        await device.updateReportedProperties(delta);
    });
    
    // 定期的なテレメトリ送信
    setInterval(async () => {
        const telemetryData = {
            temperature: 20 + Math.random() * 15,
            humidity: 40 + Math.random() * 30,
            pressure: 1000 + Math.random() * 100,
            timestamp: new Date().toISOString()
        };
        
        try {
            await device.sendTelemetry(telemetryData);
        } catch (error) {
            console.error('Failed to send telemetry:', error);
        }
    }, 10000);
    
    // デバイス状態の定期更新
    setInterval(async () => {
        const reportedProperties = {
            connectivity: 'connected',
            lastSeen: new Date().toISOString(),
            batteryLevel: Math.floor(Math.random() * 100)
        };
        
        try {
            await device.updateReportedProperties(reportedProperties);
        } catch (error) {
            console.error('Failed to update properties:', error);
        }
    }, 60000);
}

main().catch(console.error);
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

```javascript
// modules/mqtt-bridge/app.js
const { ModuleClient } = require('azure-iot-device');
const { Mqtt } = require('azure-iot-device-mqtt');
const mqtt = require('mqtt');

class MQTTBridgeModule {
    constructor() {
        this.moduleClient = null;
        this.localMqttClient = null;
        this.bridgeConfig = {
            localBroker: 'mqtt://localhost:1883',
            topicMapping: {
                'local/sensors/+/data': 'cloud/sensors/{deviceId}/telemetry',
                'cloud/commands/+': 'local/commands/{deviceId}'
            }
        };
    }
    
    async initialize() {
        // IoT Edge Module Client の初期化
        this.moduleClient = await ModuleClient.fromEnvironment(Mqtt);
        await this.moduleClient.open();
        
        console.log('IoT Edge module connected');
        
        // ローカルMQTTブローカーへの接続
        this.localMqttClient = mqtt.connect(this.bridgeConfig.localBroker);
        
        this.localMqttClient.on('connect', () => {
            console.log('Connected to local MQTT broker');
            this.setupLocalSubscriptions();
        });
        
        // クラウドからのメッセージ受信
        this.moduleClient.on('inputMessage', (inputName, message) => {
            this.handleCloudMessage(inputName, message);
        });
        
        this.setupModuleTwin();
    }
    
    setupLocalSubscriptions() {
        // ローカルMQTTトピックの購読
        Object.keys(this.bridgeConfig.topicMapping).forEach(localTopic => {
            if (localTopic.startsWith('local/')) {
                this.localMqttClient.subscribe(localTopic, (err) => {
                    if (!err) {
                        console.log(`Subscribed to local topic: ${localTopic}`);
                    }
                });
            }
        });
        
        this.localMqttClient.on('message', (topic, message) => {
            this.handleLocalMessage(topic, message);
        });
    }
    
    handleLocalMessage(topic, message) {
        // ローカルメッセージをクラウドに転送
        const deviceId = this.extractDeviceId(topic);
        const cloudTopic = this.mapToCloudTopic(topic, deviceId);
        
        if (cloudTopic) {
            const outputMessage = new Message(message);
            outputMessage.properties.add('source', 'local-mqtt');
            outputMessage.properties.add('originalTopic', topic);
            outputMessage.properties.add('deviceId', deviceId);
            
            this.moduleClient.sendOutputEvent('upstreamOutput', outputMessage, (err) => {
                if (err) {
                    console.error('Failed to send message to cloud:', err);
                } else {
                    console.log(`Bridged message from ${topic} to cloud`);
                }
            });
        }
    }
    
    handleCloudMessage(inputName, message) {
        // クラウドメッセージをローカルに転送
        console.log(`Received cloud message on ${inputName}`);
        
        const deviceId = message.properties.propertyList.find(p => p.key === 'deviceId')?.value;
        const targetTopic = message.properties.propertyList.find(p => p.key === 'targetTopic')?.value;
        
        if (deviceId && targetTopic) {
            const localTopic = targetTopic.replace('{deviceId}', deviceId);
            
            this.localMqttClient.publish(localTopic, message.data, (err) => {
                if (!err) {
                    console.log(`Bridged message from cloud to ${localTopic}`);
                }
            });
        }
        
        this.moduleClient.complete(message);
    }
    
    setupModuleTwin() {
        this.moduleClient.getTwin((err, twin) => {
            if (err) {
                console.error('Failed to get module twin:', err);
                return;
            }
            
            // Desired Properties の監視
            twin.on('properties.desired', (delta) => {
                console.log('Module twin desired properties update:', delta);
                this.updateBridgeConfig(delta);
            });
            
            // Reported Properties の更新
            const reportedProperties = {
                status: 'running',
                lastStartTime: new Date().toISOString(),
                version: '1.0.0'
            };
            
            twin.properties.reported.update(reportedProperties, (err) => {
                if (err) {
                    console.error('Failed to update reported properties:', err);
                }
            });
        });
    }
    
    updateBridgeConfig(delta) {
        if (delta.topicMapping) {
            this.bridgeConfig.topicMapping = { ...this.bridgeConfig.topicMapping, ...delta.topicMapping };
            console.log('Updated topic mapping configuration');
        }
    }
    
    extractDeviceId(topic) {
        // トピックからデバイスIDを抽出
        const parts = topic.split('/');
        return parts[2] || 'unknown';
    }
    
    mapToCloudTopic(localTopic, deviceId) {
        const mapping = this.bridgeConfig.topicMapping[localTopic.replace(/\/[^/]+\//, '/+/')];
        return mapping ? mapping.replace('{deviceId}', deviceId) : null;
    }
}

// モジュール起動
async function main() {
    const bridgeModule = new MQTTBridgeModule();
    await bridgeModule.initialize();
    
    console.log('MQTT Bridge Module started');
    
    // プロセス終了時のクリーンアップ
    process.on('SIGTERM', () => {
        console.log('SIGTERM received, shutting down gracefully');
        process.exit(0);
    });
}

main().catch(err => {
    console.error('Module startup failed:', err);
    process.exit(1);
});
```

## 8.3 Google Cloud IoT Platform

**注意**: Google Cloud IoT Core は2023年8月16日にサービス終了しました。以下は代替アーキテクチャの例です。

### 8.3.1 Cloud Pub/Sub + Cloud Run アーキテクチャ

```javascript
// Cloud Run で動作するMQTTプロキシサービス
const express = require('express');
const { PubSub } = require('@google-cloud/pubsub');
const mqtt = require('mqtt');

class GoogleCloudMQTTProxy {
    constructor() {
        this.app = express();
        this.pubsub = new PubSub();
        this.mqttClient = null;
        
        this.setupExpress();
        this.connectToMQTTBroker();
    }
    
    setupExpress() {
        this.app.use(express.json());
        
        // デバイス登録エンドポイント
        this.app.post('/devices/:deviceId/register', async (req, res) => {
            const deviceId = req.params.deviceId;
            const config = req.body;
            
            try {
                await this.registerDevice(deviceId, config);
                res.json({ success: true, deviceId });
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
        
        // デバイスコマンド送信エンドポイント
        this.app.post('/devices/:deviceId/commands', async (req, res) => {
            const deviceId = req.params.deviceId;
            const command = req.body;
            
            try {
                await this.sendDeviceCommand(deviceId, command);
                res.json({ success: true });
            } catch (error) {
                res.status(500).json({ error: error.message });
            }
        });
        
        // ヘルスチェック
        this.app.get('/health', (req, res) => {
            res.json({ status: 'healthy', timestamp: new Date().toISOString() });
        });
    }
    
    async connectToMQTTBroker() {
        // マネージドMQTTサービス（EMQX Cloud、HiveMQ Cloud等）への接続
        this.mqttClient = mqtt.connect(process.env.MQTT_BROKER_URL, {
            username: process.env.MQTT_USERNAME,
            password: process.env.MQTT_PASSWORD,
            clientId: `gcp-proxy-${Date.now()}`
        });
        
        this.mqttClient.on('connect', () => {
            console.log('Connected to MQTT broker');
            this.setupMQTTSubscriptions();
        });
        
        this.mqttClient.on('message', (topic, message) => {
            this.handleMQTTMessage(topic, message);
        });
    }
    
    setupMQTTSubscriptions() {
        // デバイステレメトリー受信
        this.mqttClient.subscribe('devices/+/telemetry', { qos: 1 });
        
        // デバイス状態更新受信
        this.mqttClient.subscribe('devices/+/state', { qos: 1 });
        
        // デバイスイベント受信
        this.mqttClient.subscribe('devices/+/events/+', { qos: 1 });
    }
    
    async handleMQTTMessage(topic, message) {
        try {
            const topicParts = topic.split('/');
            const deviceId = topicParts[1];
            const messageType = topicParts[2];
            
            const data = JSON.parse(message.toString());
            
            // Cloud Pub/Sub にメッセージ転送
            const pubsubTopic = `projects/${process.env.PROJECT_ID}/topics/iot-${messageType}`;
            
            await this.pubsub.topic(`iot-${messageType}`).publish(Buffer.from(JSON.stringify({
                deviceId: deviceId,
                messageType: messageType,
                data: data,
                timestamp: new Date().toISOString(),
                originalTopic: topic
            })));
            
            console.log(`Message forwarded to Pub/Sub: ${topic}`);
            
        } catch (error) {
            console.error('Error handling MQTT message:', error);
        }
    }
    
    async registerDevice(deviceId, config) {
        // Firestore にデバイス情報保存
        const { Firestore } = require('@google-cloud/firestore');
        const firestore = new Firestore();
        
        await firestore.collection('devices').doc(deviceId).set({
            ...config,
            registeredAt: new Date().toISOString(),
            status: 'registered'
        });
        
        console.log(`Device registered: ${deviceId}`);
    }
    
    async sendDeviceCommand(deviceId, command) {
        const topic = `devices/${deviceId}/commands`;
        
        this.mqttClient.publish(topic, JSON.stringify(command), { qos: 1 }, (err) => {
            if (err) {
                throw new Error(`Failed to send command: ${err.message}`);
            }
            console.log(`Command sent to ${deviceId}:`, command);
        });
    }
    
    start() {
        const port = process.env.PORT || 8080;
        this.app.listen(port, () => {
            console.log(`MQTT Proxy started on port ${port}`);
        });
    }
}

// サービス起動
if (require.main === module) {
    const proxy = new GoogleCloudMQTTProxy();
    proxy.start();
}

module.exports = GoogleCloudMQTTProxy;
```

### 8.3.2 Cloud Functions でのメッセージ処理

```javascript
// Cloud Functions: Pub/Sub トリガー関数
const { BigQuery } = require('@google-cloud/bigquery');
const { Firestore } = require('@google-cloud/firestore');

const bigquery = new BigQuery();
const firestore = new Firestore();

exports.processTelemetry = async (message, context) => {
    try {
        // Pub/Sub メッセージのデコード
        const messageData = JSON.parse(Buffer.from(message.data, 'base64').toString());
        
        console.log('Processing telemetry:', messageData);
        
        const { deviceId, data, timestamp } = messageData;
        
        // BigQuery にテレメトリーデータ保存
        await saveTelemetryToBigQuery(deviceId, data, timestamp);
        
        // 閾値チェックとアラート処理
        await checkThresholdsAndAlert(deviceId, data);
        
        // デバイス状態の更新
        await updateDeviceStatus(deviceId, timestamp);
        
        console.log(`Telemetry processed for device: ${deviceId}`);
        
    } catch (error) {
        console.error('Error processing telemetry:', error);
        throw error;
    }
};

async function saveTelemetryToBigQuery(deviceId, data, timestamp) {
    const dataset = bigquery.dataset('iot_data');
    const table = dataset.table('telemetry');
    
    const row = {
        device_id: deviceId,
        timestamp: timestamp,
        temperature: data.temperature || null,
        humidity: data.humidity || null,
        pressure: data.pressure || null,
        raw_data: JSON.stringify(data)
    };
    
    await table.insert([row]);
}

async function checkThresholdsAndAlert(deviceId, data) {
    // デバイス設定の取得
    const deviceDoc = await firestore.collection('devices').doc(deviceId).get();
    const deviceConfig = deviceDoc.data();
    
    if (!deviceConfig || !deviceConfig.thresholds) {
        return;
    }
    
    // 閾値チェック
    const alerts = [];
    
    if (data.temperature && deviceConfig.thresholds.temperature) {
        if (data.temperature > deviceConfig.thresholds.temperature.max) {
            alerts.push({
                type: 'HIGH_TEMPERATURE',
                value: data.temperature,
                threshold: deviceConfig.thresholds.temperature.max
            });
        }
    }
    
    if (data.humidity && deviceConfig.thresholds.humidity) {
        if (data.humidity > deviceConfig.thresholds.humidity.max) {
            alerts.push({
                type: 'HIGH_HUMIDITY',
                value: data.humidity,
                threshold: deviceConfig.thresholds.humidity.max
            });
        }
    }
    
    // アラート送信
    for (const alert of alerts) {
        await sendAlert(deviceId, alert);
    }
}

async function sendAlert(deviceId, alert) {
    // Cloud Pub/Sub 経由でアラート送信
    const { PubSub } = require('@google-cloud/pubsub');
    const pubsub = new PubSub();
    
    const alertMessage = {
        deviceId: deviceId,
        alertType: alert.type,
        value: alert.value,
        threshold: alert.threshold,
        timestamp: new Date().toISOString()
    };
    
    await pubsub.topic('iot-alerts').publish(Buffer.from(JSON.stringify(alertMessage)));
    
    console.log(`Alert sent for device ${deviceId}:`, alert);
}

async function updateDeviceStatus(deviceId, timestamp) {
    await firestore.collection('devices').doc(deviceId).update({
        lastSeen: timestamp,
        status: 'online'
    });
}
```

## 8.4 マルチクラウド戦略

### 8.4.1 クラウドアグノスティックMQTTクライアント

```javascript
class MultiCloudMQTTClient {
    constructor(configs) {
        this.configs = configs;
        this.clients = new Map();
        this.activeClient = null;
        this.fallbackOrder = ['aws', 'azure', 'gcp'];
    }
    
    async initialize() {
        // 各クラウドプロバイダーへの接続を初期化
        for (const [provider, config] of Object.entries(this.configs)) {
            try {
                const client = await this.createClient(provider, config);
                this.clients.set(provider, client);
                console.log(`Initialized ${provider} client`);
            } catch (error) {
                console.error(`Failed to initialize ${provider} client:`, error);
            }
        }
        
        // プライマリクライアントの選択
        await this.selectActiveClient();
    }
    
    async createClient(provider, config) {
        switch (provider) {
            case 'aws':
                return await this.createAWSClient(config);
            case 'azure':
                return await this.createAzureClient(config);
            case 'gcp':
                return await this.createGCPClient(config);
            default:
                throw new Error(`Unknown provider: ${provider}`);
        }
    }
    
    async createAWSClient(config) {
        const awsIot = require('aws-iot-device-sdk-v2');
        // AWS IoT Core接続実装
        // (前述のAWS実装を参照)
    }
    
    async createAzureClient(config) {
        const { Client } = require('azure-iot-device');
        // Azure IoT Hub接続実装
        // (前述のAzure実装を参照)
    }
    
    async createGCPClient(config) {
        // GCP MQTT proxy実装
        const mqtt = require('mqtt');
        return mqtt.connect(config.brokerUrl, config.options);
    }
    
    async selectActiveClient() {
        for (const provider of this.fallbackOrder) {
            const client = this.clients.get(provider);
            if (client && await this.testConnection(client, provider)) {
                this.activeClient = { provider, client };
                console.log(`Active client set to: ${provider}`);
                break;
            }
        }
        
        if (!this.activeClient) {
            throw new Error('No cloud provider available');
        }
    }
    
    async testConnection(client, provider) {
        try {
            // 各プロバイダー固有の接続テスト
            switch (provider) {
                case 'aws':
                    return client.connection && client.connection.isConnected;
                case 'azure':
                    return client.isConnected();
                case 'gcp':
                    return client.connected;
                default:
                    return false;
            }
        } catch (error) {
            return false;
        }
    }
    
    async publishTelemetry(data) {
        if (!this.activeClient) {
            throw new Error('No active client available');
        }
        
        try {
            await this.publishToProvider(this.activeClient.provider, this.activeClient.client, data);
        } catch (error) {
            console.error(`Failed to publish to ${this.activeClient.provider}:`, error);
            
            // フェイルオーバー実行
            await this.executeFailover();
            
            // リトライ
            if (this.activeClient) {
                await this.publishToProvider(this.activeClient.provider, this.activeClient.client, data);
            }
        }
    }
    
    async publishToProvider(provider, client, data) {
        const message = {
            ...data,
            timestamp: new Date().toISOString(),
            source: 'multi-cloud-client'
        };
        
        switch (provider) {
            case 'aws':
                await client.publish('telemetry/data', JSON.stringify(message), { qos: 1 });
                break;
            case 'azure':
                await client.sendEvent(new Message(JSON.stringify(message)));
                break;
            case 'gcp':
                client.publish('devices/telemetry', JSON.stringify(message), { qos: 1 });
                break;
        }
        
        console.log(`Published to ${provider}:`, data);
    }
    
    async executeFailover() {
        console.log('Executing failover...');
        
        const currentIndex = this.fallbackOrder.indexOf(this.activeClient.provider);
        const nextProviders = this.fallbackOrder.slice(currentIndex + 1);
        
        for (const provider of nextProviders) {
            const client = this.clients.get(provider);
            if (client && await this.testConnection(client, provider)) {
                this.activeClient = { provider, client };
                console.log(`Failover completed to: ${provider}`);
                return;
            }
        }
        
        // 全てのプロバイダーが利用不可
        this.activeClient = null;
        throw new Error('All cloud providers are unavailable');
    }
    
    getCurrentProvider() {
        return this.activeClient ? this.activeClient.provider : null;
    }
    
    async getStatus() {
        const status = {
            activeProvider: this.getCurrentProvider(),
            availableProviders: []
        };
        
        for (const [provider, client] of this.clients.entries()) {
            const isConnected = await this.testConnection(client, provider);
            status.availableProviders.push({
                provider,
                connected: isConnected
            });
        }
        
        return status;
    }
}

// 使用例
const multiCloudConfigs = {
    aws: {
        endpoint: 'your-endpoint.iot.us-east-1.amazonaws.com',
        certPath: './aws-cert.pem',
        keyPath: './aws-key.pem',
        thingName: 'multi-cloud-device'
    },
    azure: {
        connectionString: 'HostName=your-hub.azure-devices.net;DeviceId=multi-cloud-device;SharedAccessKey=your-key'
    },
    gcp: {
        brokerUrl: 'mqtts://your-mqtt-proxy.run.app',
        options: {
            username: 'gcp-device',
            password: 'device-token'
        }
    }
};

async function main() {
    const multiCloudClient = new MultiCloudMQTTClient(multiCloudConfigs);
    await multiCloudClient.initialize();
    
    // 定期的なテレメトリ送信
    setInterval(async () => {
        const telemetryData = {
            temperature: 20 + Math.random() * 15,
            humidity: 40 + Math.random() * 30,
            deviceId: 'multi-cloud-sensor-001'
        };
        
        try {
            await multiCloudClient.publishTelemetry(telemetryData);
        } catch (error) {
            console.error('Failed to publish telemetry:', error);
        }
    }, 30000);
    
    // ステータス監視
    setInterval(async () => {
        const status = await multiCloudClient.getStatus();
        console.log('Multi-cloud status:', status);
    }, 60000);
}

main().catch(console.error);
```

## 参考リンク

- [AWS IoT Core Developer Guide](https://docs.aws.amazon.com/iot/latest/developerguide/)
- [Azure IoT Hub Documentation](https://docs.microsoft.com/en-us/azure/iot-hub/)
- [Google Cloud Pub/Sub Documentation](https://cloud.google.com/pubsub/docs)
- [AWS IoT Device SDK v2](https://github.com/aws/aws-iot-device-sdk-js-v2)
- [Azure IoT SDK for Node.js](https://github.com/Azure/azure-iot-sdk-node)

---

**次の章**: [09-file-transfer.md](09-file-transfer.md) - ファイル転送とIoTデバイス管理