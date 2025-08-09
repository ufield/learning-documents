# ハンズオン 04: トピック設計パターン

## 🎯 学習目標

このハンズオンでは効果的なMQTTトピック設計について学習します：

- トピック階層の設計原則とベストプラクティス
- スケーラブルなトピック構造の実装
- 複雑なIoTシステムでのトピック管理
- パフォーマンスとメンテナンス性を考慮した設計
- 実際のユースケース別トピック設計パターン

**所要時間**: 約75分

## 📋 前提条件

- [01-setup-and-basic-connection](../01-setup-and-basic-connection/) の完了
- [02-publish-subscribe](../02-publish-subscribe/) の完了
- トピックとワイルドカードの基本理解

## 🏗 トピック設計の基本原則

### 1. 階層構造の重要性

良いトピック設計は以下の要素を考慮します：

```
適切なトピック例:
✅ sensors/building1/floor2/room201/temperature
✅ devices/gateway/gw001/status
✅ alerts/critical/fire/building1

避けるべきトピック例:
❌ temperature_building1_floor2_room201
❌ sensor-data-temp-humidity-pressure
❌ device_status_gateway_001
```

### 2. 設計原則

- **階層性**: トピックは論理的な階層構造を持つ
- **一貫性**: 全体を通して統一された命名規則
- **拡張性**: 将来的な拡張を考慮した設計
- **可読性**: 人間が理解しやすい構造
- **効率性**: ワイルドカードでの購読が効率的

## 📝 実装演習

### Exercise 1: 基本的なトピック設計パターン

