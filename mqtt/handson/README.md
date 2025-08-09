# MQTTハンズオン学習プログラム

このディレクトリには、MQTTを実践的に学習するための段階的なハンズオン教材が含まれています。合計約10時間のコンテンツで、基礎から実用的なアプリケーション構築まで体験できます。

## 学習の進め方

### 前提条件
- Node.js (v18以降) または Python (3.8以降)
- 基本的なプログラミング知識
- コマンドライン操作の基本知識

### 推奨学習順序

#### **Phase 1: 基礎編** (約2-3時間)
1. [01-setup-and-basic-connection](01-setup-and-basic-connection/) - 環境セットアップと基本接続
2. [02-publish-subscribe](02-publish-subscribe/) - Pub/Subの基本
3. [03-qos-and-reliability](03-qos-and-reliability/) - QoSレベルと信頼性

#### **Phase 2: 実装編** (約3-4時間)
4. [04-topic-design-patterns](04-topic-design-patterns/) - トピック設計パターン
5. [05-security-implementation](05-security-implementation/) - セキュリティ実装
6. [06-error-handling-reconnection](06-error-handling-reconnection/) - エラーハンドリングと再接続

#### **Phase 3: 発展編** (約2-3時間)
7. [07-mqtt5-advanced-features](07-mqtt5-advanced-features/) - MQTT 5.0の新機能
8. [08-cloud-integration](08-cloud-integration/) - クラウドサービス統合

#### **Phase 4: 実践編** (約2-3時間)
9. [09-iot-device-simulation](09-iot-device-simulation/) - IoTデバイスシミュレーション
10. [10-monitoring-dashboard](10-monitoring-dashboard/) - 監視ダッシュボード構築

## 各チュートリアルの構成

各ハンズオンディレクトリには以下のファイルが含まれています：

- `README.md` - 学習目標、手順、解説
- `src/` - 実装コード（段階的に完成）
- `exercises/` - 練習問題
- `solutions/` - 解答例
- `resources/` - 設定ファイルや参考資料

## 開発環境のセットアップ

### Node.js環境
```bash
# Node.js版のセットアップ
cd mqtt/handson
npm install

# 共通ライブラリのインストール
npm install mqtt ws express socket.io
```

### Python環境
```bash
# Python環境のセットアップ
cd mqtt/handson
python -m venv mqtt-env
source mqtt-env/bin/activate  # Linux/Mac
# mqtt-env\Scripts\activate  # Windows

pip install -r requirements.txt
```

### Docker環境（オプション）
```bash
# Mosquittoブローカーの起動
docker run -it -p 1883:1883 -p 9001:9001 eclipse-mosquitto:2.0

# EMQX ダッシュボード付きブローカー
docker run -d --name emqx -p 1883:1883 -p 8083:8083 -p 8084:8084 -p 8883:8883 -p 18083:18083 emqx/emqx:latest
```

## 学習のコツ

### 1. 段階的に進める
各ハンズオンは前の章で学習した内容を前提としています。順番に進めることを強く推奨します。

### 2. 実際に手を動かす
サンプルコードをそのまま動かすだけでなく、パラメータを変更したり、独自の改良を加えてみてください。

### 3. エラーを恐れない
意図的にエラーを発生させて、その解決方法を学ぶことも重要です。

### 4. ログを確認する
各実装では詳細なログ出力を行っています。ログから何が起こっているかを理解してください。

### 5. 練習問題に取り組む
各章の練習問題は理解度を確認するために設計されています。必ず取り組んでください。

## 使用するツール

### MQTTブローカー
- **Eclipse Mosquitto** - 軽量で学習に最適
- **EMQX** - 管理画面付きで可視化しやすい
- **HiveMQ Cloud** - クラウド統合の学習用

### 開発ツール
- **MQTT Explorer** - GUIでのMQTTメッセージ確認
- **mosquitto_pub/sub** - コマンドラインツール
- **Postman** - WebSocket over MQTTの테スト

### 監視ツール
- **Node-RED** - ビジュアルプログラミング
- **Grafana** - メトリクス可視化
- **Prometheus** - メトリクス収集

## トラブルシューティング

### よくある問題

#### 接続できない
- ブローカーが起動しているか確認
- ポート番号（1883, 8883）が正しいか確認
- ファイアウォールの設定を確認

#### メッセージが届かない
- トピック名が正確か確認
- QoSレベルが適切か確認
- サブスクリプションが正しく設定されているか確認

#### パフォーマンスが悪い
- ブローカーのリソース使用状況を確認
- ネットワーク遅延を確認
- メッセージサイズを確認

### サポートリソース

- **公式ドキュメント**: 各ハンズオンのREADMEに関連リンクを記載
- **コミュニティ**: MQTT.org、Stack Overflow、GitHub Issues
- **書籍**: 「MQTT Essentials」シリーズの参考書

## 評価とフィードバック

### 学習の進捗確認
各ハンズオン完了後に以下を自己評価してください：

- [ ] 基本概念を理解できた
- [ ] コードを実装・実行できた
- [ ] 練習問題を解けた
- [ ] 応用的な改良を加えられた

### 次のステップ
全てのハンズオンを完了した後は：

1. **実際のプロジェクト適用** - 学習内容を実際のプロジェクトに適用
2. **深い理解** - 公式仕様書の詳細な読み込み
3. **コミュニティ参加** - オープンソースプロジェクトへの貢献
4. **知識の共有** - ブログ記事や発表での知識共有

---

**準備ができたら**: [01-setup-and-basic-connection](01-setup-and-basic-connection/) から始めましょう！