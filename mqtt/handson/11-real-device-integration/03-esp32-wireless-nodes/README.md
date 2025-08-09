# 演習3: ESP32無線センサーノード

## 概要

ESP32マイクロコントローラーを使用して、WiFi対応の無線センサーノードを構築します。低消費電力設計、複数センサー統合、MQTT通信によるデータ送信を学びます。ESP32の豊富なGPIOとWiFi機能を活用した実用的なIoTノードを作成します。

## 学習目標

- ESP32でのWiFi接続とMQTT通信
- 複数センサーの同時制御
- 深度スリープによる省電力実装
- OTA（Over-The-Air）ファームウェア更新
- バッテリー駆動最適化

## 必要機材

### ハードウェア
- ESP32 DevKitC または ESP32-WROOM-32
- 各種センサー（DHT22、BME280、土壌湿度など）
- LED × 数個
- 抵抗 220Ω × 数個
- ブレッドボード
- ジャンパーワイヤー
- リチウムイオンバッテリー（3.7V、オプション）

### 開発環境
- Arduino IDE 2.0+ または PlatformIO
- ESP32ボードサポートパッケージ

## 演習手順

### Step 1: ESP32開発環境セットアップ

#### 1.1 Arduino IDE設定

```arduino
// Arduino IDE Board Manager URL
https://dl.espressif.com/dl/package_esp32_index.json

// 必要ライブラリ
- WiFi (ESP32内蔵)
- PubSubClient (MQTT)
- ArduinoJson
- DHT sensor library
- Adafruit BME280
- ESP32 Deep Sleep
```

#### 1.2 基本接続テスト

`examples/01_wifi_mqtt_basic/wifi_mqtt_basic.ino`:

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <esp_sleep.h>

// WiFi設定
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";

// MQTT設定
const char* mqtt_server = "192.168.1.100";  // ブローカーIP
const int mqtt_port = 1883;
const char* device_id = "esp32_node_001";

// クライアント
WiFiClient espClient;
PubSubClient client(espClient);

// タイミング制御
unsigned long lastMsg = 0;
const long interval = 30000;  // 30秒間隔

// デバイス情報
struct DeviceInfo {
  String deviceId;
  String firmwareVersion;
  String ipAddress;
  float batteryVoltage;
  int signalStrength;
} deviceInfo;

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 MQTT Sensor Node Starting...");
  
  // デバイス情報初期化
  deviceInfo.deviceId = device_id;
  deviceInfo.firmwareVersion = "1.0.0";
  
  // WiFi接続
  setupWiFi();
  
  // MQTT設定
  client.setServer(mqtt_server, mqtt_port);
  client.setCallback(callback);
  
  // LED設定
  pinMode(LED_BUILTIN, OUTPUT);
  
  Serial.println("Setup completed");
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  unsigned long now = millis();
  if (now - lastMsg > interval) {
    lastMsg = now;
    
    // センサーデータ送信
    publishSensorData();
    
    // システム状態送信
    publishSystemStatus();
    
    // バッテリー電圧チェック
    checkBatteryLevel();
  }
  
  delay(100);
}

void setupWiFi() {
  delay(10);
  Serial.println();
  Serial.print("Connecting to ");
  Serial.println(ssid);
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("WiFi connected");
    Serial.println("IP address: ");
    Serial.println(WiFi.localIP());
    
    deviceInfo.ipAddress = WiFi.localIP().toString();
    deviceInfo.signalStrength = WiFi.RSSI();
  } else {
    Serial.println("WiFi connection failed");
    // Deep sleep on connection failure
    enterDeepSleep(60);  // 1分後に再起動
  }
}

void callback(char* topic, byte* message, unsigned int length) {
  Serial.print("Message arrived on topic: ");
  Serial.println(topic);
  
  String messageTemp;
  for (int i = 0; i < length; i++) {
    messageTemp += (char)message[i];
  }
  
  Serial.print("Message: ");
  Serial.println(messageTemp);
  
  // コマンド処理
  String topicStr = String(topic);
  if (topicStr.endsWith("/command")) {
    processCommand(messageTemp);
  }
}

void processCommand(String command) {
  DynamicJsonDocument doc(1024);
  deserializeJson(doc, command);
  
  String cmdType = doc["type"];
  
  if (cmdType == "led") {
    String state = doc["state"];
    if (state == "on") {
      digitalWrite(LED_BUILTIN, HIGH);
      publishResponse("LED turned ON");
    } else if (state == "off") {
      digitalWrite(LED_BUILTIN, LOW);
      publishResponse("LED turned OFF");
    }
  } else if (cmdType == "sleep") {
    int duration = doc["duration"] | 60;  // デフォルト60秒
    publishResponse("Entering deep sleep for " + String(duration) + " seconds");
    delay(1000);
    enterDeepSleep(duration);
  } else if (cmdType == "restart") {
    publishResponse("Restarting device...");
    delay(1000);
    ESP.restart();
  } else if (cmdType == "status") {
    publishSystemStatus();
  }
}