`src/topic_patterns.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
import random
from datetime import datetime
from typing import Dict, List, Any, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from dataclasses import dataclass

console = Console()

@dataclass
class TopicPattern:
    """トピックパターンの定義"""
    name: str
    pattern: str
    description: str
    example: str
    use_case: str

class TopicDesignPatterns:
    """MQTTトピック設計パターンの実装とテスト"""
    
    def __init__(self):
        self.client = mqtt.Client(client_id="topic-pattern-tester")
        self.received_messages = []
        self.setup_mqtt_handlers()
        
        # 基本的な設計パターン
        self.patterns = [
            TopicPattern(
                name="階層型センサーデータ",
                pattern="sensors/{building}/{floor}/{room}/{sensor_type}",
                description="物理的階層を反映した構造",
                example="sensors/building1/floor2/room201/temperature",
                use_case="ビル管理システム、スマートオフィス"
            ),
            TopicPattern(
                name="デバイス中心型",
                pattern="devices/{device_type}/{device_id}/{data_type}",
                description="デバイス単位でのデータ管理",
                example="devices/gateway/gw001/status",
                use_case="IoTデバイス管理、M2M通信"
            ),
            TopicPattern(
                name="機能中心型",
                pattern="{function}/{category}/{subcategory}/{identifier}",
                description="機能やサービス別の分類",
                example="alerts/critical/fire/detector001",
                use_case="アラートシステム、通知サービス"
            ),
            TopicPattern(
                name="時系列データ型",
                pattern="timeseries/{metric}/{location}/{timestamp_bucket}",
                description="時系列データの効率的な管理",
                example="timeseries/temperature/zone1/2024-01-15T10",
                use_case="データ分析、監視システム"
            ),
            TopicPattern(
                name="コマンド・レスポンス型",
                pattern="{direction}/{device_id}/{command_type}/{session_id}",
                description="双方向通信のための構造",
                example="commands/device001/reboot/session123",
                use_case="リモート制御、デバイス管理"
            )
        ]
    
    def setup_mqtt_handlers(self):
        """MQTTイベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print("✅ トピックパターンテスターが接続されました", style="green")
        else:
            console.print(f"❌ 接続失敗: {rc}", style="red")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        message_info = {
            'topic': msg.topic,
            'payload': msg.payload.decode('utf-8'),
            'timestamp': datetime.now().isoformat(),
            'qos': msg.qos,
            'retain': msg.retain
        }
        self.received_messages.append(message_info)
        
        console.print(f"📨 受信: {msg.topic} -> {msg.payload.decode('utf-8')[:50]}...", style="dim")
    
    def connect(self) -> bool:
        """MQTTブローカーに接続"""
        try:
            self.client.connect('localhost', 1883, 60)
            self.client.loop_start()
            time.sleep(1)
            return True
        except Exception as e:
            console.print(f"❌ 接続エラー: {e}", style="red")
            return False
    
    def demonstrate_patterns(self):
        """トピックパターンのデモンストレーション"""
        console.print("\n🏗 MQTTトピック設計パターンのデモンストレーション", style="bold blue")
        
        for i, pattern in enumerate(self.patterns, 1):
            console.print(f"\n📋 パターン {i}: {pattern.name}", style="bold cyan")
            console.print(f"   構造: {pattern.pattern}")
            console.print(f"   説明: {pattern.description}")
            console.print(f"   例: {pattern.example}")
            console.print(f"   用途: {pattern.use_case}")
            
            # パターンに基づくテストデータの生成と送信
            test_topics = self.generate_test_topics(pattern)
            self.publish_test_data(test_topics, pattern.name)
            
            time.sleep(2)
    
    def generate_test_topics(self, pattern: TopicPattern) -> List[str]:
        """パターンに基づくテストトピックの生成"""
        topics = []
        
        if pattern.name == "階層型センサーデータ":
            buildings = ['building1', 'building2']
            floors = ['floor1', 'floor2', 'floor3']
            rooms = ['room101', 'room102', 'room201', 'room202']
            sensors = ['temperature', 'humidity', 'pressure', 'light']
            
            for building in buildings:
                for floor in floors[:2]:  # 最初の2階層のみ
                    for room in rooms[:2]:  # 最初の2部屋のみ
                        for sensor in sensors[:2]:  # 最初の2センサーのみ
                            topic = f"sensors/{building}/{floor}/{room}/{sensor}"
                            topics.append(topic)
        
        elif pattern.name == "デバイス中心型":
            device_types = ['gateway', 'sensor', 'actuator']
            device_ids = ['dev001', 'dev002', 'dev003']
            data_types = ['status', 'data', 'config', 'error']
            
            for dev_type in device_types:
                for dev_id in device_ids:
                    for data_type in data_types[:2]:  # 最初の2つのみ
                        topic = f"devices/{dev_type}/{dev_id}/{data_type}"
                        topics.append(topic)
        
        elif pattern.name == "機能中心型":
            functions = ['alerts', 'commands', 'responses']
            categories = ['critical', 'warning', 'info']
            subcategories = ['fire', 'security', 'system']
            identifiers = ['detector001', 'cam001', 'server001']
            
            for func in functions:
                for cat in categories[:2]:
                    for subcat in subcategories[:2]:
                        for ident in identifiers[:2]:
                            topic = f"{func}/{cat}/{subcat}/{ident}"
                            topics.append(topic)
        
        elif pattern.name == "時系列データ型":
            metrics = ['temperature', 'humidity', 'pressure']
            locations = ['zone1', 'zone2', 'zone3']
            # 現在時刻から時間バケットを生成
            current_hour = datetime.now().strftime("%Y-%m-%dT%H")
            
            for metric in metrics:
                for location in locations[:2]:
                    topic = f"timeseries/{metric}/{location}/{current_hour}"
                    topics.append(topic)
        
        elif pattern.name == "コマンド・レスポンス型":
            directions = ['commands', 'responses']
            device_ids = ['device001', 'device002']
            command_types = ['reboot', 'config', 'status']
            
            for direction in directions:
                for dev_id in device_ids:
                    for cmd_type in command_types[:2]:
                        session_id = f"session{random.randint(100, 999)}"
                        topic = f"{direction}/{dev_id}/{cmd_type}/{session_id}"
                        topics.append(topic)
        
        return topics[:8]  # 最大8トピックに制限
    
    def publish_test_data(self, topics: List[str], pattern_name: str):
        """テストデータの送信"""
        console.print(f"   📤 {len(topics)}個のテストトピックにデータを送信中...", style="yellow")
        
        for topic in topics:
            # トピックに応じた適切なテストデータを生成
            test_data = self.generate_test_payload(topic, pattern_name)
            
            try:
                self.client.publish(topic, json.dumps(test_data), qos=1)
                console.print(f"     → {topic}", style="dim")
            except Exception as e:
                console.print(f"     ❌ 送信失敗: {topic} - {e}", style="red")
        
        time.sleep(1)
    
    def generate_test_payload(self, topic: str, pattern_name: str) -> Dict[str, Any]:
        """トピックに応じたテストペイロードの生成"""
        base_payload = {
            'timestamp': datetime.now().isoformat(),
            'topic': topic,
            'pattern': pattern_name
        }
        
        # トピックの種類に応じて専用データを追加
        if 'temperature' in topic:
            base_payload.update({
                'value': round(20 + random.random() * 15, 2),
                'unit': '°C'
            })
        elif 'humidity' in topic:
            base_payload.update({
                'value': round(40 + random.random() * 40, 2),
                'unit': '%'
            })
        elif 'pressure' in topic:
            base_payload.update({
                'value': round(1000 + random.random() * 50, 2),
                'unit': 'hPa'
            })
        elif 'status' in topic:
            base_payload.update({
                'status': random.choice(['online', 'offline', 'maintenance']),
                'battery': round(random.random() * 100, 1)
            })
        elif 'alerts' in topic:
            base_payload.update({
                'severity': random.choice(['low', 'medium', 'high', 'critical']),
                'message': 'Test alert message',
                'acknowledged': False
            })
        elif 'commands' in topic:
            base_payload.update({
                'command': 'test_command',
                'parameters': {'param1': 'value1'},
                'timeout': 30
            })
        else:
            base_payload.update({
                'data': f'test_data_{random.randint(1, 1000)}'
            })
        
        return base_payload
    
    def test_subscription_patterns(self):
        """購読パターンのテスト"""
        console.print("\n🔍 購読パターンのテスト", style="bold blue")
        
        subscription_tests = [
            {
                'name': '特定建物の全センサー',
                'pattern': 'sensors/building1/+/+/+',
                'description': 'building1の全フロア・全部屋の全センサー'
            },
            {
                'name': '全建物の温度センサー',
                'pattern': 'sensors/+/+/+/temperature',
                'description': 'すべての建物の温度センサーのみ'
            },
            {
                'name': 'デバイス状態監視',
                'pattern': 'devices/+/+/status',
                'description': 'すべてのデバイスの状態情報'
            },
            {
                'name': 'クリティカルアラート',
                'pattern': 'alerts/critical/+/+',
                'description': '重要度がクリティカルなすべてのアラート'
            },
            {
                'name': '双方向通信の応答',
                'pattern': 'responses/+/+/+',
                'description': 'すべてのデバイスからの応答'
            }
        ]
        
        for test in subscription_tests:
            console.print(f"\n📡 テスト: {test['name']}", style="cyan")
            console.print(f"   パターン: {test['pattern']}")
            console.print(f"   説明: {test['description']}")
            
            # 購読開始前にメッセージリストをクリア
            self.received_messages.clear()
            
            # パターンを購読
            self.client.subscribe(test['pattern'], qos=1)
            console.print("   購読開始...")
            
            # 少し待機してメッセージを受信
            time.sleep(3)
            
            # 受信したメッセージを集計
            matching_messages = [msg for msg in self.received_messages 
                               if self.topic_matches_pattern(msg['topic'], test['pattern'])]
            
            console.print(f"   📊 マッチしたメッセージ数: {len(matching_messages)}")
            
            if matching_messages:
                console.print("   受信したトピック:")
                unique_topics = set(msg['topic'] for msg in matching_messages)
                for topic in sorted(unique_topics)[:5]:  # 最大5つまで表示
                    console.print(f"     • {topic}", style="dim")
                if len(unique_topics) > 5:
                    console.print(f"     ... 他 {len(unique_topics)-5}件", style="dim")
            
            # 購読解除
            self.client.unsubscribe(test['pattern'])
            time.sleep(1)
    
    def topic_matches_pattern(self, topic: str, pattern: str) -> bool:
        """トピックがパターンにマッチするかチェック"""
        topic_parts = topic.split('/')
        pattern_parts = pattern.split('/')
        
        if len(topic_parts) != len(pattern_parts):
            return False
        
        for i, (topic_part, pattern_part) in enumerate(zip(topic_parts, pattern_parts)):
            if pattern_part != '+' and pattern_part != topic_part:
                return False
        
        return True
    
    def analyze_topic_efficiency(self):
        """トピック効率性の分析"""
        console.print("\n📈 トピック効率性分析", style="bold blue")
        
        # 受信メッセージの統計
        if not self.received_messages:
            console.print("分析用のメッセージが不足しています", style="yellow")
            return
        
        # トピック別メッセージ数
        topic_counts = {}
        for msg in self.received_messages:
            topic = msg['topic']
            topic_counts[topic] = topic_counts.get(topic, 0) + 1
        
        # 階層レベル別の分析
        level_stats = {}
        for topic in topic_counts.keys():
            levels = len(topic.split('/'))
            if levels not in level_stats:
                level_stats[levels] = {'count': 0, 'topics': []}
            level_stats[levels]['count'] += 1
            level_stats[levels]['topics'].append(topic)
        
        # 結果表示
        table = Table(title="トピック効率性分析結果")
        table.add_column("階層レベル", style="cyan", no_wrap=True)
        table.add_column("トピック数", style="magenta")
        table.add_column("メッセージ数", style="green")
        table.add_column("平均効率", style="yellow")
        
        for level, stats in sorted(level_stats.items()):
            total_messages = sum(topic_counts.get(topic, 0) for topic in stats['topics'])
            efficiency = total_messages / stats['count'] if stats['count'] > 0 else 0
            
            table.add_row(
                str(level),
                str(stats['count']),
                str(total_messages),
                f"{efficiency:.1f}"
            )
        
        console.print(table)
        
        # 推奨事項
        recommendations = []
        
        if any(level > 6 for level in level_stats.keys()):
            recommendations.append("⚠️ 6階層を超えるトピックは複雑すぎる可能性があります")
        
        if any(level < 3 for level in level_stats.keys()):
            recommendations.append("💡 3階層未満のトピックは分類が不十分な可能性があります")
        
        avg_efficiency = sum(stats['count'] for stats in level_stats.values()) / len(level_stats) if level_stats else 0
        if avg_efficiency < 2:
            recommendations.append("📊 トピックあたりのメッセージ数が少なく、非効率な可能性があります")
        
        if recommendations:
            console.print("\n🔧 改善提案:", style="bold yellow")
            for rec in recommendations:
                console.print(f"  {rec}")
    
    def show_best_practices(self):
        """ベストプラクティスの表示"""
        console.print("\n✨ トピック設計のベストプラクティス", style="bold green")
        
        practices = [
            {
                'title': '階層設計の原則',
                'points': [
                    '論理的な階層構造を維持する',
                    '3-6階層程度に収める',
                    '一貫した命名規則を使用する',
                    '将来の拡張を考慮する'
                ]
            },
            {
                'title': 'パフォーマンス最適化',
                'points': [
                    'ワイルドカード購読を効率的に設計する',
                    '不要な階層を避ける',
                    'メッセージサイズを考慮する',
                    'QoSレベルを適切に設定する'
                ]
            },
            {
                'title': 'セキュリティ考慮事項',
                'points': [
                    'センシティブなデータは適切に分離する',
                    'アクセス制御を考慮したトピック設計',
                    '権限レベル別のトピック分類',
                    'デバッグ情報の適切な配置'
                ]
            },
            {
                'title': 'メンテナンス性',
                'points': [
                    '意味のある名前を使用する',
                    'ドキュメント化を前提とした設計',
                    'バージョニング戦略を考慮する',
                    '廃止予定トピックの管理方法'
                ]
            }
        ]
        
        for practice in practices:
            console.print(f"\n📋 {practice['title']}:", style="bold cyan")
            for point in practice['points']:
                console.print(f"   • {point}")
    
    def disconnect(self):
        """MQTTブローカーから切断"""
        self.client.loop_stop()
        self.client.disconnect()
        console.print("👋 トピックパターンテスターが切断されました", style="yellow")

# 使用例とメイン実行部
def main():
    """メイン実行関数"""
    console.print("🏗 MQTT トピック設計パターン ハンズオン", style="bold blue")
    console.print("=" * 50)
    
    tester = TopicDesignPatterns()
    
    if not tester.connect():
        console.print("❌ MQTTブローカーへの接続に失敗しました", style="red")
        return
    
    try:
        # 各演習を順番に実行
        tester.demonstrate_patterns()
        time.sleep(2)
        
        tester.test_subscription_patterns() 
        time.sleep(2)
        
        tester.analyze_topic_efficiency()
        time.sleep(2)
        
        tester.show_best_practices()
        
        console.print("\n✅ トピック設計パターンのハンズオン完了！", style="bold green")
        
    except KeyboardInterrupt:
        console.print("\n⚠️ ユーザーによって中断されました", style="yellow")
    except Exception as e:
        console.print(f"\n❌ エラーが発生しました: {e}", style="red")
    finally:
        tester.disconnect()

if __name__ == "__main__":
    main()
```

