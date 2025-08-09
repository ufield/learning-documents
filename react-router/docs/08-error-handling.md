# エラー処理とフォールバック 🟡

## 📖 この章で学ぶこと

- React Routerでのエラーハンドリング戦略
- errorElementとuseRouteErrorの使用方法
- 階層的なエラー処理
- Vue/Nuxtのエラーページとの比較
- 実用的なエラー回復パターン

**想定読了時間**: 20分

---

## 🎯 エラーハンドリングの基本概念

### Vue/Nuxtとの比較

まず、Vue/NuxtのエラーハンドリングとReact Routerの比較から始めましょう：

```javascript
// Nuxt.js
export default {
  // ページレベルのエラーハンドリング
  async asyncData({ error }) {
    try {
      const data = await $fetch('/api/data')
      return { data }
    } catch (err) {
      error({ statusCode: 404, message: 'データが見つかりません' })
    }
  }
}

// React Router v7
const router = createBrowserRouter([
  {
    path: "/users/:id",
    element: <UserDetail />,
    loader: async ({ params }) => {
      const response = await fetch(`/api/users/${params.id}`)
      if (!response.ok) {
        // エラーをthrowするとerrorElementが表示される
        throw new Response("User not found", { status: 404 })
      }
      return response.json()
    },
    errorElement: <UserErrorPage />
  }
])
```

## 🚨 基本的なエラーハンドリング

### errorElement の使用

```tsx
// エラー境界の基本実装
function UserErrorPage() {
  const error = useRouteError() as any
  
  // エラーの種類に応じて適切な表示
  if (error.status === 404) {
    return (
      <div className="error-page">
        <h1>ユーザーが見つかりません</h1>
        <p>指定されたユーザーは存在しません。</p>
        <Link to="/users">ユーザー一覧に戻る</Link>
      </div>
    )
  }
  
  if (error.status === 403) {
    return (
      <div className="error-page">
        <h1>アクセス権限がありません</h1>
        <p>このページを表示する権限がありません。</p>
        <Link to="/dashboard">ダッシュボードに戻る</Link>
      </div>
    )
  }
  
  // その他の予期しないエラー
  return (
    <div className="error-page">
      <h1>エラーが発生しました</h1>
      <p>申し訳ございません。予期しないエラーが発生しました。</p>
      <details>
        <summary>エラー詳細</summary>
        <pre>{error.message || 'Unknown error'}</pre>
      </details>
      <button onClick={() => window.location.reload()}>
        ページを再読み込み
      </button>
    </div>
  )
}

// ルート定義
const router = createBrowserRouter([
  {
    path: "/users/:id",
    element: <UserDetail />,
    loader: userLoader,
    errorElement: <UserErrorPage />
  }
])
```

### 階層的なエラーハンドリング

```tsx
// ルートレベルの階層的エラーハンドリング
const router = createBrowserRouter([
  {
    path: "/",
    element: <RootLayout />,
    errorElement: <GlobalErrorPage />, // 最上位のエラーハンドラー
    children: [
      {
        path: "dashboard",
        element: <Dashboard />,
        loader: dashboardLoader,
        errorElement: <DashboardError /> // ダッシュボード専用エラー
      },
      {
        path: "users",
        element: <UsersLayout />,
        errorElement: <UsersError />, // ユーザー関連のエラー
        children: [
          {
            path: ":id",
            element: <UserDetail />,
            loader: userDetailLoader
            // errorElementなし = 親のUsersErrorを使用
          }
        ]
      }
    ]
  }
])

// グローバルエラーページ
function GlobalErrorPage() {
  const error = useRouteError()
  
  return (
    <div className="global-error">
      <h1>アプリケーションエラー</h1>
      <p>申し訳ございません。システムエラーが発生しました。</p>
      <ErrorDetails error={error} />
      <Link to="/">ホームに戻る</Link>
    </div>
  )
}
```

## 🔧 実用的なエラーハンドリングパターン

### 1. 構造化されたエラーレスポンス

```tsx
// utils/errors.ts
export class AppError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string,
    public details?: any
  ) {
    super(message)
    this.name = 'AppError'
  }
}

export class ValidationError extends AppError {
  constructor(message: string, public fields: Record<string, string>) {
    super(message, 400, 'VALIDATION_ERROR', fields)
  }
}

export class NotFoundError extends AppError {
  constructor(resource: string = 'リソース') {
    super(`${resource}が見つかりません`, 404, 'NOT_FOUND')
  }
}

// loaders/productLoader.ts
export async function productLoader({ params }: LoaderFunctionArgs) {
  try {
    const product = await fetchProduct(params.id!)
    return { product }
  } catch (error) {
    if (error instanceof NotFoundError) {
      throw new Response(error.message, { 
        status: error.status,
        statusText: error.code 
      })
    }
    
    // 予期しないエラー
    console.error('Product loader error:', error)
    throw new Response("商品情報の取得に失敗しました", { status: 500 })
  }
}
```

