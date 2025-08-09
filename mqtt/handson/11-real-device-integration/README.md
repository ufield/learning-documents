# 11. 実デバイス連携とIoTシステム構築

## 概要

このハンズオンでは、実際のデバイス（Raspberry Pi、NVIDIA Jetson、Arduino ESP32など）を使用してMQTTベースのIoTシステムを構築します。センサーデータの収集、リアルタイム監視、エッジAI処理、デバイス制御まで、実用的なIoTアプリケーションを体験できます。

## 学習目標

- 実デバイスでのMQTT接続とデータ送信
- エッジデバイスでのセンサーデータ処理
- クラウドとエッジの連携アーキテクチャ
- デバイス管理とOTA更新
- リアルタイム監視ダッシュボード構築
- エッジAI推論とMQTT連携

## 対象デバイス

### 1. NVIDIA Jetson シリーズ
- Jetson Nano, Xavier NX, Orin Nano
- GPU活用したエッジAI処理
- カメラ・センサー統合

### 2. Raspberry Pi
- Pi 4, Pi Zero 2W
- GPIO制御とセンサー接続
- コスト効率の良いIoTノード

### 3. ESP32/Arduino
- WiFi内蔵マイクロコントローラー
- 低消費電力センサーノード
- リアルタイムデータ収集

## 前提知識

- Python プログラミング基礎
- Linux コマンドライン操作
- 電子工学基礎（センサー、GPIO）
- MQTT プロトコル理解（ハンズオン1-3完了）

## 必要な機材

### 基本セット
- 開発用PC（Windows/Mac/Linux）
- WiFiルーター（2.4GHz/5GHz対応）
- microSDカード（32GB以上、Class 10）

### デバイス別機材
詳細は各演習のREADMEを参照

## 演習構成

```
11-real-device-integration/
├── 01-jetson-setup/              # Jetson初期設定とMQTT
├── 02-raspberry-pi-sensors/      # Pi + センサーデータ収集
├── 03-esp32-wireless-nodes/      # ESP32無線センサーノード
├── 04-edge-ai-integration/       # エッジAI + MQTT
├── 05-multi-device-system/       # 複数デバイス連携システム
├── 06-device-management/         # デバイス管理・OTA更新
├── 07-real-time-dashboard/       # リアルタイム監視
├── 08-industrial-use-case/       # 産業用途事例
├── resources/                    # 共通リソース
└── solutions/                    # 完成コード
```

## クイックスタート

1. **環境準備**
```bash
# 共通依存関係インストール
pip install -r requirements.txt

# ブローカー起動（ローカル開発用）
docker run -it -p 1883:1883 eclipse-mosquitto
```

2. **デバイス選択**
使用するデバイスに応じて該当の演習フォルダに移動

3. **段階的学習**
演習01から順番に進行することを推奨

## 学習パス

### 初心者向け（2-3日）
- 01: Jetson基本セットアップ
- 02: センサーデータ収集
- 07: 基本ダッシュボード

### 中級者向け（1週間）
- 全演習を順番に実施
- カスタマイズと拡張

### 上級者向け（2週間）
- 産業用途での実装
- スケーラブルアーキテクチャ
- セキュリティ強化

## トラブルシューティング

よくある問題と解決方法は各演習のREADMEおよび`resources/troubleshooting.md`を参照してください。

## コミュニティ

- GitHub Issues: 質問・バグ報告
- 実装例の共有歓迎
- 産業用途での活用事例募集

---

**次のステップ**: [01-jetson-setup](./01-jetson-setup/README.md)でJetson Nanoの初期設定から始めましょう。