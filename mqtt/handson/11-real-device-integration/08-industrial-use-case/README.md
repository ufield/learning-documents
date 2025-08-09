# 演習8: 産業用途事例 - スマート工場監視システム

## 概要

これまでの演習で学んだ技術を統合し、実際の産業現場で使用されるスマート工場監視システムを構築します。温度・振動・音響監視、予知保全、リアルタイムアラート、ダッシュボードまで、エンドツーエンドの IoT ソリューションを実装します。

## 学習目標

- 産業IoTシステムアーキテクチャ設計
- 複数デバイス・センサーの統合管理
- リアルタイム監視とアラートシステム
- 予知保全アルゴリズム実装
- 産業用セキュリティ要件対応

## システム構成

```
スマート工場監視システム
├── エッジデバイス層
│   ├── Jetson Xavier NX (AI処理・ゲートウェイ)
│   ├── Raspberry Pi 4 × 3 (エリア監視)
│   └── ESP32 × 10 (センサーノード)
├── 通信層
│   ├── MQTT ブローカー (Eclipse Mosquitto)
│   ├── InfluxDB (時系列データ)
│   └── Redis (リアルタイムキャッシュ)
├── 処理層
│   ├── データ処理エンジン (Python)
│   ├── AI推論エンジン (TensorFlow/PyTorch)
│   └── アラート管理システム
└── 表示層
    ├── 監視ダッシュボード (Grafana)
    ├── モバイルアプリ (Flutter)
    └── 管理Webアプリ (React)
```

## 必要機材

### ハードウェア
- NVIDIA Jetson Xavier NX × 1 (メインゲートウェイ)
- Raspberry Pi 4B × 3 (エリアゲートウェイ)
- ESP32 DevKit × 10 (センサーノード)
- 産業用センサー
  - 振動センサー (ADXL345) × 5
  - 温度センサー (DS18B20) × 10
  - 圧力センサー (BMP280) × 3
  - 音響センサー (マイク) × 3
  - 電流センサー (ACS712) × 5
- ネットワーク機器
  - 産業用WiFiルーター
  - イーサネットスイッチ

### ソフトウェア
- Docker & Docker Compose
- MQTT ブローカー (Mosquitto)
- 時系列DB (InfluxDB)
- 監視ダッシュボード (Grafana)
- アプリケーション (Python/Node.js)

## 演習手順

### Step 1: システムアーキテクチャ構築

#### 1.1 Docker環境セットアップ

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  # MQTT ブローカー
  mosquitto:
    image: eclipse-mosquitto:2.0
    container_name: factory_mosquitto
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - ./mosquitto/data:/mosquitto/data
      - ./mosquitto/log:/mosquitto/log
    restart: unless-stopped
    networks:
      - factory_network

  # InfluxDB 時系列データベース
  influxdb:
    image: influxdb:2.7
    container_name: factory_influxdb
    ports:
      - "8086:8086"
    environment:
      - DOCKER_INFLUXDB_INIT_MODE=setup
      - DOCKER_INFLUXDB_INIT_USERNAME=admin
      - DOCKER_INFLUXDB_INIT_PASSWORD=smartfactory2024
      - DOCKER_INFLUXDB_INIT_ORG=SmartFactory
      - DOCKER_INFLUXDB_INIT_BUCKET=factory_sensors
    volumes:
      - influxdb_data:/var/lib/influxdb2
      - influxdb_config:/etc/influxdb2
    restart: unless-stopped
    networks:
      - factory_network

  # Redis キャッシュ
  redis:
    image: redis:7-alpine
    container_name: factory_redis
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    restart: unless-stopped
    networks:
      - factory_network

  # Grafana 監視ダッシュボード
  grafana:
    image: grafana/grafana:10.2.0
    container_name: factory_grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=smartfactory2024
      - GF_INSTALL_PLUGINS=redis-datasource
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
      - ./grafana/dashboards:/var/lib/grafana/dashboards
    restart: unless-stopped
    networks:
      - factory_network

  # データ処理エンジン
  data_processor:
    build: 
      context: ./data_processor
      dockerfile: Dockerfile
    container_name: factory_processor
    environment:
      - MQTT_BROKER=mosquitto
      - INFLUXDB_URL=http://influxdb:8086
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./data_processor:/app
      - ./shared_data:/data
    depends_on:
      - mosquitto
      - influxdb
      - redis
    restart: unless-stopped
    networks:
      - factory_network

  # アラート管理
  alert_manager:
    build:
      context: ./alert_manager
      dockerfile: Dockerfile
    container_name: factory_alerts
    environment:
      - MQTT_BROKER=mosquitto
      - REDIS_URL=redis://redis:6379
      - SMTP_SERVER=smtp.gmail.com
      - SMTP_PORT=587
    volumes:
      - ./alert_manager:/app
    depends_on:
      - mosquitto
      - redis
    restart: unless-stopped
    networks:
      - factory_network

  # Web API
  web_api:
    build:
      context: ./web_api
      dockerfile: Dockerfile
    container_name: factory_api
    ports:
      - "8000:8000"
    environment:
      - INFLUXDB_URL=http://influxdb:8086
      - REDIS_URL=redis://redis:6379
    volumes:
      - ./web_api:/app
    depends_on:
      - influxdb
      - redis
    restart: unless-stopped
    networks:
      - factory_network

networks:
  factory_network:
    driver: bridge

volumes:
  influxdb_data:
  influxdb_config:
  grafana_data:
  redis_data:
```

#### 1.2 MQTT設定

`mosquitto/config/mosquitto.conf`:

```conf
# Mosquitto設定ファイル
persistence true
persistence_location /mosquitto/data/

