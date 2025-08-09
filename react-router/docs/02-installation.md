# インストールと基本セットアップ 🟢

## 📖 この章で学ぶこと

- React Router v7のインストール方法
- 3つのモード別セットアップ手順
- Vite/Next.jsでの設定
- TypeScriptの設定
- Vue CLIからの移行のヒント

**想定読了時間**: 15分

---

## 🚀 クイックスタート

Nuxtユーザーの方は、`npx nuxi@latest init`でプロジェクトを作成する流れに慣れているでしょう。

React Routerでは、主に以下の環境で開発します：
- **Vite + React**: 最も人気のある組み合わせ（NuxtのViteに似た高速な開発体験）
- **Next.js**: App Router使用時は別途考慮が必要
- **Remix**: Framework Mode用（Nuxtに最も近いフルスタック開発）

## 📦 インストール

### 基本インストール

```bash
# npm
npm install react-router-dom

# yarn
yarn add react-router-dom

# pnpm (2025年では人気上昇中)
pnpm add react-router-dom
```

**Nuxtとの違い**: Nuxtはルーティングがデフォルトでインストールされていますが、React Routerは明示的にインストールが必要です。

## 🔧 モード別セットアップ

### 1. Declarative Mode（宣言的モード）のセットアップ 🟢

最もシンプルで理解しやすい形式です。

#### Viteでのセットアップ

```bash
# Viteプロジェクトの作成
npm create vite@latest my-react-app -- --template react-ts
cd my-react-app
npm install react-router-dom
```

#### 基本的な実装

```tsx
// main.tsx (Vue の main.js に相当)
import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <App />
    </BrowserRouter>
  </React.StrictMode>,
)
```

```tsx
// App.tsx
import { Routes, Route, Link } from 'react-router-dom'
import Home from './pages/Home'
import About from './pages/About'

function App() {
  return (
    <div>
      {/* Vue Routerの<router-link>に相当 */}
      <nav>
        <Link to="/">Home</Link>
        <Link to="/about">About</Link>
      </nav>

      {/* Vue Routerの<router-view>に相当 */}
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </div>
  )
}

export default App
```

### 2. Data Mode（データモード）のセットアップ 🟡

Nuxtの`asyncData`のような機能を使いたい場合は、このモードを選択します。

```tsx
// main.tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { RouterProvider, createBrowserRouter } from 'react-router-dom'

// ルート設定（Vue Routerのroutes配列に相当）
const router = createBrowserRouter([
  {
    path: "/",
    element: <Root />,
    loader: rootLoader, // Nuxtのasync dataに相当
    children: [
      {
        path: "products",
        element: <Products />,
        loader: productsLoader,
      },
      {
        path: "products/:id",
        element: <ProductDetail />,
        loader: productDetailLoader,
      }
    ]
  }
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
```

```tsx
// loaders/productLoader.ts
export async function productDetailLoader({ params }: { params: { id: string } }) {
  // Nuxtのasync dataと同様の処理
  const response = await fetch(`/api/products/${params.id}`)
  if (!response.ok) {
    throw new Response("Product not found", { status: 404 })
  }
  return response.json()
}

// components/ProductDetail.tsx
import { useLoaderData } from 'react-router-dom'

export default function ProductDetail() {
  // loader関数の戻り値を取得
  const product = useLoaderData() as Product
  
  return (
    <div>
      <h1>{product.name}</h1>
      <p>{product.description}</p>
    </div>
  )
}
```

### 3. Framework Mode（Remixベース）のセットアップ 🔴

Nuxt.jsのようなフルスタックフレームワークを求める場合：

```bash
# Remixプロジェクトの作成
npx create-remix@latest my-remix-app
cd my-remix-app
npm install
```

```tsx
// app/routes/products.$id.tsx (Nuxtのpages/products/_id.vueに相当)
import { json } from "@remix-run/node"
import { useLoaderData } from "@remix-run/react"

// サーバーサイドで実行される
export async function loader({ params }) {
  const product = await db.product.findUnique({
    where: { id: params.id }
  })
  return json({ product })
}

// クライアントサイドコンポーネント
export default function ProductPage() {
  const { product } = useLoaderData<typeof loader>()
  return <div>{product.name}</div>
}
```

