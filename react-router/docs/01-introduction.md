# React Routerとは - Vue Routerとの比較 🟢

## 📖 この章で学ぶこと

- React Routerの基本概念と哲学
- Vue Routerとの共通点・相違点
- React Router v7 (2025年版)の新機能
- 3つのルーティングモード

**想定読了時間**: 15分

---

## 🎯 React Routerとは

React Routerは、Reactアプリケーションにおけるクライアントサイドルーティングを実現するライブラリです。2025年現在のv7では、「React 18からReact 19への橋渡し」として、より柔軟で強力なルーティングソリューションを提供しています。

### Vue Routerユーザーから見たReact Router

Vue Routerに慣れている方なら、以下の点で親近感を感じるでしょう：

```javascript
// Vue Router
const routes = [
  {
    path: '/users/:id',
    component: UserDetail,
    children: [
      { path: 'posts', component: UserPosts }
    ]
  }
]

// React Router v7
const router = createBrowserRouter([
  {
    path: "/users/:id",
    element: <UserDetail />,
    children: [
      { path: "posts", element: <UserPosts /> }
    ]
  }
])
```

基本的な構造は非常に似ていますが、React Routerは「コンポーネント」の代わりに「element」という用語を使い、JSXで直接要素を指定します。

## 🔄 Vue RouterとReact Routerの比較表

| 機能 | Vue Router | React Router | 備考 |
|------|------------|--------------|------|
| **ルート定義** | JavaScriptオブジェクト | JavaScriptオブジェクト/JSX | React RouterはJSXでも定義可能 |
| **動的インポート** | `() => import()` | `React.lazy()` | 両方とも遅延読み込みをサポート |
| **ナビゲーションガード** | `beforeEach`, `beforeResolve` | `loader`関数 | React Routerはより宣言的 |
| **メタデータ** | `meta`フィールド | `handle`プロパティ | 同様の概念 |
| **トランジション** | `<transition>` | 外部ライブラリ | React Routerは組み込みなし |
| **スクロール制御** | 組み込み | 手動実装 | React Routerは自動スクロールなし |

## 🚀 React Router v7の3つのモード

React Router v7では、プロジェクトのニーズに応じて3つのモードから選択できます：

### 1. **Declarative Mode（宣言的モード）** 🟢
最もシンプルで、Vue Routerに最も近い使用感です。

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

**Vue開発者へのポイント**: これはVue Routerの`<router-view>`に似ていますが、Reactでは明示的に`<Routes>`と`<Route>`を使います。

### 2. **Data Mode（データモード）** 🟡
Nuxt.jsの`asyncData`やVue Router 4のナビゲーションガードに似た、データ取得機能を持ちます。

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

**Vue開発者へのポイント**: `loader`は、Vue Routerの`beforeEnter`ガードとNuxtの`asyncData`を組み合わせたような機能です。

### 3. **Framework Mode（フレームワークモード）** 🔴
Remixとの完全統合を提供し、フルスタックアプリケーション開発が可能です。

```jsx
// routes.ts (ファイルベースルーティング)
import { index, route } from "@react-router/dev/routes";

export default [
  index("routes/home.tsx"),
  route("products/:id", "routes/product.tsx"),
];
```

**Vue開発者へのポイント**: これはNuxt.jsのファイルベースルーティングに似ていますが、より明示的な設定が可能です。

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

## 💡 Vue開発者のための重要な概念の違い

### 1. **コンポーネント中心 vs Element中心**
- Vue Router: `component: UserDetail`
- React Router: `element: <UserDetail />`

React RouterはJSXを直接使用するため、propsを渡すのが簡単です：
```jsx
element: <UserDetail defaultTab="profile" />
```

### 2. **グローバルガード vs ローカルLoader**
Vue Routerのグローバルガードに対して、React Routerは各ルートに`loader`を定義します：

```javascript
// Vue Router - グローバル
router.beforeEach((to, from, next) => {
  // 全ルート共通の処理
});

// React Router - ローカル
{
  path: "/admin",
  loader: async () => {
    // このルート専用の処理
  }
}
```

### 3. **テンプレート vs JSX**
Vue Routerは`<router-view>`をテンプレートに配置しますが、React Routerは`<Outlet>`をJSX内で使用します：

```jsx
// レイアウトコンポーネント
function Layout() {
  return (
    <div>
      <Header />
      <Outlet /> {/* Vue Routerの<router-view>に相当 */}
      <Footer />
    </div>
  );
}
```

## 🎓 まとめ

React Router v7は、Vue Routerユーザーにとって親しみやすい設計でありながら、Reactのエコシステムに最適化されています。主な違いは：

1. **JSXベース**: より柔軟なコンポーネント構成が可能
2. **フックベース**: Vue 3のComposition APIと同様の考え方
3. **データフェッチング統合**: Nuxt.jsのような事前データ取得が標準機能
4. **型安全性**: TypeScriptとの深い統合

次章では、これらのモードのセットアップ方法を詳しく見ていきます。

---

**🔗 次章**: [インストールと基本セットアップ](./02-installation.md)