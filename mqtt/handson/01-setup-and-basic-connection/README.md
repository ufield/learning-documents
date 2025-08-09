# ハンズオン 01: セットアップと基本接続

## 🎯 学習目標

このハンズオンでは以下を学習します：

- MQTTブローカーのセットアップ方法
- MQTTクライアントの基本的な接続方法
- 接続状態の監視とエラーハンドリング
- 基本的なMQTTメッセージの送受信

**所要時間**: 約45分

## 📋 前提条件

- Node.js v18以降 または Python 3.8以降
- Docker（推奨）
- テキストエディタ

## 🛠 環境セットアップ

### Step 1: MQTTブローカーの起動

#### Option A: Docker でMosquitto起動（推奨）
```bash
# Mosquittoブローカーを起動
docker run -it --name mqtt-broker \
  -p 1883:1883 \
  -p 9001:9001 \
  eclipse-mosquitto:2.0

# バックグラウンドで起動する場合
docker run -d --name mqtt-broker \
  -p 1883:1883 \
  -p 9001:9001 \
  eclipse-mosquitto:2.0
```

#### Option B: ローカルインストール
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install mosquitto mosquitto-clients

# macOS
brew install mosquitto

# 起動
mosquitto -p 1883 -v
```

### Step 2: 依存関係のインストール

#### Node.js版
```bash
cd 01-setup-and-basic-connection
npm init -y
npm install mqtt chalk commander
```

#### Python版
```bash
cd 01-setup-and-basic-connection
pip install paho-mqtt rich click
```

## 📝 実装演習

### Exercise 1: 基本的な接続テスト

まず、MQTTブローカーに接続するシンプルなクライアントを作成します。

#### Node.js実装

`src/basic-connection.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');

class BasicMQTTClient {
    constructor(brokerUrl = 'mqtt://localhost:1883') {
        this.brokerUrl = brokerUrl;
        this.client = null;
        this.isConnected = false;
    }
    
    connect(clientId = 'basic-client') {
        console.log(chalk.blue(`🔗 Connecting to MQTT broker: ${this.brokerUrl}`));
        
        this.client = mqtt.connect(this.brokerUrl, {
            clientId: clientId,
            clean: true,
            connectTimeout: 4000,
            reconnectPeriod: 1000
        });
        
        this.setupEventHandlers();
        
        return new Promise((resolve, reject) => {
            this.client.on('connect', () => {
                resolve();
            });
            
            this.client.on('error', (error) => {
                reject(error);
            });
        });
    }
    
    setupEventHandlers() {
        this.client.on('connect', () => {
            this.isConnected = true;
            console.log(chalk.green('✅ Connected to MQTT broker successfully!'));
            console.log(chalk.gray(`   Client ID: ${this.client.options.clientId}`));
            console.log(chalk.gray(`   Broker: ${this.brokerUrl}`));
        });
        
        this.client.on('error', (error) => {
            console.error(chalk.red('❌ Connection error:'), error.message);
        });
        
        this.client.on('offline', () => {
            this.isConnected = false;
            console.log(chalk.yellow('⚠️  Client went offline'));
        });
        
        this.client.on('reconnect', () => {
            console.log(chalk.blue('🔄 Attempting to reconnect...'));
        });
        
        this.client.on('close', () => {
            this.isConnected = false;
            console.log(chalk.gray('🔌 Connection closed'));
        });
    }
    
    disconnect() {
        if (this.client) {
            this.client.end();
            console.log(chalk.yellow('👋 Disconnected from MQTT broker'));
        }
    }
    
    getStatus() {
        return {
            connected: this.isConnected,
            clientId: this.client?.options?.clientId,
            brokerUrl: this.brokerUrl
        };
    }
}

// 使用例
async function main() {
    const client = new BasicMQTTClient();
    
    try {
        await client.connect('handson-01-basic');
        
        console.log(chalk.green('\n📊 Connection Status:'));
        console.log(client.getStatus());
        
        // 10秒間接続を維持
        console.log(chalk.blue('\n⏰ Maintaining connection for 10 seconds...'));
        await new Promise(resolve => setTimeout(resolve, 10000));
        
        client.disconnect();
        
    } catch (error) {
        console.error(chalk.red('Failed to connect:'), error.message);
        
        // トラブルシューティングのヒント
        console.log(chalk.yellow('\n🔧 Troubleshooting tips:'));
        console.log('1. Make sure MQTT broker is running on localhost:1883');
        console.log('2. Check if the port is not blocked by firewall');
        console.log('3. Try: docker run -it -p 1883:1883 eclipse-mosquitto:2.0');
    }
}

// Ctrl+Cでのクリーンアップ
process.on('SIGINT', () => {
    console.log(chalk.yellow('\n👋 Shutting down gracefully...'));
    process.exit(0);
});