### Exercise 2: 実世界のトピック設計

`src/real_world_topics.py` を作成：

```python
import paho.mqtt.client as mqtt
import json
import time
from datetime import datetime
from typing import Dict, List, Any
from rich.console import Console
from rich.tree import Tree
from rich.table import Table
from rich.panel import Panel

console = Console()

class RealWorldTopicDesigns:
    """実世界でのトピック設計例とシミュレーション"""
    
    def __init__(self):
        self.client = mqtt.Client(client_id="real-world-simulator")
        self.setup_mqtt_handlers()
        
        # 実世界のシナリオ定義
        self.scenarios = {
            'smart_building': self.smart_building_scenario,
            'manufacturing': self.manufacturing_scenario,
            'smart_city': self.smart_city_scenario,
            'healthcare': self.healthcare_scenario,
            'agriculture': self.agriculture_scenario
        }
    
    def setup_mqtt_handlers(self):
        """MQTTイベントハンドラーの設定"""
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
    
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            console.print("✅ 実世界シミュレーターが接続されました", style="green")
    
    def on_message(self, client, userdata, msg):
        """メッセージ受信時のコールバック"""
        console.print(f"📨 {msg.topic}: {msg.payload.decode('utf-8')[:100]}...", style="dim")
    
    def connect(self):
        """MQTTブローカーに接続"""
        try:
            self.client.connect('localhost', 1883, 60)
            self.client.loop_start()
            time.sleep(1)
            return True
        except Exception as e:
            console.print(f"❌ 接続エラー: {e}", style="red")
            return False
    
    def smart_building_scenario(self):
        """スマートビルディングシナリオ"""
        console.print("\n🏢 スマートビルディングシナリオ", style="bold cyan")
        
        # トピック構造の可視化
        tree = Tree("🏢 Smart Building Topics")
        
        # 環境センサー
        env_branch = tree.add("🌡 environment/")
        env_branch.add("building1/floor1/zone_a/temperature")
        env_branch.add("building1/floor1/zone_a/humidity") 
        env_branch.add("building1/floor2/zone_b/co2")
        env_branch.add("building2/floor1/lobby/air_quality")
        
        # HVAC システム
        hvac_branch = tree.add("❄️ hvac/")
        hvac_branch.add("building1/ahu001/status")
        hvac_branch.add("building1/ahu001/setpoint")
        hvac_branch.add("building1/vav_zone_a/damper_position")
        hvac_branch.add("building2/chiller001/power_consumption")
        
        # 照明システム
        lighting_branch = tree.add("💡 lighting/")
        lighting_branch.add("building1/floor1/zone_a/brightness")
        lighting_branch.add("building1/floor2/conference_room/occupancy")
        lighting_branch.add("building2/parking/motion_detected")
        
        # セキュリティ
        security_branch = tree.add("🔒 security/")
        security_branch.add("building1/entrance/card_reader/access_log")
        security_branch.add("building1/elevator/floor2/button_pressed")
        security_branch.add("building2/emergency/fire_alarm/status")
        
        # エネルギー管理
        energy_branch = tree.add("⚡ energy/")
        energy_branch.add("building1/main_panel/total_consumption")
        energy_branch.add("building1/solar_panel/generation")
        energy_branch.add("building2/ups/battery_level")
        
        console.print(tree)
        
        # サンプルデータの送信
        sample_data = [
            ("environment/building1/floor1/zone_a/temperature", {"value": 22.5, "unit": "°C"}),
            ("hvac/building1/ahu001/status", {"running": True, "fan_speed": 75}),
            ("lighting/building1/floor1/zone_a/brightness", {"level": 80, "auto": True}),
            ("security/building1/entrance/card_reader/access_log", {"user_id": "emp001", "granted": True}),
            ("energy/building1/main_panel/total_consumption", {"power_kw": 145.7, "cost_per_hour": 18.2})
        ]
        
        self.send_sample_data(sample_data, "スマートビル")
        
        return {
            'topic_count': 17,
            'max_depth': 5,
            'categories': ['environment', 'hvac', 'lighting', 'security', 'energy']
        }
    
    def manufacturing_scenario(self):
        """製造業シナリオ"""
        console.print("\n🏭 製造業シナリオ", style="bold cyan")
        
        tree = Tree("🏭 Manufacturing Topics")
        
        # 生産ライン
        production_branch = tree.add("🔧 production/")
        production_branch.add("line1/station_a/robot001/status")
        production_branch.add("line1/station_b/conveyor/speed")
        production_branch.add("line2/quality_check/vision_system/defect_rate")
        production_branch.add("line3/packaging/throughput")
        
        # 機械監視
        machines_branch = tree.add("⚙️ machines/")
        machines_branch.add("cnc001/spindle/temperature")
        machines_branch.add("cnc001/vibration/amplitude")
        machines_branch.add("press002/hydraulic/pressure")
        machines_branch.add("welder003/power_consumption")
        
        # 品質管理
        quality_branch = tree.add("📊 quality/")
        quality_branch.add("lab/batch_001/test_results")
        quality_branch.add("inspection/station1/pass_rate")
        quality_branch.add("calibration/scale001/drift")
        
        # 在庫管理
        inventory_branch = tree.add("📦 inventory/")
        inventory_branch.add("warehouse/raw_materials/steel/level")
        inventory_branch.add("warehouse/finished_goods/product_a/count")
        inventory_branch.add("supply_chain/supplier001/delivery_status")
        
        # メンテナンス
        maintenance_branch = tree.add("🔧 maintenance/")
        maintenance_branch.add("predictive/cnc001/remaining_life")
        maintenance_branch.add("scheduled/line1/next_service")
        maintenance_branch.add("alerts/critical/machine_failure")
        
        console.print(tree)
        
        sample_data = [
            ("production/line1/station_a/robot001/status", {"status": "running", "cycle_time": 45.2}),
            ("machines/cnc001/spindle/temperature", {"value": 68.5, "threshold": 80.0}),
            ("quality/inspection/station1/pass_rate", {"rate": 98.7, "target": 99.0}),
            ("inventory/warehouse/raw_materials/steel/level", {"current": 75.2, "unit": "tons"}),
            ("maintenance/alerts/critical/machine_failure", {"machine_id": "press002", "severity": "high"})
        ]
        
        self.send_sample_data(sample_data, "製造業")
        
        return {
            'topic_count': 19,
            'max_depth': 4,
            'categories': ['production', 'machines', 'quality', 'inventory', 'maintenance']
        }
    
    def smart_city_scenario(self):
        """スマートシティシナリオ"""
        console.print("\n🏙 スマートシティシナリオ", style="bold cyan")
        
        tree = Tree("🏙 Smart City Topics")
        
        # 交通管理
        traffic_branch = tree.add("🚗 traffic/")
        traffic_branch.add("intersections/main_st_1st/traffic_light/status")
        traffic_branch.add("intersections/main_st_1st/vehicle_count")
        traffic_branch.add("parking/downtown/garage_a/occupancy")
        traffic_branch.add("public_transport/bus_route_1/bus_001/location")
        
        # 環境監視
        env_branch = tree.add("🌱 environment/")
        env_branch.add("air_quality/downtown/pm25")
        env_branch.add("air_quality/industrial_zone/no2")
        env_branch.add("weather/city_center/temperature")
        env_branch.add("noise/residential_area/decibel_level")
        
        # エネルギー・ユーティリティ
        utilities_branch = tree.add("⚡ utilities/")
        utilities_branch.add("power_grid/district_1/load")
        utilities_branch.add("water/treatment_plant/flow_rate")
        utilities_branch.add("waste/collection/truck_001/route_progress")
        utilities_branch.add("street_lighting/main_st/brightness_control")
        
        # 安全・セキュリティ
        safety_branch = tree.add("🚨 safety/")
        safety_branch.add("emergency/fire_dept/response_time")
        safety_branch.add("surveillance/downtown/camera_001/motion")
        safety_branch.add("flood_monitoring/river_level/alert_status")
        
        console.print(tree)
        
        sample_data = [
            ("traffic/intersections/main_st_1st/vehicle_count", {"count": 47, "avg_speed": 25.3}),
            ("environment/air_quality/downtown/pm25", {"value": 32.1, "aqi": "moderate"}),
            ("utilities/power_grid/district_1/load", {"current_mw": 234.7, "capacity": 300.0}),
            ("safety/flood_monitoring/river_level/alert_status", {"level": 2.3, "threshold": 3.0})
        ]
        
        self.send_sample_data(sample_data, "スマートシティ")
        
        return {
            'topic_count': 16,
            'max_depth': 4,
            'categories': ['traffic', 'environment', 'utilities', 'safety']
        }
    
    def healthcare_scenario(self):
        """ヘルスケアシナリオ"""
        console.print("\n🏥 ヘルスケアシナリオ", style="bold cyan")
        
        tree = Tree("🏥 Healthcare Topics")
        
        # 患者監視
        patient_branch = tree.add("👤 patients/")
        patient_branch.add("ward_a/room_101/patient_001/vitals/heart_rate")
        patient_branch.add("ward_a/room_101/patient_001/vitals/blood_pressure")
        patient_branch.add("icu/bed_05/patient_002/ventilator/settings")
        patient_branch.add("emergency/triage/patient_queue_length")
        
        # 医療機器
        equipment_branch = tree.add("🔬 equipment/")
        equipment_branch.add("lab/analyzer_001/test_results")
        equipment_branch.add("radiology/mri_001/schedule")
        equipment_branch.add("pharmacy/dispensing_robot/medication_count")
        equipment_branch.add("or1/anesthesia_machine/gas_levels")
        
        # 環境制御
        env_branch = tree.add("🏥 environment/")
        env_branch.add("isolation_room_3/air_pressure")
        env_branch.add("clean_room/particle_count")
        env_branch.add("blood_bank/temperature")
        env_branch.add("or2/humidity_control")
        
        # スタッフ・ワークフロー
        staff_branch = tree.add("👩‍⚕️ staff/")
        staff_branch.add("nurses/ward_a/call_button_alerts")
        staff_branch.add("doctors/emergency/availability")
        staff_branch.add("security/access_log/restricted_areas")
        
        console.print(tree)
        
        sample_data = [
            ("patients/ward_a/room_101/patient_001/vitals/heart_rate", {"bpm": 72, "status": "normal"}),
            ("equipment/lab/analyzer_001/test_results", {"test_id": "CBC001", "status": "complete"}),
            ("environment/blood_bank/temperature", {"celsius": 4.2, "alarm": False}),
            ("staff/nurses/ward_a/call_button_alerts", {"room": "102", "priority": "medium"})
        ]
        
        self.send_sample_data(sample_data, "ヘルスケア")
        
        return {
            'topic_count': 15,
            'max_depth': 6,
            'categories': ['patients', 'equipment', 'environment', 'staff']
        }
    
    def agriculture_scenario(self):
        """農業シナリオ"""
        console.print("\n🌾 農業シナリオ", style="bold cyan")
        
        tree = Tree("🌾 Agriculture Topics")
        
        # 作物監視
        crops_branch = tree.add("🌱 crops/")
        crops_branch.add("field_1/corn/growth_stage")
        crops_branch.add("field_1/corn/soil_moisture")
        crops_branch.add("field_2/wheat/nutrient_levels")
        crops_branch.add("greenhouse_a/tomatoes/leaf_temperature")
        
        # 環境条件
        weather_branch = tree.add("🌤 weather/")
        weather_branch.add("field_1/temperature")
        weather_branch.add("field_1/precipitation")
        weather_branch.add("greenhouse_a/humidity")
        weather_branch.add("farm/wind_speed")
        
        # 灌漑システム
        irrigation_branch = tree.add("💧 irrigation/")
        irrigation_branch.add("field_1/zone_a/sprinkler_status")
        irrigation_branch.add("field_2/drip_system/flow_rate")
        irrigation_branch.add("water_tank/level")
        irrigation_branch.add("pump_station/pressure")
        
        # 機械・設備
        equipment_branch = tree.add("🚜 equipment/")
        equipment_branch.add("tractor_001/gps_location")
        equipment_branch.add("tractor_001/fuel_level")
        equipment_branch.add("harvester_001/crop_yield")
        equipment_branch.add("drone_001/battery_status")
        
        # 畜産
        livestock_branch = tree.add("🐄 livestock/")
        livestock_branch.add("barn_1/cattle/feeding_schedule")
        livestock_branch.add("barn_1/temperature")
        livestock_branch.add("pasture_a/cattle_count")
        
        console.print(tree)
        
        sample_data = [
            ("crops/field_1/corn/soil_moisture", {"percentage": 67.3, "optimal_range": "60-75"}),
            ("weather/field_1/temperature", {"celsius": 24.8, "forecast": "sunny"}),
            ("irrigation/field_1/zone_a/sprinkler_status", {"active": True, "duration": 15}),
            ("equipment/tractor_001/gps_location", {"lat": 40.7128, "lon": -74.0060}),
            ("livestock/barn_1/cattle/feeding_schedule", {"next_feeding": "14:00", "feed_type": "hay"})
        ]
        
        self.send_sample_data(sample_data, "農業")
        
        return {
            'topic_count': 18,
            'max_depth': 4,
            'categories': ['crops', 'weather', 'irrigation', 'equipment', 'livestock']
        }
    
    def send_sample_data(self, sample_data: List[tuple], scenario_name: str):
        """サンプルデータの送信"""
        console.print(f"   📤 {scenario_name}のサンプルデータを送信中...", style="yellow")
        
        for topic, payload in sample_data:
            enhanced_payload = {
                **payload,
                'timestamp': datetime.now().isoformat(),
                'scenario': scenario_name
            }
            
            self.client.publish(topic, json.dumps(enhanced_payload), qos=1)
            console.print(f"     → {topic}", style="dim")
        
        time.sleep(1)
    
    def run_all_scenarios(self):
        """すべてのシナリオを実行"""
        console.print("\n🌍 実世界のトピック設計シナリオ実行", style="bold blue")
        
        results = {}
        
        for scenario_name, scenario_func in self.scenarios.items():
            console.print(f"\n" + "="*60)
            result = scenario_func()
            results[scenario_name] = result
            time.sleep(2)
        
        # 総合分析
        self.analyze_scenarios(results)
    
    def analyze_scenarios(self, results: Dict[str, Any]):
        """シナリオの総合分析"""
        console.print("\n📊 シナリオ分析結果", style="bold blue")
        
        analysis_table = Table(title="実世界シナリオの比較")
        analysis_table.add_column("シナリオ", style="cyan", no_wrap=True)
        analysis_table.add_column("トピック数", style="magenta")
        analysis_table.add_column("最大階層", style="green")
        analysis_table.add_column("カテゴリ数", style="yellow")
        analysis_table.add_column("複雑度", style="red")
        
        scenario_names = {
            'smart_building': 'スマートビル',
            'manufacturing': '製造業',
            'smart_city': 'スマートシティ',
            'healthcare': 'ヘルスケア',
            'agriculture': '農業'
        }
        
        for scenario_key, result in results.items():
            complexity = self.calculate_complexity(result)
            scenario_name = scenario_names.get(scenario_key, scenario_key)
            
            analysis_table.add_row(
                scenario_name,
                str(result['topic_count']),
                str(result['max_depth']),
                str(len(result['categories'])),
                complexity
            )
        
        console.print(analysis_table)
        
        # 設計パターンの推奨事項
        self.show_design_recommendations(results)
    
    def calculate_complexity(self, result: Dict[str, Any]) -> str:
        """複雑度の計算"""
        topic_count = result['topic_count']
        max_depth = result['max_depth']
        category_count = len(result['categories'])
        
        complexity_score = (topic_count * 0.3) + (max_depth * 2) + (category_count * 1.5)
        
        if complexity_score < 15:
            return "低"
        elif complexity_score < 25:
            return "中"
        else:
            return "高"
    
    def show_design_recommendations(self, results: Dict[str, Any]):
        """設計推奨事項の表示"""
        console.print("\n💡 設計推奨事項", style="bold green")
        
        recommendations = []
        
        # 各シナリオの特徴に基づく推奨事項
        max_topics = max(result['topic_count'] for result in results.values())
        max_depth = max(result['max_depth'] for result in results.values())
        
        if max_topics > 20:
            recommendations.append("🔹 大規模システムでは、トピック名前空間の管理を自動化することを検討してください")
        
        if max_depth > 5:
            recommendations.append("🔹 深い階層構造は、パフォーマンスと管理の複雑性を増加させる可能性があります")
        
        recommendations.extend([
            "🔹 業界固有の標準やプロトコルに準拠したトピック構造を採用してください",
            "🔹 セキュリティ要件に応じて、センシティブなデータを適切に分離してください",
            "🔹 将来的な拡張性を考慮し、バージョニング戦略を策定してください",
            "🔹 監視とロギングのためのトピックを事前に設計してください",
            "🔹 災害復旧とフェイルオーバーシナリオを考慮したトピック設計を行ってください"
        ])
        
        for rec in recommendations:
            console.print(f"  {rec}")
    
    def disconnect(self):
        """MQTTブローカーから切断"""
        self.client.loop_stop()
        self.client.disconnect()
        console.print("👋 実世界シミュレーターが切断されました", style="yellow")

# 使用例
def main():
    """メイン実行関数"""
    console.print("🌍 実世界のMQTTトピック設計例", style="bold blue")
    console.print("=" * 50)
    
    simulator = RealWorldTopicDesigns()
    
    if not simulator.connect():
        console.print("❌ MQTTブローカーへの接続に失敗しました", style="red")
        return
    
    try:
        simulator.run_all_scenarios()
        console.print("\n✅ 実世界シナリオの実行完了！", style="bold green")
        
    except KeyboardInterrupt:
        console.print("\n⚠️ ユーザーによって中断されました", style="yellow")
    except Exception as e:
        console.print(f"\n❌ エラーが発生しました: {e}", style="red")
    finally:
        simulator.disconnect()

if __name__ == "__main__":
    main()
```

