# MQTTプロトコルの詳細

## 3.1 プロトコルスタック

MQTTは、TCP/IPスタック上で動作するアプリケーション層プロトコルです。

```
┌─────────────────┐
│   MQTT Layer    │ ← アプリケーション層
├─────────────────┤
│   TLS/SSL       │ ← セキュリティ層（オプション）
├─────────────────┤
│     TCP         │ ← トランスポート層
├─────────────────┤
│      IP         │ ← ネットワーク層
└─────────────────┘
```

## 3.2 MQTTメッセージ構造

すべてのMQTTメッセージは、以下の構造を持ちます：

```
┌─────────────────┐
│  Fixed Header   │ ← 常に存在（2-5バイト）
├─────────────────┤
│ Variable Header │ ← メッセージタイプによって異なる
├─────────────────┤
│    Payload      │ ← メッセージの内容（オプション）
└─────────────────┘
```

### 3.2.1 Fixed Header

```
Bit:   7  6  5  4   3  2  1  0
      ┌─────────────┬─────────────┐
Byte 1│Message Type │    Flags    │
      └─────────────┴─────────────┘
Byte 2│      Remaining Length     │
   ~  │         (1-4 bytes)       │
      └───────────────────────────┘
```

#### Message Type（メッセージタイプ）

| Value | Name | Description |
|-------|------|-------------|
| 0 | Reserved | 予約済み |
| 1 | CONNECT | クライアント接続要求 |
| 2 | CONNACK | 接続確認応答 |
| 3 | PUBLISH | メッセージ公開 |
| 4 | PUBACK | 公開確認応答（QoS 1） |
| 5 | PUBREC | 公開受信応答（QoS 2） |
| 6 | PUBREL | 公開解放（QoS 2） |
| 7 | PUBCOMP | 公開完了（QoS 2） |
| 8 | SUBSCRIBE | 購読要求 |
| 9 | SUBACK | 購読確認応答 |
| 10 | UNSUBSCRIBE | 購読解除要求 |
| 11 | UNSUBACK | 購読解除確認応答 |
| 12 | PINGREQ | Ping要求 |
| 13 | PINGRESP | Ping応答 |
| 14 | DISCONNECT | 切断通知 |
| 15 | AUTH | 認証交換（MQTT 5.0のみ） |

#### Flags（フラグ）

PUBLISHメッセージの場合：
```
Bit 3: DUP  - 重複メッセージフラグ
Bit 2-1: QoS - Quality of Service レベル
Bit 0: RETAIN - 保持メッセージフラグ
```

#### Remaining Length（残り長さ）

Variable HeaderとPayloadの合計バイト数を可変長エンコーディングで表現：

```python
def encode_remaining_length(length):
    """残り長さのエンコード例"""
    encoded = []
    while length > 0:
        byte = length % 128
        length = length // 128
        if length > 0:
            byte |= 128  # continuation bit
        encoded.append(byte)
    return encoded

# 例：127バイト → [127]
# 例：128バイト → [128, 1]
# 例：16383バイト → [255, 127]
```

## 3.3 主要メッセージタイプの詳細

### 3.3.1 CONNECT メッセージ

クライアントがブローカーに接続する際の最初のメッセージです。

```
Variable Header:
┌─────────────────┐
│ Protocol Name   │ "MQTT" (MQTT 3.1.1) or "MQIsdp" (MQTT 3.1)
├─────────────────┤
│ Protocol Level  │ 4 (MQTT 3.1.1) or 5 (MQTT 5.0)
├─────────────────┤
│ Connect Flags   │ Clean Session, Will, QoS, etc.
├─────────────────┤
│ Keep Alive      │ 秒単位のKeep Alive間隔
└─────────────────┘

Payload:
┌─────────────────┐
│ Client ID       │ クライアント識別子
├─────────────────┤
│ Will Topic      │ LWTトピック（オプション）
├─────────────────┤
│ Will Message    │ LWTメッセージ（オプション）
├─────────────────┤
│ Username        │ ユーザー名（オプション）
├─────────────────┤
│ Password        │ パスワード（オプション）
└─────────────────┘
```

**Connect Flagsの詳細：**

```
Bit 7: Username Flag
Bit 6: Password Flag  
Bit 5: Will Retain
Bit 4-3: Will QoS (00=0, 01=1, 10=2, 11=Reserved)
Bit 2: Will Flag
Bit 1: Clean Session (MQTT 3.1.1) / Clean Start (MQTT 5.0)
Bit 0: Reserved (0)
```