# ログ設定
log_dest file /mosquitto/log/mosquitto.log
log_type error
log_type warning
log_type notice
log_type information

# WebSocket サポート
listener 9001
protocol websockets

# 認証設定（本番環境では必須）
allow_anonymous true
# password_file /mosquitto/config/passwd

# アクセス制御
# acl_file /mosquitto/config/acl.conf

# ブリッジ接続（クラウド連携用）
# connection cloud_bridge
# address cloud-mqtt-broker.example.com:8883
# bridge_protocol_version mqttv311
# bridge_insecure false
```

### Step 2: データ処理エンジン実装

#### 2.1 統合データ処理システム

`data_processor/main.py`:

```python
#!/usr/bin/env python3
import asyncio
import json
import logging
import os
import signal
import sys
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
import numpy as np
from dataclasses import dataclass, asdict
from enum import Enum
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS
import redis
import pandas as pd
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
import pickle
import threading
import time

# ログ設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class AlertLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"
    EMERGENCY = "emergency"

@dataclass
class SensorReading:
    device_id: str
    timestamp: datetime
    sensor_type: str
    value: float
    unit: str
    location: str
    metadata: Dict[str, Any] = None

@dataclass
class Alert:
    alert_id: str
    device_id: str
    alert_type: str
    level: AlertLevel
    message: str
    timestamp: datetime
    value: Optional[float] = None
    threshold: Optional[float] = None
    acknowledged: bool = False

