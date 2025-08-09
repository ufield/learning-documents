# MQTTの基本概念とアーキテクチャ

## 2.1 Publish-Subscribe パターン

MQTTの核心となるのは、Publish-Subscribe（Pub/Sub）メッセージングパターンです。これは従来のリクエスト-レスポンスモデルとは大きく異なります。

### 従来の通信方式の問題点

```
[クライアントA] ←→ [クライアントB]
```

**問題:**
- 直接的な接続が必要
- 双方が同時にオンラインである必要
- スケーリングが困難
- 障害耐性が低い

### Pub/Subの利点

```
[Publisher] → [Broker] → [Subscriber1]
                   ↓
              [Subscriber2]
                   ↓
              [Subscriber3]
```

**利点:**
- **疎結合**: PublisherとSubscriberは互いを知らない
- **スケーラビリティ**: 1つのメッセージを複数の受信者に配信
- **非同期**: 送信者と受信者が同時にオンラインである必要がない
- **柔軟性**: 動的にSubscriberを追加・削除可能

## 2.2 主要コンポーネント

### 2.2.1 MQTT Broker（ブローカー）

ブローカーはMQTTネットワークの中心的な役割を果たします。

**主要機能:**
- メッセージのルーティング
- セッション管理
- サブスクリプション管理
- 認証・認可
- QoS処理

**代表的なブローカー (2025年版):**

| ブローカー | 特徴 | 最大接続数 | ライセンス |
|------------|------|------------|------------|
| Eclipse Mosquitto | 軽量、シンプル | ~100K | EPL/EDL |
| EMQX | 高性能、スケーラブル | 数百万 | Apache 2.0 |
| HiveMQ | エンタープライズ機能 | 数百万 | 商用/CE |
| VerneMQ | 高可用性重視 | ~10万 | Apache 2.0 |
| AWS IoT Core | マネージドサービス | 無制限 | 商用 |

### 2.2.2 MQTT Client（クライアント）

クライアントはメッセージを送信（Publish）または受信（Subscribe）するデバイスです。

**クライアントの種類:**
- **Publisher**: メッセージを送信するクライアント
- **Subscriber**: メッセージを受信するクライアント
- **Publisher/Subscriber**: 両方の機能を持つクライアント

**クライアントライブラリ (2025年推奨):**

#### JavaScript/Node.js
```javascript
// MQTT.js - 最も人気のあるJavaScriptライブラリ
npm install mqtt

const mqtt = require('mqtt');
const client = mqtt.connect('mqtt://broker.example.com');
```

#### Python
```python
# paho-mqtt - 公式Pythonライブラリ
pip install paho-mqtt

import paho.mqtt.client as mqtt
client = mqtt.Client()
```

#### Java
```java
// Eclipse Paho Java Client
<dependency>
    <groupId>org.eclipse.paho</groupId>
    <artifactId>org.eclipse.paho.client.mqttv3</artifactId>
    <version>1.2.5</version>
</dependency>
```

## 2.3 Topic（トピック）

Topicは、MQTTにおけるメッセージのアドレス指定システムです。

### 2.3.1 Topic構造

```
level1/level2/level3/level4
```

**例:**
```
home/livingroom/temperature
factory/line1/sensor/pressure
vehicle/truck001/gps/latitude
iot/building5/floor2/room203/humidity
```

### 2.3.2 Topic設計のベストプラクティス

#### 階層的な構造
```
組織/場所/デバイスタイプ/デバイスID/メトリクス

acme/tokyo/sensor/temp001/temperature
acme/tokyo/sensor/temp001/humidity
acme/tokyo/actuator/valve001/status
acme/osaka/sensor/temp002/temperature
```

#### 命名規則（2025年推奨）
- **小文字のみ使用**: `temperature`（○）、`Temperature`（×）
- **アンダースコア使用**: `device_id`（○）、`deviceId`（×）
- **英数字とハイフン**: `sensor-001`（○）、`sensor#001`（×）
- **スラッシュで階層分離**: `home/kitchen/sensor`

### 2.3.3 Wildcards（ワイルドカード）

Subscribeの際に使用できる特別な文字です。

#### Single Level Wildcard (+)
```
home/+/temperature

マッチする例:
✓ home/kitchen/temperature  
✓ home/bedroom/temperature
✓ home/garage/temperature

マッチしない例:
✗ home/kitchen/sensor/temperature
✗ office/kitchen/temperature
```

#### Multi Level Wildcard (#)
```
home/kitchen/#

マッチする例:
✓ home/kitchen/temperature
✓ home/kitchen/humidity  
✓ home/kitchen/sensor/motion
✓ home/kitchen/light/switch/status

マッチしない例:
✗ home/bedroom/temperature
✗ office/kitchen/temperature
```

#### ワイルドカード使用時の注意点

```javascript
// 推奨: 具体的なsubscription
client.subscribe('home/kitchen/temperature');
client.subscribe('home/kitchen/humidity');

// 非推奨: 過度に広範囲なsubscription
client.subscribe('#'); // 全てのメッセージを受信（性能問題）

// 適切な使用例
client.subscribe('home/+/temperature'); // 全部屋の温度のみ
client.subscribe('factory/line1/#');    // 特定の生産ラインのみ
```

