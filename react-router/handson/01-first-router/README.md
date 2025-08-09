# はじめてのReact Router

**所要時間: 30分**  
**レベル: 🟢 初級**

React Routerの基本的な概念を学び、シンプルなナビゲーションを実装します。

## 🎯 学習目標

- React Routerの基本概念を理解する
- ルートの定義方法を覚える
- Link コンポーネントでナビゲーションを実装する
- useNavigate フックの使い方を覚える

## 🏗️ 作るもの

シンプルな3ページのアプリケーション：
- ホームページ
- アバウトページ
- コンタクトページ

## 📋 前提条件

- React の基本的な知識
- Node.js (v16以上) がインストールされていること

## 🚀 始め方

### ステップ 1: プロジェクトの準備

```bash
cd starter
npm install
npm run dev
```

### ステップ 2: 段階的な実装

このハンズオンは以下の段階に分かれています：

1. **Step 1**: ルーターの基本セットアップ
2. **Step 2**: ページコンポーネントの作成
3. **Step 3**: ナビゲーションの実装
4. **Step 4**: プログラム的ナビゲーションの追加

各ステップは `steps/` ディレクトリで確認できます。

### ステップ 3: 実装開始

`starter/` ディレクトリから開始し、以下の手順で進めてください：

#### Step 1: ルーターの基本セットアップ

`src/main.tsx` を編集：

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'

// ページコンポーネント（後で作成）
import Home from './pages/Home'
import About from './pages/About'
import Contact from './pages/Contact'

const router = createBrowserRouter([
  {
    path: "/",
    element: <Home />,
  },
  {
    path: "/about",
    element: <About />,
  },
  {
    path: "/contact",
    element: <Contact />,
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
```

#### Step 2: ページコンポーネントの作成

`src/pages/` ディレクトリを作成し、以下のファイルを作成：

**src/pages/Home.tsx:**
```tsx
import { Link, useNavigate } from 'react-router-dom'

function Home() {
  const navigate = useNavigate()

  return (
    <div style={{ padding: '20px' }}>
      <h1>ホームページ</h1>
      <p>React Routerの基本的なナビゲーションを学びましょう。</p>
      
      <nav style={{ margin: '20px 0' }}>
        <Link to="/about" style={{ marginRight: '20px' }}>
          アバウト
        </Link>
        <Link to="/contact">
          コンタクト
        </Link>
      </nav>

      <button onClick={() => navigate('/about')}>
        プログラム的にアバウトへ移動
      </button>
    </div>
  )
}

export default Home
```

**src/pages/About.tsx:**
```tsx
import { Link } from 'react-router-dom'

function About() {
  return (
    <div style={{ padding: '20px' }}>
      <h1>アバウトページ</h1>
      <p>このアプリはReact Routerの学習用サンプルです。</p>
      
      <nav style={{ margin: '20px 0' }}>
        <Link to="/" style={{ marginRight: '20px' }}>
          ホーム
        </Link>
        <Link to="/contact">
          コンタクト
        </Link>
      </nav>
    </div>
  )
}

export default About
```

**src/pages/Contact.tsx:**
```tsx
import { Link } from 'react-router-dom'

function Contact() {
  return (
    <div style={{ padding: '20px' }}>
      <h1>コンタクトページ</h1>
      <p>お問い合わせはこちらから。</p>
      
      <nav style={{ margin: '20px 0' }}>
        <Link to="/" style={{ marginRight: '20px' }}>
          ホーム
        </Link>
        <Link to="/about">
          アバウト
        </Link>
      </nav>
    </div>
  )
}

export default Contact
```

### ステップ 4: 動作確認

ブラウザで以下を確認してください：

1. `http://localhost:5173/` でホームページが表示される
2. リンクをクリックしてページが切り替わる
3. ブラウザの戻る/進むボタンが正常に動作する
4. URLが正しく更新される

## 🎓 学習ポイント

### 1. createBrowserRouter の役割
```tsx
const router = createBrowserRouter([...])
```
- ルートの定義配列を受け取る
- HTML5 History API を使用したナビゲーション

### 2. RouterProvider の役割
```tsx
<RouterProvider router={router} />
```
- アプリケーション全体にルーターの機能を提供

### 3. Link コンポーネント
```tsx
<Link to="/about">アバウト</Link>
```
- ページをリロードせずにナビゲーション
- `<a>` タグとしてレンダリングされる

### 4. useNavigate フック
```tsx
const navigate = useNavigate()
navigate('/about')
```
- プログラム的なナビゲーション
- フォーム送信後のリダイレクトなどに使用

## 🧪 チャレンジ課題

基本実装ができたら、以下の機能を追加してみましょう：

### チャレンジ 1: アクティブリンクのスタイリング
NavLink コンポーネントを使って、現在のページのリンクをハイライト表示してください。

### チャレンジ 2: 404ページの追加
存在しないURLにアクセスした時の404ページを作成してください。

### チャレンジ 3: ページタイトルの動的変更
各ページでブラウザタブのタイトルを変更してください。

## 📁 ファイル構成

```
01-first-router/
├── README.md
├── starter/              # スターターコード
│   ├── package.json
│   ├── vite.config.ts
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       └── index.css
├── steps/               # 段階的な実装
│   ├── step1/          # ルーターセットアップ
│   ├── step2/          # ページコンポーネント
│   ├── step3/          # ナビゲーション
│   └── step4/          # プログラム的ナビゲーション
├── completed/          # 完成版
└── challenges/         # チャレンジ課題の解答例
```

## 🔗 次のステップ

このハンズオンが完了したら、次は「[ブログサイトを作ろう](../02-blog-site/)」に進みましょう。動的ルーティングとパラメータの使い方を学びます。