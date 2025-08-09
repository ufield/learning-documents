# ネストされたルートとレイアウト 🟡

## 📖 この章で学ぶこと

- ネストされたルートの定義と実装
- Outletコンポーネントの使用方法
- 共通レイアウトパターンの作成
- Vue Routerのネストされたルートとの比較
- 実用的なレイアウト設計パターン

**想定読了時間**: 20分

---

## 🎯 ネストされたルートの基本概念

### Nuxtとの比較

Nuxtのネストされたルートと、React Routerでの実装方法を比較してみましょう：

**Nuxtの場合（ディレクトリ構造）:**
```
pages/
  admin/
    index.vue        → /admin
    users/
      index.vue      → /admin/users  
      [id].vue       → /admin/users/:id

layouts/
  admin.vue          # 共通レイアウト
```

**React Router (Data Mode):**
```javascript
const router = createBrowserRouter([
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      { index: true, element: <Dashboard /> },      // /admin
      { path: "users", element: <UserList /> },     // /admin/users
      { path: "users/:id", element: <UserDetail /> } // /admin/users/:id
    ]
  }
])
```

**React Router (Declarative Mode):**
```jsx
<Routes>
  <Route path="/admin" element={<AdminLayout />}>
    <Route index element={<Dashboard />} />
    <Route path="users" element={<UserList />} />
    <Route path="users/:id" element={<UserDetail />} />
  </Route>
</Routes>
```

**主な違い:**
- **Nuxt**: フォルダ構造で階層を表現、レイアウトは別ファイル
- **React Router**: 設定オブジェクトやJSXで階層を表現、レイアウトは親ルートの`element`
- **共通点**: どちらもネストされた構造をサポート
- **利点**: React Routerは条件付き階層やプログラム的な構造変更が容易

## 🔧 Outlet コンポーネント

NuxtのNuxtPageに相当するのが、React RouterのOutletコンポーネントです：

**Nuxtのレイアウトコンポーネント (layouts/admin.vue):**
```vue
<template>
  <div class="admin-layout">
    <nav class="sidebar">
      <!-- サイドバー -->
      <NuxtLink to="/admin">ダッシュボード</NuxtLink>
      <NuxtLink to="/admin/users">ユーザー管理</NuxtLink>
      <NuxtLink to="/admin/products">商品管理</NuxtLink>
    </nav>
    <main class="content">
      <NuxtPage /> <!-- 子ページがここに表示される -->
    </main>
  </div>
</template>
```

**React Routerのレイアウトコンポーネント:**
```tsx
import { Outlet, Link } from 'react-router-dom'

function AdminLayout() {
  return (
    <div className="admin-layout">
      <nav className="sidebar">
        <Link to="/admin">ダッシュボード</Link>
        <Link to="/admin/users">ユーザー管理</Link>
        <Link to="/admin/products">商品管理</Link>
      </nav>
      <main className="content">
        <Outlet /> {/* 子ルートがここに表示される */}
      </main>
    </div>
  )
}
```

**Outletの特徴:**
- **Nuxtとの対応**: `<NuxtPage>` と同じ役割
- **自動レンダリング**: マッチした子ルートが自動的に表示される
- **データ受け渡し**: context propsで子コンポーネントにデータを渡せる
- **レイアウト継承**: 複数階層でのレイアウト共有が可能

## 🏗️ 実用的なレイアウトパターン

### 1. 多階層レイアウト

```tsx
// ルート定義
const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,      // 最上位レイアウト
    children: [
      {
        path: "app",
        element: <AppLayout />,    // アプリケーションレイアウト
        children: [
          {
            path: "dashboard",
            element: <DashboardLayout />, // ダッシュボードレイアウト
            children: [
              { index: true, element: <Overview /> },
              { path: "analytics", element: <Analytics /> }
            ]
          }
        ]
      }
    ]
  }
])

// RootLayout.tsx - 全体共通のレイアウト
function RootLayout() {
  return (
    <div className="root-layout">
      <header>
        <GlobalHeader />
      </header>
      <Outlet /> {/* AppLayoutがここに表示 */}
      <footer>
        <GlobalFooter />
      </footer>
    </div>
  )
}

// AppLayout.tsx - アプリケーション用レイアウト
function AppLayout() {
  return (
    <div className="app-layout">
      <aside>
        <MainSidebar />
      </aside>
      <main>
        <Outlet /> {/* DashboardLayoutがここに表示 */}
      </main>
    </div>
  )
}

// DashboardLayout.tsx - ダッシュボード専用レイアウト
function DashboardLayout() {
  return (
    <div className="dashboard-layout">
      <nav>
        <DashboardTabs />
      </nav>
      <div className="dashboard-content">
        <Outlet /> {/* Overview や Analytics がここに表示 */}
      </div>
    </div>
  )
}
```

