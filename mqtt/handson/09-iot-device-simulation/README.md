# ハンズオン 09: IoTデバイスシミュレーション

## 🎯 学習目標

このハンズオンでは実践的なIoTシステムを構築します：

- 複数の仮想IoTデバイスの作成とシミュレーション
- リアルなセンサーデータの生成とパターン化
- デバイス管理とファームウェア更新のシミュレーション
- エラー処理と復旧機能の実装
- 大規模IoTシステムの運用課題の理解

**所要時間**: 約90分

## 📋 前提条件

- これまでのハンズオンの完了
- Node.js/Pythonの中級レベルの知識
- ファイルシステムとJSON操作の理解

## 🏭 IoTシミュレーションアーキテクチャ

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Device Farm   │───▶│  MQTT Broker    │◀───│ Management App  │
│                 │    │                 │    │                 │
│ • Temperature   │    │ • Message       │    │ • Monitoring    │
│ • Humidity      │    │   Routing       │    │ • Control       │
│ • Pressure      │    │ • QoS Handling  │    │ • Analytics     │
│ • Motion        │    │ • Persistence   │    │ • Alerts        │
│ • GPS Tracker   │    └─────────────────┘    └─────────────────┘
└─────────────────┘
```

## 📝 実装演習

### Exercise 1: IoTデバイスシミュレーター基盤

`src/iot_device_simulator.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import random
import asyncio
import threading
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from rich.console import Console
from rich.logging import RichHandler

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler()]
)
logger = logging.getLogger("IoTDevice")
console = Console()