void publishResponse(String message) {
  DynamicJsonDocument doc(1024);
  doc["timestamp"] = millis();
  doc["device_id"] = device_id;
  doc["message"] = message;
  
  String response;
  serializeJson(doc, response);
  
  String topic = "esp32/" + String(device_id) + "/response";
  client.publish(topic.c_str(), response.c_str());
}

void publishSensorData() {
  DynamicJsonDocument doc(2048);
  
  // タイムスタンプ
  doc["timestamp"] = millis();
  doc["device_id"] = device_id;
  
  // システム情報
  doc["system"]["uptime_ms"] = millis();
  doc["system"]["free_heap"] = ESP.getFreeHeap();
  doc["system"]["wifi_rssi"] = WiFi.RSSI();
  
  // 簡易センサーデータ（内蔵温度センサー）
  doc["sensors"]["internal_temp_c"] = temperatureRead();
  doc["sensors"]["hall_sensor"] = hallRead();
  
  // バッテリー電圧（ADC使用）
  float batteryVoltage = getBatteryVoltage();
  doc["sensors"]["battery_voltage"] = batteryVoltage;
  deviceInfo.batteryVoltage = batteryVoltage;
  
  String payload;
  serializeJson(doc, payload);
  
  String topic = "sensors/esp32/" + String(device_id) + "/data";
  bool result = client.publish(topic.c_str(), payload.c_str());
  
  Serial.println("Sensor data published: " + String(result ? "SUCCESS" : "FAILED"));
}

void publishSystemStatus() {
  DynamicJsonDocument doc(2048);
  
  doc["timestamp"] = millis();
  doc["device_id"] = deviceInfo.deviceId;
  doc["status"] = "online";
  doc["firmware_version"] = deviceInfo.firmwareVersion;
  doc["ip_address"] = deviceInfo.ipAddress;
  doc["uptime_ms"] = millis();
  doc["free_heap_bytes"] = ESP.getFreeHeap();
  doc["wifi_rssi_dbm"] = deviceInfo.signalStrength;
  doc["battery_voltage"] = deviceInfo.batteryVoltage;
  doc["cpu_freq_mhz"] = getCpuFrequencyMhz();
  
  String payload;
  serializeJson(doc, payload);
  
  String topic = "esp32/" + String(device_id) + "/status";
  client.publish(topic.c_str(), payload.c_str(), true); // retain=true
}

float getBatteryVoltage() {
  // ADC読み取り（GPIO34-39使用推奨）
  int adcValue = analogRead(A0);
  
  // ESP32のADCは0-4095、参照電圧は通常3.3V
  // 電圧分圧回路を使用している場合は適切にスケーリング
  float voltage = (adcValue / 4095.0) * 3.3 * 2.0; // 2倍は分圧回路の補正
  
  return voltage;
}

void checkBatteryLevel() {
  float voltage = deviceInfo.batteryVoltage;
  
  // 低電圧アラート（3.4V以下）
  if (voltage < 3.4 && voltage > 2.0) {  // 2.0V以下は無効な読み取り
    DynamicJsonDocument doc(1024);
    doc["timestamp"] = millis();
    doc["device_id"] = device_id;
    doc["alert_type"] = "low_battery";
    doc["battery_voltage"] = voltage;
    doc["message"] = "Battery voltage is low, consider charging";
    
    String payload;
    serializeJson(doc, payload);
    
    String topic = "alerts/esp32/" + String(device_id) + "/battery";
    client.publish(topic.c_str(), payload.c_str());
    
    // 低電圧時は深度スリープ間隔を長くして電力を節約
    if (voltage < 3.2) {
      Serial.println("Critical battery level, entering extended sleep");
      publishResponse("Critical battery - entering extended sleep mode");
      delay(1000);
      enterDeepSleep(300);  // 5分スリープ
    }
  }
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Attempting MQTT connection...");
    
    // Will message設定
    String willTopic = "esp32/" + String(device_id) + "/status";
    String willMessage = "{\"device_id\":\"" + String(device_id) + 
                        "\",\"status\":\"offline\",\"timestamp\":" + String(millis()) + "}";
    
    if (client.connect(device_id, willTopic.c_str(), 1, true, willMessage.c_str())) {
      Serial.println("connected");
      
      // コマンドトピック購読
      String commandTopic = "esp32/" + String(device_id) + "/command";
      client.subscribe(commandTopic.c_str());
      
      // オンライン状態送信
      publishSystemStatus();
      
    } else {
      Serial.print("failed, rc=");
      Serial.print(client.state());
      Serial.println(" try again in 5 seconds");
      delay(5000);
    }
  }
}

