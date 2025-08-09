# MQTT 実用サンプル集

このディレクトリには、実際のプロジェクトで活用できるMQTTアプリケーションの完全なサンプルが含まれています。

## 📁 サンプル一覧

### 1. Smart Home System
**ディレクトリ**: [smart-home-system](smart-home-system/)

スマートホームの完全な実装例：
- 複数のスマートデバイス（照明、温度センサー、スマートプラグ）
- Web ダッシュボード
- モバイル通知
- 自動化ルール

**技術スタック**: Node.js, Express, Vue.js, MQTT.js

### 2. Industrial IoT Monitor
**ディレクトリ**: [industrial-iot-monitor](industrial-iot-monitor/)

工場設備監視システム：
- PLC データ収集
- 予知保全アルゴリズム
- リアルタイムアラート
- レポート生成

**技術スタック**: Python, FastAPI, InfluxDB, Grafana

### 3. Fleet Management
**ディレクトリ**: [fleet-management](fleet-management/)

車両管理システム：
- GPS トラッキング
- 燃料監視
- 運転者行動分析
- ルート最適化

**技術スタック**: Node.js, MongoDB, React, Leaflet

### 4. Smart Agriculture
**ディレクトリ**: [smart-agriculture](smart-agriculture/)

スマート農業システム：
- 土壌センサー
- 自動灌漑制御
- 気象データ統合
- 収穫予測

**技術スタック**: Python, Django, PostgreSQL, Celery

### 5. Energy Management
**ディレクトリ**: [energy-management](energy-management/)

エネルギー管理システム：
- スマートメーター連携
- 電力需要予測
- 太陽光発電最適化
- コスト分析

**技術スタック**: Python, TimescaleDB, Plotly, MQTT

## 🚀 各サンプルの特徴

| サンプル | 複雑度 | 推奨レベル | 主要な学習ポイント |
|----------|--------|------------|-------------------|
| Smart Home | ★★☆ | 初級-中級 | 基本的なPub/Sub、Webダッシュボード |
| Industrial IoT | ★★★ | 中級-上級 | 高可用性、データ分析、監視 |
| Fleet Management | ★★★ | 中級-上級 | リアルタイム位置情報、スケール |
| Smart Agriculture | ★★☆ | 初級-中級 | センサー統合、自動制御 |
| Energy Management | ★★★ | 中級-上級 | 時系列データ、予測分析 |

## 🔧 共通セットアップ

### 前提条件
- Docker & Docker Compose
- Node.js 18+ または Python 3.9+
- Git

### MQTT ブローカーの起動
```bash
# EMQX (推奨 - 管理画面付き)
docker run -d --name emqx \
  -p 1883:1883 \
  -p 8083:8083 \
  -p 8084:8084 \
  -p 8883:8883 \
  -p 18083:18083 \
  emqx/emqx:latest

# Mosquitto (軽量)
docker run -d --name mosquitto \
  -p 1883:1883 \
  -p 9001:9001 \
  eclipse-mosquitto:2.0
```

### 管理ツールの起動
```bash
# MQTT Explorer (GUI クライアント)
# http://mqtt-explorer.com/ からダウンロード

# または、Node-RED (ビジュアルプログラミング)
docker run -it -p 1880:1880 --name nodered nodered/node-red
```

## 📖 使用方法

### 1. サンプルの選択
興味のあるサンプルディレクトリに移動：
```bash
cd smart-home-system
```

### 2. セットアップと実行
各サンプルには詳細な README.md があります：
```bash
# 依存関係のインストール
npm install
# または
pip install -r requirements.txt

# アプリケーションの起動
npm start
# または  
python app.py
```

### 3. 動作確認
- ブラウザでダッシュボードにアクセス
- MQTTメッセージの送受信を確認
- 各機能をテスト

## 🎯 学習の進め方

### 初心者の方
1. **Smart Home System** から開始
2. 基本的なPub/Subパターンを理解
3. Webダッシュボードとの統合を学習