### 2. エラー回復機能付きコンポーネント

```tsx
// components/ErrorBoundary.tsx
function ErrorBoundaryWithRetry() {
  const error = useRouteError() as any
  const navigate = useNavigate()
  const location = useLocation()
  const [retryCount, setRetryCount] = useState(0)
  
  const handleRetry = () => {
    if (retryCount < 3) {
      setRetryCount(prev => prev + 1)
      // 現在のページを再読み込み
      navigate(location.pathname + location.search, { replace: true })
    }
  }
  
  const canRetry = retryCount < 3 && error?.status !== 404
  
  return (
    <div className="error-boundary">
      <h2>エラーが発生しました</h2>
      
      {error?.status === 404 ? (
        <div>
          <p>ページが見つかりません</p>
          <Link to="/">ホームに戻る</Link>
        </div>
      ) : (
        <div>
          <p>データの読み込みに失敗しました</p>
          {canRetry && (
            <button onClick={handleRetry}>
              再試行 ({3 - retryCount}回まで)
            </button>
          )}
          {retryCount >= 3 && (
            <p>複数回試行しましたが、エラーが解決されませんでした。</p>
          )}
        </div>
      )}
      
      <details>
        <summary>エラー詳細</summary>
        <pre>{JSON.stringify(error, null, 2)}</pre>
      </details>
    </div>
  )
}
```

### 3. ネットワークエラーの処理

```tsx
// hooks/useNetworkStatus.ts
export function useNetworkStatus() {
  const [isOnline, setIsOnline] = useState(navigator.onLine)
  
  useEffect(() => {
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])
  
  return isOnline
}

// components/NetworkErrorBoundary.tsx
function NetworkErrorBoundary() {
  const error = useRouteError() as any
  const isOnline = useNetworkStatus()
  const navigate = useNavigate()
  const location = useLocation()
  
  const isNetworkError = error?.message?.includes('fetch') || !isOnline
  
  if (isNetworkError) {
    return (
      <div className="network-error">
        <h2>接続エラー</h2>
        {!isOnline ? (
          <div>
            <p>インターネット接続を確認してください</p>
            <p>接続が復旧したら自動的にページが更新されます</p>
          </div>
        ) : (
          <div>
            <p>サーバーに接続できませんでした</p>
            <button onClick={() => window.location.reload()}>
              再読み込み
            </button>
          </div>
        )}
      </div>
    )
  }
  
  // その他のエラー処理
  return <DefaultErrorBoundary />
}
```

## 🎨 ユーザビリティを考慮したエラー表示

### 1. コンテキストに応じたエラーメッセージ

```tsx
// utils/errorMessages.ts
export function getErrorMessage(error: any, context: string): string {
  const errorCode = error?.code || error?.statusText
  
  const messages: Record<string, Record<string, string>> = {
    user: {
      'NOT_FOUND': 'ユーザーが見つかりません',
      'VALIDATION_ERROR': 'ユーザー情報が正しくありません',
      'PERMISSION_DENIED': 'このユーザー情報を表示する権限がありません'
    },
    product: {
      'NOT_FOUND': '商品が見つかりません',
      'OUT_OF_STOCK': 'この商品は現在在庫切れです',
      'PRICE_CHANGED': '商品価格が変更されています'
    }
  }
  
  return messages[context]?.[errorCode] || 
         '申し訳ございません。エラーが発生しました。'
}

// components/ContextualErrorPage.tsx
function ContextualErrorPage({ context }: { context: string }) {
  const error = useRouteError()
  const errorMessage = getErrorMessage(error, context)
  
  return (
    <div className="error-page">
      <h1>{errorMessage}</h1>
      <ErrorActions error={error} context={context} />
    </div>
  )
}
```

### 2. アクション付きエラーページ

```tsx
// components/ErrorActions.tsx
function ErrorActions({ error, context }: { error: any; context: string }) {
  const navigate = useNavigate()
  
  const getActions = () => {
    const status = error?.status
    
    if (status === 404) {
      return (
        <div className="error-actions">
          <button onClick={() => navigate(-1)}>
            前のページに戻る
          </button>
          <Link to={`/${context}`}>
            {context}一覧に戻る
          </Link>
        </div>
      )
    }
    
    if (status === 403) {
      return (
        <div className="error-actions">
          <Link to="/login">ログイン</Link>
          <Link to="/dashboard">ダッシュボード</Link>
        </div>
      )
    }
    
    return (
      <div className="error-actions">
        <button onClick={() => window.location.reload()}>
          ページを再読み込み
        </button>
        <Link to="/">ホームに戻る</Link>
      </div>
    )
  }
  
  return getActions()
}
```