void enterDeepSleep(int seconds) {
  Serial.println("Entering deep sleep for " + String(seconds) + " seconds");
  
  // Wake up timer設定
  esp_sleep_enable_timer_wakeup(seconds * 1000000ULL);  // マイクロ秒単位
  
  // GPIO wake up設定（オプション）
  // esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);
  
  // Deep Sleep開始
  esp_deep_sleep_start();
}
```

### Step 2: 多センサー統合ノード

#### 2.1 環境監視ノード

`examples/02_multi_sensor_node/multi_sensor_node.ino`:

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <Adafruit_BME280.h>
#include <OneWire.h>
#include <DallasTemperature.h>

// センサーピン定義
#define DHT_PIN 4
#define DHT_TYPE DHT22
#define ONE_WIRE_BUS 2
#define SOIL_MOISTURE_PIN A0
#define LIGHT_SENSOR_PIN A3
#define PIR_PIN 5
#define BUZZER_PIN 18
#define STATUS_LED_PIN 19

// センサーインスタンス
DHT dht(DHT_PIN, DHT_TYPE);
Adafruit_BME280 bme;
OneWire oneWire(ONE_WIRE_BUS);
DallasTemperature waterTemp(&oneWire);

// センサー状態管理
struct SensorStatus {
  bool dht22_ok = false;
  bool bme280_ok = false;
  bool ds18b20_ok = false;
  bool soil_ok = true;  // アナログセンサーは常にOK
  bool light_ok = true;
  bool pir_ok = true;
} sensorStatus;

// 測定値記録
struct SensorReadings {
  float air_temp_dht = NAN;
  float air_humidity_dht = NAN;
  float air_temp_bme = NAN;
  float air_humidity_bme = NAN;
  float air_pressure_bme = NAN;
  float water_temp = NAN;
  int soil_moisture_raw = 0;
  float soil_moisture_percent = 0;
  int light_level_raw = 0;
  float light_level_percent = 0;
  bool motion_detected = false;
  float heat_index = NAN;
} readings;

// WiFi・MQTT設定（前回同様）
const char* ssid = "YOUR_WIFI_SSID";
const char* password = "YOUR_WIFI_PASSWORD";
const char* mqtt_server = "192.168.1.100";
const char* device_id = "esp32_env_monitor_001";

WiFiClient espClient;
PubSubClient client(espClient);

// タイミング制御
unsigned long lastSensorRead = 0;
unsigned long lastMqttSend = 0;
const long sensorInterval = 5000;   // 5秒間隔で読み取り
const long mqttInterval = 30000;    // 30秒間隔で送信

// 移動平均フィルタ用
const int filterSamples = 5;
float tempFilter[filterSamples] = {0};
float humidityFilter[filterSamples] = {0};
int filterIndex = 0;

void setup() {
  Serial.begin(115200);
  Serial.println("Multi-Sensor ESP32 Node Starting...");
  
  // GPIO初期化
  pinMode(PIR_PIN, INPUT);
  pinMode(BUZZER_PIN, OUTPUT);
  pinMode(STATUS_LED_PIN, OUTPUT);
  
  // ステータスLED点灯
  digitalWrite(STATUS_LED_PIN, HIGH);
  
  // センサー初期化
  initializeSensors();
  
  // WiFi・MQTT接続
  setupWiFi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
  
  Serial.println("Multi-sensor setup completed");
  
  // 初期化完了音
  beep(2, 200);
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  unsigned long now = millis();
  
  // センサー読み取り
  if (now - lastSensorRead > sensorInterval) {
    lastSensorRead = now;
    readAllSensors();
    updateStatusLED();
  }
  
  // MQTT送信
  if (now - lastMqttSend > mqttInterval) {
    lastMqttSend = now;
    publishSensorData();
    checkAlerts();
  }
  
  // モーション検出処理
  handleMotionDetection();
  
  delay(100);
}

void initializeSensors() {
  Serial.println("Initializing sensors...");
  
  // DHT22初期化
  dht.begin();
  delay(2000);
  float testTemp = dht.readTemperature();
  sensorStatus.dht22_ok = !isnan(testTemp);
  Serial.println("DHT22: " + String(sensorStatus.dht22_ok ? "OK" : "FAILED"));
  
  // BME280初期化
  sensorStatus.bme280_ok = bme.begin(0x76);  // I2Cアドレス
  Serial.println("BME280: " + String(sensorStatus.bme280_ok ? "OK" : "FAILED"));
  
  // DS18B20初期化
  waterTemp.begin();
  int deviceCount = waterTemp.getDeviceCount();
  sensorStatus.ds18b20_ok = (deviceCount > 0);
  Serial.println("DS18B20: " + String(sensorStatus.ds18b20_ok ? "OK (" + String(deviceCount) + " devices)" : "FAILED"));
  
  Serial.println("Sensor initialization completed");
}

void readAllSensors() {
  // DHT22読み取り
  if (sensorStatus.dht22_ok) {
    float temp = dht.readTemperature();
    float humidity = dht.readHumidity();
    
    if (!isnan(temp) && !isnan(humidity)) {
      readings.air_temp_dht = temp;
      readings.air_humidity_dht = humidity;
      readings.heat_index = dht.computeHeatIndex(temp, humidity, false);
      
      // 移動平均フィルタ適用
      tempFilter[filterIndex] = temp;
      humidityFilter[filterIndex] = humidity;
      filterIndex = (filterIndex + 1) % filterSamples;
    }
  }
  
  // BME280読み取り
  if (sensorStatus.bme280_ok) {
    readings.air_temp_bme = bme.readTemperature();
    readings.air_humidity_bme = bme.readHumidity();
    readings.air_pressure_bme = bme.readPressure() / 100.0; // hPa変換
  }
  
  // DS18B20読み取り
  if (sensorStatus.ds18b20_ok) {
    waterTemp.requestTemperatures();
    readings.water_temp = waterTemp.getTempCByIndex(0);
  }
  
  // 土壌湿度読み取り
  readings.soil_moisture_raw = analogRead(SOIL_MOISTURE_PIN);
  readings.soil_moisture_percent = map(readings.soil_moisture_raw, 0, 4095, 0, 100);
  
  // 照度読み取り
  readings.light_level_raw = analogRead(LIGHT_SENSOR_PIN);
  readings.light_level_percent = map(readings.light_level_raw, 0, 4095, 0, 100);
  
  // モーション検出
  readings.motion_detected = digitalRead(PIR_PIN);
}

void publishSensorData() {
  DynamicJsonDocument doc(4096);
  
  // メタデータ
  doc["timestamp"] = millis();
  doc["device_id"] = device_id;
  doc["measurement_type"] = "environmental";
  
  // 環境センサー
  if (sensorStatus.dht22_ok) {
    doc["sensors"]["dht22"]["temperature_c"] = readings.air_temp_dht;
    doc["sensors"]["dht22"]["humidity_percent"] = readings.air_humidity_dht;
    doc["sensors"]["dht22"]["heat_index_c"] = readings.heat_index;
    doc["sensors"]["dht22"]["status"] = "ok";
  } else {
    doc["sensors"]["dht22"]["status"] = "error";
  }
  
  if (sensorStatus.bme280_ok) {
    doc["sensors"]["bme280"]["temperature_c"] = readings.air_temp_bme;
    doc["sensors"]["bme280"]["humidity_percent"] = readings.air_humidity_bme;
    doc["sensors"]["bme280"]["pressure_hpa"] = readings.air_pressure_bme;
    doc["sensors"]["bme280"]["status"] = "ok";
  } else {
    doc["sensors"]["bme280"]["status"] = "error";
  }
  
  if (sensorStatus.ds18b20_ok) {
    doc["sensors"]["ds18b20"]["water_temperature_c"] = readings.water_temp;
    doc["sensors"]["ds18b20"]["status"] = "ok";
  } else {
    doc["sensors"]["ds18b20"]["status"] = "error";
  }
  
  // アナログセンサー
  doc["sensors"]["soil_moisture"]["raw_value"] = readings.soil_moisture_raw;
  doc["sensors"]["soil_moisture"]["percentage"] = readings.soil_moisture_percent;
  doc["sensors"]["light"]["raw_value"] = readings.light_level_raw;
  doc["sensors"]["light"]["percentage"] = readings.light_level_percent;
  
  // モーションセンサー
  doc["sensors"]["motion"]["detected"] = readings.motion_detected;
  
  // システム情報
  doc["system"]["uptime_ms"] = millis();
  doc["system"]["free_heap"] = ESP.getFreeHeap();
  doc["system"]["wifi_rssi"] = WiFi.RSSI();
  doc["system"]["battery_voltage"] = getBatteryVoltage();
  
  // 移動平均値（フィルタ適用済み）
  if (sensorStatus.dht22_ok) {
    float avgTemp = 0, avgHumidity = 0;
    for (int i = 0; i < filterSamples; i++) {
      avgTemp += tempFilter[i];
      avgHumidity += humidityFilter[i];
    }
    doc["filtered"]["average_temperature_c"] = avgTemp / filterSamples;
    doc["filtered"]["average_humidity_percent"] = avgHumidity / filterSamples;
  }
  
  String payload;
  serializeJson(doc, payload);
  
  String topic = "sensors/esp32/" + String(device_id) + "/environmental";
  bool result = client.publish(topic.c_str(), payload.c_str());
  
  Serial.println("Environmental data published: " + String(result ? "SUCCESS" : "FAILED"));
  
  // データ送信成功時にLED点滅
  if (result) {
    blinkStatusLED(1, 100);
  }
}

void checkAlerts() {
  DynamicJsonDocument doc(2048);
  bool alertTriggered = false;
  
  doc["timestamp"] = millis();
  doc["device_id"] = device_id;
  doc["alerts"] = JsonArray();
  
  // 温度アラート
  if (!isnan(readings.air_temp_dht)) {
    if (readings.air_temp_dht > 35.0) {
      JsonObject alert = doc["alerts"].createNestedObject();
      alert["type"] = "high_temperature";
      alert["severity"] = "warning";
      alert["value"] = readings.air_temp_dht;
      alert["threshold"] = 35.0;
      alert["sensor"] = "dht22";
      alertTriggered = true;
    } else if (readings.air_temp_dht < 5.0) {
      JsonObject alert = doc["alerts"].createNestedObject();
      alert["type"] = "low_temperature";
      alert["severity"] = "warning";
      alert["value"] = readings.air_temp_dht;
      alert["threshold"] = 5.0;
      alert["sensor"] = "dht22";
      alertTriggered = true;
    }
  }
  
  // 湿度アラート
  if (!isnan(readings.air_humidity_dht)) {
    if (readings.air_humidity_dht > 80.0) {
      JsonObject alert = doc["alerts"].createNestedObject();
      alert["type"] = "high_humidity";
      alert["severity"] = "info";
      alert["value"] = readings.air_humidity_dht;
      alert["threshold"] = 80.0;
      alertTriggered = true;
    }
  }
  
  // 土壌湿度アラート
  if (readings.soil_moisture_percent < 20) {
    JsonObject alert = doc["alerts"].createNestedObject();
    alert["type"] = "low_soil_moisture";
    alert["severity"] = "warning";
    alert["value"] = readings.soil_moisture_percent;
    alert["threshold"] = 20.0;
    alert["message"] = "Plant may need watering";
    alertTriggered = true;
  }
  
  // モーション検出
  if (readings.motion_detected) {
    JsonObject alert = doc["alerts"].createNestedObject();
    alert["type"] = "motion_detected";
    alert["severity"] = "info";
    alert["message"] = "Motion detected in monitored area";
    alertTriggered = true;
  }
  
  // アラート送信
  if (alertTriggered) {
    String payload;
    serializeJson(doc, payload);
    
    String topic = "alerts/esp32/" + String(device_id) + "/environmental";
    client.publish(topic.c_str(), payload.c_str());
    
    // アラート音
    beep(3, 150);
    
    Serial.println("Alerts published");
  }
}

void handleMotionDetection() {
  static bool lastMotionState = false;
  static unsigned long motionStartTime = 0;
  
  bool currentMotion = digitalRead(PIR_PIN);
  
  // モーション開始検出
  if (currentMotion && !lastMotionState) {
    motionStartTime = millis();
    publishMotionEvent("motion_start");
    beep(1, 100);
  }
  
  // モーション終了検出
  if (!currentMotion && lastMotionState) {
    unsigned long motionDuration = millis() - motionStartTime;
    publishMotionEvent("motion_end", motionDuration);
  }
  
  lastMotionState = currentMotion;
}

void publishMotionEvent(String eventType, unsigned long duration = 0) {
  DynamicJsonDocument doc(1024);
  
  doc["timestamp"] = millis();
  doc["device_id"] = device_id;
  doc["event_type"] = eventType;
  doc["sensor"] = "pir";
  
  if (duration > 0) {
    doc["duration_ms"] = duration;
  }
  
  String payload;
  serializeJson(doc, payload);
  
  String topic = "events/esp32/" + String(device_id) + "/motion";
  client.publish(topic.c_str(), payload.c_str());
}

void updateStatusLED() {
  // センサー健全性に基づいてLED制御
  int healthyCount = 0;
  if (sensorStatus.dht22_ok) healthyCount++;
  if (sensorStatus.bme280_ok) healthyCount++;
  if (sensorStatus.ds18b20_ok) healthyCount++;
  
  if (healthyCount >= 2) {
    // 正常：緑（常灯）
    digitalWrite(STATUS_LED_PIN, HIGH);
  } else if (healthyCount >= 1) {
    // 警告：点滅
    static unsigned long lastBlink = 0;
    if (millis() - lastBlink > 1000) {
      digitalWrite(STATUS_LED_PIN, !digitalRead(STATUS_LED_PIN));
      lastBlink = millis();
    }
  } else {
    // エラー：消灯
    digitalWrite(STATUS_LED_PIN, LOW);
  }
}

void blinkStatusLED(int times, int delayMs) {
  for (int i = 0; i < times; i++) {
    digitalWrite(STATUS_LED_PIN, LOW);
    delay(delayMs);
    digitalWrite(STATUS_LED_PIN, HIGH);
    delay(delayMs);
  }
}

void beep(int times, int duration) {
  for (int i = 0; i < times; i++) {
    digitalWrite(BUZZER_PIN, HIGH);
    delay(duration);
    digitalWrite(BUZZER_PIN, LOW);
    if (i < times - 1) delay(duration);
  }
}

// 前回と同様のヘルパー関数
void setupWiFi() { /* 前回と同様 */ }
void callback(char* topic, byte* message, unsigned int length) { /* 前回と同様 */ }
void reconnect() { /* 前回と同様 */ }
float getBatteryVoltage() { /* 前回と同様 */ }
```