### 2. 条件付きレイアウト

```tsx
// 認証状態に応じてレイアウトを切り替え
function AppRoot() {
  return (
    <Routes>
      {/* 認証不要のページ */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* 認証が必要なページ */}
      <Route path="/" element={<AuthenticatedLayout />}>
        <Route index element={<Dashboard />} />
        <Route path="profile" element={<Profile />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  )
}

// 認証チェック付きレイアウト
function AuthenticatedLayout() {
  const { user, isLoading } = useAuth()
  
  if (isLoading) {
    return <LoadingSpinner />
  }
  
  if (!user) {
    return <Navigate to="/login" replace />
  }
  
  return (
    <div className="authenticated-layout">
      <Header user={user} />
      <Outlet />
    </div>
  )
}
```

## 📊 レイアウトでのデータ共有

### 1. Outlet Context

親レイアウトから子コンポーネントにデータを渡す方法：

```tsx
// レイアウトコンポーネント
function UserLayout() {
  const { userId } = useParams()
  const [user, setUser] = useState(null)
  
  useEffect(() => {
    fetchUser(userId).then(setUser)
  }, [userId])
  
  if (!user) return <div>Loading...</div>
  
  return (
    <div>
      <h1>{user.name}</h1>
      {/* contextとしてuserデータを子コンポーネントに渡す */}
      <Outlet context={{ user, setUser }} />
    </div>
  )
}

// 子コンポーネント
import { useOutletContext } from 'react-router-dom'

interface OutletContext {
  user: User
  setUser: (user: User) => void
}

function UserProfile() {
  const { user, setUser } = useOutletContext<OutletContext>()
  
  return (
    <div>
      <h2>{user.name} のプロフィール</h2>
      {/* プロフィール編集UI */}
    </div>
  )
}
```

### 2. React Contextとの組み合わせ

```tsx
// レイアウト固有のContextを作成
const AdminContext = createContext<{
  sidebarCollapsed: boolean
  toggleSidebar: () => void
}>({
  sidebarCollapsed: false,
  toggleSidebar: () => {}
})

function AdminLayout() {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false)
  
  const toggleSidebar = () => {
    setSidebarCollapsed(prev => !prev)
  }
  
  return (
    <AdminContext.Provider value={{ sidebarCollapsed, toggleSidebar }}>
      <div className={`admin-layout ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <Sidebar />
        <main>
          <Outlet />
        </main>
      </div>
    </AdminContext.Provider>
  )
}

// 子コンポーネントでの使用
function AdminDashboard() {
  const { sidebarCollapsed, toggleSidebar } = useContext(AdminContext)
  
  return (
    <div>
      <button onClick={toggleSidebar}>
        {sidebarCollapsed ? 'サイドバーを表示' : 'サイドバーを隠す'}
      </button>
    </div>
  )
}
```

## 🎨 実用的なレイアウト例

### 1. ECサイトのレイアウト

```tsx
const router = createBrowserRouter([
  {
    path: "/",
    element: <MainLayout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: "products", element: <ProductsPage /> },
      {
        path: "account",
        element: <AccountLayout />,
        children: [
          { index: true, element: <AccountDashboard /> },
          { path: "orders", element: <OrderHistory /> },
          { path: "profile", element: <ProfileEdit /> }
        ]
      }
    ]
  }
])

// メインレイアウト
function MainLayout() {
  return (
    <div className="main-layout">
      <header>
        <Navigation />
      </header>
      <main>
        <Outlet />
      </main>
      <footer>
        <SiteFooter />
      </footer>
    </div>
  )
}

