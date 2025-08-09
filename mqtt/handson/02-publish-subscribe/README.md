# ハンズオン 02: Publish/Subscribe の基本

## 🎯 学習目標

このハンズオンでは以下を学習します：

- MQTTのPublish/Subscribe（Pub/Sub）パターンの理解
- メッセージの送信（Publish）方法
- メッセージの受信（Subscribe）方法  
- トピックとワイルドカードの使用方法
- 複数クライアント間での通信

**所要時間**: 約60分

## 📋 前提条件

- [01-setup-and-basic-connection](../01-setup-and-basic-connection/) の完了
- MQTTブローカーが起動していること

## 🎭 Pub/Subパターンの理解

従来の通信方式（リクエスト-レスポンス）と異なり、MQTTのPub/Subパターンでは：

```
Publisher → [Topic] → Broker → [Topic] → Subscriber(s)
```

- **Publisher**: メッセージを送信する側
- **Subscriber**: メッセージを受信する側  
- **Topic**: メッセージのルーティング先
- **Broker**: メッセージの仲介役

## 📝 実装演習

### Exercise 1: 基本的なPublish/Subscribe

#### シンプルなPublisher作成

`src/publisher.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');

class MQTTPublisher {
    constructor(brokerUrl = 'mqtt://localhost:1883') {
        this.client = mqtt.connect(brokerUrl, {
            clientId: `publisher-${Date.now()}`,
            clean: true
        });
        
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.client.on('connect', () => {
            console.log(chalk.green('📡 Publisher connected to broker'));
        });
        
        this.client.on('error', (error) => {
            console.error(chalk.red('❌ Publisher error:'), error.message);
        });
    }
    
    async publish(topic, message, options = {}) {
        return new Promise((resolve, reject) => {
            const payload = typeof message === 'object' ? JSON.stringify(message) : message;
            
            console.log(chalk.blue(`📤 Publishing to topic: ${topic}`));
            console.log(chalk.gray(`   Message: ${payload}`));
            console.log(chalk.gray(`   QoS: ${options.qos || 0}`));
            
            this.client.publish(topic, payload, options, (error, packet) => {
                if (error) {
                    console.error(chalk.red('❌ Publish failed:'), error.message);
                    reject(error);
                } else {
                    console.log(chalk.green('✅ Message published successfully'));
                    resolve(packet);
                }
            });
        });
    }
    
    disconnect() {
        this.client.end();
        console.log(chalk.yellow('👋 Publisher disconnected'));
    }
}

// 使用例
async function demonstratePublishing() {
    const publisher = new MQTTPublisher();
    
    // 接続完了まで少し待機
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    try {
        // シンプルなテキストメッセージ
        await publisher.publish('sensors/temperature', '23.5');
        
        // JSONメッセージ
        await publisher.publish('sensors/data', {
            sensorId: 'temp-001',
            temperature: 23.5,
            humidity: 45.2,
            timestamp: new Date().toISOString()
        });
        
        // QoS 1でのメッセージ送信
        await publisher.publish('alerts/high-temperature', 'Temperature exceeded threshold!', {
            qos: 1
        });
        
        // Retainedメッセージ
        await publisher.publish('sensors/temp-001/status', 'online', {
            qos: 1,
            retain: true
        });
        
    } catch (error) {
        console.error('Publishing failed:', error);
    } finally {
        publisher.disconnect();
    }
}

if (require.main === module) {
    demonstratePublishing();
}

module.exports = MQTTPublisher;
```

#### シンプルなSubscriber作成

