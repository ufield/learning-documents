# 演習2: Raspberry Pi センサーネットワーク

## 概要

Raspberry Pi 4/Zero 2Wを使用して、多種類のセンサーを統合したIoTセンサーネットワークを構築します。複数のPiデバイスでセンサーデータを収集し、MQTTでデータ集約・分析を行います。

## 学習目標

- Raspberry Pi でのセンサー統合
- GPIO、I2C、SPI通信活用
- 複数デバイス間のMQTT連携
- エラーハンドリングと復旧処理
- 省電力モード実装

## 必要機材

### ハードウェア（Pi 1台分）
- Raspberry Pi 4B (4GB推奨) または Pi Zero 2W
- microSDカード (32GB以上)
- 5V 3A USB-C電源（Pi 4）/ microUSB電源（Zero 2W）

### センサー類
- **環境センサー**
  - DHT22/AM2302 (温湿度)
  - BMP280/BME280 (気圧/温湿度)
  - MQ-2 (可燃ガス)
  - BH1750 (照度)

- **モーションセンサー**
  - PIR HC-SR501 (人感)
  - HC-SR04 (超音波距離)
  - ADXL345 (3軸加速度)

- **その他**
  - DS18B20 (防水温度)
  - 土壌湿度センサー
  - Rain sensor
  - LED × 数個

### 電子部品
- ブレッドボード
- ジャンパーワイヤー (オス-メス、メス-メス)
- 抵抗各種 (220Ω, 1kΩ, 4.7kΩ, 10kΩ)
- プルアップ抵抗用 4.7kΩ

## 演習手順

### Step 1: Raspberry Pi セットアップ

#### 1.1 OS インストール

```bash
# Raspberry Pi Imager使用、またはコマンドライン
# Raspberry Pi OS Lite (64-bit) 推奨

# 初回起動設定
sudo raspi-config
# - SSH enable
# - I2C enable  
# - SPI enable
# - 1-Wire enable
# - GPU memory split: 16MB (headless時)

# システム更新
sudo apt update && sudo apt upgrade -y

# Python開発環境
sudo apt install -y python3-pip python3-venv git
sudo apt install -y i2c-tools python3-smbus python3-spidev
```

#### 1.2 センサーライブラリセットアップ

```bash
# 仮想環境作成
python3 -m venv ~/pi_mqtt_env
source ~/pi_mqtt_env/bin/activate

# 基本パッケージ
pip install -r requirements.txt

# GPIO確認
gpio readall  # WiringPi
i2cdetect -y 1  # I2Cデバイス確認
```

### Step 2: 統合センサー管理システム

#### 2.1 センサー抽象化レイヤー

`src/sensor_manager.py`:

```python
#!/usr/bin/env python3
import time
import json
import asyncio
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional
import RPi.GPIO as GPIO

# センサーライブラリ
import Adafruit_DHT
import board
import busio
import adafruit_bmp280
import adafruit_bh1750
import w1thermsensor

class BaseSensor(ABC):
    """センサー基底クラス"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        self.name = name
        self.config = config
        self.last_reading = None
        self.error_count = 0
        self.max_errors = config.get('max_errors', 5)
        self.enabled = True
        
        self.logger = logging.getLogger(f"sensor.{name}")
    
    @abstractmethod
    async def read(self) -> Optional[Dict[str, Any]]:
        """センサーデータ読み取り"""
        pass
    
    def is_healthy(self) -> bool:
        """センサー健全性チェック"""
        return self.enabled and self.error_count < self.max_errors
    
    def handle_error(self, error: Exception):
        """エラーハンドリング"""
        self.error_count += 1
        self.logger.error(f"Sensor error: {error}")
        
        if self.error_count >= self.max_errors:
            self.enabled = False
            self.logger.critical(f"Sensor {self.name} disabled due to errors")

class DHT22Sensor(BaseSensor):
    """DHT22 温湿度センサー"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.pin = config['pin']
        
    async def read(self) -> Optional[Dict[str, Any]]:
        try:
            humidity, temperature = Adafruit_DHT.read_retry(Adafruit_DHT.DHT22, self.pin)
            
            if humidity is not None and temperature is not None:
                data = {
                    'temperature_c': round(temperature, 2),
                    'humidity_percent': round(humidity, 2),
                    'heat_index_c': self._calculate_heat_index(temperature, humidity)
                }
                self.last_reading = data
                self.error_count = 0  # リセット
                return data
            else:
                raise ValueError("Failed to get valid reading")
                
        except Exception as e:
            self.handle_error(e)
            return None
    
    def _calculate_heat_index(self, temp_c: float, humidity: float) -> float:
        """体感温度計算"""
        if temp_c < 27:  # 80°F
            return temp_c
        
        temp_f = temp_c * 9/5 + 32
        hi_f = (-42.379 + 2.04901523 * temp_f + 10.14333127 * humidity -
                0.22475541 * temp_f * humidity - 6.83783e-3 * temp_f**2 -
                5.481717e-2 * humidity**2 + 1.22874e-3 * temp_f**2 * humidity +
                8.5282e-4 * temp_f * humidity**2 - 1.99e-6 * temp_f**2 * humidity**2)
        
        return round((hi_f - 32) * 5/9, 2)

class BMP280Sensor(BaseSensor):
    """BMP280 気圧センサー"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        try:
            i2c = busio.I2C(board.SCL, board.SDA)
            self.bmp = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)
            self.bmp.sea_level_pressure = config.get('sea_level_pressure', 1013.25)
        except Exception as e:
            self.handle_error(e)
            self.bmp = None
    
    async def read(self) -> Optional[Dict[str, Any]]:
        if not self.bmp:
            return None
            
        try:
            data = {
                'temperature_c': round(self.bmp.temperature, 2),
                'pressure_hpa': round(self.bmp.pressure, 2),
                'altitude_m': round(self.bmp.altitude, 1)
            }
            self.last_reading = data
            self.error_count = 0
            return data
            
        except Exception as e:
            self.handle_error(e)
            return None

class PIRMotionSensor(BaseSensor):
    """PIR人感センサー"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.pin = config['pin']
        self.motion_detected = False
        self.last_motion_time = None
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.pin, GPIO.IN)
        
        # 割り込み設定
        GPIO.add_event_detect(self.pin, GPIO.BOTH, 
                             callback=self._motion_callback, bouncetime=300)
    
    def _motion_callback(self, channel):
        """モーション検出コールバック"""
        if GPIO.input(channel):
            self.motion_detected = True
            self.last_motion_time = time.time()
    
    async def read(self) -> Optional[Dict[str, Any]]:
        try:
            current_state = GPIO.input(self.pin)
            motion_detected = self.motion_detected
            
            # フラグリセット
            self.motion_detected = False
            
            data = {
                'motion_detected': motion_detected,
                'current_state': bool(current_state),
                'last_motion_timestamp': self.last_motion_time
            }
            
            self.last_reading = data
            return data
            
        except Exception as e:
            self.handle_error(e)
            return None

class UltrasonicSensor(BaseSensor):
    """HC-SR04 超音波距離センサー"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        self.trig_pin = config['trig_pin']
        self.echo_pin = config['echo_pin']
        
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.trig_pin, GPIO.OUT)
        GPIO.setup(self.echo_pin, GPIO.IN)
        GPIO.output(self.trig_pin, False)
    
    async def read(self) -> Optional[Dict[str, Any]]:
        try:
            # トリガーパルス送信
            GPIO.output(self.trig_pin, True)
            await asyncio.sleep(0.00001)  # 10μs
            GPIO.output(self.trig_pin, False)
            
            # エコー測定
            timeout = time.time() + 0.1  # 100ms timeout
            
            # LOW→HIGH待機
            while GPIO.input(self.echo_pin) == 0:
                pulse_start = time.time()
                if pulse_start > timeout:
                    raise TimeoutError("Echo start timeout")
            
            # HIGH→LOW待機
            while GPIO.input(self.echo_pin) == 1:
                pulse_end = time.time()
                if pulse_end > timeout:
                    raise TimeoutError("Echo end timeout")
            
            # 距離計算 (音速: 343m/s)
            pulse_duration = pulse_end - pulse_start
            distance_cm = (pulse_duration * 34300) / 2
            
            data = {
                'distance_cm': round(distance_cm, 2),
                'pulse_duration_us': round(pulse_duration * 1000000, 2)
            }
            
            self.last_reading = data
            self.error_count = 0
            return data
            
        except Exception as e:
            self.handle_error(e)
            return None

class DS18B20Sensor(BaseSensor):
    """DS18B20 1-Wire温度センサー"""
    
    def __init__(self, name: str, config: Dict[str, Any]):
        super().__init__(name, config)
        try:
            sensor_id = config.get('sensor_id')
            if sensor_id:
                self.sensor = w1thermsensor.W1ThermSensor(sensor_id=sensor_id)
            else:
                self.sensor = w1thermsensor.W1ThermSensor()
        except Exception as e:
            self.handle_error(e)
            self.sensor = None
    
    async def read(self) -> Optional[Dict[str, Any]]:
        if not self.sensor:
            return None
            
        try:
            temperature = self.sensor.get_temperature()
            data = {
                'temperature_c': round(temperature, 2),
                'sensor_id': self.sensor.id
            }
            
            self.last_reading = data
            self.error_count = 0
            return data
            
        except Exception as e:
            self.handle_error(e)
            return None

class SensorManager:
    """センサー統合管理"""
    
    def __init__(self, config_file: str):
        self.sensors = {}
        self.config = {}
        self.running = False
        
        self.logger = logging.getLogger("sensor_manager")
        self.load_config(config_file)
        self.init_sensors()
    
    def load_config(self, config_file: str):
        """設定ファイル読み込み"""
        import yaml
        try:
            with open(config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            self.logger.error(f"Config load error: {e}")
            self.config = {}
    
    def init_sensors(self):
        """センサー初期化"""
        sensor_configs = self.config.get('sensors', {})
        
        for sensor_name, sensor_config in sensor_configs.items():
            sensor_type = sensor_config.get('type')
            
            try:
                if sensor_type == 'dht22':
                    sensor = DHT22Sensor(sensor_name, sensor_config)
                elif sensor_type == 'bmp280':
                    sensor = BMP280Sensor(sensor_name, sensor_config)
                elif sensor_type == 'pir':
                    sensor = PIRMotionSensor(sensor_name, sensor_config)
                elif sensor_type == 'ultrasonic':
                    sensor = UltrasonicSensor(sensor_name, sensor_config)
                elif sensor_type == 'ds18b20':
                    sensor = DS18B20Sensor(sensor_name, sensor_config)
                else:
                    self.logger.warning(f"Unknown sensor type: {sensor_type}")
                    continue
                
                self.sensors[sensor_name] = sensor
                self.logger.info(f"Initialized sensor: {sensor_name}")
                
            except Exception as e:
                self.logger.error(f"Failed to initialize {sensor_name}: {e}")
    
    async def read_all_sensors(self) -> Dict[str, Any]:
        """全センサー読み取り"""
        results = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.config.get('device_id', 'raspberry_pi'),
            'sensors': {}
        }
        
        # 並行読み取り
        read_tasks = []
        sensor_names = []
        
        for sensor_name, sensor in self.sensors.items():
            if sensor.is_healthy():
                read_tasks.append(sensor.read())
                sensor_names.append(sensor_name)
        
        # 非同期実行
        readings = await asyncio.gather(*read_tasks, return_exceptions=True)
        
        # 結果整理
        for sensor_name, reading in zip(sensor_names, readings):
            if isinstance(reading, Exception):
                self.logger.error(f"Error reading {sensor_name}: {reading}")
                results['sensors'][sensor_name] = {'error': str(reading)}
            elif reading is not None:
                results['sensors'][sensor_name] = reading
        
        return results
    
    def get_sensor_status(self) -> Dict[str, Any]:
        """センサー状態取得"""
        status = {}
        
        for sensor_name, sensor in self.sensors.items():
            status[sensor_name] = {
                'enabled': sensor.enabled,
                'healthy': sensor.is_healthy(),
                'error_count': sensor.error_count,
                'last_reading': sensor.last_reading
            }
        
        return status
    
    def cleanup(self):
        """リソースクリーンアップ"""
        GPIO.cleanup()
        self.logger.info("Sensor manager cleaned up")

# 使用例
async def main():
    # ログ設定
    logging.basicConfig(level=logging.INFO,
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # センサーマネージャー初期化
    sensor_manager = SensorManager('sensor_config.yaml')
    
    try:
        while True:
            # 全センサー読み取り
            data = await sensor_manager.read_all_sensors()
            print(json.dumps(data, indent=2))
            
            # ステータス確認
            status = sensor_manager.get_sensor_status()
            print(f"Sensor status: {status}")
            
            await asyncio.sleep(10)
            
    except KeyboardInterrupt:
        print("Stopping sensor manager...")
    finally:
        sensor_manager.cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

#### 2.2 設定ファイル

`sensor_config.yaml`:

```yaml
device_id: "raspberry_pi_sensor_01"
mqtt:
  broker_host: "localhost"
  broker_port: 1883
  topics:
    sensor_data: "sensors/pi/{device_id}/data"
    status: "sensors/pi/{device_id}/status"
    alerts: "sensors/pi/{device_id}/alerts"