class IoTDevice:
    """IoTデバイスシミュレーター"""
    
    def __init__(self, config: Dict[str, Any]):
        self.device_id = config['device_id']
        self.device_type = config['device_type']
        self.location = config['location']
        self.report_interval = config.get('report_interval', 30)  # 秒
        self.error_rate = config.get('error_rate', 0.02)  # 2%エラー率
        
        # デバイス状態
        self.is_online = False
        self.battery_level = 100.0
        self.firmware_version = '1.0.0'
        self.last_seen = None
        
        # センサーデータ生成用
        self.sensor_state = self.initialize_sensor_state()
        
        # MQTT設定
        will_message = json.dumps({
            'status': 'offline',
            'timestamp': datetime.now().isoformat(),
            'reason': 'unexpected_disconnect'
        })
        
        self.client = mqtt.Client(
            client_id=self.device_id,
            clean_session=False  # セッション保持
        )
        
        # Last Will Testament設定
        self.client.will_set(
            topic=f"devices/{self.device_id}/status",
            payload=will_message,
            qos=1,
            retain=True
        )
        
        self.setup_mqtt_handlers()
        self.report_timer = None
        self.running = False
    
    def initialize_sensor_state(self) -> Dict[str, Dict[str, Any]]:
        """センサー状態の初期化"""
        states = {
            'temperature': {
                'value': 20 + random.random() * 10,  # 20-30度
                'trend': 0,
                'noise': 0.5
            },
            'humidity': {
                'value': 40 + random.random() * 20,  # 40-60%
                'trend': 0,
                'noise': 2
            },
            'pressure': {
                'value': 1013 + random.random() * 20,  # 1013-1033 hPa
                'trend': 0,
                'noise': 1
            }
        }
        
        # デバイスタイプ別の特別なセンサー
        if self.device_type == 'motion':
            states['motion'] = {
                'detected': False,
                'last_detected': None
            }
        elif self.device_type == 'gps':
            states['location'] = {
                'latitude': 35.6762 + (random.random() - 0.5) * 0.1,  # 東京周辺
                'longitude': 139.6503 + (random.random() - 0.5) * 0.1,
                'altitude': random.random() * 100,
                'speed': 0
            }
        
        return states
    
    def setup_mqtt_handlers(self):
        """イベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.client.on_disconnect = self.on_disconnect
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            self.is_online = True
            self.last_seen = datetime.now().isoformat()
            
            console.print(f"🟢 Device {self.device_id} connected", style="green")
            
            # デバイス管理トピックを購読
            self.subscribe_to_management_topics()
            
            # オンライン状態を報告
            self.report_status('online')
            
            # 定期報告開始
            self.start_periodic_reporting()
        else:
            logger.error(f"Device {self.device_id} connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        self.handle_command(msg.topic, msg.payload)
    
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        if rc != 0:
            console.print(f"🟡 Device {self.device_id} went offline unexpectedly", style="yellow")
        self.is_online = False
        self.stop_periodic_reporting()
    
    def subscribe_to_management_topics(self):
        """デバイス管理トピックを購読"""
        topics = [
            f"devices/{self.device_id}/commands/+",
            "devices/broadcast/+",
            f"firmware/{self.device_type}/+"
        ]
        
        for topic in topics:
            self.client.subscribe(topic, qos=1)
    
    def handle_command(self, topic: str, message: bytes):
        """コマンド処理"""
        try:
            command = json.loads(message.decode('utf-8'))
            topic_parts = topic.split('/')
            command_type = topic_parts[-1]
            
            console.print(f"📡 Device {self.device_id} received command: {command_type}", style="blue")
            
            if command_type == 'reboot':
                self.handle_reboot(command)
            elif command_type == 'update_interval':
                self.handle_update_interval(command)
            elif command_type == 'firmware_update':
                asyncio.create_task(self.handle_firmware_update(command))
            elif command_type == 'calibrate':
                self.handle_calibrate(command)
            else:
                console.print(f"⚠️  Unknown command: {command_type}", style="yellow")
                
        except (json.JSONDecodeError, KeyError) as e:
            logger.error(f"Command parsing error: {e}")
    
    def handle_reboot(self, command: Dict[str, Any]):
        """リブート処理"""
        console.print(f"🔄 Device {self.device_id} rebooting...", style="yellow")
        
        # オフライン状態を報告
        self.report_status('rebooting')
        
        # 接続を一時的に切断
        self.client.disconnect()
        
        # 3-10秒のランダムな再起動時間
        reboot_time = 3 + random.random() * 7
        
        def reconnect():
            time.sleep(reboot_time)
            self.client.reconnect()
            console.print(f"✅ Device {self.device_id} rebooted successfully", style="green")
        
        threading.Thread(target=reconnect, daemon=True).start()
    
    def handle_update_interval(self, command: Dict[str, Any]):
        """レポート間隔更新処理"""
        new_interval = command.get('interval', 30)
        
        if 5 <= new_interval <= 300:  # 5秒-5分の範囲
            self.report_interval = new_interval
            console.print(f"✅ Device {self.device_id} interval updated to {new_interval}s", style="green")
            
            # 定期報告を再開
            self.stop_periodic_reporting()
            self.start_periodic_reporting()
            
            # 確認応答
            response = {
                'success': True,
                'new_interval': new_interval,
                'timestamp': datetime.now().isoformat()
            }
            self.client.publish(
                f"devices/{self.device_id}/responses/update_interval",
                json.dumps(response),
                qos=1
            )
        else:
            console.print(f"❌ Invalid interval: {new_interval}s", style="red")
    
    async def handle_firmware_update(self, command: Dict[str, Any]):
        """ファームウェア更新処理"""
        console.print(f"📦 Device {self.device_id} starting firmware update...", style="blue")
        
        # ファームウェア更新シミュレーション
        update_steps = [
            'Downloading firmware',
            'Verifying checksum',
            'Backing up current firmware',
            'Installing new firmware',
            'Rebooting device'
        ]
        
        for i, step in enumerate(update_steps):
            progress = ((i + 1) / len(update_steps)) * 100
            
            console.print(f"📦 {step}... ({progress:.0f}%)", style="blue")
            
            # 進捗を報告
            progress_data = {
                'step': step,
                'progress': progress,
                'timestamp': datetime.now().isoformat()
            }
            self.client.publish(
                f"devices/{self.device_id}/firmware_update_progress",
                json.dumps(progress_data),
                qos=1
            )
            
            # 各ステップに時間をかける
            await asyncio.sleep(2 + random.random() * 3)
            
            # 10%の確率で失敗シミュレーション
            if random.random() < 0.1 and i == 3:
                console.print(f"❌ Firmware update failed at step: {step}", style="red")
                result = {
                    'success': False,
                    'error': f'Failed at: {step}',
                    'timestamp': datetime.now().isoformat()
                }
                self.client.publish(
                    f"devices/{self.device_id}/firmware_update_result",
                    json.dumps(result),
                    qos=1
                )
                return
        
        # 成功時
        self.firmware_version = command.get('version', '1.1.0')
        console.print(f"✅ Device {self.device_id} firmware updated to {self.firmware_version}", style="green")
        
        result = {
            'success': True,
            'old_version': '1.0.0',
            'new_version': self.firmware_version,
            'timestamp': datetime.now().isoformat()
        }
        self.client.publish(
            f"devices/{self.device_id}/firmware_update_result",
            json.dumps(result),
            qos=1
        )
    
    def handle_calibrate(self, command: Dict[str, Any]):
        """センサー校正処理"""
        console.print(f"🔧 Device {self.device_id} calibrating sensors...", style="blue")
        
        # センサーキャリブレーション
        sensors = command.get('sensors', {})
        for sensor_type in self.sensor_state.keys():
            if sensor_type in sensors:
                calibration = sensors[sensor_type]
                if 'value' in self.sensor_state[sensor_type]:
                    offset = calibration.get('offset', 0)
                    self.sensor_state[sensor_type]['value'] += offset
        
        console.print(f"✅ Device {self.device_id} calibration completed", style="green")
        
        # 校正結果を報告
        response = {
            'success': True,
            'calibrated_sensors': list(sensors.keys()),
            'timestamp': datetime.now().isoformat()
        }
        self.client.publish(
            f"devices/{self.device_id}/responses/calibrate",
            json.dumps(response),
            qos=1
        )
    
    def start_periodic_reporting(self):
        """定期レポート開始"""
        if self.report_timer:
            self.report_timer.cancel()
        
        def report_loop():
            if self.running and self.is_online:
                self.generate_and_send_sensor_data()
                self.report_timer = threading.Timer(self.report_interval, report_loop)
                self.report_timer.start()
        
        self.running = True
        report_loop()
    
    def stop_periodic_reporting(self):
        """定期レポート停止"""
        self.running = False
        if self.report_timer:
            self.report_timer.cancel()
            self.report_timer = None
    
    def generate_and_send_sensor_data(self):
        """センサーデータ生成と送信"""
        # バッテリー消耗シミュレーション
        self.battery_level = max(0, self.battery_level - 0.01)
        self.last_seen = datetime.now().isoformat()
        
        # エラー発生シミュレーション
        if random.random() < self.error_rate:
            self.send_error_report()
            return
        
        # センサーデータ生成
        sensor_data = self.generate_sensor_data()
        
        # データ送信
        self.send_sensor_data(sensor_data)
        
        # 低バッテリー警告
        if self.battery_level < 20:
            self.send_low_battery_alert()
    
    def generate_sensor_data(self) -> Dict[str, Any]:
        """センサーデータ生成"""
        data = {
            'device_id': self.device_id,
            'device_type': self.device_type,
            'location': self.location,
            'timestamp': datetime.now().isoformat(),
            'battery_level': round(self.battery_level, 2),
            'firmware_version': self.firmware_version
        }
        
        # 基本センサーデータの生成
        for sensor_type in ['temperature', 'humidity', 'pressure']:
            if sensor_type in self.sensor_state:
                sensor = self.sensor_state[sensor_type]
                
                # トレンド変化
                sensor['trend'] += (random.random() - 0.5) * 0.1
                sensor['trend'] = max(-1, min(1, sensor['trend']))
                
                # 値の更新（トレンド + ノイズ）
                sensor['value'] += sensor['trend'] + (random.random() - 0.5) * sensor['noise']
                
                # 範囲制限
                if sensor_type == 'temperature':
                    sensor['value'] = max(-10, min(50, sensor['value']))
                elif sensor_type == 'humidity':
                    sensor['value'] = max(0, min(100, sensor['value']))
                elif sensor_type == 'pressure':
                    sensor['value'] = max(980, min(1050, sensor['value']))
                
                data[sensor_type] = round(sensor['value'], 2)
        
        # デバイス固有のデータ
        if self.device_type == 'motion':
            motion_detected = random.random() < 0.1  # 10%の確率で動きを検知
            data['motion_detected'] = motion_detected
            if motion_detected:
                self.sensor_state['motion']['last_detected'] = data['timestamp']
                data['last_motion_time'] = data['timestamp']
        elif self.device_type == 'gps':
            location = self.sensor_state['location']
            
            # GPS位置の微小変動（歩行シミュレーション）
            location['latitude'] += (random.random() - 0.5) * 0.0001
            location['longitude'] += (random.random() - 0.5) * 0.0001
            location['speed'] = random.random() * 5  # 0-5 km/h
            
            data['gps'] = {
                'latitude': round(location['latitude'], 6),
                'longitude': round(location['longitude'], 6),
                'altitude': round(location['altitude'], 1),
                'speed': round(location['speed'], 1)
            }
        
        return data
    
    def send_sensor_data(self, data: Dict[str, Any]):
        """センサーデータ送信"""
        topic = f"sensors/{self.device_type}/{self.device_id}/data"
        
        try:
            self.client.publish(topic, json.dumps(data), qos=1)
            temp = data.get('temperature', 'N/A')
            console.print(f"📊 Data sent from {self.device_id}: T:{temp}°C", style="dim")
        except Exception as e:
            logger.error(f"Failed to send data from {self.device_id}: {e}")
    
    def send_error_report(self):
        """エラーレポート送信"""
        error_types = [
            'sensor_read_failed',
            'low_battery',
            'network_instability',
            'memory_overflow',
            'temperature_out_of_range'
        ]
        
        error_report = {
            'device_id': self.device_id,
            'error_type': random.choice(error_types),
            'timestamp': datetime.now().isoformat(),
            'battery_level': self.battery_level,
            'details': 'Error occurred during normal operation'
        }
        
        self.client.publish(f"devices/{self.device_id}/errors", json.dumps(error_report), qos=1)
        console.print(f"🚨 Error reported from {self.device_id}: {error_report['error_type']}", style="red")
    
    def send_low_battery_alert(self):
        """低バッテリーアラート送信"""
        alert = {
            'device_id': self.device_id,
            'alert_type': 'low_battery',
            'battery_level': self.battery_level,
            'timestamp': datetime.now().isoformat(),
            'severity': 'critical' if self.battery_level < 10 else 'warning'
        }
        
        self.client.publish(f"alerts/low_battery/{self.device_id}", json.dumps(alert), qos=1)
        console.print(f"🪫 Low battery alert from {self.device_id}: {self.battery_level}%", style="yellow")
    
    def report_status(self, status: str):
        """ステータス報告"""
        status_report = {
            'device_id': self.device_id,
            'status': status,
            'timestamp': datetime.now().isoformat(),
            'battery_level': self.battery_level,
            'firmware_version': self.firmware_version
        }
        
        self.client.publish(
            f"devices/{self.device_id}/status",
            json.dumps(status_report),
            qos=1,
            retain=True
        )
    
    def connect(self):
        """ブローカーに接続"""
        try:
            self.client.connect('localhost', 1883, 60)
            self.client.loop_start()
            return True
        except Exception as e:
            logger.error(f"Connection failed for {self.device_id}: {e}")
            return False
    
    def disconnect(self):
        """デバイス切断"""
        self.stop_periodic_reporting()
        self.report_status('offline')
        
        time.sleep(1)
        self.client.loop_stop()
        self.client.disconnect()
        console.print(f"👋 Device {self.device_id} disconnected", style="yellow")


class IoTDeviceFarm:
    """IoTデバイスファーム管理クラス"""
    
    def __init__(self):
        self.devices: Dict[str, IoTDevice] = {}
        self.is_running = False
    
    def create_device(self, config: Dict[str, Any]) -> IoTDevice:
        """デバイス作成"""
        device = IoTDevice(config)
        self.devices[config['device_id']] = device
        return device
    
    def create_device_farm(self, device_count: int):
        """デバイスファーム作成"""
        console.print(f"🏭 Creating IoT device farm with {device_count} devices", style="blue")
        
        device_types = ['temperature', 'motion', 'gps', 'environmental']
        locations = ['Building-A', 'Building-B', 'Warehouse', 'Factory-Floor', 'Office']
        
        for i in range(device_count):
            device_type = device_types[i % len(device_types)]
            location = locations[i % len(locations)]
            
            config = {
                'device_id': f"{device_type}-{str(i + 1).zfill(3)}",
                'device_type': device_type,
                'location': f"{location}-{i // len(locations) + 1}",
                'report_interval': 20 + random.random() * 20,  # 20-40秒
                'error_rate': 0.01 + random.random() * 0.02  # 1-3%
            }
            
            device = self.create_device(config)
            device.connect()
        
        console.print(f"✅ Created {len(self.devices)} IoT devices", style="green")
    
    def start(self):
        """ファーム開始"""
        self.is_running = True
        console.print("🟢 IoT Device Farm started", style="green")
    
    def stop(self):
        """ファーム停止"""
        self.is_running = False
        
        console.print("🟡 Stopping all devices...", style="yellow")
        
        for device in self.devices.values():
            device.disconnect()
        
        console.print("🔴 IoT Device Farm stopped", style="red")
    
    def get_device_stats(self) -> Dict[str, Any]:
        """デバイス統計情報取得"""
        stats = {
            'total_devices': len(self.devices),
            'online_devices': sum(1 for d in self.devices.values() if d.is_online),
            'device_types': {},
            'avg_battery': 0,
            'low_battery_count': 0
        }
        
        total_battery = 0
        for device in self.devices.values():
            # デバイスタイプ別カウント
            device_type = device.device_type
            if device_type not in stats['device_types']:
                stats['device_types'][device_type] = 0
            stats['device_types'][device_type] += 1
            
            # バッテリー統計
            total_battery += device.battery_level
            if device.battery_level < 20:
                stats['low_battery_count'] += 1
        
        if len(self.devices) > 0:
            stats['avg_battery'] = round(total_battery / len(self.devices), 1)
        
        return stats


# 使用例
def main():
    """メイン関数"""
    import signal
    import sys
    
    # ファーム作成
    farm = IoTDeviceFarm()
    
    def signal_handler(signum, frame):
        console.print("\n⚠️  Received shutdown signal", style="yellow")
        farm.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # 10台のデバイスでファーム作成
        farm.create_device_farm(10)
        farm.start()
        
        # シミュレーション実行
        while True:
            time.sleep(30)
            stats = farm.get_device_stats()
            console.print(f"\n📊 Farm Stats: {stats['online_devices']}/{stats['total_devices']} online, "
                         f"Avg Battery: {stats['avg_battery']}%, Low: {stats['low_battery_count']}")
            
    except KeyboardInterrupt:
        console.print("\n⚠️  Keyboard interrupt received", style="yellow")
    finally:
        farm.stop()

if __name__ == "__main__":
    main()
```
    
    subscribeToManagementTopics() {
        const topics = [
            `devices/${this.deviceId}/commands/+`,
            `devices/broadcast/+`,
            `firmware/${this.deviceType}/+`
        ];
        
        topics.forEach(topic => {
            this.client.subscribe(topic, { qos: 1 });
        });
    }
    
    handleCommand(topic, message) {
        try {
            const command = JSON.parse(message.toString());
            const topicParts = topic.split('/');
            const commandType = topicParts[topicParts.length - 1];
            
            console.log(chalk.blue(`📡 Device ${this.deviceId} received command: ${commandType}`));
            
            switch (commandType) {
                case 'reboot':
                    this.handleReboot(command);
                    break;
                case 'update_interval':
                    this.handleUpdateInterval(command);
                    break;
                case 'firmware_update':
                    this.handleFirmwareUpdate(command);
                    break;
                case 'calibrate':
                    this.handleCalibrate(command);
                    break;
                default:
                    console.log(chalk.yellow(`⚠️  Unknown command: ${commandType}`));
            }
        } catch (error) {
            console.error(chalk.red(`❌ Command parsing error: ${error.message}`));
        }
    }
    
    async handleReboot(command) {
        console.log(chalk.yellow(`🔄 Device ${this.deviceId} rebooting...`));
        
        // オフライン状態を報告
        this.reportStatus('rebooting');
        
        // 接続を一時的に切断
        this.client.end();
        
        // 3-10秒のランダムな再起動時間
        const rebootTime = 3000 + Math.random() * 7000;
        
        setTimeout(() => {
            // 再接続
            this.client.reconnect();
            console.log(chalk.green(`✅ Device ${this.deviceId} rebooted successfully`));
        }, rebootTime);
    }
    
    handleUpdateInterval(command) {
        const newInterval = command.interval * 1000; // 秒をミリ秒に変換
        
        if (newInterval >= 5000 && newInterval <= 300000) { // 5秒-5分の範囲
            this.reportInterval = newInterval;
            console.log(chalk.green(`✅ Device ${this.deviceId} interval updated to ${command.interval}s`));
            
            // 定期報告を再開
            this.stopPeriodicReporting();
            this.startPeriodicReporting();
            
            // 確認応答
            this.client.publish(`devices/${this.deviceId}/responses/update_interval`, 
                JSON.stringify({
                    success: true,
                    newInterval: command.interval,
                    timestamp: new Date().toISOString()
                }), { qos: 1 });
        } else {
            console.log(chalk.red(`❌ Invalid interval: ${command.interval}s`));
        }
    }
    
    async handleFirmwareUpdate(command) {
        console.log(chalk.blue(`📦 Device ${this.deviceId} starting firmware update...`));
        
        // ファームウェア更新シミュレーション
        const updateSteps = [
            'Downloading firmware',
            'Verifying checksum', 
            'Backing up current firmware',
            'Installing new firmware',
            'Rebooting device'
        ];
        
        for (let i = 0; i < updateSteps.length; i++) {
            const step = updateSteps[i];
            const progress = ((i + 1) / updateSteps.length) * 100;
            
            console.log(chalk.blue(`📦 ${step}... (${progress.toFixed(0)}%)`));
            
            // 進捗を報告
            this.client.publish(`devices/${this.deviceId}/firmware_update_progress`,
                JSON.stringify({
                    step: step,
                    progress: progress,
                    timestamp: new Date().toISOString()
                }), { qos: 1 });
                
            // 各ステップに時間をかける
            await new Promise(resolve => setTimeout(resolve, 2000 + Math.random() * 3000));
            
            // 10%の確率で失敗シミュレーション
            if (Math.random() < 0.1 && i === 3) {
                console.log(chalk.red(`❌ Firmware update failed at step: ${step}`));
                this.client.publish(`devices/${this.deviceId}/firmware_update_result`,
                    JSON.stringify({
                        success: false,
                        error: `Failed at: ${step}`,
                        timestamp: new Date().toISOString()
                    }), { qos: 1 });
                return;
            }
        }
        
        // 成功時
        this.firmwareVersion = command.version;
        console.log(chalk.green(`✅ Device ${this.deviceId} firmware updated to ${command.version}`));
        
        this.client.publish(`devices/${this.deviceId}/firmware_update_result`,
            JSON.stringify({
                success: true,
                oldVersion: '1.0.0',
                newVersion: command.version,
                timestamp: new Date().toISOString()
            }), { qos: 1 });
    }
    
    handleCalibrate(command) {
        console.log(chalk.blue(`🔧 Device ${this.deviceId} calibrating sensors...`));
        
        // センサーキャリブレーション
        Object.keys(this.sensorState).forEach(sensorType => {
            if (command.sensors && command.sensors[sensorType]) {
                const calibration = command.sensors[sensorType];
                if (this.sensorState[sensorType].value !== undefined) {
                    this.sensorState[sensorType].value += calibration.offset || 0;
                }
            }
        });
        
        console.log(chalk.green(`✅ Device ${this.deviceId} calibration completed`));
        
        // 校正結果を報告
        this.client.publish(`devices/${this.deviceId}/responses/calibrate`,
            JSON.stringify({
                success: true,
                calibratedSensors: Object.keys(command.sensors || {}),
                timestamp: new Date().toISOString()
            }), { qos: 1 });
    }
    
    startPeriodicReporting() {
        if (this.reportTimer) {
            clearInterval(this.reportTimer);
        }
        
        this.reportTimer = setInterval(() => {
            this.generateAndSendSensorData();
        }, this.reportInterval);
    }
    
    stopPeriodicReporting() {
        if (this.reportTimer) {
            clearInterval(this.reportTimer);
            this.reportTimer = null;
        }
    }
    
    generateAndSendSensorData() {
        // バッテリー消耗シミュレーション
        this.batteryLevel = Math.max(0, this.batteryLevel - 0.01);
        this.lastSeen = new Date().toISOString();
        
        // エラー発生シミュレーション
        if (Math.random() < this.errorRate) {
            this.sendErrorReport();
            return;
        }
        
        // センサーデータ生成
        const sensorData = this.generateSensorData();
        
        // データ送信
        this.sendSensorData(sensorData);
        
        // 低バッテリー警告
        if (this.batteryLevel < 20) {
            this.sendLowBatteryAlert();
        }
    }
    
    generateSensorData() {
        const data = {
            deviceId: this.deviceId,
            deviceType: this.deviceType,
            location: this.location,
            timestamp: new Date().toISOString(),
            batteryLevel: this.batteryLevel,
            firmwareVersion: this.firmwareVersion
        };
        
        // 基本センサーデータの生成
        ['temperature', 'humidity', 'pressure'].forEach(sensorType => {
            if (this.sensorState[sensorType]) {
                const sensor = this.sensorState[sensorType];
                
                // トレンド変化
                sensor.trend += (Math.random() - 0.5) * 0.1;
                sensor.trend = Math.max(-1, Math.min(1, sensor.trend));
                
                // 値の更新（トレンド + ノイズ）
                sensor.value += sensor.trend + (Math.random() - 0.5) * sensor.noise;
                
                // 範囲制限
                if (sensorType === 'temperature') {
                    sensor.value = Math.max(-10, Math.min(50, sensor.value));
                } else if (sensorType === 'humidity') {
                    sensor.value = Math.max(0, Math.min(100, sensor.value));
                } else if (sensorType === 'pressure') {
                    sensor.value = Math.max(980, Math.min(1050, sensor.value));
                }
                
                data[sensorType] = parseFloat(sensor.value.toFixed(2));
            }
        });
        
        // デバイス固有のデータ
        if (this.deviceType === 'motion') {
            const motionDetected = Math.random() < 0.1; // 10%の確率で動きを検知
            data.motionDetected = motionDetected;
            if (motionDetected) {
                this.sensorState.motion.lastDetected = data.timestamp;
                data.lastMotionTime = data.timestamp;
            }
        } else if (this.deviceType === 'gps') {
            const location = this.sensorState.location;
            
            // GPS位置の微小変動（歩行シミュレーション）
            location.latitude += (Math.random() - 0.5) * 0.0001;
            location.longitude += (Math.random() - 0.5) * 0.0001;
            location.speed = Math.random() * 5; // 0-5 km/h
            
            data.gps = {
                latitude: parseFloat(location.latitude.toFixed(6)),
                longitude: parseFloat(location.longitude.toFixed(6)),
                altitude: parseFloat(location.altitude.toFixed(1)),
                speed: parseFloat(location.speed.toFixed(1))
            };
        }
        
        return data;
    }
    
    sendSensorData(data) {
        const topic = `sensors/${this.deviceType}/${this.deviceId}/data`;
        
        this.client.publish(topic, JSON.stringify(data), { qos: 1 }, (error) => {
            if (error) {
                console.error(chalk.red(`❌ Failed to send data from ${this.deviceId}`), error);
            } else {
                console.log(chalk.gray(`📊 Data sent from ${this.deviceId}: T:${data.temperature}°C`));
            }
        });
    }
    
    sendErrorReport() {
        const errorTypes = [
            'sensor_read_failed',
            'low_battery',
            'network_instability',
            'memory_overflow',
            'temperature_out_of_range'
        ];
        
        const errorReport = {
            deviceId: this.deviceId,
            errorType: errorTypes[Math.floor(Math.random() * errorTypes.length)],
            timestamp: new Date().toISOString(),
            batteryLevel: this.batteryLevel,
            details: `Error occurred during normal operation`
        };
        
        this.client.publish(`devices/${this.deviceId}/errors`, JSON.stringify(errorReport), { qos: 1 });
        console.log(chalk.red(`🚨 Error reported from ${this.deviceId}: ${errorReport.errorType}`));
    }
    
    sendLowBatteryAlert() {
        const alert = {
            deviceId: this.deviceId,
            alertType: 'low_battery',
            batteryLevel: this.batteryLevel,
            timestamp: new Date().toISOString(),
            severity: this.batteryLevel < 10 ? 'critical' : 'warning'
        };
        
        this.client.publish(`alerts/low_battery/${this.deviceId}`, JSON.stringify(alert), { qos: 1 });
        console.log(chalk.yellow(`🪫 Low battery alert from ${this.deviceId}: ${this.batteryLevel}%`));
    }
    
    reportStatus(status) {
        const statusReport = {
            deviceId: this.deviceId,
            status: status,
            timestamp: new Date().toISOString(),
            batteryLevel: this.batteryLevel,
            firmwareVersion: this.firmwareVersion
        };
        
        this.client.publish(`devices/${this.deviceId}/status`, JSON.stringify(statusReport), { 
            qos: 1, 
            retain: true 
        });
    }
    
    async saveState() {
        const state = {
            deviceId: this.deviceId,
            deviceType: this.deviceType,
            location: this.location,
            isOnline: this.isOnline,
            batteryLevel: this.batteryLevel,
            firmwareVersion: this.firmwareVersion,
            lastSeen: this.lastSeen,
            sensorState: this.sensorState,
            reportInterval: this.reportInterval
        };
        
        try {
            const stateDir = './device_states';
            await fs.mkdir(stateDir, { recursive: true });
            
            const statePath = path.join(stateDir, `${this.deviceId}.json`);
            await fs.writeFile(statePath, JSON.stringify(state, null, 2));
        } catch (error) {
            console.error(chalk.red(`❌ Failed to save state for ${this.deviceId}:`, error.message));
        }
    }
    
    disconnect() {
        this.stopPeriodicReporting();
        this.reportStatus('offline');
        
        setTimeout(() => {
            this.client.end();
            console.log(chalk.yellow(`👋 Device ${this.deviceId} disconnected`));
        }, 1000);
    }
}

```

### Exercise 2: デバイス管理アプリケーション

`src/device_manager.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import asyncio
import threading
from datetime import datetime
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.panel import Panel
from rich.prompt import Prompt
from rich.layout import Layout

console = Console()

class IoTDeviceManager:
    """デバイス管理アプリケーション"""
    
    def __init__(self):
        self.client = mqtt.Client(
            client_id='device-manager',
            clean_session=True
        )
        
        self.devices: Dict[str, Dict[str, Any]] = {}
        self.running = False
        self.setup_mqtt_handlers()
    
    def setup_mqtt_handlers(self):
        """イベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print("🎛️  Device Manager connected", style="green")
            self.subscribe_to_device_topics()
    
    def subscribe_to_device_topics(self):
        """デバイストピックを購読"""
        topics = [
            'devices/+/status',
            'devices/+/errors',
            'devices/+/responses/+',
            'devices/+/firmware_update_progress',
            'devices/+/firmware_update_result',
            'sensors/+/+/data',
            'alerts/+/+'
        ]
        
        for topic in topics:
            self.client.subscribe(topic, qos=1)
            
        console.print(f"Subscribed to {len(topics)} device monitoring topics")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        self.handle_device_message(msg.topic, msg.payload)
    
    def handle_device_message(self, topic: str, message: bytes):
        """デバイスメッセージ処理"""
        try:
            data = json.loads(message.decode('utf-8'))
            topic_parts = topic.split('/')
            
            # デバイスIDを取得
            if len(topic_parts) >= 2:
                if topic.startswith('devices/'):
                    device_id = topic_parts[1]
                elif topic.startswith('sensors/'):
                    device_id = data.get('device_id', topic_parts[2]) if len(topic_parts) >= 3 else 'unknown'
                elif topic.startswith('alerts/'):
                    device_id = data.get('device_id', topic_parts[2]) if len(topic_parts) >= 3 else 'unknown'
                else:
                    return
                
                # デバイス情報更新
                if device_id not in self.devices:
                    self.devices[device_id] = {
                        'device_id': device_id,
                        'last_seen': datetime.now().isoformat(),
                        'status': 'unknown',
                        'message_count': 0,
                        'errors': [],
                        'last_data': None
                    }
                
                device_info = self.devices[device_id]
                device_info['last_seen'] = datetime.now().isoformat()
                device_info['message_count'] += 1
                
                # メッセージタイプ別処理
                if '/status' in topic:
                    device_info['status'] = data.get('status', 'unknown')
                    device_info['battery_level'] = data.get('battery_level', 0)
                    device_info['firmware_version'] = data.get('firmware_version', 'unknown')
                    
                elif '/errors' in topic:
                    error_info = {
                        'timestamp': data.get('timestamp', datetime.now().isoformat()),
                        'error_type': data.get('error_type', 'unknown'),
                        'details': data.get('details', '')
                    }
                    device_info['errors'].append(error_info)
                    
                    # エラーリストを最大100件に制限
                    if len(device_info['errors']) > 100:
                        device_info['errors'] = device_info['errors'][-100:]
                    
                    console.print(f"🚨 Error from {device_id}: {error_info['error_type']}", style="red")
                    
                elif '/data' in topic:
                    device_info['last_data'] = data
                    device_info['device_type'] = data.get('device_type', 'unknown')
                    device_info['location'] = data.get('location', 'unknown')
                    
                elif 'alerts/' in topic:
                    console.print(f"🚨 Alert from {device_id}: {data.get('alert_type', 'unknown')}", style="yellow")
                    
        except (json.JSONDecodeError, KeyError) as e:
            # 不正なメッセージは無視
            pass
    
    def send_command_to_device(self, device_id: str, command_type: str, **kwargs):
        """デバイスにコマンド送信"""
        command = {
            'timestamp': datetime.now().isoformat(),
            'command_id': f"cmd_{int(time.time())}",
            **kwargs
        }
        
        topic = f"devices/{device_id}/commands/{command_type}"
        
        try:
            self.client.publish(topic, json.dumps(command), qos=1)
            console.print(f"📡 Sent {command_type} command to {device_id}", style="blue")
            return True
        except Exception as e:
            console.print(f"❌ Failed to send command: {e}", style="red")
            return False
    
    def send_broadcast_command(self, command_type: str, **kwargs):
        """全デバイスにブロードキャストコマンド送信"""
        command = {
            'timestamp': datetime.now().isoformat(),
            'command_id': f"broadcast_{int(time.time())}",
            **kwargs
        }
        
        topic = f"devices/broadcast/{command_type}"
        
        try:
            self.client.publish(topic, json.dumps(command), qos=1)
            console.print(f"📶 Broadcast {command_type} command sent", style="blue")
            return True
        except Exception as e:
            console.print(f"❌ Failed to send broadcast: {e}", style="red")
            return False
    
    def get_device_stats(self) -> Dict[str, Any]:
        """デバイス統計情報取得"""
        now = datetime.now()
        online_devices = []
        offline_devices = []
        
        for device_id, device_info in self.devices.items():
            last_seen = datetime.fromisoformat(device_info['last_seen'])
            time_diff = (now - last_seen).total_seconds()
            
            if time_diff < 120:  # 2分以内に通信があったらオンライン
                online_devices.append(device_info)
            else:
                offline_devices.append(device_info)
        
        # デバイスタイプ別統計
        device_types = {}
        for device in online_devices:
            device_type = device.get('device_type', 'unknown')
            if device_type not in device_types:
                device_types[device_type] = 0
            device_types[device_type] += 1
        
        # エラー統計
        total_errors = sum(len(device.get('errors', [])) for device in self.devices.values())
        
        return {
            'total_devices': len(self.devices),
            'online_devices': len(online_devices),
            'offline_devices': len(offline_devices),
            'device_types': device_types,
            'total_errors': total_errors,
            'total_messages': sum(device.get('message_count', 0) for device in self.devices.values())
        }
    
    def create_status_table(self) -> Table:
        """デバイスステータステーブル作成"""
        table = Table(title="IoT Device Status")
        table.add_column("Device ID", style="cyan", no_wrap=True)
        table.add_column("Type", style="magenta")
        table.add_column("Status", style="green")
        table.add_column("Battery", style="yellow")
        table.add_column("Firmware", style="blue")
        table.add_column("Last Seen", style="dim")
        table.add_column("Errors", style="red")
        
        now = datetime.now()
        
        for device_id, device_info in sorted(self.devices.items()):
            last_seen = datetime.fromisoformat(device_info['last_seen'])
            time_diff = (now - last_seen).total_seconds()
            
            # ステータスの色付け
            if time_diff < 120:
                status_style = "[green]●[/green]"
            else:
                status_style = "[red]●[/red]"
            
            # 最終通信時刻のフォーマット
            if time_diff < 60:
                last_seen_str = f"{int(time_diff)}s ago"
            elif time_diff < 3600:
                last_seen_str = f"{int(time_diff/60)}m ago"
            else:
                last_seen_str = f"{int(time_diff/3600)}h ago"
            
            battery_level = device_info.get('battery_level', 0)
            battery_str = f"{battery_level:.1f}%" if battery_level > 0 else "N/A"
            
            error_count = len(device_info.get('errors', []))
            
            table.add_row(
                device_id,
                device_info.get('device_type', 'unknown'),
                f"{status_style} {device_info.get('status', 'unknown')}",
                battery_str,
                device_info.get('firmware_version', 'unknown'),
                last_seen_str,
                str(error_count) if error_count > 0 else "-"
            )
        
        return table
    
    def run_interactive_cli(self):
        """インタラクティブCLI実行"""
        console.print("🎛️  IoT Device Manager - Interactive Mode", style="bold green")
        console.print("Type 'help' for available commands\n")
        
        while self.running:
            try:
                command = Prompt.ask("[bold blue]manager[/bold blue]", default="")
                
                if not command:
                    continue
                    
                self.handle_cli_command(command)
                    
            except KeyboardInterrupt:
                console.print("\n⚠️  Exiting...", style="yellow")
                break
            except Exception as e:
                console.print(f"❌ CLI Error: {e}", style="red")
    
    def handle_cli_command(self, command: str):
        """コマンド処理"""
        parts = command.strip().split()
        if not parts:
            return
        
        cmd = parts[0].lower()
        args = parts[1:]
        
        if cmd == 'help':
            self.show_help()
        elif cmd == 'status' or cmd == 'st':
            console.print(self.create_status_table())
        elif cmd == 'stats':
            self.show_stats()
        elif cmd == 'reboot':
            if args:
                device_id = args[0]
                self.send_command_to_device(device_id, 'reboot')
            else:
                console.print("❌ Usage: reboot <device_id>", style="red")
        elif cmd == 'interval':
            if len(args) >= 2:
                device_id, interval = args[0], int(args[1])
                self.send_command_to_device(device_id, 'update_interval', interval=interval)
            else:
                console.print("❌ Usage: interval <device_id> <seconds>", style="red")
        elif cmd == 'firmware':
            if len(args) >= 2:
                device_id, version = args[0], args[1]
                self.send_command_to_device(device_id, 'firmware_update', version=version)
            else:
                console.print("❌ Usage: firmware <device_id> <version>", style="red")
        elif cmd == 'broadcast':
            if args:
                command_type = args[0]
                if command_type == 'reboot':
                    self.send_broadcast_command('reboot')
                elif command_type == 'interval' and len(args) >= 2:
                    interval = int(args[1])
                    self.send_broadcast_command('update_interval', interval=interval)
                else:
                    console.print("❌ Usage: broadcast [reboot|interval <seconds>]", style="red")
            else:
                console.print("❌ Usage: broadcast <command>", style="red")
        elif cmd == 'errors':
            if args:
                device_id = args[0]
                self.show_device_errors(device_id)
            else:
                console.print("❌ Usage: errors <device_id>", style="red")
        elif cmd == 'clear':
            console.clear()
        elif cmd == 'quit' or cmd == 'exit':
            self.running = False
        else:
            console.print(f"❌ Unknown command: {cmd}", style="red")
    
    def show_help(self):
        """ヘルプ表示"""
        help_text = """
[bold blue]Available Commands:[/bold blue]

[cyan]status (st)[/cyan]        - Show device status table
[cyan]stats[/cyan]             - Show overall statistics
[cyan]reboot <device_id>[/cyan] - Reboot specific device
[cyan]interval <device_id> <sec>[/cyan] - Update report interval
[cyan]firmware <device_id> <ver>[/cyan] - Update firmware
[cyan]broadcast <cmd>[/cyan]   - Send broadcast command
[cyan]errors <device_id>[/cyan] - Show device errors
[cyan]clear[/cyan]             - Clear screen
[cyan]help[/cyan]              - Show this help
[cyan]quit/exit[/cyan]         - Exit manager
        """
        console.print(Panel(help_text, title="Help", border_style="blue"))
    
    def show_stats(self):
        """統計情報表示"""
        stats = self.get_device_stats()
        
        stats_text = f"""
[green]Total Devices:[/green] {stats['total_devices']}
[green]Online:[/green] {stats['online_devices']}
[red]Offline:[/red] {stats['offline_devices']}
[yellow]Total Messages:[/yellow] {stats['total_messages']}
[red]Total Errors:[/red] {stats['total_errors']}

[cyan]Device Types:[/cyan]
        """
        
        for device_type, count in stats['device_types'].items():
            stats_text += f"  {device_type}: {count}\n"
        
        console.print(Panel(stats_text, title="Statistics", border_style="green"))
    
    def show_device_errors(self, device_id: str):
        """デバイスエラー表示"""
        if device_id not in self.devices:
            console.print(f"❌ Device {device_id} not found", style="red")
            return
        
        errors = self.devices[device_id].get('errors', [])
        if not errors:
            console.print(f"No errors found for {device_id}", style="green")
            return
        
        error_table = Table(title=f"Errors for {device_id}")
        error_table.add_column("Time", style="dim")
        error_table.add_column("Type", style="red")
        error_table.add_column("Details", style="yellow")
        
        for error in errors[-20:]:  # 最新20件を表示
            timestamp = error['timestamp'][:19].replace('T', ' ')
            error_table.add_row(
                timestamp,
                error['error_type'],
                error['details'][:50] + '...' if len(error['details']) > 50 else error['details']
            )
        
        console.print(error_table)
    
    def start(self):
        """マネージャー開始"""
        try:
            self.client.connect('localhost', 1883, 60)
            self.client.loop_start()
            time.sleep(2)  # 接続完了まで待機
            
            self.running = True
            self.run_interactive_cli()
            
        except Exception as e:
            console.print(f"❌ Failed to start device manager: {e}", style="red")
        finally:
            self.stop()
    
    def stop(self):
        """マネージャー停止"""
        self.running = False
        self.client.loop_stop()
        self.client.disconnect()
        console.print("👋 Device Manager stopped", style="yellow")