`src/subscriber.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');

class MQTTSubscriber {
    constructor(brokerUrl = 'mqtt://localhost:1883') {
        this.client = mqtt.connect(brokerUrl, {
            clientId: `subscriber-${Date.now()}`,
            clean: true
        });
        
        this.subscriptions = new Map();
        this.messageCount = 0;
        
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.client.on('connect', () => {
            console.log(chalk.green('📡 Subscriber connected to broker'));
        });
        
        this.client.on('message', (topic, message, packet) => {
            this.handleMessage(topic, message, packet);
        });
        
        this.client.on('error', (error) => {
            console.error(chalk.red('❌ Subscriber error:'), error.message);
        });
        
        this.client.on('subscribe', (granted) => {
            console.log(chalk.green('✅ Successfully subscribed:'));
            granted.forEach(sub => {
                console.log(chalk.gray(`   Topic: ${sub.topic}, QoS: ${sub.qos}`));
            });
        });
    }
    
    handleMessage(topic, message, packet) {
        this.messageCount++;
        
        console.log(chalk.cyan(`\n📬 Message received (#${this.messageCount})`));
        console.log(chalk.blue(`   Topic: ${topic}`));
        console.log(chalk.blue(`   QoS: ${packet.qos}`));
        console.log(chalk.blue(`   Retain: ${packet.retain}`));
        console.log(chalk.blue(`   Payload: ${message.toString()}`));
        
        // JSONメッセージの場合はパースして表示
        try {
            const jsonData = JSON.parse(message.toString());
            console.log(chalk.magenta('   Parsed JSON:'));
            console.log(chalk.gray(JSON.stringify(jsonData, null, 4)));
        } catch (e) {
            // JSON以外のメッセージの場合は無視
        }
        
        // カスタム処理のデモ
        this.processMessageByTopic(topic, message.toString());
    }
    
    processMessageByTopic(topic, message) {
        if (topic.startsWith('sensors/temperature')) {
            const temp = parseFloat(message);
            if (temp > 30) {
                console.log(chalk.red('🔥 High temperature alert!'));
            } else if (temp < 10) {
                console.log(chalk.blue('🧊 Low temperature alert!'));
            }
        } else if (topic.startsWith('alerts/')) {
            console.log(chalk.yellow('⚠️  Alert received - escalating to monitoring system'));
        }
    }
    
    async subscribe(topic, options = {}) {
        return new Promise((resolve, reject) => {
            console.log(chalk.blue(`📥 Subscribing to topic: ${topic}`));
            console.log(chalk.gray(`   QoS: ${options.qos || 0}`));
            
            this.client.subscribe(topic, options, (error, granted) => {
                if (error) {
                    console.error(chalk.red('❌ Subscribe failed:'), error.message);
                    reject(error);
                } else {
                    this.subscriptions.set(topic, options);
                    resolve(granted);
                }
            });
        });
    }
    
    async unsubscribe(topic) {
        return new Promise((resolve, reject) => {
            console.log(chalk.yellow(`📤 Unsubscribing from topic: ${topic}`));
            
            this.client.unsubscribe(topic, (error) => {
                if (error) {
                    console.error(chalk.red('❌ Unsubscribe failed:'), error.message);
                    reject(error);
                } else {
                    this.subscriptions.delete(topic);
                    console.log(chalk.green('✅ Successfully unsubscribed'));
                    resolve();
                }
            });
        });
    }
    
    disconnect() {
        this.client.end();
        console.log(chalk.yellow(`👋 Subscriber disconnected (received ${this.messageCount} messages)`));
    }
    
    getStats() {
        return {
            messageCount: this.messageCount,
            subscriptions: Array.from(this.subscriptions.keys())
        };
    }
}

// 使用例
async function demonstrateSubscribing() {
    const subscriber = new MQTTSubscriber();
    
    // 接続完了まで少し待機
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    try {
        // 複数のトピックに購読
        await subscriber.subscribe('sensors/temperature');
        await subscriber.subscribe('sensors/data');
        await subscriber.subscribe('alerts/+'); // ワイルドカード使用
        await subscriber.subscribe('sensors/+/status', { qos: 1 });
        
        console.log(chalk.green('\n🎧 Listening for messages... (Press Ctrl+C to stop)'));
        
        // 60秒間メッセージを待機
        await new Promise(resolve => setTimeout(resolve, 60000));
        
    } catch (error) {
        console.error('Subscribing failed:', error);
    } finally {
        const stats = subscriber.getStats();
        console.log(chalk.cyan('\n📊 Session Statistics:'));
        console.log(`   Messages received: ${stats.messageCount}`);
        console.log(`   Subscriptions: ${stats.subscriptions.join(', ')}`);
        
        subscriber.disconnect();
    }
}

// Ctrl+Cでのクリーンアップ
process.on('SIGINT', () => {
    console.log(chalk.yellow('\n👋 Shutting down gracefully...'));
    process.exit(0);
});

if (require.main === module) {
    demonstrateSubscribing();
}

module.exports = MQTTSubscriber;
```

### Exercise 2: ワイルドカードの実践

`src/wildcard-demo.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');

