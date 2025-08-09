# 演習1: NVIDIA Jetson セットアップとMQTT基礎

## 概要

NVIDIA Jetson Nano/Xavier NX/Orin Nanoを使用してMQTTクライアントを実装し、基本的なセンサーデータ送信を行います。JetsonのGPU能力を活用したエッジAI処理の準備も行います。

## 学習目標

- Jetsonの初期設定とネットワーク接続
- Python MQTT クライアント実装
- GPIO制御とセンサー読み取り
- システム監視データのMQTT送信
- JetPack SDK環境構築

## 必要機材

### ハードウェア
- NVIDIA Jetson Nano/Xavier NX/Orin Nano
- microSDカード (64GB以上推奨)
- USB WiFi ドングル または イーサネットケーブル
- 5V 4A 電源アダプター (Nano: microUSB, Xavier/Orin: USB-C)
- HDMIケーブルとモニター (初期設定用)
- USB キーボード・マウス

### センサー（オプション）
- DHT22 温湿度センサー
- BMP280 気圧センサー
- PIR モーションセンサー
- LED × 2個
- 抵抗 220Ω × 2個
- ジャンパーワイヤー

## 演習手順

### Step 1: Jetson初期設定

#### 1.1 JetPackインストール

```bash
# NVIDIA SDK Manager使用、またはイメージファイルをSDカードに書き込み
# https://developer.nvidia.com/embedded/jetpack

# 初回起動後の設定
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip git curl wget

# システム情報確認
jetson_release
nvidia-smi  # GPU情報確認（Orinの場合）
```

#### 1.2 開発環境セットアップ

```bash
# Python環境構築
python3 -m pip install --upgrade pip
pip3 install virtualenv

# 仮想環境作成
python3 -m venv ~/mqtt_env
source ~/mqtt_env/bin/activate

# 必要パッケージインストール
pip install paho-mqtt adafruit-circuitpython-dht adafruit-blinka
pip install psutil GPUtil jetson-stats
pip install numpy opencv-python  # AI処理用
```

#### 1.3 GPIO設定

```bash
# Jetsonユーザーをgpioグループに追加
sudo usermod -a -G gpio $USER
sudo reboot

# GPIO制御ライブラリ
pip install Jetson.GPIO
```

### Step 2: 基本MQTT接続

#### 2.1 MQTT接続テスト

`src/basic_mqtt_test.py`を作成:

```python
#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
import socket

class JetsonMQTTClient:
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client_id = f"jetson_{socket.gethostname()}_{int(time.time())}"
        self.client = mqtt.Client(client_id=self.client_id)
        
        # コールバック設定
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message
        self.client.on_publish = self.on_publish
        
        print(f"Jetson MQTT Client initialized: {self.client_id}")
    
    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("✓ Connected to MQTT broker successfully")
            # デバイス情報トピックに購読
            client.subscribe("jetson/+/command")
            client.subscribe("jetson/+/config")
        else:
            print(f"✗ Connection failed with code {rc}")
    
    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            print(f"⚠ Unexpected disconnection: {rc}")
        else:
            print("Disconnected from broker")
    
    def on_message(self, client, userdata, msg):
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            print(f"📨 Received: {topic} -> {payload}")
            
            # コマンド処理
            if "/command" in topic:
                self.handle_command(payload)
                
        except Exception as e:
            print(f"Error processing message: {e}")
    
    def on_publish(self, client, userdata, mid):
        print(f"📤 Message published: {mid}")
    
    def handle_command(self, command):
        """デバイスコマンド処理"""
        cmd_type = command.get("type")
        
        if cmd_type == "reboot":
            print("🔄 Reboot command received")
            # 実際の環境では: os.system("sudo reboot")
            
        elif cmd_type == "status":
            self.publish_system_status()
            
        elif cmd_type == "led":
            state = command.get("state", "off")
            print(f"💡 LED command: {state}")
            # GPIO制御実装
    
    def connect(self):
        """ブローカーに接続"""
        try:
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """ブローカーから切断"""
        self.client.loop_stop()
        self.client.disconnect()
    
    def publish_system_status(self):
        """システムステータス送信"""
        import psutil
        
        try:
            # システム情報収集
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # GPU情報（可能な場合）
            gpu_info = self.get_gpu_info()
            
            # 温度情報
            temp_info = self.get_temperature_info()
            
            status_data = {
                "timestamp": datetime.now().isoformat(),
                "device_id": self.client_id,
                "system": {
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory.percent,
                    "memory_used_gb": round(memory.used / (1024**3), 2),
                    "disk_percent": disk.percent,
                    "uptime_seconds": time.time() - psutil.boot_time()
                },
                "gpu": gpu_info,
                "temperature": temp_info
            }
            
            topic = f"jetson/{socket.gethostname()}/status"
            self.client.publish(topic, json.dumps(status_data), qos=1)
            print(f"📊 System status published to {topic}")
            
        except Exception as e:
            print(f"Error publishing system status: {e}")
    
    def get_gpu_info(self):
        """GPU情報取得"""
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                return {
                    "name": gpu.name,
                    "memory_used_mb": gpu.memoryUsed,
                    "memory_total_mb": gpu.memoryTotal,
                    "memory_percent": round((gpu.memoryUsed / gpu.memoryTotal) * 100, 1),
                    "temperature": gpu.temperature,
                    "load_percent": gpu.load * 100
                }
        except ImportError:
            # jetson-statsを試す
            try:
                from jtop import jtop
                with jtop() as jetson:
                    if jetson.ok():
                        gpu_info = jetson.gpu
                        return {
                            "name": "Tegra GPU",
                            "frequency_mhz": gpu_info.get("frequency", {}).get("cur", 0),
                            "load_percent": gpu_info.get("use", 0)
                        }
            except Exception:
                pass
        
        return {"available": False, "error": "GPU monitoring not available"}
    
    def get_temperature_info(self):
        """温度情報取得"""
        temp_info = {}
        
        try:
            # CPUサーマル情報
            temps = psutil.sensors_temperatures()
            if temps:
                for name, entries in temps.items():
                    for entry in entries:
                        temp_info[f"{name}_{entry.label or 'main'}"] = entry.current
            
            # Jetson固有の温度センサー
            try:
                with open('/sys/class/thermal/thermal_zone0/temp', 'r') as f:
                    cpu_temp = float(f.read().strip()) / 1000.0
                    temp_info['cpu_thermal'] = cpu_temp
            except FileNotFoundError:
                pass
                
        except Exception as e:
            temp_info['error'] = str(e)
        
        return temp_info

def main():
    """メイン実行関数"""
    # ブローカー設定（環境変数から読み込み可能）
    import os
    broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
    broker_port = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    
    client = JetsonMQTTClient(broker_host, broker_port)
    
    if not client.connect():
        print("Failed to connect to MQTT broker")
        return
    
    print("🚀 Jetson MQTT client started")
    print("Press Ctrl+C to stop")
    
    try:
        # 定期的にシステムステータス送信
        while True:
            client.publish_system_status()
            time.sleep(30)  # 30秒間隔
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping client...")
        client.disconnect()
        print("✓ Client stopped")

if __name__ == "__main__":
    main()
```

#### 2.2 実行とテスト

```bash
# スクリプト実行権限付与
chmod +x src/basic_mqtt_test.py

# MQTT ブローカー起動（別ターミナル）
mosquitto -v

# Jetsonクライアント実行
python3 src/basic_mqtt_test.py

# 別ターミナルでトピック監視
mosquitto_sub -h localhost -t "jetson/+/+"

# コマンド送信テスト
mosquitto_pub -h localhost -t "jetson/jetson-nano/command" \
  -m '{"type": "status"}'
```

### Step 3: センサー統合

#### 3.1 DHT22温湿度センサー

`src/sensor_integration.py`:

```python
#!/usr/bin/env python3
import time
import json
import board
import adafruit_dht
from datetime import datetime
from basic_mqtt_test import JetsonMQTTClient

class JetsonSensorClient(JetsonMQTTClient):
    def __init__(self, broker_host="localhost", broker_port=1883):
        super().__init__(broker_host, broker_port)
        
        # センサー初期化
        self.dht = None
        self.init_sensors()
    
    def init_sensors(self):
        """センサー初期化"""
        try:
            # DHT22 on pin D4
            self.dht = adafruit_dht.DHT22(board.D4)
            print("✓ DHT22 sensor initialized")
        except Exception as e:
            print(f"⚠ Sensor initialization failed: {e}")
            self.dht = None
    
    def read_sensors(self):
        """センサーデータ読み取り"""
        sensor_data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.client_id
        }
        
        # DHT22 温湿度
        if self.dht:
            try:
                temperature = self.dht.temperature
                humidity = self.dht.humidity
                
                if temperature is not None and humidity is not None:
                    sensor_data["temperature_c"] = round(temperature, 2)
                    sensor_data["humidity_percent"] = round(humidity, 2)
                    sensor_data["heat_index"] = self.calculate_heat_index(
                        temperature, humidity
                    )
            except RuntimeError as e:
                sensor_data["dht_error"] = str(e)
        
        return sensor_data
    
    def calculate_heat_index(self, temp_c, humidity):
        """体感温度計算"""
        temp_f = temp_c * 9/5 + 32
        
        if temp_f < 80:
            return temp_c
        
        # Heat Index formula
        c1, c2, c3 = -42.379, 2.04901523, 10.14333127
        c4, c5, c6 = -0.22475541, -6.83783e-3, -5.481717e-2
        c7, c8, c9 = 1.22874e-3, 8.5282e-4, -1.99e-6
        
        hi = (c1 + c2*temp_f + c3*humidity + c4*temp_f*humidity + 
              c5*temp_f**2 + c6*humidity**2 + c7*temp_f**2*humidity + 
              c8*temp_f*humidity**2 + c9*temp_f**2*humidity**2)
        
        return round((hi - 32) * 5/9, 2)  # Convert back to Celsius
    
    def publish_sensor_data(self):
        """センサーデータ送信"""
        try:
            data = self.read_sensors()
            topic = f"jetson/{socket.gethostname()}/sensors"
            
            self.client.publish(topic, json.dumps(data), qos=1)
            print(f"🌡️ Sensor data published: T={data.get('temperature_c')}°C, "
                  f"H={data.get('humidity_percent')}%")
            
        except Exception as e:
            print(f"Error publishing sensor data: {e}")

def main():
    import os
    import socket
    
    broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
    broker_port = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    
    client = JetsonSensorClient(broker_host, broker_port)
    
    if not client.connect():
        print("Failed to connect to MQTT broker")
        return
    
    print("🌡️ Jetson sensor client started")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            # センサーデータ送信
            client.publish_sensor_data()
            
            # システムステータス送信（5分間隔）
            current_time = time.time()
            if int(current_time) % 300 == 0:  # Every 5 minutes
                client.publish_system_status()
            
            time.sleep(10)  # 10秒間隔
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping sensor client...")
        client.disconnect()
        print("✓ Sensor client stopped")

if __name__ == "__main__":
    main()
```

#### 3.2 LED制御統合

`src/led_control.py`:

```python
#!/usr/bin/env python3
import Jetson.GPIO as GPIO
import time
import json
from sensor_integration import JetsonSensorClient

class JetsonControlClient(JetsonSensorClient):
    def __init__(self, broker_host="localhost", broker_port=1883):
        super().__init__(broker_host, broker_port)
        
        # GPIO設定
        self.led_pins = {
            "status": 18,    # Status LED
            "alert": 19      # Alert LED
        }
        self.init_gpio()
    
    def init_gpio(self):
        """GPIO初期化"""
        GPIO.setmode(GPIO.BOARD)
        GPIO.setwarnings(False)
        
        for name, pin in self.led_pins.items():
            GPIO.setup(pin, GPIO.OUT)
            GPIO.output(pin, GPIO.LOW)
        
        print("✓ GPIO initialized")
    
    def handle_command(self, command):
        """拡張コマンド処理"""
        super().handle_command(command)
        
        cmd_type = command.get("type")
        
        if cmd_type == "led":
            led_name = command.get("led", "status")
            state = command.get("state", "off")
            duration = command.get("duration", 0)
            
            self.control_led(led_name, state, duration)
            
        elif cmd_type == "alert":
            level = command.get("level", "info")
            message = command.get("message", "")
            self.handle_alert(level, message)
    
    def control_led(self, led_name, state, duration=0):
        """LED制御"""
        if led_name not in self.led_pins:
            print(f"⚠ Unknown LED: {led_name}")
            return
        
        pin = self.led_pins[led_name]
        
        if state.lower() == "on":
            GPIO.output(pin, GPIO.HIGH)
            print(f"💡 {led_name} LED: ON")
            
            if duration > 0:
                time.sleep(duration)
                GPIO.output(pin, GPIO.LOW)
                print(f"💡 {led_name} LED: OFF (after {duration}s)")
                
        elif state.lower() == "off":
            GPIO.output(pin, GPIO.LOW)
            print(f"💡 {led_name} LED: OFF")
            
        elif state.lower() == "blink":
            times = duration if duration > 0 else 3
            for _ in range(times):
                GPIO.output(pin, GPIO.HIGH)
                time.sleep(0.5)
                GPIO.output(pin, GPIO.LOW)
                time.sleep(0.5)
            print(f"💡 {led_name} LED: Blinked {times} times")
    
    def handle_alert(self, level, message):
        """アラート処理"""
        print(f"🚨 Alert [{level}]: {message}")
        
        if level == "critical":
            self.control_led("alert", "blink", 5)
        elif level == "warning":
            self.control_led("alert", "on", 2)
        
        # アラート状態を送信
        alert_data = {
            "timestamp": datetime.now().isoformat(),
            "device_id": self.client_id,
            "level": level,
            "message": message,
            "handled": True
        }
        
        topic = f"jetson/{socket.gethostname()}/alerts"
        self.client.publish(topic, json.dumps(alert_data), qos=1)
    
    def check_sensor_alerts(self, sensor_data):
        """センサーベースアラートチェック"""
        temp = sensor_data.get("temperature_c")
        humidity = sensor_data.get("humidity_percent")
        
        alerts = []
        
        if temp is not None:
            if temp > 35:
                alerts.append(("critical", f"High temperature: {temp}°C"))
            elif temp < 5:
                alerts.append(("warning", f"Low temperature: {temp}°C"))
        
        if humidity is not None:
            if humidity > 80:
                alerts.append(("warning", f"High humidity: {humidity}%"))
            elif humidity < 20:
                alerts.append(("warning", f"Low humidity: {humidity}%"))
        
        for level, message in alerts:
            self.handle_alert(level, message)
    
    def publish_sensor_data(self):
        """拡張センサーデータ送信"""
        data = self.read_sensors()
        
        # アラートチェック
        self.check_sensor_alerts(data)
        
        # データ送信
        import socket
        topic = f"jetson/{socket.gethostname()}/sensors"
        self.client.publish(topic, json.dumps(data), qos=1)
        
        # ステータスLED点滅
        self.control_led("status", "on", 0.1)
    
    def cleanup(self):
        """リソースクリーンアップ"""
        GPIO.cleanup()
        print("✓ GPIO cleaned up")

def main():
    import os
    import socket
    
    broker_host = os.getenv('MQTT_BROKER_HOST', 'localhost')
    broker_port = int(os.getenv('MQTT_BROKER_PORT', '1883'))
    
    client = JetsonControlClient(broker_host, broker_port)
    
    if not client.connect():
        print("Failed to connect to MQTT broker")
        return
    
    print("🎛️ Jetson control client started")
    print("Press Ctrl+C to stop")
    
    try:
        while True:
            client.publish_sensor_data()
            time.sleep(10)
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping control client...")
        client.disconnect()
        client.cleanup()
        print("✓ Control client stopped")

if __name__ == "__main__":
    main()
```