### 3.3.2 CONNACK メッセージ

ブローカーからクライアントへの接続確認応答です。

```
Variable Header:
┌─────────────────┐
│ Connect Ack     │
│ Flags           │ Session Present フラグ
├─────────────────┤
│ Connect Return  │ 接続結果コード
│ Code           │
└─────────────────┘
```

**接続結果コード（MQTT 3.1.1）:**

| Code | Description |
|------|-------------|
| 0 | 接続受諾 |
| 1 | 接続拒否：サポートされていないプロトコルバージョン |
| 2 | 接続拒否：不正なクライアント識別子 |
| 3 | 接続拒否：サーバー利用不可 |
| 4 | 接続拒否：不正なユーザー名またはパスワード |
| 5 | 接続拒否：認証されていない |

### 3.3.3 PUBLISH メッセージ

最も重要なメッセージタイプで、データを送信するために使用されます。

```
Variable Header:
┌─────────────────┐
│ Topic Name      │ 公開先トピック名
├─────────────────┤
│ Packet ID       │ QoS 1,2の場合のみ
└─────────────────┘

Payload:
┌─────────────────┐
│ Application     │ 実際のメッセージデータ
│ Message         │ (バイナリ可能)
└─────────────────┘
```

**PUBLISHメッセージの例（16進数）:**

```
30 0D 00 04 74 65 73 74 48 65 6C 6C 6F 21

解析:
30      - Fixed Header: PUBLISH, QoS=0, Retain=0, DUP=0
0D      - Remaining Length: 13バイト
00 04   - Topic Length: 4バイト
74 65 73 74 - Topic Name: "test"
48 65 6C 6C 6F 21 - Payload: "Hello!"
```

## 3.4 QoS フロー詳細

### 3.4.1 QoS 0 フロー

```
Publisher                    Broker                    Subscriber
    |                          |                          |
    |---- PUBLISH (QoS 0) ---->|                          |
    |                          |---- PUBLISH (QoS 0) ---->|
    |                          |                          |
```

**特徴:**
- 単方向通信
- 確認応答なし
- 最小限のオーバーヘッド

### 3.4.2 QoS 1 フロー

```
Publisher                    Broker                    Subscriber
    |                          |                          |
    |---- PUBLISH (QoS 1) ---->|                          |
    |<------- PUBACK ----------|                          |
    |                          |---- PUBLISH (QoS 1) ---->|
    |                          |<------- PUBACK ----------|
```

**特徴:**
- 確認応答による確実な配信
- メッセージIDによる管理
- 重複の可能性あり

### 3.4.3 QoS 2 フロー

```
Publisher                    Broker                    Subscriber
    |                          |                          |
    |---- PUBLISH (QoS 2) ---->|                          |
    |<------- PUBREC ----------|                          |
    |------- PUBREL ---------->|                          |
    |<------ PUBCOMP ----------|                          |
    |                          |---- PUBLISH (QoS 2) ---->|
    |                          |<------- PUBREC ----------|
    |                          |------- PUBREL ---------->|
    |                          |<------ PUBCOMP ----------|
```

**特徴:**
- 4段階ハンドシェイク
- 重複なし、欠落なし
- 最も確実だが最も重い

## 3.5 MQTT 5.0の新機能

### 3.5.1 Properties（プロパティ）

MQTT 5.0では、メッセージにプロパティを追加できます：

```javascript
// Session Expiry Interval
client.publish('topic', 'message', {
    properties: {
        sessionExpiryInterval: 3600, // 1時間
        messageExpiryInterval: 300,  // 5分
        topicAlias: 1,              // トピックエイリアス
        userProperties: {
            'source': 'sensor001',
            'location': 'warehouse-A'
        }
    }
});
```

### 3.5.2 Reason Codes（理由コード）

MQTT 5.0では、詳細な理由コードが提供されます：

**CONNACK Reason Codes:**
| Code | Name | Description |
|------|------|-------------|
| 0x00 | Success | 接続成功 |
| 0x80 | Unspecified error | 未特定エラー |
| 0x81 | Malformed Packet | 不正なパケット |
| 0x82 | Protocol Error | プロトコルエラー |
| 0x83 | Implementation specific error | 実装固有エラー |
| 0x84 | Unsupported Protocol Version | 未サポートプロトコルバージョン |
| 0x85 | Client Identifier not valid | 無効なクライアント識別子 |
| 0x86 | Bad User Name or Password | 不正なユーザー名またはパスワード |
| 0x87 | Not authorized | 認証されていない |
| 0x88 | Server unavailable | サーバー利用不可 |
| 0x89 | Server busy | サーバーがビジー |
| 0x8A | Banned | 禁止されている |

