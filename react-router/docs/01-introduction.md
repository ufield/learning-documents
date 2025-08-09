# React Routerとは - Nuxtとの対比 🟢

## 📖 この章で学ぶこと

- React Routerの基本概念と哲学
- Nuxtのルーティングとの違いと共通点
- React Router v7 (2025年版)の新機能
- 3つのルーティングモードの詳細解説

**想定読了時間**: 15分

---

## 🎯 React Routerとは

React Routerは、Reactアプリケーションにおけるクライアントサイドルーティングを実現するライブラリです。2025年現在のv7では、「React 18からReact 19への橋渡し」として、より柔軟で強力なルーティングソリューションを提供しています。

### Nuxtユーザーから見たReact Router

Nuxt.jsに慣れている方にとって、React Routerは以下のような特徴があります：

**Nuxtの場合（ファイルベース）:**
```
pages/
  index.vue          → /
  users/
    index.vue        → /users
    [id].vue         → /users/:id
    [id]/
      posts.vue      → /users/:id/posts
```

**React Router v7の場合（設定ベース）:**
```javascript
const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/users", element: <UsersList /> },
  { 
    path: "/users/:id", 
    element: <UserDetail />,
    children: [
      { path: "posts", element: <UserPosts /> }
    ]
  }
])
```

**主な違い:**
- **Nuxt**: ファイル構造がそのままルート構造になる
- **React Router**: JavaScriptでルートを明示的に定義する
- **共通点**: どちらもネストされたルートをサポート
- **利点**: React Routerは条件付きルートや動的ルート生成が容易

## 🔄 Nuxtとの主な違い

### ルーティングの定義方法

**Nuxt（ファイルベース）の特徴:**
- ファイル構造がそのままURL構造になる
- 新しいページは単純にファイルを作成するだけ
- ルート設定を書く必要がない
- 自動でルートが生成される

**React Router（設定ベース）の特徴:**
- JavaScriptでルート設定を明示的に書く
- ルート構造が一箇所で管理される
- 条件付きルートや動的ルート生成が簡単
- より細かい制御が可能

### データフェッチングの違い

**Nuxtの場合:**
```javascript
// pages/users/[id].vue
export default {
  async asyncData({ params, $axios }) {
    const user = await $axios.$get(`/api/users/${params.id}`)
    return { user }
  }
}
```

**React Routerの場合:**
```javascript
// loaderという仕組みでデータを事前取得
export async function userLoader({ params }) {
  const response = await fetch(`/api/users/${params.id}`)
  return response.json()
}

// ルート設定
{ 
  path: "/users/:id", 
  element: <UserDetail />,
  loader: userLoader 
}
```

**主な違い:**
- **Nuxt**: コンポーネントファイル内でasyncDataを定義
- **React Router**: 独立したloader関数を定義してルートに関連付け
- **共通点**: どちらもページ表示前にデータを取得
- **利点**: React Routerはloader関数を再利用しやすい

## 🚀 React Router v7の3つのモード

React Router v7では、プロジェクトのニーズに応じて3つのモードから選択できます：

### 1. **Declarative Mode（宣言的モード）** 🟢
最もシンプルで理解しやすいモードです。JSXでルートを直接宣言します。

```jsx
// 基本的な使い方
import { BrowserRouter, Routes, Route } from "react-router-dom";

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/about" element={<About />} />
      </Routes>
    </BrowserRouter>
  );
}
```

**特徴:**
- JSX内でルートを定義する最も直感的な方法
- `<Routes>`と`<Route>`コンポーネントを使用
- Nuxtのページファイルのような感覚で、見た目で理解しやすい
- 小〜中規模のアプリケーションに適している

### 2. **Data Mode（データモード）** 🟡
Nuxtの`asyncData`に似た、データ取得機能を持つ高度なモードです。

```jsx
const router = createBrowserRouter([
  {
    path: "/products/:id",
    element: <Product />,
    loader: async ({ params }) => {
      // Nuxtのasync dataのような事前データ取得
      const product = await fetch(`/api/products/${params.id}`).then(r => r.json());
      return { product };
    }
  }
]);

// コンポーネント内でデータを使用
function Product() {
  const { product } = useLoaderData();
  return <div>{product.name}</div>;
}
```

