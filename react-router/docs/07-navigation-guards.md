# ナビゲーションガードと認証 🟡

## 📖 この章で学ぶこと

- React Routerでの認証実装パターン
- 保護されたルートの作成方法
- リダイレクト処理とナビゲーションガード
- Vue RouterのbeforeRouteGuardとの比較
- JWTトークンベースの認証システム

**想定読了時間**: 25分

---

## 🎯 認証の基本概念

### Nuxtとの比較

Nuxtのmiddlewareと、React Routerでの認証ガード実装を比較してみましょう：

**Nuxtの場合:**
```javascript
// middleware/auth.js
export default function ({ store, redirect, route }) {
  const isAuthenticated = store.getters['auth/isAuthenticated']
  
  if (!isAuthenticated) {
    return redirect(`/login?redirect=${route.fullPath}`)
  }
}

// pages/dashboard.vue
export default {
  middleware: 'auth' // ミドルウェアを適用
}
```

**React Routerの場合:**
```javascript
// loader関数によるガード
async function protectedLoader({ request }: LoaderFunctionArgs) {
  const isAuthenticated = await checkAuth()
  
  if (!isAuthenticated) {
    const url = new URL(request.url)
    throw redirect(`/login?from=${encodeURIComponent(url.pathname)}`)
  }
  
  return null
}

// ルート設定
{
  path: "/dashboard",
  element: <Dashboard />,
  loader: protectedLoader
}
```

**主な違い:**
- **Nuxt**: middlewareフォルダでミドルウェアを定義し、ページで指定
- **React Router**: loader関数でガードロジックを実装し、ルートに関連付け
- **共通点**: どちらもページ表示前に認証チェックを実行
- **利点**: React Routerはloader内でデータ取得と認証を同時に処理可能

## 🔐 基本的な認証実装

### 認証コンテキストの作成

```tsx
// contexts/AuthContext.tsx
interface User {
  id: string
  name: string
  email: string
  role: string
}

interface AuthContextType {
  user: User | null
  isAuthenticated: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  isLoading: boolean
}

const AuthContext = createContext<AuthContextType | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  
  // 初期化時にトークンからユーザー情報を復元
  useEffect(() => {
    const initAuth = async () => {
      const token = localStorage.getItem('authToken')
      if (token) {
        try {
          const userData = await verifyToken(token)
          setUser(userData)
        } catch (error) {
          localStorage.removeItem('authToken')
        }
      }
      setIsLoading(false)
    }
    
    initAuth()
  }, [])
  
  const login = async (email: string, password: string) => {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password })
      })
      
      if (!response.ok) {
        throw new Error('ログインに失敗しました')
      }
      
      const { user, token } = await response.json()
      localStorage.setItem('authToken', token)
      setUser(user)
    } catch (error) {
      throw error
    }
  }
  
  const logout = () => {
    localStorage.removeItem('authToken')
    setUser(null)
  }
  
  return (
    <AuthContext.Provider value={{
      user,
      isAuthenticated: !!user,
      login,
      logout,
      isLoading
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
```

### 保護されたルートコンポーネント

```tsx
// components/ProtectedRoute.tsx
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()
  
  if (isLoading) {
    return <div>認証状態を確認中...</div>
  }
  
  if (!isAuthenticated) {
    // ログイン後に元のページに戻れるよう現在のパスを保存
    return <Navigate to="/login" state={{ from: location.pathname }} replace />
  }
  
  return <>{children}</>
}

// 使用例
function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        
        {/* 保護されたルート */}
        <Route path="/dashboard" element={
          <ProtectedRoute>
            <Dashboard />
          </ProtectedRoute>
        } />
        
        <Route path="/profile" element={
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        } />
      </Routes>
    </AuthProvider>
  )
}
```

## 🚪 Loader関数を使った認証ガード

### より洗練された認証チェック

```tsx
// loaders/authLoaders.ts
export async function requireAuth({ request }: LoaderFunctionArgs) {
  const token = localStorage.getItem('authToken')
  
  if (!token) {
    const url = new URL(request.url)
    throw redirect(`/login?from=${encodeURIComponent(url.pathname)}`)
  }
  
  try {
    // トークンの有効性を確認
    const user = await verifyToken(token)
    return { user }
  } catch (error) {
    localStorage.removeItem('authToken')
    throw redirect('/login')
  }
}

// 管理者権限が必要なページ用
export async function requireAdmin({ request }: LoaderFunctionArgs) {
  const { user } = await requireAuth({ request })
  
  if (user.role !== 'admin') {
    throw new Response('管理者権限が必要です', { status: 403 })
  }
  
  return { user }
}

// ルート定義
const router = createBrowserRouter([
  {
    path: "/dashboard",
    element: <Dashboard />,
    loader: requireAuth,
    errorElement: <ErrorPage />
  },
  {
    path: "/admin",
    element: <AdminPanel />,
    loader: requireAdmin,
    errorElement: <ErrorPage />
  }
])
```