class WildcardDemo {
    constructor() {
        this.client = mqtt.connect('mqtt://localhost:1883', {
            clientId: 'wildcard-demo'
        });
        
        this.testTopics = [
            'home/livingroom/temperature',
            'home/livingroom/humidity',
            'home/bedroom/temperature', 
            'home/bedroom/light',
            'home/kitchen/temperature',
            'office/room1/temperature',
            'office/room1/humidity',
            'factory/line1/sensor1/temperature',
            'factory/line1/sensor2/pressure'
        ];
        
        this.setupEventHandlers();
    }
    
    setupEventHandlers() {
        this.client.on('connect', () => {
            console.log(chalk.green('📡 Wildcard demo client connected'));
        });
        
        this.client.on('message', (topic, message, packet) => {
            console.log(chalk.cyan(`📬 [${packet.qos}] ${topic}: ${message.toString()}`));
        });
    }
    
    async demonstrateWildcards() {
        console.log(chalk.yellow('🎯 MQTT Wildcard Demonstration\n'));
        
        // テストデータの公開
        console.log(chalk.blue('📤 Publishing test messages...'));
        for (const topic of this.testTopics) {
            const value = (Math.random() * 30 + 10).toFixed(1);
            await this.publish(topic, value);
        }
        
        await new Promise(resolve => setTimeout(resolve, 2000));
        
        // ワイルドカードパターンの実験
        const wildcardPatterns = [
            {
                pattern: 'home/+/temperature',
                description: '家の全ての部屋の温度'
            },
            {
                pattern: 'home/livingroom/+', 
                description: 'リビングルームの全てのセンサー'
            },
            {
                pattern: '+/+/temperature',
                description: '全ての建物の全ての部屋の温度'
            },
            {
                pattern: 'factory/#',
                description: '工場の全てのデータ'
            },
            {
                pattern: '+/+/+',
                description: '3階層のトピック全て'
            }
        ];
        
        for (const pattern of wildcardPatterns) {
            await this.demonstratePattern(pattern);
            await new Promise(resolve => setTimeout(resolve, 3000));
        }
    }
    
    async demonstratePattern({ pattern, description }) {
        console.log(chalk.yellow(`\n🔍 Testing pattern: ${pattern}`));
        console.log(chalk.gray(`   Description: ${description}`));
        
        // パターンに購読
        await new Promise((resolve, reject) => {
            this.client.subscribe(pattern, (error) => {
                if (error) reject(error);
                else resolve();
            });
        });
        
        console.log(chalk.green('✅ Subscribed. Publishing messages...'));
        
        // マッチするメッセージを再公開
        let matchCount = 0;
        for (const topic of this.testTopics) {
            if (this.topicMatches(topic, pattern)) {
                matchCount++;
                const value = (Math.random() * 30 + 10).toFixed(1);
                await this.publish(topic, `${value} (matched)`);
            }
        }
        
        console.log(chalk.blue(`📊 Pattern matched ${matchCount} topics`));
        
        // 購読解除
        await new Promise((resolve) => {
            this.client.unsubscribe(pattern, () => resolve());
        });
        
        console.log(chalk.gray('📤 Unsubscribed from pattern'));
    }
    
    topicMatches(topic, pattern) {
        // シンプルなマッチング実装
        const topicParts = topic.split('/');
        const patternParts = pattern.split('/');
        
        if (pattern.includes('#')) {
            const hashIndex = patternParts.indexOf('#');
            return topicParts.slice(0, hashIndex).every((part, i) => 
                patternParts[i] === part || patternParts[i] === '+'
            );
        }
        
        if (topicParts.length !== patternParts.length) {
            return false;
        }
        
        return topicParts.every((part, i) => 
            patternParts[i] === part || patternParts[i] === '+'
        );
    }
    
    async publish(topic, message) {
        return new Promise((resolve, reject) => {
            this.client.publish(topic, message, (error) => {
                if (error) reject(error);
                else resolve();
            });
        });
    }
    
    disconnect() {
        this.client.end();
        console.log(chalk.yellow('\n👋 Wildcard demo completed'));
    }
}

// 実行
async function main() {
    const demo = new WildcardDemo();
    
    // 接続完了まで待機
    await new Promise(resolve => setTimeout(resolve, 1000));
    
    try {
        await demo.demonstrateWildcards();
    } catch (error) {
        console.error(chalk.red('Demo failed:'), error);
    } finally {
        demo.disconnect();
    }
}

if (require.main === module) {
    main();
}

module.exports = WildcardDemo;
```

### Exercise 3: チャットアプリケーション

`src/chat-application.js` を作成：

```javascript
const mqtt = require('mqtt');
const chalk = require('chalk');
const readline = require('readline');