# 使用例
def main():
    """メイン関数"""
    manager = IoTDeviceManager()
    manager.start()

if __name__ == "__main__":
    main()
            'sensors/+/+/data', 
            'devices/+/errors',
            'alerts/+/+',
            'devices/+/responses/+',
            'devices/+/firmware_update_progress',
            'devices/+/firmware_update_result'
        ];
        
        topics.forEach(topic => {
            this.client.subscribe(topic, { qos: 1 });
        });
        
        console.log(chalk.blue('📡 Subscribed to device management topics'));
    }
    
    handleDeviceMessage(topic, message) {
        try {
            const data = JSON.parse(message.toString());
            const topicParts = topic.split('/');
            
            if (topic.includes('/status')) {
                this.updateDeviceStatus(data);
            } else if (topic.includes('/data')) {
                this.processSensorData(topicParts, data);
            } else if (topic.includes('/errors')) {
                this.handleDeviceError(data);
            } else if (topic.includes('/alerts/')) {
                this.handleAlert(topicParts, data);
            } else if (topic.includes('/responses/')) {
                this.handleCommandResponse(topicParts, data);
            } else if (topic.includes('/firmware_update')) {
                this.handleFirmwareUpdate(topicParts, data);
            }
        } catch (error) {
            console.error(chalk.red('❌ Message parsing error:'), error.message);
        }
    }
    
    updateDeviceStatus(statusData) {
        const deviceId = statusData.deviceId;
        
        if (!this.devices.has(deviceId)) {
            this.devices.set(deviceId, {
                deviceId: deviceId,
                firstSeen: new Date().toISOString(),
                messageCount: 0,
                errors: [],
                alerts: []
            });
        }
        
        const device = this.devices.get(deviceId);
        Object.assign(device, statusData);
        
        const statusColor = statusData.status === 'online' ? 'green' : 
                           statusData.status === 'offline' ? 'red' : 'yellow';
        
        console.log(chalk[statusColor](`📱 Device ${deviceId}: ${statusData.status}`));
    }
    
    processSensorData(topicParts, data) {
        const deviceId = data.deviceId;
        
        if (this.devices.has(deviceId)) {
            const device = this.devices.get(deviceId);
            device.messageCount++;
            device.lastData = data;
            device.lastSeen = data.timestamp;
            
            // 異常値の検知
            this.checkAnomalyValues(data);
        }
    }
    
    checkAnomalyValues(data) {
        const anomalies = [];
        
        if (data.temperature && (data.temperature < -5 || data.temperature > 45)) {
            anomalies.push(`Temperature: ${data.temperature}°C`);
        }
        
        if (data.humidity && (data.humidity < 10 || data.humidity > 95)) {
            anomalies.push(`Humidity: ${data.humidity}%`);
        }
        
        if (data.batteryLevel && data.batteryLevel < 15) {
            anomalies.push(`Low battery: ${data.batteryLevel}%`);
        }
        
        if (anomalies.length > 0) {
            console.log(chalk.yellow(`⚠️  Anomaly detected in ${data.deviceId}:`));
            anomalies.forEach(anomaly => {
                console.log(chalk.yellow(`   - ${anomaly}`));
            });
        }
    }
    
    handleDeviceError(errorData) {
        console.log(chalk.red(`🚨 Device Error: ${errorData.deviceId}`));
        console.log(chalk.red(`   Type: ${errorData.errorType}`));
        console.log(chalk.red(`   Time: ${errorData.timestamp}`));
        
        if (this.devices.has(errorData.deviceId)) {
            const device = this.devices.get(errorData.deviceId);
            device.errors.push(errorData);
            
            // エラーが頻発している場合は警告
            const recentErrors = device.errors.filter(error => 
                new Date(error.timestamp) > new Date(Date.now() - 300000) // 5分以内
            );
            
            if (recentErrors.length > 3) {
                console.log(chalk.red(`🔥 Multiple errors from ${errorData.deviceId} - requires attention`));
            }
        }
    }
    
    handleAlert(topicParts, alertData) {
        const alertType = topicParts[1];
        
        console.log(chalk.yellow(`🚨 ALERT [${alertType}]: ${alertData.deviceId}`));
        console.log(chalk.yellow(`   Severity: ${alertData.severity}`));
        
        if (this.devices.has(alertData.deviceId)) {
            const device = this.devices.get(alertData.deviceId);
            device.alerts.push(alertData);
        }
    }
    
    handleCommandResponse(topicParts, responseData) {
        const command = topicParts[3];
        console.log(chalk.blue(`📋 Command Response [${command}]: ${responseData.deviceId}`));
        console.log(chalk.blue(`   Success: ${responseData.success}`));
    }
    
    handleFirmwareUpdate(topicParts, updateData) {
        const updateType = topicParts[3];
        
        if (updateType === 'progress') {
            console.log(chalk.blue(`📦 Firmware Update Progress: ${updateData.deviceId}`));
            console.log(chalk.blue(`   ${updateData.step}: ${updateData.progress}%`));
        } else if (updateType === 'result') {
            const status = updateData.success ? 'SUCCESS' : 'FAILED';
            const color = updateData.success ? 'green' : 'red';
            
            console.log(chalk[color](`📦 Firmware Update ${status}: ${updateData.deviceId}`));
            if (updateData.success) {
                console.log(chalk.green(`   Updated to version: ${updateData.newVersion}`));
            } else {
                console.log(chalk.red(`   Error: ${updateData.error}`));
            }
        }
    }
    
    setupCLI() {
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            prompt: chalk.blue('DeviceManager> ')
        });
        
        this.rl.on('line', (input) => {
            this.handleCommand(input.trim());
        });
        
        // 初期プロンプト表示
        setTimeout(() => {
            console.log(chalk.yellow('\n🎛️  IoT Device Manager CLI'));
            console.log(chalk.gray('Type "help" for available commands\n'));
            this.rl.prompt();
        }, 2000);
    }
    
    handleCommand(input) {
        const [command, ...args] = input.split(' ');
        
        switch (command.toLowerCase()) {
            case 'help':
                this.showHelp();
                break;
            case 'list':
                this.listDevices();
                break;
            case 'status':
                this.showDeviceStatus(args[0]);
                break;
            case 'reboot':
                this.rebootDevice(args[0]);
                break;
            case 'interval':
                this.updateReportInterval(args[0], parseInt(args[1]));
                break;
            case 'firmware':
                this.updateFirmware(args[0], args[1]);
                break;
            case 'calibrate':
                this.calibrateDevice(args[0]);
                break;
            case 'broadcast':
                this.broadcastCommand(args[0], args.slice(1));
                break;
            case 'stats':
                this.showSystemStats();
                break;
            case 'errors':
                this.showRecentErrors();
                break;
            case 'alerts':
                this.showRecentAlerts();
                break;
            case 'quit':
                this.quit();
                return;
            default:
                console.log(chalk.red(`❌ Unknown command: ${command}`));
                console.log(chalk.gray('Type "help" for available commands'));
        }
        
        this.rl.prompt();
    }
    
    showHelp() {
        console.log(chalk.blue('\n📖 Available Commands:'));
        console.log('  help                     - Show this help');
        console.log('  list                     - List all devices');  
        console.log('  status <deviceId>        - Show device details');
        console.log('  reboot <deviceId>        - Reboot a device');
        console.log('  interval <deviceId> <sec> - Update report interval');
        console.log('  firmware <deviceId> <ver> - Update firmware');
        console.log('  calibrate <deviceId>     - Calibrate sensors');
        console.log('  broadcast <command>      - Send command to all devices');
        console.log('  stats                    - Show system statistics');
        console.log('  errors                   - Show recent errors');
        console.log('  alerts                   - Show recent alerts');
        console.log('  quit                     - Exit manager\n');
    }
    
    listDevices() {
        if (this.devices.size === 0) {
            console.log(chalk.yellow('📱 No devices found'));
            return;
        }
        
        console.log(chalk.blue(`\n📱 Devices (${this.devices.size} total):`));
        console.log(chalk.gray('ID'.padEnd(20) + 'Status'.padEnd(12) + 'Battery'.padEnd(10) + 'Messages'.padEnd(10) + 'Last Seen'));
        console.log(chalk.gray('-'.repeat(80)));
        
        Array.from(this.devices.values()).forEach(device => {
            const status = device.status || 'unknown';
            const battery = device.batteryLevel ? `${device.batteryLevel.toFixed(1)}%` : 'N/A';
            const messages = device.messageCount || 0;
            const lastSeen = device.lastSeen ? new Date(device.lastSeen).toLocaleTimeString() : 'Never';
            
            const statusColor = status === 'online' ? 'green' : 
                               status === 'offline' ? 'red' : 'yellow';
            
            console.log(
                device.deviceId.padEnd(20) + 
                chalk[statusColor](status.padEnd(12)) +
                battery.padEnd(10) +
                messages.toString().padEnd(10) +
                lastSeen
            );
        });
    }
    
    showDeviceStatus(deviceId) {
        if (!deviceId) {
            console.log(chalk.red('❌ Please specify a device ID'));
            return;
        }
        
        const device = this.devices.get(deviceId);
        if (!device) {
            console.log(chalk.red(`❌ Device not found: ${deviceId}`));
            return;
        }
        
        console.log(chalk.blue(`\n📱 Device Details: ${deviceId}`));
        console.log(`Status: ${device.status || 'unknown'}`);
        console.log(`Battery: ${device.batteryLevel ? device.batteryLevel.toFixed(1) + '%' : 'N/A'}`);
        console.log(`Firmware: ${device.firmwareVersion || 'N/A'}`);
        console.log(`Messages: ${device.messageCount || 0}`);
        console.log(`First Seen: ${device.firstSeen ? new Date(device.firstSeen).toLocaleString() : 'N/A'}`);
        console.log(`Last Seen: ${device.lastSeen ? new Date(device.lastSeen).toLocaleString() : 'Never'}`);
        
        if (device.lastData) {
            console.log('\nLast Sensor Data:');
            Object.entries(device.lastData).forEach(([key, value]) => {
                if (key !== 'deviceId' && key !== 'timestamp') {
                    console.log(`  ${key}: ${JSON.stringify(value)}`);
                }
            });
        }
        
        if (device.errors && device.errors.length > 0) {
            console.log(chalk.red(`\nRecent Errors (${device.errors.length}):`));
            device.errors.slice(-5).forEach(error => {
                console.log(chalk.red(`  ${error.errorType} - ${new Date(error.timestamp).toLocaleString()}`));
            });
        }
    }
    
    rebootDevice(deviceId) {
        if (!deviceId) {
            console.log(chalk.red('❌ Please specify a device ID'));
            return;
        }
        
        console.log(chalk.blue(`🔄 Sending reboot command to ${deviceId}`));
        
        const command = {
            timestamp: new Date().toISOString(),
            requestId: `reboot_${Date.now()}`
        };
        
        this.client.publish(`devices/${deviceId}/commands/reboot`, JSON.stringify(command), { qos: 1 });
    }
    
    updateReportInterval(deviceId, intervalSeconds) {
        if (!deviceId || !intervalSeconds) {
            console.log(chalk.red('❌ Usage: interval <deviceId> <seconds>'));
            return;
        }
        
        if (intervalSeconds < 5 || intervalSeconds > 300) {
            console.log(chalk.red('❌ Interval must be between 5 and 300 seconds'));
            return;
        }
        
        console.log(chalk.blue(`⏱️  Updating report interval for ${deviceId} to ${intervalSeconds}s`));
        
        const command = {
            interval: intervalSeconds,
            timestamp: new Date().toISOString()
        };
        
        this.client.publish(`devices/${deviceId}/commands/update_interval`, JSON.stringify(command), { qos: 1 });
    }
    
    updateFirmware(deviceId, version) {
        if (!deviceId || !version) {
            console.log(chalk.red('❌ Usage: firmware <deviceId> <version>'));
            return;
        }
        
        console.log(chalk.blue(`📦 Starting firmware update for ${deviceId} to version ${version}`));
        
        const command = {
            version: version,
            downloadUrl: `https://firmware.example.com/${version}.bin`,
            checksum: 'sha256:example_checksum',
            timestamp: new Date().toISOString()
        };
        
        this.client.publish(`devices/${deviceId}/commands/firmware_update`, JSON.stringify(command), { qos: 1 });
    }
    
    showSystemStats() {
        const totalDevices = this.devices.size;
        const onlineDevices = Array.from(this.devices.values()).filter(d => d.status === 'online').length;
        const devicesWithErrors = Array.from(this.devices.values()).filter(d => d.errors && d.errors.length > 0).length;
        const totalMessages = Array.from(this.devices.values()).reduce((sum, d) => sum + (d.messageCount || 0), 0);
        
        console.log(chalk.blue('\n📊 System Statistics:'));
        console.log(`Total Devices: ${totalDevices}`);
        console.log(`Online Devices: ${onlineDevices}`);
        console.log(`Offline Devices: ${totalDevices - onlineDevices}`);
        console.log(`Devices with Errors: ${devicesWithErrors}`);
        console.log(`Total Messages: ${totalMessages}`);
    }
    
    quit() {
        console.log(chalk.yellow('\n👋 Device Manager shutting down...'));
        this.rl.close();
        this.client.end();
        process.exit(0);
    }
}