### Step 3: 省電力・バッテリー最適化

#### 3.1 Deep Sleep実装

`examples/03_power_optimized/power_optimized.ino`:

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <DHT.h>
#include <esp_sleep.h>
#include <esp_wifi.h>
#include <esp_bt.h>

// 省電力設定
#define SLEEP_INTERVAL_NORMAL 300   // 5分（通常時）
#define SLEEP_INTERVAL_LOW_BATTERY 900  // 15分（低電圧時）
#define BATTERY_LOW_THRESHOLD 3.4   // 低電圧閾値
#define BATTERY_CRITICAL_THRESHOLD 3.2  // 危険電圧閾値

// RTC Memory（Deep Sleep中も保持される）
RTC_DATA_ATTR int bootCount = 0;
RTC_DATA_ATTR float lastBatteryVoltage = 0;
RTC_DATA_ATTR unsigned long totalUptime = 0;
RTC_DATA_ATTR int consecutiveErrors = 0;

// Wake up原因
esp_sleep_wakeup_cause_t wakeup_reason;

void setup() {
  Serial.begin(115200);
  
  // ブート回数増加
  bootCount++;
  totalUptime += millis();
  
  // Wake up原因確認
  wakeup_reason = esp_sleep_get_wakeup_cause();
  printWakeupReason();
  
  // 省電力設定
  configurePowerSaving();
  
  // クリティカルな電圧チェック
  float batteryVoltage = getBatteryVoltage();
  if (batteryVoltage < BATTERY_CRITICAL_THRESHOLD && batteryVoltage > 2.0) {
    Serial.println("CRITICAL BATTERY LEVEL - Emergency sleep");
    enterEmergencySleep();
  }
  
  // センサー・WiFi初期化
  initializeAndRun();
  
  // 次のスリープ準備
  prepareForSleep();
}

