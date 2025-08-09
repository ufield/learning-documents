# 基本的なルーティング 🟢

## 📖 この章で学ぶこと

- React Routerの基本的なルーティング実装
- Link vs NavLink の使い分け
- useNavigate によるプログラマティックナビゲーション
- Vue Routerとの実装比較
- よくあるルーティングパターン

**想定読了時間**: 15分

---

## 🎯 基本的なルート定義

### Vue Routerとの比較

まず、Vue Routerに慣れている方向けに、基本的なルート定義の比較から始めましょう：

```javascript
// Vue Router
const routes = [
  { path: '/', component: Home },
  { path: '/about', component: About },
  { path: '/contact', component: Contact }
]

// React Router (Declarative Mode)
function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/about" element={<About />} />
      <Route path="/contact" element={<Contact />} />
    </Routes>
  )
}

// React Router (Data Mode) - より構造化された方法
const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/about", element: <About /> },
  { path: "/contact", element: <Contact /> }
])
```

## 🔗 ナビゲーションリンク

### Link コンポーネント

Vue Routerの`<router-link>`に相当するのが`<Link>`コンポーネントです：

```tsx
// Vue Router
<router-link to="/about">About</router-link>
<router-link :to="{ name: 'user', params: { id: 123 }}">User</router-link>

// React Router
import { Link } from 'react-router-dom'

<Link to="/about">About</Link>
<Link to={`/users/${userId}`}>User</Link>
```

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

**Vue開発者へのポイント**: Vue Routerの`router-link-active`クラスと同様の機能ですが、React Routerではより柔軟にカスタマイズできます。

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

Vue Routerの`router.push()`に相当する機能です：

```tsx
import { useNavigate } from 'react-router-dom'

function LoginForm() {
  const navigate = useNavigate()

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    
    try {
      await login(formData)
      
      // Vue: this.$router.push('/dashboard')
      navigate('/dashboard')
      
      // 置換（履歴を残さない）
      // Vue: this.$router.replace('/dashboard')
      navigate('/dashboard', { replace: true })
      
      // 相対パス
      navigate('../products')
      
      // 戻る・進む
      navigate(-1) // 戻る
      navigate(1)  // 進む
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

Vue Routerの`$route`に相当します：

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

// Vue Routerとの比較
// Vue: this.$route.path → React: location.pathname
// Vue: this.$route.query → React: new URLSearchParams(location.search)
// Vue: this.$route.hash → React: location.hash
```

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

## 🔄 Vue Router → React Router チートシート

| 操作 | Vue Router | React Router |
|------|------------|--------------|
| リンク作成 | `<router-link to="/about">` | `<Link to="/about">` |
| アクティブリンク | `router-link-active` クラス | `<NavLink className={...}>` |
| プログラマティック遷移 | `this.$router.push()` | `navigate()` |
| 現在のルート | `this.$route` | `useLocation()` |
| ルート監視 | `watch: { $route() {} }` | `useEffect` + `location` |
| 名前付きルート | `{ name: 'user' }` | パスを直接指定 |

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

React Routerの基本的なルーティングは、Vue Routerと多くの共通概念を持ちながら、Reactのコンポーネントベースのアプローチに最適化されています：

1. **宣言的なルート定義**: JSXを使った直感的な定義
2. **フックベースのAPI**: `useNavigate`、`useLocation`など
3. **柔軟なリンクコンポーネント**: `Link`と`NavLink`の使い分け
4. **型安全性**: TypeScriptとの優れた統合

次章では、動的ルーティングとパラメータの扱い方について学びます。

---

**🔗 次章**: [動的ルートとパラメータ](./04-route-parameters.md)