// アカウント専用レイアウト
function AccountLayout() {
  return (
    <div className="account-layout">
      <div className="container">
        <aside>
          <AccountNavigation />
        </aside>
        <main>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
```

### 2. ダッシュボードアプリケーション

```tsx
// より複雑なダッシュボードの例
function DashboardApp() {
  return (
    <Routes>
      <Route path="/" element={<PublicLayout />}>
        <Route index element={<Landing />} />
        <Route path="login" element={<Login />} />
      </Route>
      
      <Route path="/app" element={<AppLayout />}>
        <Route index element={<Navigate to="dashboard" replace />} />
        
        <Route path="dashboard" element={<DashboardLayout />}>
          <Route index element={<Overview />} />
          <Route path="analytics" element={<Analytics />} />
        </Route>
        
        <Route path="projects" element={<ProjectsLayout />}>
          <Route index element={<ProjectsList />} />
          <Route path=":projectId" element={<ProjectDetail />} />
          <Route path=":projectId/settings" element={<ProjectSettings />} />
        </Route>
        
        <Route path="settings" element={<SettingsLayout />}>
          <Route index element={<GeneralSettings />} />
          <Route path="team" element={<TeamSettings />} />
          <Route path="billing" element={<BillingSettings />} />
        </Route>
      </Route>
    </Routes>
  )
}
```

## 🔄 Nuxt.js → React Router チートシート

| 概念 | Nuxt.js | React Router |
|------|---------|--------------|
| 子ページ表示 | `<NuxtPage>` | `<Outlet>` |
| ネストルート定義 | ディレクトリ構造 | `children` 配列 |
| インデックスルート | `index.vue` | `index: true` |
| レイアウト | `layouts/` フォルダ | 親ルートの `element` |
| データ共有 | provide/inject | Outlet context/React Context |
| 共通レイアウト | `definePageMeta({ layout: 'admin' })` | レイアウトコンポーネント + `<Outlet>` |

## 💡 ベストプラクティス

### 1. レイアウトの分離

```tsx
// ❌ 悪い例: ロジックとUIが混在
function AdminLayout() {
  const [users, setUsers] = useState([])
  const [products, setProducts] = useState([])
  // ... 複雑なビジネスロジック
  
  return (
    <div>
      <Sidebar users={users} products={products} />
      <Outlet />
    </div>
  )
}

// ✅ 良い例: レイアウトは表示に集中
function AdminLayout() {
  return (
    <div className="admin-layout">
      <AdminSidebar />
      <main className="admin-content">
        <Outlet />
      </main>
    </div>
  )
}
```

### 2. 型安全なOutlet Context

```tsx
// 型定義
interface AdminOutletContext {
  currentUser: User
  permissions: Permission[]
  refreshUser: () => Promise<void>
}

// レイアウト
function AdminLayout() {
  const context: AdminOutletContext = {
    currentUser,
    permissions,
    refreshUser
  }
  
  return (
    <div>
      <Outlet context={context} />
    </div>
  )
}

// カスタムフック
function useAdminContext() {
  return useOutletContext<AdminOutletContext>()
}

// 使用
function AdminPage() {
  const { currentUser, permissions } = useAdminContext()
  // 型安全に使用可能
}
```

### 3. レスポンシブレイアウト

```tsx
function ResponsiveLayout() {
  const [isMobile, setIsMobile] = useState(false)
  
  useEffect(() => {
    const checkMobile = () => {
      setIsMobile(window.innerWidth < 768)
    }
    
    checkMobile()
    window.addEventListener('resize', checkMobile)
    return () => window.removeEventListener('resize', checkMobile)
  }, [])
  
  return (
    <div className={`layout ${isMobile ? 'mobile' : 'desktop'}`}>
      {isMobile ? <MobileNavigation /> : <DesktopSidebar />}
      <main>
        <Outlet />
      </main>
    </div>
  )
}
```

## 🎓 まとめ

React Routerのネストされたルートは、Nuxtのディレクトリベースルーティングと異なるアプローチですが、より柔軟で型安全なレイアウト構築を可能にします：

1. **Outletコンポーネント**: Nuxtの`<NuxtPage>`に相当する子ルート表示機能
2. **明示的なレイアウト設計**: 設定ベースでより複雑な構造にも対応
3. **階層的なデータ共有**: Outlet ContextやReact Contextを活用
4. **条件付きレイアウト**: 認証状態などに基づく動的レイアウト変更
5. **型安全性**: TypeScriptとの統合で開発時の安全性向上

Nuxtのように「フォルダを作るだけ」の簡潔さはありませんが、その分レイアウトの組み合わせや条件分岐、プログラム的な制御において高い柔軟性を発揮します。特に大規模なアプリケーションで複数のレイアウトパターンが必要な場合に威力を発揮します。

次章では、データローディングとActionsについて学びます。

---

**🔗 次章**: [データローディングとActions](./06-data-loading.md)