void loop() {
  // メインループは使用しない（省電力のため）
}

void configurePowerSaving() {
  // CPU周波数を最低に設定
  setCpuFrequencyMhz(80);  // 240MHz → 80MHz
  
  // Bluetooth無効化
  esp_bt_controller_disable();
  
  // 不要なペリフェラル無効化
  esp_wifi_set_ps(WIFI_PS_MAX_MODEM);
  
  Serial.println("Power saving configured");
}

void initializeAndRun() {
  // センサー初期化
  DHT dht(4, DHT22);
  dht.begin();
  
  // WiFi接続
  if (!connectWiFiQuick()) {
    consecutiveErrors++;
    if (consecutiveErrors > 3) {
      Serial.println("Multiple WiFi failures - Extended sleep");
      enterExtendedSleep();
    }
    return;
  }
  
  // MQTT接続・データ送信
  if (connectAndPublish(&dht)) {
    consecutiveErrors = 0;  // 成功時はエラーカウンタリセット
  } else {
    consecutiveErrors++;
  }
}

bool connectWiFiQuick() {
  const char* ssid = "YOUR_WIFI_SSID";
  const char* password = "YOUR_WIFI_PASSWORD";
  
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  // 最大20秒で接続試行
  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 40) {
    delay(500);
    attempts++;
  }
  
  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi connected quickly");
    return true;
  } else {
    Serial.println("WiFi connection failed");
    return false;
  }
}