## 🔧 TypeScript設定

### 基本的な型定義

```typescript
// types/router.ts
export interface RouteParams {
  id: string
}

export interface LoaderData<T> {
  data: T
  meta?: {
    lastUpdated: string
  }
}
```

### 型安全なルート定義

```typescript
// router/index.ts
import { createBrowserRouter } from 'react-router-dom'
import type { RouteObject } from 'react-router-dom'

// Vue Routerのルート定義に似た形式
const routes: RouteObject[] = [
  {
    path: '/',
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: 'users/:id',
        element: <UserDetail />,
        loader: async ({ params }) => {
          // paramsは自動的に型推論される
          return fetch(`/api/users/${params.id}`)
        },
      },
    ],
  },
]

export const router = createBrowserRouter(routes)
```

### 型安全なフック

```typescript
// hooks/useTypedParams.ts
import { useParams } from 'react-router-dom'

export function useTypedParams<T extends Record<string, string>>() {
  return useParams() as T
}

// 使用例
interface UserParams {
  userId: string
}

function UserDetail() {
  const { userId } = useTypedParams<UserParams>()
  // userIdは string 型として扱われる
}
```

## 🔄 Nuxtプロジェクトからの移行

Nuxtプロジェクトから移行する場合の対応表：

| Nuxt | React (Vite) | 説明 |
|------|--------------|------|
| `nuxt.config.ts` | `vite.config.ts` | ビルド設定 |
| `pages/` ディレクトリ | ルート設定オブジェクト | ページとルートの対応 |
| `layouts/` | コンポーネント + Outlet | レイアウトの実装 |
| `components/` | `src/components/` | 共通コンポーネント |
| `.env` | `.env.VITE_*` | 環境変数（プレフィックスが必要） |

### 移行例

```javascript
// Nuxt（ファイルベースルーティング）
// pages/index.vue → /
// pages/users/[id].vue → /users/:id

// React Router（設定ベースルーティング）
const routes = [
  {
    path: '/',
    element: <Home />,
    handle: { requiresAuth: false }, // Nuxtのmiddlewareに相当
  },
  {
    path: '/users/:id',
    element: <UserDetail />,
    loader: userLoader, // Nuxtのasync dataに相当
  }
]
```

**主な違い:**
- **Nuxt**: ファイル作成だけでルートが生成される
- **React Router**: 明示的にルート設定を記述する必要がある
- **利点**: 条件付きルートや複雑なルート構造を実装しやすい

## 🛠️ 開発ツール

### React Developer Tools

NuxtのVue DevtoolsのReact版です：

1. Chrome/Firefox拡張機能をインストール
2. Components タブでルート構造を確認
3. Profiler タブでパフォーマンスを分析

### React Router DevTools

2025年現在、React Router専用のDevToolsが利用可能：

```tsx
// 開発環境でのみ有効化
if (import.meta.env.DEV) {
  import('@react-router/devtools').then(({ ReactRouterDevtools }) => {
    ReactRouterDevtools.init(router)
  })
}
```

## ⚡ パフォーマンス設定

### プリフェッチング

```tsx
// Nuxtのプリフェッチに相当
<Link to="/about" prefetch="intent">
  About
</Link>
```

### 遅延読み込み

```tsx
// Nuxtの動的インポートに相当
const About = lazy(() => import('./pages/About'))

const router = createBrowserRouter([
  {
    path: '/about',
    element: (
      <Suspense fallback={<Loading />}>
        <About />
      </Suspense>
    ),
  },
])
```

## 🎓 まとめ

React Router v7のセットアップは、Nuxtエコシステムと多くの共通点があります：

1. **パッケージ管理**: npm/yarn/pnpmで簡単にインストール
2. **モード選択**: プロジェクトの要件に応じて3つのモードから選択
3. **TypeScript**: Nuxtと同様に第一級のサポート
4. **開発ツール**: 充実したデバッグツール

次章では、実際のルーティング実装について詳しく見ていきます。

---

**🔗 次章**: [基本的なルーティング](./03-basic-routing.md)