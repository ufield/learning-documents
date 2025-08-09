#!/usr/bin/env python3
"""
MQTT基本接続デモ - Python版
基本的なMQTT接続とイベントハンドリング
"""

import paho.mqtt.client as mqtt
import time
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

class BasicMQTTClient:
    """基本的なMQTTクライアントクラス"""
    
    def __init__(self, broker_host="localhost", broker_port=1883):
        self.broker_host = broker_host
        self.broker_port = broker_port
        self.client = None
        self.is_connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            self.is_connected = True
            console.print("✅ Connected to MQTT broker successfully!", style="bold green")
            console.print(f"   Client ID: {client._client_id.decode()}", style="dim")
            console.print(f"   Broker: {self.broker_host}:{self.broker_port}", style="dim")
            console.print(f"   Session Present: {flags['session_present']}", style="dim")
        else:
            console.print(f"❌ Connection failed with code: {rc}", style="bold red")
            self.print_connection_error(rc)
            
    def on_disconnect(self, client, userdata, rc):
        """切断時のコールバック"""
        self.is_connected = False
        if rc != 0:
            console.print("⚠️  Unexpected disconnection", style="bold yellow")
        else:
            console.print("🔌 Disconnected gracefully", style="dim")
            
    def on_log(self, client, userdata, level, buf):
        """ログ出力用コールバック（デバッグ時に有効）"""
        if level <= mqtt.MQTT_LOG_INFO:
            console.print(f"[LOG] {buf}", style="dim blue")
        
    def print_connection_error(self, rc):
        """接続エラーの詳細説明"""
        error_messages = {
            1: "Incorrect protocol version - ブローカーがプロトコルバージョンを認識しない",
            2: "Invalid client identifier - クライアントIDが無効",
            3: "Server unavailable - ブローカーが利用不可", 
            4: "Bad username or password - ユーザー名またはパスワードが無効",
            5: "Not authorized - 認証されていない"
        }
        
        if rc in error_messages:
            console.print(f"Error details: {error_messages[rc]}", style="red")
            
        # トラブルシューティングのヒント
        self.show_troubleshooting_tips()
            
    def show_troubleshooting_tips(self):
        """トラブルシューティングのヒント表示"""
        console.print("\n🔧 Troubleshooting tips:", style="bold yellow")
        console.print("1. Make sure MQTT broker is running on localhost:1883")
        console.print("2. Check if the port is not blocked by firewall") 
        console.print("3. Try: docker run -it -p 1883:1883 eclipse-mosquitto:2.0")
        console.print("4. For Raspberry Pi: sudo systemctl status mosquitto")
        
    def connect(self, client_id="basic-python-client"):
        """ブローカーに接続"""
        console.print(f"🔗 Connecting to MQTT broker: {self.broker_host}:{self.broker_port}", 
                     style="bold blue")
        
        # MQTTクライアントの作成
        self.client = mqtt.Client(client_id=client_id)
        
        # コールバック設定
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log  # デバッグ用
        
        try:
            # 接続実行
            self.client.connect(self.broker_host, self.broker_port, 60)
            self.client.loop_start()
            
            # 接続完了まで待機
            timeout = 10
            start_time = time.time()
            
            while not self.is_connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
                
            if not self.is_connected:
                raise Exception("Connection timeout")
                
            return True
            
        except Exception as e:
            console.print(f"❌ Connection error: {e}", style="bold red")
            return False
            
    def disconnect(self):
        """ブローカーから切断"""
        if self.client and self.is_connected:
            self.client.loop_stop()
            self.client.disconnect()
            console.print("👋 Disconnected from MQTT broker", style="yellow")
            
    def get_status(self):
        """接続状態を取得"""
        return {
            "connected": self.is_connected,
            "client_id": self.client._client_id.decode() if self.client else None,
            "broker": f"{self.broker_host}:{self.broker_port}",
            "transport": "TCP"
        }
    
    def test_connection_parameters(self):
        """様々な接続パラメータをテスト"""
        test_configs = [
            {
                "name": "Default Connection",
                "client_id": "test-default",
                "clean_session": True,
                "keepalive": 60
            },
            {
                "name": "Persistent Session",
                "client_id": "test-persistent", 
                "clean_session": False,
                "keepalive": 60
            },
            {
                "name": "Short Keep Alive",
                "client_id": "test-short-ka",
                "clean_session": True,
                "keepalive": 30
            }
        ]
        
        console.print("\n🧪 Testing different connection parameters:", style="bold cyan")
        
        for config in test_configs:
            console.print(f"\n📋 Testing: {config['name']}")
            console.print(f"   Clean Session: {config['clean_session']}")
            console.print(f"   Keep Alive: {config['keepalive']}s")
            
            test_client = mqtt.Client(
                client_id=config['client_id'],
                clean_session=config['clean_session']
            )
            
            # テスト用コールバック
            connection_result = {"success": False, "session_present": False}
            
            def on_test_connect(client, userdata, flags, rc):
                if rc == 0:
                    connection_result["success"] = True
                    connection_result["session_present"] = flags.get('session_present', False)
                    
            test_client.on_connect = on_test_connect
            
            try:
                test_client.connect(self.broker_host, self.broker_port, config['keepalive'])
                test_client.loop_start()
                
                # 接続結果待機
                time.sleep(2)
                
                if connection_result["success"]:
                    console.print("   ✅ Connection successful", style="green")
                    if connection_result["session_present"]:
                        console.print("   📋 Session was present (persistent)", style="blue")
                    else:
                        console.print("   📄 New session created", style="dim")
                else:
                    console.print("   ❌ Connection failed", style="red")
                    
                test_client.loop_stop()
                test_client.disconnect()
                
            except Exception as e:
                console.print(f"   ❌ Test failed: {e}", style="red")
                
            time.sleep(1)  # テスト間の待機
            