bool connectAndPublish(DHT* dht) {
  WiFiClient espClient;
  PubSubClient client(espClient);
  
  client.setServer("192.168.1.100", 1883);
  
  // MQTT接続試行
  String clientId = "esp32_power_opt_" + String(ESP.getEfuseMac());
  if (!client.connect(clientId.c_str())) {
    Serial.println("MQTT connection failed");
    return false;
  }
  
  // センサーデータ収集
  float temperature = dht->readTemperature();
  float humidity = dht->readHumidity();
  float batteryVoltage = getBatteryVoltage();
  
  // データ送信
  DynamicJsonDocument doc(1024);
  doc["boot_count"] = bootCount;
  doc["uptime_total_ms"] = totalUptime;
  doc["wake_reason"] = getWakeupReasonString();
  doc["battery_voltage"] = batteryVoltage;
  doc["wifi_rssi"] = WiFi.RSSI();
  
  if (!isnan(temperature) && !isnan(humidity)) {
    doc["temperature_c"] = temperature;
    doc["humidity_percent"] = humidity;
  } else {
    doc["sensor_error"] = true;
  }
  
  // システム情報
  doc["free_heap"] = ESP.getFreeHeap();
  doc["cpu_freq_mhz"] = getCpuFrequencyMhz();
  
  String payload;
  serializeJson(doc, payload);
  
  String topic = "sensors/esp32/" + clientId + "/power_optimized";
  bool success = client.publish(topic.c_str(), payload.c_str());
  
  // 切断
  client.disconnect();
  
  return success;
}

void prepareForSleep() {
  float batteryVoltage = getBatteryVoltage();
  lastBatteryVoltage = batteryVoltage;
  
  int sleepTime = SLEEP_INTERVAL_NORMAL;
  
  // バッテリーレベルに応じてスリープ時間調整
  if (batteryVoltage < BATTERY_LOW_THRESHOLD) {
    sleepTime = SLEEP_INTERVAL_LOW_BATTERY;
    Serial.println("Low battery - Extended sleep interval");
  }
  
  // エラー状況に応じて調整
  if (consecutiveErrors > 1) {
    sleepTime *= 2;  // エラー時は2倍長くスリープ
    Serial.println("Consecutive errors - Extended sleep");
  }
  
  // WiFi・Bluetoothをオフ
  WiFi.disconnect();
  WiFi.mode(WIFI_OFF);
  esp_wifi_stop();
  
  Serial.println("Entering deep sleep for " + String(sleepTime) + " seconds");
  Serial.flush();
  
  // Deep Sleep設定
  esp_sleep_enable_timer_wakeup(sleepTime * 1000000ULL);
  
  // GPIO Wake up（オプション）
  esp_sleep_enable_ext0_wakeup(GPIO_NUM_0, 0);  // プッシュボタン
  
  esp_deep_sleep_start();
}