// 実行
if (require.main === module) {
    new IoTDeviceManager();
}

module.exports = IoTDeviceManager;
```

## 🎯 練習問題

### 問題1: デバイス起動とモニタリング
1. `iot-device-simulator.js`を使って10台のデバイスを起動してください
2. `device-manager.js`で各デバイスの状態を監視してください
3. いくつかのデバイスをリブートして、状態変化を観察してください

### 問題2: ファームウェア更新
1. デバイスマネージャーから特定のデバイスのファームウェアを更新してください
2. 更新プロセスの進捗を観察してください
3. 故意に失敗を発生させて、エラーハンドリングを確認してください

### 問題3: カスタムデバイスタイプ
以下の仕様で新しいデバイスタイプ「smart-meter」を作成してください：
- 電力消費量（kWh）を測定
- 5分間隔でデータ送信
- 使用量が500kWhを超えるとアラート送信
- 料金計算機能（1kWh = 30円）

## ✅ 確認チェックリスト

- [ ] 複数のIoTデバイスをシミュレーションできた
- [ ] リアルタイムでデバイス状態を監視できた
- [ ] デバイス管理コマンドを実行できた
- [ ] ファームウェア更新プロセスを理解した
- [ ] エラーレポートとアラートシステムを確認した
- [ ] デバイス固有のデータ生成を実装できた
- [ ] 大規模IoTシステムの運用課題を理解した

## 🔧 実用的な拡張例

このハンズオンで作成したシミュレーターは、以下のような実用的な拡張が可能です：

### データベース連携
```javascript
// PostgreSQL/InfluxDBへのデータ保存
const { Client } = require('pg');
const client = new Client({
    connectionString: 'postgresql://user:pass@localhost/iotdb'
});

// データ保存
async function saveSensorData(data) {
    await client.query(
        'INSERT INTO sensor_data (device_id, temperature, humidity, timestamp) VALUES ($1, $2, $3, $4)',
        [data.deviceId, data.temperature, data.humidity, data.timestamp]
    );
}
```

### Grafana/Prometheusとの統合
```javascript
// Prometheusメトリクスの出力
const promClient = require('prom-client');

const temperatureGauge = new promClient.Gauge({
    name: 'iot_temperature_celsius',
    help: 'Temperature in Celsius',
    labelNames: ['device_id', 'location']
});

// メトリクスの更新
temperatureGauge.set({
    device_id: data.deviceId,
    location: data.location
}, data.temperature);
```

---

**次のステップ**: [10-monitoring-dashboard](../10-monitoring-dashboard/) で監視ダッシュボードの構築を学習しましょう！