class FactoryDataProcessor:
    """工場データ処理エンジン"""
    
    def __init__(self):
        # 環境変数から設定読み込み
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.influxdb_url = os.getenv('INFLUXDB_URL', 'http://localhost:8086')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        
        # クライアント初期化
        self.mqtt_client = None
        self.influxdb_client = None
        self.redis_client = None
        self.write_api = None
        
        # データバッファ
        self.sensor_buffer = []
        self.buffer_lock = threading.Lock()
        self.max_buffer_size = 1000
        
        # 異常検知モデル
        self.anomaly_models = {}
        self.scalers = {}
        
        # 統計情報
        self.stats = {
            'messages_processed': 0,
            'alerts_generated': 0,
            'anomalies_detected': 0,
            'last_processing_time': None
        }
        
        # 閾値設定
        self.thresholds = {
            'temperature': {'warning': 70, 'critical': 80},
            'vibration': {'warning': 5.0, 'critical': 8.0},
            'pressure': {'warning': 1050, 'critical': 1100},
            'current': {'warning': 15.0, 'critical': 20.0},
            'noise_level': {'warning': 80, 'critical': 90}
        }
        
        self.running = False
        
        logger.info("Factory Data Processor initialized")
    
    async def initialize(self):
        """システム初期化"""
        try:
            # MQTT接続
            await self.setup_mqtt()
            
            # InfluxDB接続
            self.setup_influxdb()
            
            # Redis接続
            self.setup_redis()
            
            # 異常検知モデル読み込み
            self.load_anomaly_models()
            
            logger.info("All systems initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    async def setup_mqtt(self):
        """MQTT設定"""
        self.mqtt_client = mqtt.Client(client_id="factory_data_processor")
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        self.mqtt_client.on_disconnect = self.on_mqtt_disconnect
        
        try:
            self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
            self.mqtt_client.loop_start()
            logger.info("MQTT client started")
        except Exception as e:
            logger.error(f"MQTT connection failed: {e}")
            raise
    
    def setup_influxdb(self):
        """InfluxDB設定"""
        try:
            self.influxdb_client = InfluxDBClient(
                url=self.influxdb_url,
                token="your-influxdb-token",  # 実際の環境では環境変数から取得
                org="SmartFactory"
            )
            self.write_api = self.influxdb_client.write_api(write_options=SYNCHRONOUS)
            logger.info("InfluxDB client initialized")
        except Exception as e:
            logger.error(f"InfluxDB connection failed: {e}")
            raise
    
    def setup_redis(self):
        """Redis設定"""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("Redis client initialized")
        except Exception as e:
            logger.error(f"Redis connection failed: {e}")
            raise
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT接続時処理"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            
            # 全センサートピック購読
            topics = [
                "sensors/+/+/data",
                "sensors/+/+/environmental",
                "esp32/+/data",
                "jetson/+/sensors",
                "alerts/+/+/+"
            ]
            
            for topic in topics:
                client.subscribe(topic, qos=1)
                logger.info(f"Subscribed to {topic}")
        else:
            logger.error(f"MQTT connection failed with code {rc}")
    
    def on_mqtt_disconnect(self, client, userdata, rc):
        """MQTT切断時処理"""
        if rc != 0:
            logger.warning("Unexpected MQTT disconnection")
    
    def on_mqtt_message(self, client, userdata, msg):
        """MQTTメッセージ処理"""
        try:
            topic = msg.topic
            payload = json.loads(msg.payload.decode())
            
            # メッセージタイプに応じて処理
            if "/data" in topic or "/environmental" in topic or "/sensors" in topic:
                asyncio.create_task(self.process_sensor_data(topic, payload))
            elif "/alerts" in topic:
                asyncio.create_task(self.process_alert(topic, payload))
            
            self.stats['messages_processed'] += 1
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    async def process_sensor_data(self, topic: str, data: Dict[str, Any]):
        """センサーデータ処理"""
        try:
            device_id = data.get('device_id')
            timestamp_str = data.get('timestamp')
            
            if not device_id or not timestamp_str:
                logger.warning(f"Invalid sensor data format: {data}")
                return
            
            # タイムスタンプ解析
            try:
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now(timezone.utc)
            
            # センサー別処理
            sensor_readings = []
            
            # デバイスタイプに応じてデータ抽出
            if 'sensors' in data:
                # 複数センサー形式 (Raspberry Pi等)
                for sensor_name, sensor_data in data['sensors'].items():
                    if isinstance(sensor_data, dict):
                        readings = self.extract_readings_from_dict(
                            device_id, timestamp, sensor_name, sensor_data
                        )
                        sensor_readings.extend(readings)
            else:
                # 単純形式 (ESP32等)
                readings = self.extract_readings_from_simple_data(
                    device_id, timestamp, data
                )
                sensor_readings.extend(readings)
            
            # データバッファに追加
            with self.buffer_lock:
                self.sensor_buffer.extend(sensor_readings)
                if len(self.sensor_buffer) > self.max_buffer_size:
                    # バッファオーバーフロー対策
                    self.sensor_buffer = self.sensor_buffer[-self.max_buffer_size:]
            
            # InfluxDBに書き込み
            await self.write_to_influxdb(sensor_readings)
            
            # リアルタイム監視
            await self.real_time_monitoring(sensor_readings)
            
            # 異常検知
            await self.detect_anomalies(sensor_readings)
            
        except Exception as e:
            logger.error(f"Sensor data processing error: {e}")
    
    def extract_readings_from_dict(self, device_id: str, timestamp: datetime, 
                                   sensor_name: str, sensor_data: Dict[str, Any]) -> List[SensorReading]:
        """辞書形式からセンサー読み取り値抽出"""
        readings = []
        
        # 温度データ
        if 'temperature_c' in sensor_data:
            readings.append(SensorReading(
                device_id=device_id,
                timestamp=timestamp,
                sensor_type='temperature',
                value=sensor_data['temperature_c'],
                unit='celsius',
                location=self.get_device_location(device_id),
                metadata={'sensor_name': sensor_name}
            ))
        
        # 湿度データ
        if 'humidity_percent' in sensor_data:
            readings.append(SensorReading(
                device_id=device_id,
                timestamp=timestamp,
                sensor_type='humidity',
                value=sensor_data['humidity_percent'],
                unit='percent',
                location=self.get_device_location(device_id),
                metadata={'sensor_name': sensor_name}
            ))
        
        # 気圧データ
        if 'pressure_hpa' in sensor_data:
            readings.append(SensorReading(
                device_id=device_id,
                timestamp=timestamp,
                sensor_type='pressure',
                value=sensor_data['pressure_hpa'],
                unit='hpa',
                location=self.get_device_location(device_id),
                metadata={'sensor_name': sensor_name}
            ))
        
        return readings
    
    def extract_readings_from_simple_data(self, device_id: str, timestamp: datetime, 
                                          data: Dict[str, Any]) -> List[SensorReading]:
        """シンプル形式からセンサー読み取り値抽出"""
        readings = []
        
        # 直接的なセンサー値
        sensor_mappings = {
            'temperature_c': ('temperature', 'celsius'),
            'humidity_percent': ('humidity', 'percent'),
            'pressure_hpa': ('pressure', 'hpa'),
            'vibration_g': ('vibration', 'g'),
            'current_a': ('current', 'ampere'),
            'noise_level_db': ('noise_level', 'decibel'),
            'battery_voltage': ('voltage', 'volt')
        }
        
        for key, (sensor_type, unit) in sensor_mappings.items():
            if key in data and isinstance(data[key], (int, float)):
                readings.append(SensorReading(
                    device_id=device_id,
                    timestamp=timestamp,
                    sensor_type=sensor_type,
                    value=float(data[key]),
                    unit=unit,
                    location=self.get_device_location(device_id)
                ))
        
        return readings
    
    def get_device_location(self, device_id: str) -> str:
        """デバイス位置情報取得"""
        # Redis から位置情報取得（事前設定済み）
        try:
            location = self.redis_client.hget(f"device:{device_id}", "location")
            return location or "unknown"
        except:
            return "unknown"
    
    async def write_to_influxdb(self, readings: List[SensorReading]):
        """InfluxDB書き込み"""
        try:
            points = []
            
            for reading in readings:
                point = Point("sensor_data") \
                    .tag("device_id", reading.device_id) \
                    .tag("sensor_type", reading.sensor_type) \
                    .tag("location", reading.location) \
                    .field("value", reading.value) \
                    .field("unit", reading.unit) \
                    .time(reading.timestamp, WritePrecision.MS)
                
                if reading.metadata:
                    for key, value in reading.metadata.items():
                        point = point.tag(key, str(value))
                
                points.append(point)
            
            # バッチ書き込み
            self.write_api.write(bucket="factory_sensors", record=points)
            logger.debug(f"Written {len(points)} points to InfluxDB")
            
        except Exception as e:
            logger.error(f"InfluxDB write error: {e}")
    
    async def real_time_monitoring(self, readings: List[SensorReading]):
        """リアルタイム監視"""
        try:
            for reading in readings:
                # 閾値チェック
                thresholds = self.thresholds.get(reading.sensor_type)
                if not thresholds:
                    continue
                
                alert_level = None
                
                if reading.value >= thresholds.get('critical', float('inf')):
                    alert_level = AlertLevel.CRITICAL
                elif reading.value >= thresholds.get('warning', float('inf')):
                    alert_level = AlertLevel.WARNING
                
                if alert_level:
                    alert = Alert(
                        alert_id=f"{reading.device_id}_{reading.sensor_type}_{int(time.time())}",
                        device_id=reading.device_id,
                        alert_type=f"{reading.sensor_type}_threshold",
                        level=alert_level,
                        message=f"{reading.sensor_type} value {reading.value}{reading.unit} exceeds {alert_level.value} threshold",
                        timestamp=reading.timestamp,
                        value=reading.value,
                        threshold=thresholds.get(alert_level.value.lower())
                    )
                    
                    await self.send_alert(alert)
                
                # Redis に最新値キャッシュ
                cache_key = f"latest:{reading.device_id}:{reading.sensor_type}"
                cache_data = {
                    'value': reading.value,
                    'timestamp': reading.timestamp.isoformat(),
                    'unit': reading.unit
                }
                self.redis_client.hset(cache_key, mapping=cache_data)
                self.redis_client.expire(cache_key, 3600)  # 1時間TTL
                
        except Exception as e:
            logger.error(f"Real-time monitoring error: {e}")
    
    async def detect_anomalies(self, readings: List[SensorReading]):
        """異常検知"""
        try:
            for reading in readings:
                model_key = f"{reading.sensor_type}_{reading.location}"
                
                if model_key not in self.anomaly_models:
                    continue
                
                model = self.anomaly_models[model_key]
                scaler = self.scalers.get(model_key)
                
                if model and scaler:
                    # 特徴量準備（現在値 + 過去N個の値）
                    features = await self.prepare_features_for_anomaly_detection(reading)
                    
                    if features is not None:
                        # 標準化
                        features_scaled = scaler.transform([features])
                        
                        # 異常スコア計算
                        anomaly_score = model.decision_function(features_scaled)[0]
                        is_anomaly = model.predict(features_scaled)[0] == -1
                        
                        if is_anomaly:
                            alert = Alert(
                                alert_id=f"anomaly_{reading.device_id}_{reading.sensor_type}_{int(time.time())}",
                                device_id=reading.device_id,
                                alert_type="anomaly_detection",
                                level=AlertLevel.WARNING,
                                message=f"Anomaly detected in {reading.sensor_type}: score {anomaly_score:.3f}",
                                timestamp=reading.timestamp,
                                value=reading.value
                            )
                            
                            await self.send_alert(alert)
                            self.stats['anomalies_detected'] += 1
                            
                            logger.warning(f"Anomaly detected: {alert.message}")
        
        except Exception as e:
            logger.error(f"Anomaly detection error: {e}")
    
    async def prepare_features_for_anomaly_detection(self, reading: SensorReading) -> Optional[List[float]]:
        """異常検知用特徴量準備"""
        try:
            # 過去10個の値を取得（時系列特徴として使用）
            cache_pattern = f"history:{reading.device_id}:{reading.sensor_type}:*"
            history_keys = self.redis_client.keys(cache_pattern)
            
            if len(history_keys) < 5:  # 最小必要数
                return None
            
            # 履歴値取得・ソート
            history_values = []
            for key in sorted(history_keys):
                value = self.redis_client.get(key)
                if value:
                    history_values.append(float(value))
            
            # 統計的特徴量計算
            if len(history_values) >= 5:
                features = [
                    reading.value,  # 現在値
                    np.mean(history_values),  # 平均
                    np.std(history_values),   # 標準偏差
                    np.min(history_values),   # 最小値
                    np.max(history_values),   # 最大値
                ]
                
                # 現在値を履歴に追加
                history_key = f"history:{reading.device_id}:{reading.sensor_type}:{int(time.time())}"
                self.redis_client.setex(history_key, 3600, reading.value)  # 1時間保持
                
                return features
            
        except Exception as e:
            logger.error(f"Feature preparation error: {e}")
        
        return None
    
    def load_anomaly_models(self):
        """異常検知モデル読み込み"""
        try:
            model_dir = "/app/models"
            if not os.path.exists(model_dir):
                logger.warning("Model directory not found, creating sample models")
                self.create_sample_models()
                return
            
            for filename in os.listdir(model_dir):
                if filename.endswith('_model.pkl'):
                    model_key = filename.replace('_model.pkl', '')
                    
                    with open(os.path.join(model_dir, filename), 'rb') as f:
                        self.anomaly_models[model_key] = pickle.load(f)
                    
                    scaler_filename = f"{model_key}_scaler.pkl"
                    scaler_path = os.path.join(model_dir, scaler_filename)
                    
                    if os.path.exists(scaler_path):
                        with open(scaler_path, 'rb') as f:
                            self.scalers[model_key] = pickle.load(f)
            
            logger.info(f"Loaded {len(self.anomaly_models)} anomaly detection models")
            
        except Exception as e:
            logger.error(f"Model loading error: {e}")
    
    def create_sample_models(self):
        """サンプル異常検知モデル作成"""
        try:
            os.makedirs("/app/models", exist_ok=True)
            
            # サンプルデータ生成
            for sensor_type in ['temperature', 'vibration', 'pressure']:
                for location in ['area_1', 'area_2', 'area_3']:
                    # 正常データ生成
                    np.random.seed(42)
                    normal_data = np.random.normal(50, 10, (1000, 5))  # 5特徴量
                    
                    # 異常検知モデル学習
                    model = IsolationForest(contamination=0.1, random_state=42)
                    model.fit(normal_data)
                    
                    # スケーラー学習
                    scaler = StandardScaler()
                    scaler.fit(normal_data)
                    
                    # モデル保存
                    model_key = f"{sensor_type}_{location}"
                    
                    with open(f"/app/models/{model_key}_model.pkl", 'wb') as f:
                        pickle.dump(model, f)
                    
                    with open(f"/app/models/{model_key}_scaler.pkl", 'wb') as f:
                        pickle.dump(scaler, f)
                    
                    self.anomaly_models[model_key] = model
                    self.scalers[model_key] = scaler
            
            logger.info("Sample anomaly detection models created")
            
        except Exception as e:
            logger.error(f"Sample model creation error: {e}")
    
    async def send_alert(self, alert: Alert):
        """アラート送信"""
        try:
            # MQTTでアラート送信
            alert_data = asdict(alert)
            alert_data['timestamp'] = alert.timestamp.isoformat()
            alert_data['level'] = alert.level.value
            
            topic = f"factory/alerts/{alert.device_id}/{alert.alert_type}"
            self.mqtt_client.publish(topic, json.dumps(alert_data), qos=1)
            
            # Redis にアラート履歴保存
            alert_key = f"alert:{alert.alert_id}"
            self.redis_client.hset(alert_key, mapping=alert_data)
            self.redis_client.expire(alert_key, 86400 * 7)  # 7日保持
            
            # アラート統計更新
            self.stats['alerts_generated'] += 1
            
            logger.info(f"Alert sent: {alert.message}")
            
        except Exception as e:
            logger.error(f"Alert sending error: {e}")
    
    async def process_alert(self, topic: str, data: Dict[str, Any]):
        """外部アラート処理"""
        try:
            # 既存アラートの処理・集約
            logger.info(f"Processing external alert from {topic}")
            
        except Exception as e:
            logger.error(f"Alert processing error: {e}")
    
    async def run_periodic_tasks(self):
        """定期実行タスク"""
        while self.running:
            try:
                # 統計情報更新
                self.stats['last_processing_time'] = datetime.now().isoformat()
                
                # Redis に統計情報保存
                self.redis_client.hset("system:stats", mapping=self.stats)
                
                # バッファ状況確認
                with self.buffer_lock:
                    buffer_size = len(self.sensor_buffer)
                
                logger.info(f"Stats: {self.stats}, Buffer: {buffer_size}")
                
                # 60秒待機
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Periodic task error: {e}")
                await asyncio.sleep(60)
    
    async def run(self):
        """メインループ"""
        self.running = True
        
        # 初期化
        if not await self.initialize():
            logger.error("Initialization failed, exiting...")
            return
        
        logger.info("Factory Data Processor started")
        
        # 定期タスク開始
        periodic_task = asyncio.create_task(self.run_periodic_tasks())
        
        try:
            # メインループ
            while self.running:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            self.running = False
            periodic_task.cancel()
            await self.cleanup()
    
    async def cleanup(self):
        """リソースクリーンアップ"""
        try:
            if self.mqtt_client:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
            
            if self.influxdb_client:
                self.influxdb_client.close()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Cleanup error: {e}")

def main():
    """メイン関数"""
    processor = FactoryDataProcessor()
    
    # シグナルハンドラー
    def signal_handler(signum, frame):
        logger.info("Shutdown signal received")
        processor.running = False
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # イベントループ実行
    try:
        asyncio.run(processor.run())
    except KeyboardInterrupt:
        logger.info("Process interrupted")
    except Exception as e:
        logger.error(f"Process error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Step 3: 監視ダッシュボード設定

#### 3.1 Grafana ダッシュボード

`grafana/dashboards/factory_overview.json`:

```json
{
  "dashboard": {
    "id": null,
    "title": "Smart Factory Overview",
    "tags": ["factory", "iot", "monitoring"],
    "timezone": "browser",
    "refresh": "5s",
    "time": {
      "from": "now-1h",
      "to": "now"
    },
    "panels": [
      {
        "id": 1,
        "title": "Factory Layout",
        "type": "piechart",
        "targets": [
          {
            "expr": "from(bucket: \"factory_sensors\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> group(columns: [\"location\"]) |> count()",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 0},
        "options": {
          "legend": {"displayMode": "table", "placement": "right"}
        }
      },
      {
        "id": 2,
        "title": "Temperature Distribution",
        "type": "heatmap",
        "targets": [
          {
            "expr": "from(bucket: \"factory_sensors\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"temperature\")",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 0}
      },
      {
        "id": 3,
        "title": "Vibration Levels",
        "type": "graph",
        "targets": [
          {
            "expr": "from(bucket: \"factory_sensors\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"vibration\") |> group(columns: [\"device_id\"]) |> mean()",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 24, "x": 0, "y": 8},
        "yAxes": [
          {
            "label": "Vibration (g)",
            "max": 10,
            "min": 0
          }
        ],
        "thresholds": [
          {"value": 5, "colorMode": "critical", "op": "gt"},
          {"value": 3, "colorMode": "warning", "op": "gt"}
        ]
      },
      {
        "id": 4,
        "title": "Current Alerts",
        "type": "table",
        "targets": [
          {
            "expr": "from(bucket: \"factory_sensors\") |> range(start: -24h) |> filter(fn: (r) => r._measurement == \"alerts\")",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 16},
        "styles": [
          {
            "alias": "Level",
            "colorMode": "cell",
            "colors": ["green", "yellow", "red"],
            "thresholds": ["0", "1"]
          }
        ]
      },
      {
        "id": 5,
        "title": "Device Status",
        "type": "stat",
        "targets": [
          {
            "expr": "from(bucket: \"factory_sensors\") |> range(start: -5m) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> group(columns: [\"device_id\"]) |> count()",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 16},
        "options": {
          "colorMode": "background",
          "graphMode": "area",
          "justifyMode": "auto",
          "orientation": "horizontal"
        },
        "fieldConfig": {
          "defaults": {
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 5},
                {"color": "green", "value": 10}
              ]
            }
          }
        }
      },
      {
        "id": 6,
        "title": "Production Line Efficiency",
        "type": "gauge",
        "targets": [
          {
            "expr": "from(bucket: \"factory_sensors\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"production_data\" and r.metric == \"efficiency\")",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 0, "y": 24},
        "fieldConfig": {
          "defaults": {
            "min": 0,
            "max": 100,
            "unit": "percent",
            "thresholds": {
              "steps": [
                {"color": "red", "value": 0},
                {"color": "yellow", "value": 70},
                {"color": "green", "value": 85}
              ]
            }
          }
        }
      },
      {
        "id": 7,
        "title": "Energy Consumption",
        "type": "graph",
        "targets": [
          {
            "expr": "from(bucket: \"factory_sensors\") |> range(start: -1h) |> filter(fn: (r) => r._measurement == \"sensor_data\" and r.sensor_type == \"current\") |> aggregateWindow(every: 5m, fn: mean)",
            "refId": "A"
          }
        ],
        "gridPos": {"h": 8, "w": 12, "x": 12, "y": 24},
        "yAxes": [
          {
            "label": "Current (A)",
            "min": 0
          }
        ]
      }
    ],
    "templating": {
      "list": [
        {
          "name": "location",
          "type": "query",
          "query": "from(bucket: \"factory_sensors\") |> range(start: -24h) |> filter(fn: (r) => r._measurement == \"sensor_data\") |> distinct(column: \"location\")",
          "refresh": 1,
          "includeAll": true
        }
      ]
    },
    "annotations": {
      "list": [
        {
          "name": "Alerts",
          "datasource": "InfluxDB",
          "enable": true,
          "iconColor": "red",
          "query": "from(bucket: \"factory_sensors\") |> range(start: $__timeFrom, stop: $__timeTo) |> filter(fn: (r) => r._measurement == \"alerts\")"
        }
      ]
    }
  }
}
```

### Step 4: アラート管理システム

#### 4.1 アラート管理サービス

`alert_manager/main.py`:

```python
#!/usr/bin/env python3
import asyncio
import json
import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, List, Set
import paho.mqtt.client as mqtt
import redis
from dataclasses import dataclass
from enum import Enum
import os
import requests

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    SMS = "sms"
    WEBHOOK = "webhook"

@dataclass
class NotificationRule:
    alert_type: str
    severity_levels: List[str]
    channels: List[NotificationChannel]
    escalation_time_minutes: int
    recipients: List[str]
    enabled: bool = True

class AlertManager:
    """工場アラート管理システム"""
    
    def __init__(self):
        # 環境変数設定
        self.mqtt_broker = os.getenv('MQTT_BROKER', 'localhost')
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
        self.smtp_server = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_username = os.getenv('SMTP_USERNAME', '')
        self.smtp_password = os.getenv('SMTP_PASSWORD', '')
        self.slack_webhook = os.getenv('SLACK_WEBHOOK_URL', '')
        
        # クライアント
        self.mqtt_client = mqtt.Client("alert_manager")
        self.redis_client = redis.from_url(self.redis_url, decode_responses=True)
        
        # アラート管理
        self.active_alerts = {}  # alert_id -> alert_data
        self.escalated_alerts = set()
        self.notification_rules = self.load_notification_rules()
        
        # 通知抑制（同じアラートの重複送信防止）
        self.notification_cooldown = {}  # alert_key -> last_sent_time
        self.cooldown_minutes = 15
        
        logger.info("Alert Manager initialized")
    
    def load_notification_rules(self) -> List[NotificationRule]:
        """通知ルール読み込み"""
        return [
            NotificationRule(
                alert_type="temperature_threshold",
                severity_levels=["critical", "emergency"],
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                escalation_time_minutes=10,
                recipients=["maintenance@factory.com", "supervisor@factory.com"]
            ),
            NotificationRule(
                alert_type="vibration_threshold",
                severity_levels=["critical", "emergency"],
                channels=[NotificationChannel.EMAIL, NotificationChannel.SMS],
                escalation_time_minutes=5,
                recipients=["maintenance@factory.com"]
            ),
            NotificationRule(
                alert_type="anomaly_detection",
                severity_levels=["warning", "critical"],
                channels=[NotificationChannel.SLACK],
                escalation_time_minutes=30,
                recipients=["analytics@factory.com"]
            ),
            NotificationRule(
                alert_type="device_offline",
                severity_levels=["warning", "critical"],
                channels=[NotificationChannel.EMAIL],
                escalation_time_minutes=20,
                recipients=["it@factory.com"]
            )
        ]
    
    async def initialize(self):
        """初期化"""
        try:
            # MQTT接続
            self.mqtt_client.on_connect = self.on_connect
            self.mqtt_client.on_message = self.on_message
            self.mqtt_client.connect(self.mqtt_broker, 1883, 60)
            self.mqtt_client.loop_start()
            
            logger.info("Alert Manager initialized successfully")
            return True
            
        except Exception as e:
            logger.error(f"Initialization failed: {e}")
            return False
    
    def on_connect(self, client, userdata, flags, rc):
        """MQTT接続時処理"""
        if rc == 0:
            logger.info("Connected to MQTT broker")
            
            # アラートトピック購読
            client.subscribe("factory/alerts/+/+", qos=1)
            client.subscribe("alerts/+/+/+", qos=1)
            
        else:
            logger.error(f"MQTT connection failed: {rc}")
    
    def on_message(self, client, userdata, msg):
        """MQTTメッセージ処理"""
        try:
            topic = msg.topic
            alert_data = json.loads(msg.payload.decode())
            
            asyncio.create_task(self.process_alert(alert_data))
            
        except Exception as e:
            logger.error(f"Message processing error: {e}")
    
    async def process_alert(self, alert_data: Dict):
        """アラート処理"""
        try:
            alert_id = alert_data.get('alert_id')
            alert_type = alert_data.get('alert_type')
            level = alert_data.get('level', 'info')
            device_id = alert_data.get('device_id')
            
            if not alert_id or not alert_type:
                logger.warning(f"Invalid alert data: {alert_data}")
                return
            
            # アラート記録
            alert_data['received_timestamp'] = datetime.now().isoformat()
            self.active_alerts[alert_id] = alert_data
            
            # Redis に保存
            self.redis_client.hset(f"alert:{alert_id}", mapping=alert_data)
            self.redis_client.expire(f"alert:{alert_id}", 86400 * 30)  # 30日保持
            
            # 通知ルール適用
            await self.apply_notification_rules(alert_data)
            
            # エスカレーション スケジューリング
            await self.schedule_escalation(alert_data)
            
            logger.info(f"Processed alert: {alert_id} ({alert_type}, {level})")
            
        except Exception as e:
            logger.error(f"Alert processing error: {e}")
    
    async def apply_notification_rules(self, alert_data: Dict):
        """通知ルール適用"""
        try:
            alert_type = alert_data.get('alert_type')
            level = alert_data.get('level')
            
            # 適用可能なルール検索
            applicable_rules = [
                rule for rule in self.notification_rules
                if rule.enabled and 
                (rule.alert_type == alert_type or rule.alert_type == "all") and
                level in rule.severity_levels
            ]
            
            for rule in applicable_rules:
                # 通知クールダウンチェック
                cooldown_key = f"{alert_type}_{alert_data.get('device_id')}_{level}"
                
                if self.is_notification_in_cooldown(cooldown_key):
                    logger.debug(f"Notification in cooldown: {cooldown_key}")
                    continue
                
                # 通知送信
                await self.send_notifications(alert_data, rule)
                
                # クールダウン設定
                self.notification_cooldown[cooldown_key] = datetime.now()
                
        except Exception as e:
            logger.error(f"Notification rule application error: {e}")
    
    def is_notification_in_cooldown(self, cooldown_key: str) -> bool:
        """通知クールダウンチェック"""
        last_sent = self.notification_cooldown.get(cooldown_key)
        if not last_sent:
            return False
        
        time_diff = datetime.now() - last_sent
        return time_diff.total_seconds() < (self.cooldown_minutes * 60)
    
    async def send_notifications(self, alert_data: Dict, rule: NotificationRule):
        """通知送信"""
        try:
            for channel in rule.channels:
                for recipient in rule.recipients:
                    if channel == NotificationChannel.EMAIL:
                        await self.send_email_notification(alert_data, recipient)
                    elif channel == NotificationChannel.SLACK:
                        await self.send_slack_notification(alert_data)
                    elif channel == NotificationChannel.WEBHOOK:
                        await self.send_webhook_notification(alert_data, recipient)
                    
        except Exception as e:
            logger.error(f"Notification sending error: {e}")
    
    async def send_email_notification(self, alert_data: Dict, recipient: str):
        """メール通知送信"""
        try:
            if not self.smtp_username or not self.smtp_password:
                logger.warning("SMTP credentials not configured")
                return
            
            # メール内容作成
            subject = f"Factory Alert: {alert_data.get('alert_type')} - {alert_data.get('level').upper()}"
            
            body = f"""
            Factory Alert Notification
            ==========================
            
            Alert ID: {alert_data.get('alert_id')}
            Device ID: {alert_data.get('device_id')}
            Alert Type: {alert_data.get('alert_type')}
            Severity: {alert_data.get('level')}
            Message: {alert_data.get('message')}
            Timestamp: {alert_data.get('timestamp')}
            
            {"Value: " + str(alert_data.get('value')) if alert_data.get('value') else ""}
            {"Threshold: " + str(alert_data.get('threshold')) if alert_data.get('threshold') else ""}
            
            Please take appropriate action immediately.
            
            Factory Monitoring System
            """
            
            # メール作成
            msg = MIMEMultipart()
            msg['From'] = self.smtp_username
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))
            
            # SMTP送信
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.starttls()
            server.login(self.smtp_username, self.smtp_password)
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Email sent to {recipient}")
            
        except Exception as e:
            logger.error(f"Email sending error: {e}")
    
    async def send_slack_notification(self, alert_data: Dict):
        """Slack通知送信"""
        try:
            if not self.slack_webhook:
                logger.warning("Slack webhook not configured")
                return
            
            # Slack メッセージ作成
            color = {
                'info': '#36a64f',
                'warning': '#ff9900',
                'critical': '#ff0000',
                'emergency': '#990000'
            }.get(alert_data.get('level'), '#36a64f')
            
            message = {
                "attachments": [
                    {
                        "color": color,
                        "title": f"Factory Alert: {alert_data.get('alert_type')}",
                        "title_link": "http://grafana.factory.local:3000",
                        "fields": [
                            {
                                "title": "Device ID",
                                "value": alert_data.get('device_id'),
                                "short": True
                            },
                            {
                                "title": "Severity",
                                "value": alert_data.get('level').upper(),
                                "short": True
                            },
                            {
                                "title": "Message",
                                "value": alert_data.get('message'),
                                "short": False
                            },
                            {
                                "title": "Timestamp",
                                "value": alert_data.get('timestamp'),
                                "short": True
                            }
                        ],
                        "footer": "Factory Monitoring System",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }
            
            # Webhook送信
            response = requests.post(self.slack_webhook, json=message, timeout=10)
            
            if response.status_code == 200:
                logger.info("Slack notification sent")
            else:
                logger.error(f"Slack notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Slack notification error: {e}")
    
    async def send_webhook_notification(self, alert_data: Dict, webhook_url: str):
        """Webhook通知送信"""
        try:
            payload = {
                "alert": alert_data,
                "timestamp": datetime.now().isoformat(),
                "source": "factory_alert_manager"
            }
            
            response = requests.post(webhook_url, json=payload, timeout=10)
            
            if response.status_code == 200:
                logger.info(f"Webhook notification sent to {webhook_url}")
            else:
                logger.error(f"Webhook notification failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Webhook notification error: {e}")
    
    async def schedule_escalation(self, alert_data: Dict):
        """エスカレーション スケジューリング"""
        try:
            alert_id = alert_data.get('alert_id')
            alert_type = alert_data.get('alert_type')
            
            # エスカレーションルール検索
            escalation_rules = [
                rule for rule in self.notification_rules
                if rule.alert_type == alert_type and rule.escalation_time_minutes > 0
            ]
            
            for rule in escalation_rules:
                # エスカレーション タイマー設定
                delay_seconds = rule.escalation_time_minutes * 60
                
                asyncio.create_task(
                    self.escalate_alert_after_delay(alert_id, delay_seconds)
                )
                
        except Exception as e:
            logger.error(f"Escalation scheduling error: {e}")
    
    async def escalate_alert_after_delay(self, alert_id: str, delay_seconds: int):
        """遅延エスカレーション"""
        try:
            await asyncio.sleep(delay_seconds)
            
            # アラートがまだ未解決かチェック
            if alert_id in self.active_alerts and alert_id not in self.escalated_alerts:
                alert_data = self.active_alerts[alert_id]
                
                # エスカレーション通知
                escalated_data = alert_data.copy()
                escalated_data['escalated'] = True
                escalated_data['escalation_timestamp'] = datetime.now().isoformat()
                
                # 管理者に通知
                await self.send_escalation_notification(escalated_data)
                
                self.escalated_alerts.add(alert_id)
                
                logger.warning(f"Alert escalated: {alert_id}")
                
        except Exception as e:
            logger.error(f"Alert escalation error: {e}")
    
    async def send_escalation_notification(self, alert_data: Dict):
        """エスカレーション通知送信"""
        try:
            # 高優先度通知として管理者に送信
            escalation_rule = NotificationRule(
                alert_type="escalation",
                severity_levels=["critical"],
                channels=[NotificationChannel.EMAIL, NotificationChannel.SLACK],
                escalation_time_minutes=0,
                recipients=["manager@factory.com", "supervisor@factory.com"]
            )
            
            await self.send_notifications(alert_data, escalation_rule)
            
        except Exception as e:
            logger.error(f"Escalation notification error: {e}")
    
    async def run_maintenance_tasks(self):
        """メンテナンスタスク"""
        while True:
            try:
                # 古いアラートクリーンアップ
                current_time = datetime.now()
                expired_alerts = []
                
                for alert_id, alert_data in self.active_alerts.items():
                    alert_time = datetime.fromisoformat(alert_data.get('timestamp', ''))
                    if (current_time - alert_time).total_seconds() > 86400:  # 24時間
                        expired_alerts.append(alert_id)
                
                for alert_id in expired_alerts:
                    del self.active_alerts[alert_id]
                    self.escalated_alerts.discard(alert_id)
                
                # 通知クールダウンクリーンアップ
                expired_cooldowns = []
                for key, last_sent in self.notification_cooldown.items():
                    if (current_time - last_sent).total_seconds() > (self.cooldown_minutes * 60):
                        expired_cooldowns.append(key)
                
                for key in expired_cooldowns:
                    del self.notification_cooldown[key]
                
                logger.info(f"Maintenance: Cleaned {len(expired_alerts)} alerts, {len(expired_cooldowns)} cooldowns")
                
                # 1時間待機
                await asyncio.sleep(3600)
                
            except Exception as e:
                logger.error(f"Maintenance task error: {e}")
                await asyncio.sleep(3600)
    
    async def run(self):
        """メインループ"""
        if not await self.initialize():
            logger.error("Initialization failed")
            return
        
        logger.info("Alert Manager started")
        
        # メンテナンスタスク開始
        maintenance_task = asyncio.create_task(self.run_maintenance_tasks())
        
        try:
            while True:
                await asyncio.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Shutdown requested")
        finally:
            maintenance_task.cancel()
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()

def main():
    alert_manager = AlertManager()
    asyncio.run(alert_manager.run())

if __name__ == "__main__":
    main()
```

## 課題

### 基礎課題

1. **システム構築**
   - Docker環境での全サービス起動
   - MQTT通信確認

2. **データ収集**
   - 複数デバイスからのデータ収集
   - InfluxDBへの書き込み確認

3. **監視ダッシュボード**
   - Grafanaダッシュボード設定
   - リアルタイム表示

### 応用課題

1. **アラートシステム**
   - 複数チャネル通知実装
   - エスカレーション機能

2. **予知保全**
   - 異常検知アルゴリズム実装
   - 機械学習モデル統合

3. **スケーラビリティ**
   - 負荷分散実装
   - 高可用性設計

## 運用・保守

### システム監視
```bash
# サービス状態確認
docker-compose ps

# ログ確認
docker-compose logs -f data_processor

# メトリクス確認
curl http://localhost:8086/health  # InfluxDB
curl http://localhost:3000/api/health  # Grafana
```

### バックアップ
```bash
# InfluxDB バックアップ
docker exec factory_influxdb influx backup /backup

# Grafana設定バックアップ
docker exec factory_grafana grafana-cli admin export-dashboard
```

## 次のステップ

この産業用途事例を基に、実際の工場・製造業での IoT システム導入を進めることができます。セキュリティ強化、クラウド連携、AIによる高度な予知保全などの発展的な機能追加も可能です。

---

この演習により、実際の産業現場で使用される包括的な IoT システムの設計・実装・運用を体験できます。