**特徴:**
- **loader関数**: ページ表示前にデータを取得（Nuxtのasync dataと同等）
- **action関数**: フォーム送信やデータ更新を処理
- **より構造化**: 設定オブジェクトでルートを管理
- **パフォーマンス**: データとルートのコード分割が可能
- **中〜大規模アプリケーション**: 複雑なデータフローに対応

### 3. **Framework Mode（フレームワークモード）** 🔴
Remixフレームワークとの統合で、Nuxtのようなフルスタック開発が可能です。

```jsx
// routes.ts (ファイルベースルーティング)
import { index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("products/:id", "routes/product.tsx"),
];
```

**特徴:**
- **Nuxtライク**: ファイルベースルーティングとフルスタック機能
- **サーバーサイド**: SSR、API routes、サーバーアクション
- **統合開発**: フロントエンドとバックエンドを一体で開発
- **エンタープライズ**: 大規模アプリケーション向け
- **Remixベース**: 実績のあるフルスタックフレームワーク

## 🆕 2025年の新機能

React Router v7では、以下の新機能が追加されています：

### 1. **React Server Components (RSC) サポート** 🔴
```jsx
// サーバーコンポーネントとして定義
export default async function ProductList() {
  const products = await db.products.findAll();
  return <ProductGrid products={products} />;
}
```

### 2. **型安全性の向上** 🟡
```typescript
// 完全に型付けされたルートパラメータ
const router = createBrowserRouter<{
  "/users/:userId": { userId: string };
  "/posts/:postId": { postId: string };
}>([...]);
```

### 3. **ミドルウェアAPI** 🔴
```javascript
// Express風のミドルウェア (v7.8.0以降)
export async function middleware({ request, params }) {
  // 認証チェック、ロギングなど
  if (!request.headers.get("authorization")) {
    throw new Response("Unauthorized", { status: 401 });
  }
}
```

## 💡 Nuxt開発者のための重要な概念の違い

### 1. **ファイルベース vs 設定ベース**
**Nuxtの場合:**
- ファイルを作成するだけでルートが自動生成される
- `pages/users/[id].vue` → `/users/:id`

**React Routerの場合:**
- ルート設定を明示的に書く必要がある
- `{ path: "/users/:id", element: <UserDetail /> }`

### 2. **asyncData vs loader関数**
**Nuxtの場合:**
```javascript
// コンポーネント内で定義
export default {
  async asyncData({ params }) {
    // データ取得処理
  }
}
```

**React Routerの場合:**
```javascript
// 独立した関数として定義
export async function userLoader({ params }) {
  // データ取得処理
}

// ルート設定に関連付け
{ path: "/users/:id", element: <UserDetail />, loader: userLoader }
```

### 3. **NuxtPage vs Outlet**
**Nuxtの場合:**
```vue
<template>
  <div>
    <Header />
    <NuxtPage />  <!-- 子ページがここに表示 -->
    <Footer />
  </div>
</template>
```

**React Routerの場合:**
```jsx
function Layout() {
  return (
    <div>
      <Header />
      <Outlet />  {/* 子ルートがここに表示 */}
      <Footer />
    </div>
  );
}
```

## 🎓 まとめ

React Router v7は、Nuxtユーザーにとって理解しやすい設計でありながら、Reactのエコシステムに最適化されています。主な特徴は：

1. **JSXベース**: より柔軟で宣言的なルート定義が可能
2. **フックベース**: React Hooksを活用したモダンな設計
3. **データフェッチング統合**: NuxtのasyncDataに匹敵する事前データ取得機能
4. **型安全性**: TypeScriptとの深い統合で開発効率向上
5. **モード選択**: プロジェクトの規模に応じて最適なモードを選択可能

Nuxtの「ファイルを作るだけ」の簡単さに対して、React Routerは「設定で明示的に定義」するアプローチです。最初は手間に感じるかもしれませんが、大規模になるほどその柔軟性と制御の細かさが威力を発揮します。

次章では、これらのモードの具体的なセットアップ方法を詳しく見ていきます。

---

**🔗 次章**: [インストールと基本セットアップ](./02-installation.md)