### 役割ベースのアクセス制御 (RBAC)

```tsx
// utils/permissions.ts
export const ROLES = {
  USER: 'user',
  ADMIN: 'admin',
  MODERATOR: 'moderator'
} as const

export const PERMISSIONS = {
  READ_USERS: 'read:users',
  WRITE_USERS: 'write:users',
  DELETE_USERS: 'delete:users',
  MODERATE_CONTENT: 'moderate:content'
} as const

const rolePermissions = {
  [ROLES.USER]: [],
  [ROLES.MODERATOR]: [PERMISSIONS.MODERATE_CONTENT],
  [ROLES.ADMIN]: [
    PERMISSIONS.READ_USERS,
    PERMISSIONS.WRITE_USERS,
    PERMISSIONS.DELETE_USERS,
    PERMISSIONS.MODERATE_CONTENT
  ]
}

export function hasPermission(userRole: string, permission: string): boolean {
  return rolePermissions[userRole as keyof typeof rolePermissions]?.includes(permission) ?? false
}

// hooks/usePermissions.ts
export function usePermissions() {
  const { user } = useAuth()
  
  const checkPermission = (permission: string) => {
    if (!user) return false
    return hasPermission(user.role, permission)
  }
  
  const hasRole = (role: string) => {
    return user?.role === role
  }
  
  return {
    checkPermission,
    hasRole,
    isAdmin: hasRole(ROLES.ADMIN),
    isModerator: hasRole(ROLES.MODERATOR)
  }
}
```

### 条件付きレンダリングコンポーネント

```tsx
// components/PermissionGate.tsx
interface PermissionGateProps {
  permission?: string
  role?: string
  fallback?: React.ReactNode
  children: React.ReactNode
}

function PermissionGate({ 
  permission, 
  role, 
  fallback = null, 
  children 
}: PermissionGateProps) {
  const { checkPermission, hasRole } = usePermissions()
  
  let hasAccess = true
  
  if (permission) {
    hasAccess = checkPermission(permission)
  }
  
  if (role) {
    hasAccess = hasRole(role)
  }
  
  return hasAccess ? <>{children}</> : <>{fallback}</>
}

// 使用例
function UserManagement() {
  return (
    <div>
      <h1>ユーザー管理</h1>
      
      <PermissionGate permission={PERMISSIONS.READ_USERS}>
        <UserList />
      </PermissionGate>
      
      <PermissionGate 
        permission={PERMISSIONS.DELETE_USERS}
        fallback={<p>削除権限がありません</p>}
      >
        <DeleteUserButton />
      </PermissionGate>
      
      <PermissionGate role={ROLES.ADMIN}>
        <AdminOnlySection />
      </PermissionGate>
    </div>
  )
}
```

## 🔄 ログイン・ログアウト処理

### ログインページの実装

```tsx
// pages/LoginPage.tsx
function LoginPage() {
  const { login, isAuthenticated } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(false)
  
  // ログイン済みの場合はリダイレクト
  useEffect(() => {
    if (isAuthenticated) {
      const from = location.state?.from || '/dashboard'
      navigate(from, { replace: true })
    }
  }, [isAuthenticated, navigate, location])
  
  const handleSubmit = async (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault()
    setError('')
    setIsLoading(true)
    
    const formData = new FormData(e.currentTarget)
    const email = formData.get('email') as string
    const password = formData.get('password') as string
    
    try {
      await login(email, password)
      // useEffect内でリダイレクトが処理される
    } catch (error) {
      setError('メールアドレスまたはパスワードが正しくありません')
    } finally {
      setIsLoading(false)
    }
  }
  
  return (
    <div className="login-page">
      <form onSubmit={handleSubmit}>
        <h1>ログイン</h1>
        
        {error && <div className="error">{error}</div>}
        
        <div>
          <label>
            メールアドレス:
            <input type="email" name="email" required />
          </label>
        </div>
        
        <div>
          <label>
            パスワード:
            <input type="password" name="password" required />
          </label>
        </div>
        
        <button type="submit" disabled={isLoading}>
          {isLoading ? 'ログイン中...' : 'ログイン'}
        </button>
      </form>
    </div>
  )
}
```

### 自動ログアウト機能

```tsx
// hooks/useAutoLogout.ts
export function useAutoLogout(timeoutMinutes: number = 30) {
  const { logout, isAuthenticated } = useAuth()
  const timeoutRef = useRef<NodeJS.Timeout>()
  
  const resetTimer = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current)
    }
    
    if (isAuthenticated) {
      timeoutRef.current = setTimeout(() => {
        logout()
        alert('セッションがタイムアウトしました。再度ログインしてください。')
      }, timeoutMinutes * 60 * 1000)
    }
  }, [logout, isAuthenticated, timeoutMinutes])
  
  useEffect(() => {
    // ユーザーの活動を監視
    const events = ['mousedown', 'mousemove', 'keypress', 'scroll', 'touchstart']
    
    const resetOnActivity = () => resetTimer()
    
    events.forEach(event => {
      document.addEventListener(event, resetOnActivity, true)
    })
    
    resetTimer()
    
    return () => {
      events.forEach(event => {
        document.removeEventListener(event, resetOnActivity, true)
      })
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current)
      }
    }
  }, [resetTimer])
}
```