if (require.main === module) {
    main();
}

module.exports = BasicMQTTClient;
```

#### Python実装

`src/basic_connection.py` を作成：

```python
import paho.mqtt.client as mqtt
import time
import sys
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()

class BasicMQTTClient:
    def __init__(self, broker_url="localhost", broker_port=1883):
        self.broker_url = broker_url
        self.broker_port = broker_port
        self.client = None
        self.is_connected = False
        
    def on_connect(self, client, userdata, flags, rc):
        """接続時のコールバック"""
        if rc == 0:
            self.is_connected = True
            console.print("✅ Connected to MQTT broker successfully!", style="bold green")
            console.print(f"   Client ID: {client._client_id.decode()}", style="dim")
            console.print(f"   Broker: {self.broker_url}:{self.broker_port}", style="dim")
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
        """ログ出力用コールバック"""
        console.print(f"[LOG] {buf}", style="dim blue")
        
    def print_connection_error(self, rc):
        """接続エラーの説明"""
        error_messages = {
            1: "Incorrect protocol version",
            2: "Invalid client identifier",
            3: "Server unavailable", 
            4: "Bad username or password",
            5: "Not authorized"
        }
        
        if rc in error_messages:
            console.print(f"Error details: {error_messages[rc]}", style="red")
            
    def connect(self, client_id="basic-python-client"):
        """ブローカーに接続"""
        console.print(f"🔗 Connecting to MQTT broker: {self.broker_url}:{self.broker_port}", style="bold blue")
        
        self.client = mqtt.Client(client_id=client_id)
        
        # コールバック設定
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_log = self.on_log
        
        try:
            self.client.connect(self.broker_url, self.broker_port, 60)
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
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            console.print("👋 Disconnected from MQTT broker", style="yellow")
            
    def get_status(self):
        """接続状態を取得"""
        return {
            "connected": self.is_connected,
            "client_id": self.client._client_id.decode() if self.client else None,
            "broker": f"{self.broker_url}:{self.broker_port}"
        }

def main():
    """メイン処理"""
    client = BasicMQTTClient()
    
    try:
        # 接続試行
        if client.connect("handson-01-basic-python"):
            
            # 接続状態の表示
            status = client.get_status()
            
            status_panel = Panel.fit(
                f"Connected: {status['connected']}\n"
                f"Client ID: {status['client_id']}\n"
                f"Broker: {status['broker']}",
                title="📊 Connection Status",
                border_style="green"
            )
            console.print(status_panel)
            
            # 10秒間接続を維持
            console.print("\n⏰ Maintaining connection for 10 seconds...", style="bold blue")
            
            for i in range(10, 0, -1):
                console.print(f"   {i} seconds remaining...", style="dim", end="\r")
                time.sleep(1)
                
            console.print("\n")
            client.disconnect()
            
        else:
            console.print("\n🔧 Troubleshooting tips:", style="bold yellow")
            console.print("1. Make sure MQTT broker is running on localhost:1883")
            console.print("2. Check if the port is not blocked by firewall") 
            console.print("3. Try: docker run -it -p 1883:1883 eclipse-mosquitto:2.0")
            
    except KeyboardInterrupt:
        console.print("\n👋 Shutting down gracefully...", style="yellow")
        client.disconnect()
        sys.exit(0)
        
    except Exception as e:
        console.print(f"\n❌ Unexpected error: {e}", style="bold red")
        client.disconnect()
        sys.exit(1)

if __name__ == "__main__":
    main()
```

### Exercise 2: 接続パラメータの実験

接続時の様々なパラメータを変更して動作を確認します。

`src/connection-parameters.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');

class ConnectionExperiment {
    constructor() {
        this.experiments = [
            {
                name: 'Default Connection',
                options: {
                    clientId: 'experiment-default',
                    clean: true,
                    connectTimeout: 4000
                }
            },
            {
                name: 'Persistent Session',
                options: {
                    clientId: 'experiment-persistent',
                    clean: false,  // セッションを保持
                    connectTimeout: 4000
                }
            },
            {
                name: 'Custom Keep Alive',
                options: {
                    clientId: 'experiment-keepalive',
                    clean: true,
                    connectTimeout: 4000,
                    keepalive: 30  // 30秒のキープアライブ
                }
            },
            {
                name: 'With Last Will Testament',
                options: {
                    clientId: 'experiment-lwt',
                    clean: true,
                    connectTimeout: 4000,
                    will: {
                        topic: 'clients/experiment-lwt/status',
                        payload: 'offline',
                        qos: 1,
                        retain: true
                    }
                }
            }
        ];
    }
    
