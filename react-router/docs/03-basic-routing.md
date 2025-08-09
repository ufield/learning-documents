# 基本的なルーティング 🟢

## 📖 この章で学ぶこと

- React Routerの基本的なルーティング実装
- Link vs NavLink の使い分けと使用場面
- useNavigate によるプログラム的ナビゲーション
- Nuxtのナビゲーションとの違い
- よくあるルーティングパターンと実装例

**想定読了時間**: 20分

---

## 🎯 基本的なルート定義

### Nuxtとの比較

Nuxtではファイルベースでルートが自動生成されるのに対し、React Routerでは明示的にルートを定義します：

**Nuxtの場合（自動生成）:**
```
pages/
  index.vue     → /
  about.vue     → /about  
  contact.vue   → /contact
```

**React Router (Declarative Mode):**
```jsx
function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/about" element={<About />} />
      <Route path="/contact" element={<Contact />} />
    </Routes>
  )
}
```

**React Router (Data Mode) - より構造化された方法:**
```javascript
const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/about", element: <About /> },
  { path: "/contact", element: <Contact /> }
])
```

**主な違い:**
- **Nuxt**: ファイル作成だけで自動的にルート生成
- **React Router**: 全ルートを明示的に設定
- **利点**: 条件付きルートや動的ルート構成が容易
- **管理**: 一箇所ですべてのルートを把握可能

## 🔗 ナビゲーションリンク

### Link コンポーネント

NuxtのNuxtLinkに相当するのが、React RouterのLinkコンポーネントです：

**Nuxtの場合:**
```vue
<template>
  <NuxtLink to="/about">About</NuxtLink>
  <NuxtLink :to="`/users/${userId}`">User</NuxtLink>
</template>
```

**React Routerの場合:**
```tsx
import { Link } from 'react-router-dom'

<Link to="/about">About</Link>
<Link to={`/users/${userId}`}>User</Link>
```

**Linkコンポーネントの特徴:**
- **SPA対応**: ページリロードなしで画面遷移
- **プログラム的**: 条件付きリンク生成が簡単
- **アクセシビリティ**: 自動的に適切なaria属性を設定
- **プリフェッチ**: ホバー時の事前読み込みに対応

### NavLink - アクティブ状態の管理

`<NavLink>`は、現在のルートと一致する場合に特別なスタイリングを適用できます：

```tsx
import { NavLink } from 'react-router-dom'

// 基本的な使用
<NavLink 
  to="/about"
  className={({ isActive }) => isActive ? "active" : ""}
>
  About
</NavLink>

// より高度な例
<NavLink
  to="/products"
  className={({ isActive, isPending }) => {
    return isActive ? "active" : isPending ? "pending" : ""
  }}
  style={({ isActive }) => ({
    fontWeight: isActive ? "bold" : "normal",
    color: isActive ? "#e74c3c" : "#333"
  })}
>
  Products
</NavLink>
```

**Nuxtとの違い**: Nuxtでは`router-link-active`クラスが自動適用されますが、React Routerでは関数を使ってより柔軟にスタイルを制御できます。

### 実用的なナビゲーションメニューの例

```tsx
function Navigation() {
  const navItems = [
    { path: '/', label: 'ホーム' },
    { path: '/products', label: '商品一覧' },
    { path: '/about', label: '会社概要' },
    { path: '/contact', label: 'お問い合わせ' }
  ]

  return (
    <nav className="main-nav">
      <ul>
        {navItems.map(item => (
          <li key={item.path}>
            <NavLink
              to={item.path}
              className={({ isActive }) => 
                `nav-link ${isActive ? 'nav-link--active' : ''}`
              }
              end // 完全一致の場合のみアクティブ
            >
              {item.label}
            </NavLink>
          </li>
        ))}
      </ul>
    </nav>
  )
}
```

## 🚀 プログラマティックナビゲーション

### useNavigate フック

Nuxtの`navigateTo()`や`$router.push()`に相当する機能です：

```tsx
import { useNavigate } from 'react-router-dom'

function LoginForm() {
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    
    try {
      await login(formData)
      
      // Nuxt: await navigateTo('/dashboard')
      navigate('/dashboard')
      
      // 置換（履歴を残さない）
      // Nuxt: await navigateTo('/dashboard', { replace: true })
      navigate('/dashboard', { replace: true })
      
      // 相対パス移動
      navigate('../products')
      
      // 戻る・進む
      navigate(-1) // ブラウザの「戻る」
      navigate(1)  // ブラウザの「進む」
    } catch (error) {
      console.error('ログイン失敗:', error)
    }
  }

  return (
    <form onSubmit={handleSubmit}>
      {/* フォームの内容 */}
    </form>
  )
}
```

**useNavigateの特徴:**
- **非同期不要**: Nuxtのように`await`は不要
- **履歴管理**: ブラウザ履歴との統合
- **相対パス**: 現在位置からの相対移動に対応
- **状態付き遷移**: stateオブジェクトを渡すことが可能
```

### ナビゲーションオプション

```tsx
// state を渡す（Vue Routerのparamsに似た機能）
navigate('/products', { 
  state: { 
    from: 'home',
    filter: 'electronics' 
  } 
})

