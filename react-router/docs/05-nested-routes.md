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

### Vue Routerとの比較

まず、Vue Routerのネストされたルートとの比較から始めましょう：

```javascript
// Vue Router
const routes = [
  {
    path: '/admin',
    component: AdminLayout,
    children: [
      { path: '', component: Dashboard },        // /admin
      { path: 'users', component: UserList },    // /admin/users
      { path: 'users/:id', component: UserDetail } // /admin/users/:id
    ]
  }
]

// React Router (Data Mode)
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

// React Router (Declarative Mode)
<Routes>
  <Route path="/admin" element={<AdminLayout />}>
    <Route index element={<Dashboard />} />
    <Route path="users" element={<UserList />} />
    <Route path="users/:id" element={<UserDetail />} />
  </Route>
</Routes>
```

## 🔧 Outlet コンポーネント

Vue Routerの`<router-view>`に相当するのが`<Outlet>`コンポーネントです：

```tsx
// Vue.js のレイアウトコンポーネント
<template>
  <div class="admin-layout">
    <nav><!-- サイドバー --></nav>
    <main>
      <router-view /> <!-- 子ルートがここに表示される -->
    </main>
  </div>
</template>

// React のレイアウトコンポーネント
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

## 🔄 Vue Router → React Router チートシート

| 概念 | Vue Router | React Router |
|------|------------|--------------|
| 子ルート表示 | `<router-view>` | `<Outlet>` |
| ネストルート定義 | `children` 配列 | `children` 配列 |
| インデックスルート | `path: ''` | `index: true` |
| レイアウト継承 | 自動 | 明示的な `<Outlet>` |
| データ共有 | props/provide/inject | Outlet context/React Context |

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

React Routerのネストされたルートは、Vue Routerと似た概念でありながら、より柔軟で型安全なレイアウト構築を可能にします：

1. **Outletコンポーネント**: Vue Routerの`<router-view>`に相当
2. **階層化されたレイアウト**: 複雑なアプリケーション構造に対応
3. **データ共有**: Outlet ContextやReact Contextとの組み合わせ
4. **型安全性**: TypeScriptとの優れた統合

次章では、データローディングとActionsについて学びます。

---

**🔗 次章**: [データローディングとActions](./06-data-loading.md)