sensors:
  environment_dht:
    type: "dht22"
    pin: 4
    max_errors: 3
    
  pressure_sensor:
    type: "bmp280"
    sea_level_pressure: 1013.25
    max_errors: 5
    
  motion_detector:
    type: "pir"
    pin: 18
    max_errors: 2
    
  distance_sensor:
    type: "ultrasonic"
    trig_pin: 23
    echo_pin: 24
    max_errors: 3
    
  water_temp:
    type: "ds18b20"
    sensor_id: null  # 自動検出
    max_errors: 2

# アラート設定
alerts:
  temperature:
    high_threshold: 35.0
    low_threshold: 5.0
  humidity:
    high_threshold: 80.0
    low_threshold: 20.0
  motion:
    detection_timeout: 300  # 5分
  distance:
    min_distance: 10.0  # 10cm未満で警告

# 省電力設定
power_management:
  sleep_between_readings: 10  # 秒
  deep_sleep_schedule:
    enabled: false
    start_hour: 23
    end_hour: 6
```

### Step 3: MQTT統合クライアント

#### 3.1 Raspberry Pi MQTTクライアント

`src/pi_mqtt_client.py`:

```python
#!/usr/bin/env python3
import asyncio
import json
import time
import socket
import yaml
from datetime import datetime
from typing import Dict, Any
import paho.mqtt.client as mqtt
from sensor_manager import SensorManager