## 🔄 Vue Router → React Router チートシート

| 機能 | Vue Router | React Router |
|------|------------|--------------|
| グローバルガード | `beforeEach` | loader関数 |
| ルートガード | `beforeEnter` | loader関数 |
| コンポーネントガード | `beforeRouteEnter` | コンポーネント内チェック |
| 認証チェック | `to.meta.requiresAuth` | `ProtectedRoute` |
| リダイレクト | `next('/login')` | `redirect('/login')` |
| 権限チェック | 手動実装 | `PermissionGate` |

## 🛡️ セキュリティのベストプラクティス

### 1. トークンの安全な管理

```tsx
// utils/tokenManager.ts
class TokenManager {
  private static readonly TOKEN_KEY = 'authToken'
  private static readonly REFRESH_TOKEN_KEY = 'refreshToken'
  
  static setTokens(accessToken: string, refreshToken: string) {
    localStorage.setItem(this.TOKEN_KEY, accessToken)
    localStorage.setItem(this.REFRESH_TOKEN_KEY, refreshToken)
  }
  
  static getAccessToken(): string | null {
    return localStorage.getItem(this.TOKEN_KEY)
  }
  
  static getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY)
  }
  
  static clearTokens() {
    localStorage.removeItem(this.TOKEN_KEY)
    localStorage.removeItem(this.REFRESH_TOKEN_KEY)
  }
  
  static async refreshAccessToken(): Promise<string | null> {
    const refreshToken = this.getRefreshToken()
    if (!refreshToken) return null
    
    try {
      const response = await fetch('/api/auth/refresh', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refreshToken })
      })
      
      if (!response.ok) {
        this.clearTokens()
        return null
      }
      
      const { accessToken, refreshToken: newRefreshToken } = await response.json()
      this.setTokens(accessToken, newRefreshToken)
      
      return accessToken
    } catch (error) {
      this.clearTokens()
      return null
    }
  }
}
```

### 2. APIリクエストインターセプター

```tsx
// utils/apiClient.ts
class ApiClient {
  private static async request(url: string, options: RequestInit = {}) {
    let token = TokenManager.getAccessToken()
    
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { Authorization: `Bearer ${token}` }),
        ...options.headers
      }
    })
    
    // トークンが期限切れの場合は更新を試行
    if (response.status === 401 && token) {
      const newToken = await TokenManager.refreshAccessToken()
      
      if (newToken) {
        // 更新されたトークンで再試行
        return fetch(url, {
          ...options,
          headers: {
            'Content-Type': 'application/json',
            Authorization: `Bearer ${newToken}`,
            ...options.headers
          }
        })
      }
    }
    
    return response
  }
  
  static get(url: string) {
    return this.request(url, { method: 'GET' })
  }
  
  static post(url: string, data: any) {
    return this.request(url, {
      method: 'POST',
      body: JSON.stringify(data)
    })
  }
}
```

### 3. CSRFプロテクション

```tsx
// React Routerのaction関数でCSRFトークンを処理
export async function protectedAction({ request }: ActionFunctionArgs) {
  const formData = await request.formData()
  const csrfToken = formData.get('_token') as string
  
  // CSRFトークンの検証
  if (!isValidCSRFToken(csrfToken)) {
    throw new Response('Invalid CSRF token', { status: 403 })
  }
  
  // 実際の処理
}

// フォームコンポーネント
function SecureForm() {
  const [csrfToken, setCsrfToken] = useState('')
  
  useEffect(() => {
    // CSRFトークンを取得
    fetch('/api/csrf-token')
      .then(r => r.json())
      .then(data => setCsrfToken(data.token))
  }, [])
  
  return (
    <Form method="post">
      <input type="hidden" name="_token" value={csrfToken} />
      {/* その他のフォームフィールド */}
    </Form>
  )
}
```

## 🎓 まとめ

React Routerでの認証とナビゲーションガードは、Vue Routerのガード機能と似た概念でありながら、より柔軟で組み合わせやすい実装を可能にします：

1. **Loader関数ベースのガード**: より宣言的で型安全
2. **コンポーネントベースの保護**: 再利用可能で直感的
3. **権限ベースのアクセス制御**: スケーラブルな権限管理
4. **セキュリティ機能**: CSRFプロテクション、トークン管理

次章では、エラー処理とフォールバックについて学びます。

---

**🔗 次章**: [エラー処理とフォールバック](./08-error-handling.md)