void enterEmergencySleep() {
  Serial.println("EMERGENCY SLEEP - 1 hour");
  Serial.flush();
  
  esp_sleep_enable_timer_wakeup(3600 * 1000000ULL);  // 1時間
  esp_deep_sleep_start();
}

void enterExtendedSleep() {
  Serial.println("EXTENDED SLEEP - 30 minutes");
  Serial.flush();
  
  esp_sleep_enable_timer_wakeup(1800 * 1000000ULL);  // 30分
  esp_deep_sleep_start();
}

void printWakeupReason() {
  switch(wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0:
      Serial.println("Wakeup caused by external signal using RTC_IO");
      break;
    case ESP_SLEEP_WAKEUP_EXT1:
      Serial.println("Wakeup caused by external signal using RTC_CNTL");
      break;
    case ESP_SLEEP_WAKEUP_TIMER:
      Serial.println("Wakeup caused by timer");
      break;
    case ESP_SLEEP_WAKEUP_TOUCHPAD:
      Serial.println("Wakeup caused by touchpad");
      break;
    case ESP_SLEEP_WAKEUP_ULP:
      Serial.println("Wakeup caused by ULP program");
      break;
    default:
      Serial.printf("Wakeup was not caused by deep sleep: %d\n", wakeup_reason);
      break;
  }
}

String getWakeupReasonString() {
  switch(wakeup_reason) {
    case ESP_SLEEP_WAKEUP_EXT0: return "external_rtc_io";
    case ESP_SLEEP_WAKEUP_EXT1: return "external_rtc_cntl";
    case ESP_SLEEP_WAKEUP_TIMER: return "timer";
    case ESP_SLEEP_WAKEUP_TOUCHPAD: return "touchpad";
    case ESP_SLEEP_WAKEUP_ULP: return "ulp";
    default: return "power_on_reset";
  }
}

float getBatteryVoltage() {
  // 複数回測定して平均化
  float sum = 0;
  for (int i = 0; i < 10; i++) {
    sum += analogRead(A0);
    delay(10);
  }
  
  float average = sum / 10.0;
  float voltage = (average / 4095.0) * 3.3 * 2.0;  // 電圧分圧補正
  
  return voltage;
}
```

### Step 4: OTAファームウェア更新

#### 4.1 OTA対応版

`examples/04_ota_enabled/ota_enabled.ino`:

```cpp
#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoOTA.h>
#include <Update.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>

const char* FIRMWARE_VERSION = "1.2.0";
const char* OTA_PASSWORD = "secure_ota_password";

void setup() {
  Serial.begin(115200);
  Serial.println("ESP32 OTA-Enabled Node v" + String(FIRMWARE_VERSION));
  
  setupWiFi();
  setupOTA();
  setupMQTT();
  
  // OTA準備完了通知
  publishOTAStatus("ready");
}

void setupOTA() {
  // Hostname設定
  ArduinoOTA.setHostname("esp32-sensor-node");
  ArduinoOTA.setPassword(OTA_PASSWORD);
  
  ArduinoOTA.onStart([]() {
    String type = (ArduinoOTA.getCommand() == U_FLASH) ? "sketch" : "filesystem";
    Serial.println("OTA Start updating " + type);
    publishOTAStatus("updating");
  });
  
  ArduinoOTA.onEnd([]() {
    Serial.println("\nOTA End");
    publishOTAStatus("completed");
  });
  
  ArduinoOTA.onProgress([](unsigned int progress, unsigned int total) {
    int percent = (progress * 100) / total;
    Serial.printf("OTA Progress: %u%%\r", percent);
    
    // 進捗をMQTTで報告（10%刻み）
    static int lastPercent = 0;
    if (percent >= lastPercent + 10) {
      publishOTAProgress(percent);
      lastPercent = percent;
    }
  });
  
  ArduinoOTA.onError([](ota_error_t error) {
    Serial.printf("OTA Error[%u]: ", error);
    String errorMsg = "";
    
    if (error == OTA_AUTH_ERROR) errorMsg = "Auth Failed";
    else if (error == OTA_BEGIN_ERROR) errorMsg = "Begin Failed";
    else if (error == OTA_CONNECT_ERROR) errorMsg = "Connect Failed";
    else if (error == OTA_RECEIVE_ERROR) errorMsg = "Receive Failed";
    else if (error == OTA_END_ERROR) errorMsg = "End Failed";
    
    Serial.println(errorMsg);
    publishOTAStatus("error", errorMsg);
  });
  
  ArduinoOTA.begin();
  Serial.println("OTA Ready");
}