class PiMQTTClient:
    """Raspberry Pi MQTT統合クライアント"""
    
    def __init__(self, config_file: str = "sensor_config.yaml"):
        self.config_file = config_file
        self.load_config()
        
        # コンポーネント初期化
        self.sensor_manager = SensorManager(config_file)
        self.mqtt_client = None
        self.device_id = self.config.get('device_id', f'pi_{socket.gethostname()}')
        
        # 統計情報
        self.stats = {
            'messages_sent': 0,
            'errors': 0,
            'start_time': time.time()
        }
        
        # MQTT設定
        self.setup_mqtt()
    
    def load_config(self):
        """設定読み込み"""
        try:
            with open(self.config_file, 'r') as f:
                self.config = yaml.safe_load(f)
        except Exception as e:
            print(f"Config load error: {e}")
            self.config = {}
    
    def setup_mqtt(self):
        """MQTT設定"""
        mqtt_config = self.config.get('mqtt', {})
        
        self.mqtt_client = mqtt.Client(client_id=self.device_id)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_disconnect = self.on_disconnect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_publish = self.on_publish
        
        # 遺言設定
        status_topic = mqtt_config.get('topics', {}).get('status', 'sensors/pi/{device_id}/status').format(device_id=self.device_id)
        will_message = json.dumps({
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'status': 'offline',
            'reason': 'unexpected_disconnect'
        })
        self.mqtt_client.will_set(status_topic, will_message, qos=1, retain=True)
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時処理"""
        if rc == 0:
            print(f"✓ MQTT connected: {self.device_id}")
            
            # コマンドトピック購読
            command_topic = f"sensors/pi/{self.device_id}/command"
            client.subscribe(command_topic, qos=1)
            
            # オンライン状態送信
            self.publish_status('online')
            
        else:
            print(f"✗ MQTT connection failed: {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        """切断時処理"""
        if rc != 0:
            print(f"⚠ Unexpected MQTT disconnect: {rc}")
        else:
            print("MQTT disconnected")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信処理"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            print(f"📨 Command received: {payload}")
            
            if "/command" in topic:
                asyncio.create_task(self.handle_command(payload))
                
        except Exception as e:
            print(f"Message processing error: {e}")
    
    def on_publish(self, client, userdata, mid):
        """発行時処理"""
        self.stats['messages_sent'] += 1
    
    async def handle_command(self, command: Dict[str, Any]):
        """コマンド処理"""
        cmd_type = command.get('type')
        
        if cmd_type == 'status':
            self.publish_status('online', include_stats=True)
            
        elif cmd_type == 'sensor_status':
            status = self.sensor_manager.get_sensor_status()
            self.publish_sensor_status(status)
            
        elif cmd_type == 'restart_sensor':
            sensor_name = command.get('sensor')
            if sensor_name in self.sensor_manager.sensors:
                # センサー再初期化
                sensor_config = self.config.get('sensors', {}).get(sensor_name)
                if sensor_config:
                    # TODO: センサー再初期化実装
                    print(f"🔄 Restarting sensor: {sensor_name}")
                    
        elif cmd_type == 'reboot':
            print("🔄 Reboot command received")
            self.publish_status('rebooting')
            # 実際の環境では: os.system("sudo reboot")
            
        elif cmd_type == 'update_config':
            new_config = command.get('config', {})
            self.update_config(new_config)
    
    def publish_status(self, status: str, include_stats: bool = False):
        """状態送信"""
        mqtt_config = self.config.get('mqtt', {})
        status_topic = mqtt_config.get('topics', {}).get('status', 'sensors/pi/{device_id}/status').format(device_id=self.device_id)
        
        status_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'status': status
        }
        
        if include_stats:
            uptime = time.time() - self.stats['start_time']
            status_data.update({
                'uptime_seconds': round(uptime, 2),
                'messages_sent': self.stats['messages_sent'],
                'errors': self.stats['errors'],
                'sensor_count': len(self.sensor_manager.sensors)
            })
        
        self.mqtt_client.publish(status_topic, json.dumps(status_data), qos=1, retain=True)
    
    def publish_sensor_data(self, sensor_data: Dict[str, Any]):
        """センサーデータ送信"""
        mqtt_config = self.config.get('mqtt', {})
        data_topic = mqtt_config.get('topics', {}).get('sensor_data', 'sensors/pi/{device_id}/data').format(device_id=self.device_id)
        
        self.mqtt_client.publish(data_topic, json.dumps(sensor_data), qos=1)
    
    def publish_alert(self, alert_type: str, message: str, level: str = 'warning'):
        """アラート送信"""
        mqtt_config = self.config.get('mqtt', {})
        alert_topic = mqtt_config.get('topics', {}).get('alerts', 'sensors/pi/{device_id}/alerts').format(device_id=self.device_id)
        
        alert_data = {
            'timestamp': datetime.now().isoformat(),
            'device_id': self.device_id,
            'type': alert_type,
            'level': level,
            'message': message
        }
        
        self.mqtt_client.publish(alert_topic, json.dumps(alert_data), qos=1)
    
    def check_sensor_alerts(self, sensor_data: Dict[str, Any]):
        """センサーデータアラートチェック"""
        alert_config = self.config.get('alerts', {})
        sensors = sensor_data.get('sensors', {})
        
        # 温度アラート
        for sensor_name, data in sensors.items():
            temp = data.get('temperature_c')
            if temp is not None:
                temp_config = alert_config.get('temperature', {})
                high_threshold = temp_config.get('high_threshold', 35.0)
                low_threshold = temp_config.get('low_threshold', 5.0)
                
                if temp > high_threshold:
                    self.publish_alert('high_temperature', 
                                     f'{sensor_name}: {temp}°C (threshold: {high_threshold}°C)', 
                                     'critical')
                elif temp < low_threshold:
                    self.publish_alert('low_temperature', 
                                     f'{sensor_name}: {temp}°C (threshold: {low_threshold}°C)', 
                                     'warning')
        
        # 湿度アラート
        for sensor_name, data in sensors.items():
            humidity = data.get('humidity_percent')
            if humidity is not None:
                humidity_config = alert_config.get('humidity', {})
                high_threshold = humidity_config.get('high_threshold', 80.0)
                low_threshold = humidity_config.get('low_threshold', 20.0)
                
                if humidity > high_threshold:
                    self.publish_alert('high_humidity', 
                                     f'{sensor_name}: {humidity}% (threshold: {high_threshold}%)', 
                                     'warning')
                elif humidity < low_threshold:
                    self.publish_alert('low_humidity', 
                                     f'{sensor_name}: {humidity}% (threshold: {low_threshold}%)', 
                                     'warning')
    
    async def connect(self) -> bool:
        """MQTT接続"""
        mqtt_config = self.config.get('mqtt', {})
        broker_host = mqtt_config.get('broker_host', 'localhost')
        broker_port = mqtt_config.get('broker_port', 1883)
        
        try:
            self.mqtt_client.connect(broker_host, broker_port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            print(f"MQTT connection error: {e}")
            self.stats['errors'] += 1
            return False
    
    def disconnect(self):
        """MQTT切断"""
        self.publish_status('offline')
        self.mqtt_client.loop_stop()
        self.mqtt_client.disconnect()
    
    async def run(self):
        """メインループ"""
        print(f"🚀 Starting Pi MQTT Client: {self.device_id}")
        
        if not await self.connect():
            print("Failed to connect to MQTT broker")
            return
        
        try:
            while True:
                # センサーデータ読み取り
                sensor_data = await self.sensor_manager.read_all_sensors()
                
                # データ送信
                self.publish_sensor_data(sensor_data)
                
                # アラートチェック
                self.check_sensor_alerts(sensor_data)
                
                # 待機
                sleep_time = self.config.get('power_management', {}).get('sleep_between_readings', 10)
                await asyncio.sleep(sleep_time)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping Pi MQTT Client...")
        except Exception as e:
            print(f"Runtime error: {e}")
            self.stats['errors'] += 1
        finally:
            self.disconnect()
            self.sensor_manager.cleanup()
            print("✓ Pi MQTT Client stopped")

def main():
    """メイン関数"""
    client = PiMQTTClient()
    asyncio.run(client.run())

if __name__ == "__main__":
    main()
```

### Step 4: 複数デバイス連携

#### 4.1 デバイス発見とネットワーク管理

`src/device_discovery.py`:

```python
#!/usr/bin/env python3
import json
import time
import asyncio
import socket
from typing import Dict, List
import paho.mqtt.client as mqtt

class DeviceDiscovery:
    """MQTTデバイス発見・管理"""
    
    def __init__(self, broker_host="localhost"):
        self.broker_host = broker_host
        self.devices = {}  # device_id -> device_info
        self.mqtt_client = mqtt.Client("device_discovery")
        
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        
        print("🔍 Device Discovery initialized")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✓ Discovery client connected")
            # 全デバイスの状態トピックを監視
            client.subscribe("sensors/+/+/status", qos=1)
            client.subscribe("jetson/+/status", qos=1)
            
            # 発見要求送信
            self.request_device_announcement()
    
    def on_message(self, client, userdata, msg):
        """デバイス状態メッセージ処理"""
        try:
            topic_parts = msg.topic.split('/')
            payload = json.loads(msg.payload.decode())
            
            device_id = payload.get('device_id')
            if not device_id:
                return
            
            # デバイス情報更新
            device_info = {
                'device_id': device_id,
                'last_seen': time.time(),
                'status': payload.get('status', 'unknown'),
                'topic_prefix': '/'.join(topic_parts[:-1]),
                'device_type': topic_parts[0],  # sensors, jetson, etc.
                'raw_status': payload
            }
            
            # 新規デバイス検出
            if device_id not in self.devices:
                print(f"📱 New device discovered: {device_id} ({device_info['device_type']})")
            
            self.devices[device_id] = device_info
            
        except Exception as e:
            print(f"Error processing device message: {e}")
    
    def request_device_announcement(self):
        """デバイス発見要求"""
        discovery_request = {
            'type': 'discovery',
            'timestamp': time.time(),
            'requester': 'device_discovery'
        }
        
        # 各デバイスタイプに発見要求送信
        topics = [
            'sensors/broadcast/command',
            'jetson/broadcast/command'
        ]
        
        for topic in topics:
            self.mqtt_client.publish(topic, json.dumps(discovery_request), qos=1)
    
    def get_online_devices(self) -> List[Dict]:
        """オンラインデバイス取得"""
        current_time = time.time()
        online_devices = []
        
        for device_id, info in self.devices.items():
            # 5分以内に見たデバイスをオンラインとみなす
            if (current_time - info['last_seen']) < 300 and info['status'] != 'offline':
                online_devices.append(info)
        
        return online_devices
    
    def get_device_by_type(self, device_type: str) -> List[Dict]:
        """タイプ別デバイス取得"""
        return [info for info in self.devices.values() 
                if info['device_type'] == device_type]
    
    async def monitor_devices(self):
        """デバイス監視ループ"""
        try:
            self.mqtt_client.connect(self.broker_host, 1883, 60)
            self.mqtt_client.loop_start()
            
            while True:
                online_devices = self.get_online_devices()
                print(f"\n📊 Device Status Summary ({len(online_devices)} online)")
                
                for device in online_devices:
                    print(f"  {device['device_id']} ({device['device_type']}) - {device['status']}")
                
                # 定期的に発見要求
                if int(time.time()) % 60 == 0:  # 1分間隔
                    self.request_device_announcement()
                
                await asyncio.sleep(10)
                
        except KeyboardInterrupt:
            print("\n🛑 Stopping device discovery...")
        finally:
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
    
    def cleanup(self):
        """クリーンアップ"""
        self.mqtt_client.disconnect()

async def main():
    """メイン関数"""
    discovery = DeviceDiscovery()
    await discovery.monitor_devices()

if __name__ == "__main__":
    asyncio.run(main())
```

## 課題

### 基礎課題

1. **単一センサー実装**
   - DHT22温湿度センサーの基本読み取り
   - MQTTでデータ送信

2. **複数センサー統合**
   - 3種類以上のセンサー同時動作
   - エラーハンドリング実装

3. **アラートシステム**
   - 閾値ベースアラート
   - MQTT経由でのアラート送信

### 応用課題

1. **マルチデバイス連携**
   - 2台以上のPiでセンサーネットワーク構築
   - 集約ダッシュボード

2. **省電力実装**
   - スリープモード対応
   - バッテリー動作最適化

3. **エッジ分析**
   - センサーデータの前処理
   - 異常検出アルゴリズム

## 次のステップ

演習3でESP32を使った無線センサーノードを追加し、より大規模なIoTネットワークを構築します。

---

この演習では、Raspberry Piを使った本格的なセンサーネットワークを学べます。実際の産業用途でも使える堅牢な設計になっています。