    async runExperiment(experiment) {
        console.log(chalk.blue(`\n🧪 Running experiment: ${experiment.name}`));
        console.log(chalk.gray('   Options:', JSON.stringify(experiment.options, null, 2)));
        
        return new Promise((resolve) => {
            const client = mqtt.connect('mqtt://localhost:1883', experiment.options);
            
            const timeout = setTimeout(() => {
                console.log(chalk.red('   ❌ Connection timeout'));
                client.end();
                resolve({ success: false, error: 'timeout' });
            }, 10000);
            
            client.on('connect', (connack) => {
                clearTimeout(timeout);
                console.log(chalk.green('   ✅ Connection successful'));
                console.log(chalk.gray(`   Session present: ${connack.sessionPresent}`));
                
                // すぐに切断
                setTimeout(() => {
                    client.end();
                    resolve({ success: true, sessionPresent: connack.sessionPresent });
                }, 1000);
            });
            
            client.on('error', (error) => {
                clearTimeout(timeout);
                console.log(chalk.red(`   ❌ Connection failed: ${error.message}`));
                client.end();
                resolve({ success: false, error: error.message });
            });
        });
    }
    
    async runAllExperiments() {
        console.log(chalk.yellow('🔬 Starting Connection Parameter Experiments\n'));
        
        const results = [];
        
        for (const experiment of this.experiments) {
            const result = await this.runExperiment(experiment);
            results.push({
                name: experiment.name,
                ...result
            });
            
            // 実験間に少し待機
            await new Promise(resolve => setTimeout(resolve, 2000));
        }
        
        // 結果サマリー
        console.log(chalk.yellow('\n📊 Experiment Results Summary:'));
        results.forEach(result => {
            const status = result.success ? chalk.green('✅ PASS') : chalk.red('❌ FAIL');
            console.log(`${status} ${result.name}`);
            if (result.error) {
                console.log(chalk.red(`     Error: ${result.error}`));
            }
            if (result.sessionPresent !== undefined) {
                console.log(chalk.gray(`     Session Present: ${result.sessionPresent}`));
            }
        });
    }
}

// 実行
if (require.main === module) {
    const experiment = new ConnectionExperiment();
    experiment.runAllExperiments().then(() => {
        console.log(chalk.green('\n🎉 All experiments completed!'));
        process.exit(0);
    }).catch(error => {
        console.error(chalk.red('Experiment failed:'), error);
        process.exit(1);
    });
}

module.exports = ConnectionExperiment;
```

## 🎯 練習問題

### 問題1: 基本接続の確認
1. 作成したコードを実行して、MQTTブローカーに正常に接続できることを確認してください。
2. ブローカーを停止して、エラーハンドリングが正しく動作することを確認してください。

### 問題2: 接続パラメータの実験
1. `connection-parameters.js`を実行して、各実験結果を確認してください。
2. `Persistent Session`の実験で、2回目の接続時に`sessionPresent`が`true`になることを確認してください。

### 問題3: カスタムクライアント作成
以下の要件でクライアントを作成してください：
- クライアントID: `your-name-client`
- Keep Alive: 45秒
- Clean Session: false
- Last Will Testament: 
  - Topic: `status/your-name`
  - Message: `went offline unexpectedly`
  - QoS: 1
  - Retain: true

## ✅ 確認チェックリスト

- [ ] MQTTブローカーが正常に起動している
- [ ] 基本的な接続コードが動作する
- [ ] 接続エラーが適切にハンドリングされる
- [ ] 接続パラメータの違いを理解できた
- [ ] Last Will Testamentの概念を理解できた
- [ ] Persistent Sessionの動作を確認できた

## 🔧 トラブルシューティング

### 接続できない場合
1. **ブローカーが起動しているか確認**
   ```bash
   docker ps  # Dockerの場合
   netstat -an | grep 1883  # ポート確認
   ```

2. **ファイアウォールの確認**
   ```bash
   telnet localhost 1883
   ```

3. **ログの確認**
   - Node.jsの場合：コンソールログを確認
   - Pythonの場合：`on_log`コールバックでデバッグ

### よくあるエラー

- `ECONNREFUSED`: ブローカーが起動していない
- `ENOTFOUND`: ホスト名の解決に失敗
- `Connection timeout`: ネットワークの問題

## 📚 学習リソース

- [MQTT.org - Getting Started](https://mqtt.org/getting-started/)
- [Eclipse Mosquitto Documentation](https://mosquitto.org/documentation/)
- [Paho MQTT Python Client](https://www.eclipse.org/paho/index.php?page=clients/python/docs/index.php)
- [MQTT.js Documentation](https://github.com/mqttjs/MQTT.js#readme)

---

**次のステップ**: [02-publish-subscribe](../02-publish-subscribe/) でメッセージの送受信を学習しましょう！