### 中級者の方
1. **Smart Agriculture** で制御システムを学習
2. **Fleet Management** でスケーラビリティを理解
3. 独自の改良を加えてみる

### 上級者の方
1. **Industrial IoT Monitor** で高可用性を学習
2. **Energy Management** で分析機能を理解
3. 本格的なプロダクション環境を構築

## 🔍 コード解説

各サンプルには以下の解説が含まれています：

### アーキテクチャ図
システム全体の構成と各コンポーネントの関係

### 重要なコード部分
```javascript
// 例：デバイス認証の実装
const authenticateDevice = (clientId, username, password) => {
    // デバイス認証ロジック
    return deviceRegistry.validate(clientId, username, password);
};
```

### デプロイメント手順
本番環境へのデプロイ方法と注意事項

### 運用のベストプラクティス
監視、ログ、バックアップなどの実運用ノウハウ

## 🛠 カスタマイズガイド

### 設定の変更
```javascript
// config/default.js
module.exports = {
    mqtt: {
        broker: 'mqtt://localhost:1883',
        options: {
            keepalive: 60,
            reschedulePings: false,
            protocolId: 'MQIsdp',
            protocolVersion: 3,
            reconnectPeriod: 1000
        }
    },
    database: {
        url: 'mongodb://localhost:27017/iot_system'
    }
};
```

### 新しいデバイスタイプの追加
```javascript
// devices/custom-sensor.js
class CustomSensor extends BaseDevice {
    constructor(config) {
        super(config);
        this.sensorType = 'custom';
    }
    
    generateData() {
        return {
            customValue: Math.random() * 100,
            timestamp: new Date().toISOString()
        };
    }
}
```

## 📊 パフォーマンス指標

各サンプルには以下のパフォーマンス指標が含まれています：

- **スループット**: 秒間メッセージ処理数
- **レイテンシ**: エンドツーエンド遅延
- **リソース使用量**: CPU、メモリ、ディスク
- **可用性**: アップタイム、エラー率

## 🔒 セキュリティ考慮事項

### 認証・認可
- JWT トークン認証
- デバイス証明書管理  
- ロールベースアクセス制御

### 通信セキュリティ
- TLS/SSL 暗号化
- ペイロード暗号化
- 侵入検知

### データ保護
- 個人情報の匿名化
- データ暗号化
- バックアップ暗号化

## 🌐 本番環境デプロイ

### クラウドデプロイ
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  mqtt-app:
    image: my-iot-app:latest
    environment:
      - NODE_ENV=production
      - MQTT_BROKER=ssl://production-broker:8883
    deploy:
      replicas: 3
      resources:
        limits:
          cpus: '0.5'
          memory: 512M
```

### モニタリング
- Prometheus + Grafana
- ELK Stack
- Jaeger (分散トレーシング)

### CI/CD パイプライン
```yaml
# .github/workflows/deploy.yml
name: Deploy IoT Application
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run tests
        run: npm test
      - name: Deploy
        run: ./deploy.sh
```

## 📚 参考資料

### ドキュメント
- [MQTT 5.0 Specification](https://docs.oasis-open.org/mqtt/mqtt/v5.0/)
- [Node.js MQTT Client](https://github.com/mqttjs/MQTT.js)
- [Python Paho MQTT](https://www.eclipse.org/paho/clients/python/)

### ツール・ライブラリ
- [MQTT Explorer](http://mqtt-explorer.com/)
- [Node-RED](https://nodered.org/)
- [Grafana](https://grafana.com/)

### コミュニティ
- [MQTT.org Community](https://mqtt.org/community)
- [Eclipse IoT](https://iot.eclipse.org/)
- [Stack Overflow - MQTT](https://stackoverflow.com/questions/tagged/mqtt)

---

**始める準備はできましたか？** 興味のあるサンプルを選んで、実際のIoTアプリケーション開発を体験してください！