## 🎯 練習問題

### 問題1: カスタムトピック設計
以下の要件に基づいてトピック構造を設計してください：
- オフィスビル（3階建て、各階10部屋）
- センサー：温度、湿度、照度、人感
- 制御：照明、空調、ブラインド

### 問題2: スケーラビリティテスト
100台のデバイスが同時にデータを送信する場合のトピック設計を考えてください。

### 問題3: セキュリティ考慮設計
機密レベルの異なるデータ（Public、Internal、Confidential）を扱うトピック構造を設計してください。

## ✅ 確認チェックリスト

- [ ] トピック階層の設計原則を理解できた
- [ ] 実世界のユースケース別設計パターンを学んだ
- [ ] ワイルドカードを効率的に使用する方法を習得した
- [ ] パフォーマンスと保守性を考慮した設計ができる
- [ ] 様々な業界でのトピック設計例を確認した

## 📚 参考資料

- [MQTT Topic Best Practices](https://www.hivemq.com/blog/mqtt-topic-tree-design-best-practices/)
- [Industrial IoT Topic Design](https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.html)
- [Scalable MQTT Architecture](https://www.emqx.com/en/blog/mqtt-topic-design)

---

**次のステップ**: [05-security-implementation](../05-security-implementation/) でMQTTセキュリティの実装について詳しく学習しましょう！