class MQTTChatApp {
    constructor(username) {
        this.username = username;
        this.client = mqtt.connect('mqtt://localhost:1883', {
            clientId: `chat-${username}-${Date.now()}`,
            clean: true,
            will: {
                topic: 'chat/system',
                payload: JSON.stringify({
                    type: 'user_disconnect',
                    username: username,
                    timestamp: new Date().toISOString()
                }),
                qos: 1
            }
        });
        
        this.isConnected = false;
        this.setupMQTTHandlers();
        this.setupReadlineInterface();
    }
    
    setupMQTTHandlers() {
        this.client.on('connect', () => {
            this.isConnected = true;
            console.log(chalk.green(`🎉 Welcome to MQTT Chat, ${this.username}!`));
            console.log(chalk.gray('💡 Commands: /help, /users, /quit'));
            console.log(chalk.gray('📝 Type your message and press Enter to send\n'));
            
            // チャットルームに参加
            this.subscribeToChat();
            this.announceJoin();
        });
        
        this.client.on('message', (topic, message, packet) => {
            this.handleMessage(topic, message, packet);
        });
        
        this.client.on('error', (error) => {
            console.error(chalk.red('❌ Connection error:'), error.message);
        });
    }
    
    setupReadlineInterface() {
        this.rl = readline.createInterface({
            input: process.stdin,
            output: process.stdout,
            prompt: chalk.blue(`${this.username}> `)
        });
        
        this.rl.on('line', (input) => {
            this.handleUserInput(input.trim());
        });
        
        this.rl.on('SIGINT', () => {
            this.quit();
        });
    }
    
    async subscribeToChat() {
        try {
            await this.subscribe('chat/messages', 1);
            await this.subscribe('chat/system', 1);
            await this.subscribe(`chat/private/${this.username}`, 1);
            
            this.rl.prompt();
        } catch (error) {
            console.error(chalk.red('Failed to subscribe to chat topics'));
        }
    }
    
    subscribe(topic, qos = 0) {
        return new Promise((resolve, reject) => {
            this.client.subscribe(topic, { qos }, (error) => {
                if (error) reject(error);
                else resolve();
            });
        });
    }
    
    handleMessage(topic, message, packet) {
        try {
            const data = JSON.parse(message.toString());
            
            if (data.username === this.username) {
                return; // 自分のメッセージは表示しない
            }
            
            // プロンプトをクリア
            readline.cursorTo(process.stdout, 0);
            readline.clearLine(process.stdout, 0);
            
            if (topic === 'chat/messages') {
                console.log(chalk.cyan(`💬 ${data.username}: ${data.message}`));
            } else if (topic === 'chat/system') {
                this.handleSystemMessage(data);
            } else if (topic.startsWith('chat/private/')) {
                console.log(chalk.magenta(`🔒 [Private] ${data.username}: ${data.message}`));
            }
            
            this.rl.prompt();
        } catch (error) {
            // JSON以外のメッセージは無視
        }
    }
    
    handleSystemMessage(data) {
        switch (data.type) {
            case 'user_join':
                console.log(chalk.green(`👋 ${data.username} joined the chat`));
                break;
            case 'user_disconnect':
                console.log(chalk.yellow(`👋 ${data.username} left the chat`));
                break;
            case 'user_list':
                console.log(chalk.blue(`👥 Online users: ${data.users.join(', ')}`));
                break;
        }
    }
    
    handleUserInput(input) {
        if (!this.isConnected) {
            console.log(chalk.red('❌ Not connected to chat server'));
            this.rl.prompt();
            return;
        }
        
        if (input.startsWith('/')) {
            this.handleCommand(input);
        } else if (input.length > 0) {
            this.sendMessage(input);
        }
        
        this.rl.prompt();
    }
    
    handleCommand(command) {
        const [cmd, ...args] = command.split(' ');
        
        switch (cmd.toLowerCase()) {
            case '/help':
                console.log(chalk.blue('📖 Available commands:'));
                console.log('  /help - Show this help');
                console.log('  /users - List online users');
                console.log('  /private <username> <message> - Send private message');
                console.log('  /quit - Leave the chat');
                break;
                
            case '/users':
                this.requestUserList();
                break;
                
            case '/private':
                if (args.length < 2) {
                    console.log(chalk.red('❌ Usage: /private <username> <message>'));
                } else {
                    const [targetUser, ...messageParts] = args;
                    this.sendPrivateMessage(targetUser, messageParts.join(' '));
                }
                break;
                
            case '/quit':
                this.quit();
                break;
                
            default:
                console.log(chalk.red(`❌ Unknown command: ${cmd}`));
                console.log(chalk.gray('💡 Type /help for available commands'));
                break;
        }
    }
    