void publishOTAStatus(String status, String message = "") {
  DynamicJsonDocument doc(512);
  doc["device_id"] = WiFi.getHostname();
  doc["firmware_version"] = FIRMWARE_VERSION;
  doc["ota_status"] = status;
  doc["timestamp"] = millis();
  
  if (message != "") {
    doc["message"] = message;
  }
  
  String payload;
  serializeJson(doc, payload);
  
  String topic = "ota/esp32/" + String(WiFi.getHostname()) + "/status";
  client.publish(topic.c_str(), payload.c_str(), true);
}

void publishOTAProgress(int percent) {
  DynamicJsonDocument doc(256);
  doc["device_id"] = WiFi.getHostname();
  doc["progress_percent"] = percent;
  doc["timestamp"] = millis();
  
  String payload;
  serializeJson(doc, payload);
  
  String topic = "ota/esp32/" + String(WiFi.getHostname()) + "/progress";
  client.publish(topic.c_str(), payload.c_str());
}

// HTTP OTA更新
void performHTTPUpdate(String updateUrl) {
  Serial.println("Starting HTTP OTA update from: " + updateUrl);
  publishOTAStatus("downloading");
  
  HTTPClient http;
  http.begin(updateUrl);
  
  int httpCode = http.GET();
  
  if (httpCode == HTTP_CODE_OK) {
    int contentLength = http.getSize();
    
    if (contentLength > 0) {
      WiFiClient* client = http.getStreamPtr();
      
      if (Update.begin(contentLength)) {
        Serial.println("Starting update...");
        
        size_t written = Update.writeStream(*client);
        
        if (written == contentLength) {
          Serial.println("Update written successfully");
          
          if (Update.end()) {
            if (Update.isFinished()) {
              Serial.println("Update successfully completed. Rebooting...");
              publishOTAStatus("completed");
              delay(1000);
              ESP.restart();
            } else {
              publishOTAStatus("error", "Update not finished");
            }
          } else {
            publishOTAStatus("error", "Update end failed: " + String(Update.getError()));
          }
        } else {
          publishOTAStatus("error", "Written only : " + String(written) + "/" + String(contentLength));
        }
      } else {
        publishOTAStatus("error", "Not enough space to begin OTA");
      }
    } else {
      publishOTAStatus("error", "Invalid content length");
    }
  } else {
    publishOTAStatus("error", "HTTP error: " + String(httpCode));
  }
  
  http.end();
}

void callback(char* topic, byte* message, unsigned int length) {
  String messageTemp;
  for (int i = 0; i < length; i++) {
    messageTemp += (char)message[i];
  }
  
  String topicStr = String(topic);
  
  if (topicStr.endsWith("/ota/command")) {
    DynamicJsonDocument doc(1024);
    deserializeJson(doc, messageTemp);
    
    String command = doc["command"];
    
    if (command == "update") {
      String updateUrl = doc["url"];
      if (updateUrl != "") {
        performHTTPUpdate(updateUrl);
      }
    } else if (command == "check_version") {
      publishOTAStatus("version_info");
    } else if (command == "restart") {
      publishOTAStatus("restarting");
      delay(1000);
      ESP.restart();
    }
  }
}

void loop() {
  ArduinoOTA.handle();  // OTA処理
  
  if (!client.connected()) {
    reconnect();
  }
  client.loop();
  
  // 通常のセンサー処理
  static unsigned long lastUpdate = 0;
  if (millis() - lastUpdate > 60000) {  // 1分間隔
    lastUpdate = millis();
    publishSensorData();
  }
  
  delay(100);
}
```

## 課題

### 基礎課題

1. **基本MQTT通信**
   - ESP32からMQTTブローカーへの接続
   - センサーデータ送信

2. **複数センサー統合**
   - 3種類以上のセンサー同時運用
   - アラート機能実装

3. **省電力実装**
   - Deep Sleep活用
   - バッテリー駆動時間最適化

### 応用課題

1. **メッシュネットワーク**
   - ESP-NOW使用
   - 複数ESP32間通信

2. **OTA更新システム**
   - リモートファームウェア更新
   - 段階的更新管理

3. **エッジ処理**
   - ローカルデータ処理
   - 異常検出アルゴリズム

## トラブルシューティング

### WiFi接続問題
```cpp
// 電波強度確認
Serial.println("RSSI: " + String(WiFi.RSSI()));

// MACアドレス確認
Serial.println("MAC: " + WiFi.macAddress());
```

### センサー認識問題
```cpp
// I2Cスキャン
Wire.begin();
for (byte i = 8; i < 120; i++) {
  Wire.beginTransmission(i);
  if (Wire.endTransmission() == 0) {
    Serial.println("I2C device at 0x" + String(i, HEX));
  }
}
```

## 次のステップ

演習4のエッジAI統合で、ESP32とJetsonの連携システムを構築します。

---

この演習で、産業レベルのIoTセンサーノードの基礎を学べます。実際のプロジェクトでも応用可能な実装例です。