// 受け取り側
import { useLocation } from 'react-router-dom'

function Products() {
  const location = useLocation()
  const { from, filter } = location.state || {}
  
  // stateを使った処理
}
```

## 📍 現在のルート情報の取得

### useLocation フック

NuxtでuseRouteを使って現在のルート情報を取得するのと同様に、React RouterではuseLocationを使います：

**Nuxtの場合:**
```javascript
// composables/useRoute()
const route = useRoute()
console.log(route.path)     // 現在のパス
console.log(route.query)    // クエリパラメータ
console.log(route.hash)     // ハッシュ
```

**React Routerの場合:**
```tsx
import { useLocation } from 'react-router-dom'

function CurrentPageInfo() {
  const location = useLocation()

  return (
    <div>
      <p>現在のパス: {location.pathname}</p>
      <p>クエリ文字列: {location.search}</p>
      <p>ハッシュ: {location.hash}</p>
      <p>state: {JSON.stringify(location.state)}</p>
    </div>
  )
}
```

**対応関係:**
- **Nuxt**: `route.path` → **React Router**: `location.pathname`
- **Nuxt**: `route.query` → **React Router**: `new URLSearchParams(location.search)`
- **Nuxt**: `route.hash` → **React Router**: `location.hash`
- **追加機能**: `location.state`でナビゲーション時のデータ受け渡しが可能

## 🎨 実践的なルーティングパターン

### 1. 条件付きルーティング

```tsx
function App() {
  const { user } = useAuth()

  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route 
        path="/dashboard" 
        element={user ? <Dashboard /> : <Navigate to="/login" />} 
      />
      <Route path="/login" element={<Login />} />
    </Routes>
  )
}
```

### 2. デフォルトルート（404ページ）

```tsx
<Routes>
  <Route path="/" element={<Home />} />
  <Route path="/about" element={<About />} />
  {/* 404ページ - 最後に配置 */}
  <Route path="*" element={<NotFound />} />
</Routes>
```

### 3. インデックスルート

```tsx
<Routes>
  <Route path="/" element={<Layout />}>
    {/* indexルートは親のパスで表示される */}
    <Route index element={<Home />} />
    <Route path="about" element={<About />} />
    <Route path="products" element={<Products />} />
  </Route>
</Routes>
```

## 🔄 Nuxt.js → React Router チートシート

| 操作 | Nuxt.js | React Router | 
|------|---------|--------------|
| リンク作成 | `<NuxtLink to="/about">` | `<Link to="/about">` |
| アクティブリンク | `router-link-active` | `<NavLink className={...}>` |
| プログラム的遷移 | `navigateTo()` / `$router.push()` | `navigate()` |
| 現在のルート | `useRoute()` | `useLocation()` |
| ルート監視 | `watch(() => route.path)` | `useEffect` + `location` |
| ファイルベース | `pages/about.vue` | ルート設定オブジェクト |

## 💡 ベストプラクティス

### 1. リンクコンポーネントの選択

```tsx
// 通常のナビゲーション → Link
<Link to="/about">About</Link>

// メニューやタブ → NavLink
<NavLink to="/products" className={({ isActive }) => ...}>
  Products
</NavLink>

// 外部リンク → 通常の<a>タグ
<a href="https://example.com" target="_blank" rel="noopener noreferrer">
  External Link
</a>
```

### 2. ナビゲーションの型安全性

```typescript
// ルートパスを定数化
export const ROUTES = {
  HOME: '/',
  PRODUCTS: '/products',
  PRODUCT_DETAIL: (id: string) => `/products/${id}`,
  ABOUT: '/about',
} as const

// 使用例
<Link to={ROUTES.PRODUCTS}>商品一覧</Link>
navigate(ROUTES.PRODUCT_DETAIL(productId))
```

### 3. ナビゲーションガードの実装

```tsx
function PrivateRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuth()
  const location = useLocation()

  if (!isAuthenticated) {
    // ログイン後に元のページに戻れるようにstateを保存
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  return <>{children}</>
}

// 使用例
<Routes>
  <Route path="/dashboard" element={
    <PrivateRoute>
      <Dashboard />
    </PrivateRoute>
  } />
</Routes>
```

## 🎓 まとめ

React Routerの基本的なルーティングは、Nuxtのファイルベースルーティングとは異なるアプローチですが、Reactのコンポーネントベース設計に最適化されています：

1. **明示的なルート定義**: すべてのルートを一箇所で管理
2. **フックベースのAPI**: `useNavigate`、`useLocation`などReact Hooksの活用
3. **柔軟なリンクコンポーネント**: `Link`と`NavLink`の使い分けで様々なUIに対応
4. **プログラム的制御**: 条件付きルートや動的ルート生成が容易
5. **TypeScript統合**: 型安全性による開発効率の向上

Nuxtの「ファイルを作るだけ」の簡単さはありませんが、その分より細かい制御と柔軟性を得られます。特に大規模なアプリケーションでは、この明示的なアプローチが威力を発揮します。

次章では、動的ルーティングとパラメータの詳細な扱い方について学びます。

---

**🔗 次章**: [動的ルートとパラメータ](./04-route-parameters.md)