    sendMessage(message) {
        const messageData = {
            username: this.username,
            message: message,
            timestamp: new Date().toISOString()
        };
        
        this.client.publish('chat/messages', JSON.stringify(messageData), { qos: 1 });
    }
    
    sendPrivateMessage(targetUser, message) {
        const messageData = {
            username: this.username,
            message: message,
            timestamp: new Date().toISOString()
        };
        
        this.client.publish(`chat/private/${targetUser}`, JSON.stringify(messageData), { qos: 1 });
        console.log(chalk.magenta(`🔒 [Private to ${targetUser}]: ${message}`));
    }
    
    announceJoin() {
        const joinData = {
            type: 'user_join',
            username: this.username,
            timestamp: new Date().toISOString()
        };
        
        this.client.publish('chat/system', JSON.stringify(joinData), { qos: 1 });
    }
    
    requestUserList() {
        // 実際のアプリケーションでは、サーバー側でユーザーリストを管理する必要があります
        console.log(chalk.gray('👥 User list functionality would require server-side implementation'));
    }
    
    quit() {
        console.log(chalk.yellow('\n👋 Leaving chat...'));
        
        if (this.isConnected) {
            const disconnectData = {
                type: 'user_disconnect',
                username: this.username,
                timestamp: new Date().toISOString()
            };
            
            this.client.publish('chat/system', JSON.stringify(disconnectData), { qos: 1 });
        }
        
        this.rl.close();
        this.client.end();
        process.exit(0);
    }
}

// コマンドライン引数からユーザー名を取得
const username = process.argv[2];

if (!username) {
    console.log(chalk.red('❌ Please provide a username'));
    console.log(chalk.blue('Usage: node chat-application.js <username>'));
    process.exit(1);
}

// チャットアプリケーション開始
new MQTTChatApp(username);
```

## 🎯 練習問題

### 問題1: 基本的なPub/Sub
1. ターミナルを2つ開いて、一方でSubscriber、もう一方でPublisherを実行してください
2. 様々なトピックとメッセージでやり取りを確認してください

### 問題2: ワイルドカードの理解
1. `wildcard-demo.js`を実行して、各パターンの動作を確認してください
2. 独自のワイルドカードパターンを作成してテストしてください

### 問題3: チャットアプリケーション
1. 複数のターミナルで異なるユーザー名でチャットアプリを起動してください
2. メッセージのやり取りと各種コマンドを試してください
3. プライベートメッセージ機能を確認してください

### 問題4: カスタム実装
温度センサーの監視システムを作成してください：
- Publisher: 5秒間隔で温度データ（15-35度のランダム値）を送信
- Subscriber: 30度以上で警告、10度以下でアラート表示
- Topic: `sensors/building1/room{1-3}/temperature`

## ✅ 確認チェックリスト

- [ ] PublisherとSubscriberの基本動作を理解した
- [ ] 様々なデータ形式（文字列、JSON）でメッセージを送受信できた
- [ ] QoSレベルの違いを理解した
- [ ] Retainedメッセージの動作を確認した
- [ ] ワイルドカード（+と#）の使い方を理解した
- [ ] 複数クライアント間でのリアルタイム通信を実現できた
- [ ] Last Will Testamentの動作を確認した

## 📊 理解度チェック

以下の質問に答えられるか確認してください：

1. `home/+/temperature`と`home/#`の違いは何ですか？
2. Retainedメッセージはいつ使用しますか？
3. QoS 0とQoS 1の違いは何ですか？
4. Last Will Testamentはどのような場面で有効ですか？

## 🔧 トラブルシューティング

### メッセージが届かない
- トピック名のタイプミスを確認
- Subscriberが正しく購読しているか確認
- ブローカーのログを確認

### 重複メッセージ
- Clean Sessionの設定を確認
- QoS 1での重複は正常な動作

### チャットで文字化け
- UTF-8エンコーディングを確認
- JSONの形式を確認

---

**次のステップ**: [03-qos-and-reliability](../03-qos-and-reliability/) でメッセージの信頼性について詳しく学習しましょう！