### Step 4: システム統合テスト

#### 4.1 統合テストスクリプト

`src/integration_test.py`:

```python
#!/usr/bin/env python3
import threading
import time
import json
import paho.mqtt.client as mqtt
from led_control import JetsonControlClient

def test_mqtt_subscriber():
    """MQTTメッセージ監視"""
    def on_connect(client, userdata, flags, rc):
        print("Test subscriber connected")
        client.subscribe("jetson/+/+")
    
    def on_message(client, userdata, msg):
        try:
            data = json.loads(msg.payload.decode())
            print(f"📨 {msg.topic}: {data}")
        except:
            print(f"📨 {msg.topic}: {msg.payload.decode()}")
    
    subscriber = mqtt.Client("test_subscriber")
    subscriber.on_connect = on_connect
    subscriber.on_message = on_message
    subscriber.connect("localhost", 1883, 60)
    subscriber.loop_forever()

def test_command_sender():
    """コマンド送信テスト"""
    import socket
    hostname = socket.gethostname()
    
    commander = mqtt.Client("test_commander")
    commander.connect("localhost", 1883, 60)
    commander.loop_start()
    
    time.sleep(2)  # 接続待機
    
    test_commands = [
        {"type": "status"},
        {"type": "led", "led": "status", "state": "blink", "duration": 3},
        {"type": "alert", "level": "warning", "message": "Test alert"},
        {"type": "led", "led": "alert", "state": "on", "duration": 2}
    ]
    
    for i, cmd in enumerate(test_commands):
        print(f"\n📤 Sending command {i+1}: {cmd}")
        topic = f"jetson/{hostname}/command"
        commander.publish(topic, json.dumps(cmd))
        time.sleep(5)
    
    commander.loop_stop()
    commander.disconnect()

def main():
    print("🧪 Starting integration test")
    
    # サブスクライバーを別スレッドで起動
    subscriber_thread = threading.Thread(target=test_mqtt_subscriber, daemon=True)
    subscriber_thread.start()
    
    # Jetsonクライアント起動
    client_thread = threading.Thread(target=start_jetson_client, daemon=True)
    client_thread.start()
    
    time.sleep(3)  # 起動待機
    
    # コマンド送信テスト
    test_command_sender()
    
    print("\n✅ Integration test completed")

def start_jetson_client():
    """Jetsonクライアント起動"""
    client = JetsonControlClient()
    if client.connect():
        try:
            while True:
                client.publish_sensor_data()
                time.sleep(15)
        except:
            pass
        finally:
            client.disconnect()
            client.cleanup()

if __name__ == "__main__":
    main()
```

## 課題

### 基礎課題

1. **基本接続テスト**
   - Jetsonをローカルブローカーに接続
   - システムステータス送信確認

2. **センサーデータ収集**
   - DHT22で温湿度測定
   - 10秒間隔でデータ送信

3. **LED制御**
   - MQTTコマンドでLED ON/OFF
   - アラート時の自動点滅

### 応用課題

1. **アラートシステム**
   - 閾値ベースアラート実装
   - 複数レベル対応

2. **データ永続化**
   - InfluxDBとの連携
   - 履歴データ保存

3. **Web監視**
   - Flask/FastAPI でWeb API
   - リアルタイム監視画面

## トラブルシューティング

### よくある問題

1. **GPIO Permission denied**
```bash
sudo usermod -a -G gpio $USER
sudo reboot
```

2. **DHT22読み取りエラー**
- 配線確認
- 電源電圧確認
- プルアップ抵抗追加

3. **MQTT接続失敗**
```bash
# ブローカー状態確認
systemctl status mosquitto

# ファイアウォール確認
sudo ufw status
```

## 次のステップ

演習2でRaspberry Piとの連携、センサーノード拡張を行います。

---

**参考資料**
- [NVIDIA Jetson GPIO Library](https://github.com/NVIDIA/jetson-gpio)
- [Adafruit CircuitPython](https://circuitpython.org/)
- [MQTT Paho Python](https://pypi.org/project/paho-mqtt/)