def main():
    """メイン処理"""
    try:
        # コマンドライン引数の処理
        broker_host = sys.argv[1] if len(sys.argv) > 1 else "localhost"
        broker_port = int(sys.argv[2]) if len(sys.argv) > 2 else 1883
        
        console.print(Panel.fit(
            f"🏠 MQTT Basic Connection Demo\n\n"
            f"Broker: {broker_host}:{broker_port}\n"
            f"Language: Python 3\n"
            f"Library: paho-mqtt",
            title="MQTT Connection Test",
            border_style="blue"
        ))
        
        # 基本接続テスト
        client = BasicMQTTClient(broker_host, broker_port)
        
        if client.connect("handson-01-basic-python"):
            
            # 接続状態の表示
            status = client.get_status()
            
            status_panel = Panel.fit(
                f"Connected: {status['connected']}\n"
                f"Client ID: {status['client_id']}\n"
                f"Broker: {status['broker']}\n"
                f"Transport: {status['transport']}",
                title="📊 Connection Status",
                border_style="green"
            )
            console.print(status_panel)
            
            # 接続パラメータテスト
            test_params = console.input("\n🧪 Test different connection parameters? [y/N]: ")
            if test_params.lower() in ['y', 'yes']:
                client.test_connection_parameters()
            
            # 10秒間接続を維持
            console.print("\n⏰ Maintaining connection for 10 seconds...", style="bold blue")
            
            for i in range(10, 0, -1):
                console.print(f"   {i} seconds remaining... (Press Ctrl+C to exit early)", 
                            style="dim", end="\r")
                time.sleep(1)
                
            console.print("\n")
            client.disconnect()
            
            console.print("✨ Basic connection test completed successfully!", style="bold green")
            
        else:
            client.show_troubleshooting_tips()
            sys.exit(1)
            
    except KeyboardInterrupt:
        console.print("\n👋 Shutting down gracefully...", style="yellow")
        if 'client' in locals():
            client.disconnect()
        sys.exit(0)
        
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="bold red")
        if 'client' in locals():
            client.disconnect()
        sys.exit(1)


if __name__ == "__main__":
    main()