### 3.5.3 Topic Alias（トピックエイリアス）

```javascript
// 最初のPublish（トピック名とエイリアスを送信）
client.publish('very/long/topic/name/with/many/levels', 'message1', {
    properties: { topicAlias: 42 }
});

// 以降のPublish（エイリアスのみ使用、帯域幅節約）
client.publish('', 'message2', {
    properties: { topicAlias: 42 }
});
```

### 3.5.4 Shared Subscriptions（共有サブスクリプション）

```javascript
// 従来の方法：全てのサブスクライバーがメッセージを受信
client1.subscribe('sensor/data');
client2.subscribe('sensor/data');
client3.subscribe('sensor/data');
// 3つのクライアント全てが同じメッセージを受信

// MQTT 5.0の共有サブスクリプション：負荷分散
client1.subscribe('$share/workers/sensor/data');
client2.subscribe('$share/workers/sensor/data'); 
client3.subscribe('$share/workers/sensor/data');
// 1つのクライアントのみがメッセージを受信（ラウンドロビン）
```

## 3.6 パフォーマンス考慮事項

### 3.6.1 メッセージサイズ最適化

```javascript
// 非効率：JSONでの送信
const inefficient = JSON.stringify({
    timestamp: 1638360000000,
    temperature: 23.5,
    humidity: 45.2,
    pressure: 1013.25
});
// サイズ: ~75バイト

// 効率的：バイナリでの送信
const efficient = Buffer.alloc(20);
efficient.writeUInt32BE(1638360000, 0);  // timestamp
efficient.writeFloatBE(23.5, 4);        // temperature  
efficient.writeFloatBE(45.2, 8);        // humidity
efficient.writeFloatBE(1013.25, 12);    // pressure
// サイズ: 20バイト
```

### 3.6.2 接続プール管理

```javascript
class MQTTConnectionPool {
    constructor(brokerUrl, poolSize = 5) {
        this.brokerUrl = brokerUrl;
        this.poolSize = poolSize;
        this.connections = [];
        this.currentIndex = 0;
    }
    
    async initialize() {
        for (let i = 0; i < this.poolSize; i++) {
            const client = mqtt.connect(this.brokerUrl, {
                clientId: `pool_client_${i}_${Date.now()}`
            });
            await new Promise((resolve) => {
                client.on('connect', resolve);
            });
            this.connections.push(client);
        }
    }
    
    getConnection() {
        const conn = this.connections[this.currentIndex];
        this.currentIndex = (this.currentIndex + 1) % this.poolSize;
        return conn;
    }
}
```

## 3.7 デバッグとトラブルシューティング

### 3.7.1 Wiresharkでの解析

MQTTパケットをWiresharkで解析する際の重要なフィルター：

```
# MQTT関連のみ表示
mqtt

# 特定のクライアントIDのメッセージ
mqtt.clientid == "sensor001"

# 特定のトピックへのPUBLISH
mqtt.topic == "home/temperature"

# CONNECTメッセージのみ
mqtt.msgtype == 1

# エラーのあるCONNACK
mqtt.conack.return_code != 0
```

### 3.7.2 一般的な問題と解決策

**問題1: 接続が頻繁に切断される**
```
原因: Keep Aliveの設定不備
解決: Keep Alive値を適切に設定

client.connect('mqtt://broker.example.com', {
    keepalive: 60,  // 60秒間隔
    reschedulePings: false
});
```

**問題2: メッセージが受信されない**
```
原因: QoS設定やセッション管理の問題
解決: Clean Sessionと適切なQoS使用

client.connect('mqtt://broker.example.com', {
    clean: false,  // セッション保持
});

client.subscribe('topic', { qos: 1 });
```

## 参考リンク

- [MQTT Version 5.0 Specification](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
- [MQTT Version 3.1.1 Specification](http://docs.oasis-open.org/mqtt/mqtt/v3.1.1/mqtt-v3.1.1.html)
- [Wireshark MQTT Dissector](https://wiki.wireshark.org/MQTT)
- [MQTT Packet Format Examples](https://github.com/mqtt/mqtt.github.io/wiki/packet-format)

---

**次の章**: [04-brokers-and-clients.md](04-brokers-and-clients.md) - ブローカーとクライアントの理解