### 3. プログレッシブなエラー表示

```tsx
// components/ProgressiveErrorBoundary.tsx
function ProgressiveErrorBoundary() {
  const error = useRouteError() as any
  const [showDetails, setShowDetails] = useState(false)
  const [reportSent, setReportSent] = useState(false)
  
  const sendErrorReport = async () => {
    try {
      await fetch('/api/error-reports', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          error: error.message,
          stack: error.stack,
          url: window.location.href,
          timestamp: new Date().toISOString()
        })
      })
      setReportSent(true)
    } catch (err) {
      console.error('Failed to send error report:', err)
    }
  }
  
  return (
    <div className="progressive-error">
      <h2>問題が発生しました</h2>
      
      <div className="error-summary">
        <p>ページの読み込み中にエラーが発生しました。</p>
      </div>
      
      <div className="error-actions">
        <button onClick={() => window.location.reload()}>
          再読み込み
        </button>
        <Link to="/">ホームに戻る</Link>
      </div>
      
      <div className="error-details-section">
        <button 
          onClick={() => setShowDetails(!showDetails)}
          className="details-toggle"
        >
          {showDetails ? '詳細を隠す' : '詳細を表示'}
        </button>
        
        {showDetails && (
          <div className="error-details">
            <h3>エラー詳細</h3>
            <pre>{JSON.stringify(error, null, 2)}</pre>
            
            {!reportSent ? (
              <button onClick={sendErrorReport}>
                エラーレポートを送信
              </button>
            ) : (
              <p>エラーレポートが送信されました。ありがとうございます。</p>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
```

## 🔄 Vue/Nuxt → React Router チートシート

| 機能 | Vue/Nuxt | React Router |
|------|----------|--------------|
| ページレベルエラー | `error()` 関数 | `throw Response()` |
| エラーページ | `error.vue` | `errorElement` |
| エラー情報取得 | `$nuxt.error` | `useRouteError()` |
| グローバルエラー | `plugins/error.js` | ルートレベル `errorElement` |
| 404ページ | `pages/_.vue` | `path: "*"` |
| エラー回復 | 手動実装 | 手動実装 |

## 💡 ベストプラクティス

### 1. エラーの分類と対応

```tsx
// utils/errorClassification.ts
export enum ErrorType {
  NETWORK = 'network',
  AUTHORIZATION = 'authorization',
  NOT_FOUND = 'not_found',
  VALIDATION = 'validation',
  SERVER = 'server',
  UNKNOWN = 'unknown'
}

export function classifyError(error: any): ErrorType {
  if (!navigator.onLine || error?.message?.includes('fetch')) {
    return ErrorType.NETWORK
  }
  
  if (error?.status === 401 || error?.status === 403) {
    return ErrorType.AUTHORIZATION
  }
  
  if (error?.status === 404) {
    return ErrorType.NOT_FOUND
  }
  
  if (error?.status >= 400 && error?.status < 500) {
    return ErrorType.VALIDATION
  }
  
  if (error?.status >= 500) {
    return ErrorType.SERVER
  }
  
  return ErrorType.UNKNOWN
}
```

### 2. エラー監視とレポート

```tsx
// utils/errorReporting.ts
export class ErrorReporter {
  static async report(error: Error, context?: Record<string, any>) {
    // 開発環境ではコンソールにのみ出力
    if (process.env.NODE_ENV === 'development') {
      console.error('Error reported:', error, context)
      return
    }
    
    try {
      await fetch('/api/errors', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: error.message,
          stack: error.stack,
          url: window.location.href,
          userAgent: navigator.userAgent,
          timestamp: new Date().toISOString(),
          context
        })
      })
    } catch (reportError) {
      console.error('Failed to report error:', reportError)
    }
  }
  
  static setupGlobalErrorHandler() {
    window.addEventListener('error', (event) => {
      this.report(event.error, {
        type: 'global_error',
        filename: event.filename,
        lineno: event.lineno,
        colno: event.colno
      })
    })
    
    window.addEventListener('unhandledrejection', (event) => {
      this.report(new Error(event.reason), {
        type: 'unhandled_promise_rejection'
      })
    })
  }
}
```

## 🎓 まとめ

React Routerのエラーハンドリングは、Vue/Nuxtのエラー処理と似た概念でありながら、より細かい制御と階層的な管理を提供します：

1. **errorElement**: 宣言的で階層的なエラー境界
2. **useRouteError**: 構造化されたエラー情報の取得
3. **レスポンシブなエラー処理**: ネットワーク状態やコンテキストを考慮
4. **ユーザビリティ**: エラー回復とプログレッシブな情報表示

次に上級編のドキュメントを作成していきます。

---

**🔗 次章**: [パフォーマンス最適化](./09-performance.md)