## 2.4 Quality of Service (QoS)

QoSは、メッセージ配信の信頼性レベルを定義します。

### QoS 0: At most once（最大1回配信）

```
Publisher → [PUBLISH] → Broker → [PUBLISH] → Subscriber
```

**特徴:**
- 最も軽量
- メッセージが失われる可能性あり
- 重複なし
- ファイア・アンド・フォーゲット方式

**用途:**
- 環境センサーの定期データ（少々の欠落は許容可能）
- ログデータ
- リアルタイム位置情報

### QoS 1: At least once（最低1回配信）

```
Publisher → [PUBLISH] → Broker → [PUBLISH] → Subscriber
         ← [PUBACK]  ←        ← [PUBACK]  ←
```

**特徴:**
- メッセージは必ず配信される
- 重複の可能性あり
- 確認応答が必要

**用途:**
- 重要な測定値
- アラート通知
- 設定変更通知

### QoS 2: Exactly once（正確に1回配信）

```
Publisher → [PUBLISH] → Broker → [PUBLISH] → Subscriber
         ← [PUBREC]  ←        ← [PUBREC]  ←
         → [PUBREL]  →        → [PUBREL]  →
         ← [PUBCOMP] ←        ← [PUBCOMP] ←
```

**特徴:**
- 重複なし、欠落なし
- 最も信頼性が高い
- 4回のメッセージ交換が必要（最も重い）

**用途:**
- 課金情報
- 制御コマンド
- 法的に重要なデータ

### QoS選択の指針

| データの性質 | 推奨QoS | 理由 |
|--------------|---------|------|
| 定期的なセンサーデータ | QoS 0 | 軽量、次のデータで補完可能 |
| アラート・通知 | QoS 1 | 確実な配信が必要 |
| 制御コマンド | QoS 2 | 重複実行を防ぐ必要 |
| 設定データ | QoS 1 | 確実な配信、冪等性で重複対応 |

## 2.5 セッション管理

### 2.5.1 Clean Session（MQTT 3.1.1）

```javascript
// Clean Session = true（セッション情報を保持しない）
const client = mqtt.connect('mqtt://broker.example.com', {
    clean: true,
    clientId: 'sensor001'
});

// Clean Session = false（セッション情報を保持）
const client = mqtt.connect('mqtt://broker.example.com', {
    clean: false,
    clientId: 'sensor001'
});
```

### 2.5.2 Session Expiry（MQTT 5.0）

```javascript
// MQTT 5.0のより柔軟なセッション管理
const client = mqtt.connect('mqtt://broker.example.com', {
    protocolVersion: 5,
    clean: false,              // Clean Start
    sessionExpiryInterval: 300, // 5分後にセッション期限切れ
    clientId: 'sensor001'
});
```

**セッションで保持される情報:**
- Subscriptions
- QoS 1, 2 メッセージの配信状態
- 未配信のQoS 1, 2 メッセージ
- Will Message設定

## 2.6 Keep Alive機能

```javascript
const client = mqtt.connect('mqtt://broker.example.com', {
    keepalive: 60 // 60秒間隔でping送信
});
```

**動作シーケンス:**
```
Client → [PINGREQ] → Broker
      ← [PINGRESP] ←
```

**タイムアウト計算:**
```
タイムアウト = Keep Alive × 1.5
例：Keep Alive = 60秒の場合、90秒でタイムアウト
```

## 2.7 Last Will and Testament (LWT)

クライアントが予期せず切断された場合の処理です。

```javascript
const client = mqtt.connect('mqtt://broker.example.com', {
    will: {
        topic: 'devices/sensor001/status',
        payload: 'offline',
        qos: 1,
        retain: true
    }
});
```

**動作例:**
1. センサーが正常接続 → `devices/sensor001/status: "online"`
2. ネットワーク障害で突然切断
3. ブローカーがタイムアウトを検知
4. LWTメッセージを自動送信 → `devices/sensor001/status: "offline"`

## 2.8 Retained Messages

```javascript
// Retainedメッセージの送信
client.publish('home/kitchen/temperature', '23.5', {
    qos: 1,
    retain: true
});

// 新しいSubscriberがjoinした場合
client.subscribe('home/kitchen/temperature');
// すぐに最新の温度 "23.5" を受信
```

**用途:**
- デバイスの現在状態
- 設定値
- 最新の測定値

## 参考リンク

- [MQTT Essentials - HiveMQ](https://www.hivemq.com/mqtt-essentials/)
- [Understanding MQTT Topics & Wildcards](https://www.hivemq.com/blog/mqtt-essentials-part-5-mqtt-topics-best-practices/)
- [MQTT QoS Levels Explained](https://www.hivemq.com/blog/mqtt-essentials-part-6-mqtt-quality-of-service-levels/)
- [EMQX - MQTT Concepts](https://docs.emqx.com/en/emqx/latest/mqtt/mqtt-concepts.html)

---

**次の章**: [03-protocol-basics.md](03-protocol-basics.md) - MQTTプロトコルの詳細