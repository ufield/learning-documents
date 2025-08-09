# MQTT学習プロジェクト

## 📖 概要

このプロジェクトは、MQTT（Message Queuing Telemetry Transport）プロトコルを包括的に学習するための教育リソースです。IoT開発者、システムアーキテクト、エンジニアがMQTTの基礎から実践的な応用まで段階的に習得できるよう設計されています。

**言語**: Python (主要), JavaScript (参考)  
**対象レベル**: 初級〜上級  
**推定学習時間**: 総合約20時間（docs: 5時間、handson: 15時間）

## 🌟 2025年版の特徴

### Python中心の実装
- **主要言語をPythonに変更**: より学習しやすく、IoT開発に適したPython実装
- **豊富なライブラリ活用**: paho-mqtt, rich, pandas, FastAPI等を使用
- **実践的なサンプル**: 実際のIoTプロジェクトで使える完全なPythonコード

### 最新技術への対応
- **MQTT 5.0対応**: 最新のMQTT仕様に準拠
- **クラウド統合**: AWS IoT Core, Azure IoT Hub との連携
- **セキュリティ強化**: TLS/SSL、認証、認可の実装
- **産業用IoT**: Manufacturing 4.0 に対応した監視システム

### 包括的な学習コンテンツ
- **理論と実践の両立**: 概念理解から実装まで一貫したカリキュラム  
- **段階的な難易度**: 基礎から高度な応用まで無理なくステップアップ
- **リアルタイム監視**: Rich libraryを使った美しいコンソール表示

## 📚 コンテンツ構成

### 📖 ドキュメント (docs/) - 約5時間
理論的な基礎から実践的な応用まで、MQTTの全体像を網羅：

1. **[01-introduction.md](docs/01-introduction.md)** - MQTT入門とIoTエコシステム
2. **[02-concepts.md](docs/02-concepts.md)** - Pub/Subパターンとコアコンセプト  
3. **[03-protocol-basics.md](docs/03-protocol-basics.md)** - プロトコル詳細とメッセージ構造
4. **[04-brokers-and-clients.md](docs/04-brokers-and-clients.md)** - ブローカー選択とクライアント実装
5. **[05-qos-and-reliability.md](docs/05-qos-and-reliability.md)** - QoSとメッセージ信頼性
6. **[06-security.md](docs/06-security.md)** - セキュリティとベストプラクティス
7. **[07-mqtt5-features.md](docs/07-mqtt5-features.md)** - MQTT 5.0の新機能
8. **[08-cloud-integration.md](docs/08-cloud-integration.md)** - クラウドプラットフォーム統合  
9. **[09-file-transfer.md](docs/09-file-transfer.md)** - IoTデバイス向けファイル転送
10. **[10-monitoring-and-troubleshooting.md](docs/10-monitoring-and-troubleshooting.md)** - 運用監視とトラブルシューティング

### 🛠 ハンズオン (handson/) - 約15時間
実際にコードを書きながら学ぶ実践的な演習：

1. **[01-setup-and-basic-connection](handson/01-setup-and-basic-connection/)** - 環境構築と基本接続 (90分)
2. **[02-publish-subscribe](handson/02-publish-subscribe/)** - Pub/Subの基本実装 (120分)  
3. **[03-qos-and-reliability](handson/03-qos-and-reliability/)** - QoSと信頼性の実装 (90分)
4. **[04-security-and-authentication](handson/04-security-and-authentication/)** - セキュリティと認証 (120分)
5. **[09-iot-device-simulation](handson/09-iot-device-simulation/)** - IoTデバイスシミュレーション (90分)

### 💼 実用サンプル (examples/) - 参考実装
実際のプロジェクトで活用できる完全なシステム：

- **[smart-home-system](examples/smart-home-system/)** - スマートホーム制御システム
- **[industrial-iot-monitor](examples/industrial-iot-monitor/)** - 産業用IoT監視システム
- その他の実践的なサンプル

## 🚀 クイックスタート

### 1. 環境準備

```bash
# Python 3.9+ が必要
python --version

# プロジェクトをクローン
git clone <repository-url>
cd mqtt

# 依存関係をインストール
pip install -r requirements.txt
```

### 2. MQTTブローカーの起動

```bash
# Docker使用（推奨）
docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto:2.0

# または Homebrew (macOS)
brew install mosquitto
mosquitto -c /usr/local/etc/mosquitto/mosquitto.conf
```

### 3. 最初のハンズオンを実行

```bash
cd handson/01-setup-and-basic-connection/src
python basic_connection.py
```

## 🎯 学習パス

### 🔰 初心者向け (5-8時間)
1. docs/01-introduction.md → 02-concepts.md を読む
2. handson/01-setup-and-basic-connection を実行
3. handson/02-publish-subscribe を実行  
4. examples/smart-home-system を参照

### 🎓 中級者向け (8-12時間)
1. 上記に加えて docs/03-protocol-basics.md → 05-qos-and-reliability.md
2. handson/03-qos-and-reliability を実行
3. handson/04-security-and-authentication を実行
4. examples/industrial-iot-monitor を参照

### 🏆 上級者向け (12-20時間)  
1. 全ドキュメントを読破
2. 全ハンズオンを完了
3. 独自のIoTシステムを設計・実装
4. 本格的なプロダクション環境を構築

## 🛠 技術スタック

### コア技術
- **Python 3.9+** - メイン実装言語
- **paho-mqtt** - 公式PythonMQTTクライアント  
- **Rich** - 美しいコンソール表示
- **FastAPI** - 高性能Webフレームワーク

### データ処理・分析  
- **pandas, numpy** - データ分析
- **matplotlib, plotly** - データ可視化
- **scikit-learn** - 機械学習（予知保全用）

### インフラ・デプロイ
- **Docker** - コンテナ化
- **SQLite/PostgreSQL** - データ永続化
- **Redis** - キャッシュ・セッション管理  

### クラウド統合
- **AWS IoT Core** - AWS統合  
- **Azure IoT Hub** - Azure統合
- **InfluxDB** - 時系列データベース

## 📊 プロジェクト統計

```
📁 プロジェクト規模
├── 📚 ドキュメント: 10章 (約50,000文字)
├── 🛠 ハンズオン: 5つ (段階的難易度)  
├── 💼 サンプル: 3つ以上 (実用的システム)
├── 🐍 Pythonコード: 5,000行以上
└── 📦 依存関係: 50+パッケージ (厳選)
```

## 🤝 貢献・フィードバック

### 貢献歓迎
- バグ報告・修正
- 新しいサンプル追加
- ドキュメント改善
- 多言語対応

### フィードバック方法  
- GitHub Issues
- Pull Requests
- ディスカッション

## 📝 ライセンス

このプロジェクトはMITライセンスの下で公開されています。教育目的での自由な利用、改変、再配布が可能です。

## 🌐 関連リンク

- [MQTT.org](https://mqtt.org/) - 公式サイト
- [Eclipse Paho](https://www.eclipse.org/paho/) - MQTTクライアントライブラリ
- [HiveMQ](https://www.hivemq.com/) - MQTTブローカー・情報サイト
- [AWS IoT Core](https://aws.amazon.com/iot-core/) - AWSのMQTTサービス  

---

**🎓 Python中心のMQTT学習で、次世代IoTエンジニアを目指しましょう！**

*最終更新: 2025年1月*