# データローディングとActions 🟡

## 📖 この章で学ぶこと

- loader関数によるデータの事前取得
- action関数によるフォーム処理
- useLoaderData と useActionData の使用方法
- Nuxtのasync dataやfetchとの比較
- 実用的なデータフェッチパターン

**想定読了時間**: 25分

---

## 🎯 Loader関数 - データの事前取得

### Nuxtとの比較

React Routerの`loader`は、NuxtのSSRデータフェッチング機能と似た概念です：

```javascript
// Nuxt.js
export default {
  async asyncData({ params, $axios }) {
    const user = await $axios.$get(`/api/users/${params.id}`)
    return { user }
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
        throw new Response("User not found", { status: 404 })
      }
      return response.json()
    }
  }
])
```

### 基本的なLoader実装

```tsx
// loaders/userLoader.ts
export async function userLoader({ params }: LoaderFunctionArgs) {
  const userId = params.id!
  
  try {
    const user = await fetch(`/api/users/${userId}`).then(r => r.json())
    return { user }
  } catch (error) {
    // エラーをthrowすると、errorElementが表示される
    throw new Response("ユーザーが見つかりません", { 
      status: 404,
      statusText: "User Not Found" 
    })
  }
}

// ルート定義
const router = createBrowserRouter([
  {
    path: "/users/:id",
    element: <UserDetail />,
    loader: userLoader,
    errorElement: <ErrorPage />
  }
])

// コンポーネント内でのデータ使用
function UserDetail() {
  const { user } = useLoaderData() as { user: User }
  
  return (
    <div>
      <h1>{user.name}</h1>
      <p>{user.email}</p>
    </div>
  )
}
```

### 並列データローディング

```tsx
// 複数のAPIを並列で呼び出し
export async function dashboardLoader() {
  const [
    userResponse,
    statsResponse,
    notificationsResponse
  ] = await Promise.all([
    fetch('/api/user/profile'),
    fetch('/api/dashboard/stats'),
    fetch('/api/notifications')
  ])
  
  return {
    user: await userResponse.json(),
    stats: await statsResponse.json(),
    notifications: await notificationsResponse.json()
  }
}

// コンポーネント
function Dashboard() {
  const { user, stats, notifications } = useLoaderData() as {
    user: User
    stats: DashboardStats
    notifications: Notification[]
  }
  
  return (
    <div>
      <UserProfile user={user} />
      <StatsOverview stats={stats} />
      <NotificationList notifications={notifications} />
    </div>
  )
}
```

## 🔄 Action関数 - フォーム処理

### 基本的なAction実装

Vue/Nuxtのフォーム処理と比較して、React Routerのactionはより宣言的です：

```tsx
// actions/userActions.ts
export async function updateUserAction({ request, params }: ActionFunctionArgs) {
  const userId = params.id!
  const formData = await request.formData()
  
  const userData = {
    name: formData.get('name') as string,
    email: formData.get('email') as string
  }
  
  try {
    const response = await fetch(`/api/users/${userId}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(userData)
    })
    
    if (!response.ok) {
      return {
        error: 'ユーザーの更新に失敗しました'
      }
    }
    
    return {
      success: true,
      user: await response.json()
    }
  } catch (error) {
    return {
      error: 'ネットワークエラーが発生しました'
    }
  }
}

// ルート定義
const router = createBrowserRouter([
  {
    path: "/users/:id/edit",
    element: <UserEditForm />,
    loader: userLoader,
    action: updateUserAction
  }
])
```

### フォームコンポーネント

```tsx
import { Form, useLoaderData, useActionData, useNavigation } from 'react-router-dom'

function UserEditForm() {
  const { user } = useLoaderData() as { user: User }
  const actionData = useActionData() as { error?: string; success?: boolean } | undefined
  const navigation = useNavigation()
  
  // Nuxtのthis.$nuxt.$loadingと同様
  const isSubmitting = navigation.state === 'submitting'

  return (
    <div>
      <h1>{user.name} の編集</h1>
      
      {/* React RouterのFormコンポーネントを使用 */}
      <Form method="post">
        <div>
          <label>
            名前:
            <input 
              type="text" 
              name="name" 
              defaultValue={user.name}
              required 
            />
          </label>
        </div>
        
        <div>
          <label>
            メール:
            <input 
              type="email" 
              name="email" 
              defaultValue={user.email}
              required 
            />
          </label>
        </div>
        
        <button type="submit" disabled={isSubmitting}>
          {isSubmitting ? '更新中...' : '更新'}
        </button>
      </Form>
      
      {/* エラー・成功メッセージの表示 */}
      {actionData?.error && (
        <div className="error">{actionData.error}</div>
      )}
      
      {actionData?.success && (
        <div className="success">更新が完了しました</div>
      )}
    </div>
  )
}
```

## 🔗 データの関連性と再取得

### ルート間でのデータ共有

```tsx
// 関連するデータを効率的に管理
const router = createBrowserRouter([
  {
    path: "/users",
    element: <UsersLayout />,
    loader: usersListLoader,
    children: [
      {
        index: true,
        element: <UsersList />
      },
      {
        path: ":id",
        element: <UserDetail />,
        loader: userDetailLoader
      }
    ]
  }
])

// 親のloaderデータを子コンポーネントで使用
import { useRouteLoaderData } from 'react-router-dom'

function UserDetail() {
  // 親ルートのloaderデータを取得
  const usersList = useRouteLoaderData("users") as User[]
  const { user } = useLoaderData() as { user: User }
  
  return (
    <div>
      <p>総ユーザー数: {usersList.length}</p>
      <h1>{user.name}</h1>
    </div>
  )
}
```

### データの自動再取得

```tsx
// actionが実行された後、関連するloaderが自動的に再実行される
export async function deleteUserAction({ params }: ActionFunctionArgs) {
  const userId = params.id!
  
  await fetch(`/api/users/${userId}`, { method: 'DELETE' })
  
  // ユーザー一覧ページにリダイレクト
  // この時、usersListLoaderが自動的に再実行される
  return redirect('/users')
}

// 手動でのデータ再取得
import { useFetcher } from 'react-router-dom'

function UserRefreshButton() {
  const fetcher = useFetcher()
  
  const handleRefresh = () => {
    // loaderを手動で再実行
    fetcher.load('/api/users/current')
  }
  
  return (
    <button onClick={handleRefresh}>
      {fetcher.state === 'loading' ? '更新中...' : 'データを更新'}
    </button>
  )
}
```

## 🎨 実用的なデータパターン

### 1. 検索とフィルタリング

```tsx
// 検索パラメータを考慮したloader
export async function productsLoader({ request }: LoaderFunctionArgs) {
  const url = new URL(request.url)
  const searchParams = {
    q: url.searchParams.get('q') || '',
    category: url.searchParams.get('category') || '',
    page: parseInt(url.searchParams.get('page') || '1'),
    limit: parseInt(url.searchParams.get('limit') || '20')
  }
  
  const queryString = new URLSearchParams({
    ...searchParams,
    page: searchParams.page.toString(),
    limit: searchParams.limit.toString()
  }).toString()
  
  const products = await fetch(`/api/products?${queryString}`)
    .then(r => r.json())
  
  return { products, searchParams }
}

// 検索フォーム
function ProductSearchForm() {
  const { searchParams } = useLoaderData() as {
    products: Product[]
    searchParams: any
  }
  
  return (
    <Form method="get" role="search">
      <input 
        type="search" 
        name="q" 
        defaultValue={searchParams.q}
        placeholder="商品を検索..."
      />
      <select name="category" defaultValue={searchParams.category}>
        <option value="">すべてのカテゴリ</option>
        <option value="electronics">家電</option>
        <option value="clothing">衣類</option>
      </select>
      <button type="submit">検索</button>
    </Form>
  )
}
```

### 2. 楽観的更新

```tsx
// 楽観的UI更新を伴うアクション
function TodoItem({ todo }: { todo: Todo }) {
  const fetcher = useFetcher()
  
  // 楽観的更新: サーバーレスポンスを待たずにUIを更新
  const isCompleted = fetcher.formData 
    ? fetcher.formData.get('completed') === 'true'
    : todo.completed
  
  return (
    <div className={isCompleted ? 'completed' : ''}>
      <fetcher.Form method="post" action={`/todos/${todo.id}/toggle`}>
        <input 
          type="hidden" 
          name="completed" 
          value={(!isCompleted).toString()} 
        />
        <button type="submit">
          {isCompleted ? '✓' : '○'}
        </button>
      </fetcher.Form>
      <span>{todo.title}</span>
    </div>
  )
}
```

### 3. 条件付きローディング

```tsx
// 認証状態に応じたデータ取得
export async function protectedLoader({ request }: LoaderFunctionArgs) {
  const token = await getAuthToken(request)
  
  if (!token) {
    // 認証が必要な場合はログインページにリダイレクト
    throw redirect('/login')
  }
  
  try {
    const [userData, dashboardData] = await Promise.all([
      fetch('/api/user', { 
        headers: { Authorization: `Bearer ${token}` } 
      }).then(r => r.json()),
      fetch('/api/dashboard', { 
        headers: { Authorization: `Bearer ${token}` } 
      }).then(r => r.json())
    ])
    
    return { user: userData, dashboard: dashboardData }
  } catch (error) {
    // 認証エラーの場合
    throw redirect('/login')
  }
}
```

## 🔄 Vue/Nuxt → React Router チートシート

| 機能 | Vue/Nuxt | React Router |
|------|----------|--------------|
| データ事前取得 | `asyncData` | `loader` |
| フォーム送信 | `$axios.post()` | `action` + `Form` |
| ローディング状態 | `$nuxt.$loading` | `useNavigation()` |
| サーバーサイドデータ | `fetch()` | `loader` (SSR対応) |
| 楽観的更新 | 手動実装 | `useFetcher` |
| データ再取得 | `$fetch` | `useFetcher.load()` |

## 💡 ベストプラクティス

### 1. Loaderの型安全性

```typescript
// 型定義
interface UserLoaderData {
  user: User
  permissions: Permission[]
}

// Loader
export async function userLoader({ params }: LoaderFunctionArgs): Promise<UserLoaderData> {
  // 実装
}

// カスタムフック
function useUserData() {
  return useLoaderData() as UserLoaderData
}

// コンポーネント
function UserDetail() {
  const { user, permissions } = useUserData()
  // 型安全に使用可能
}
```

### 2. エラーハンドリング

```tsx
// 構造化されたエラーレスポンス
export async function userLoader({ params }: LoaderFunctionArgs) {
  try {
    const user = await fetchUser(params.id!)
    return { user }
  } catch (error) {
    if (error instanceof NotFoundError) {
      throw new Response("User not found", { status: 404 })
    }
    
    if (error instanceof UnauthorizedError) {
      throw redirect('/login')
    }
    
    // その他のエラー
    throw new Response("Internal Server Error", { status: 500 })
  }
}
```

### 3. パフォーマンス最適化

```tsx
// データのキャッシュと最適化
const dataCache = new Map()

export async function cachedLoader({ params }: LoaderFunctionArgs) {
  const cacheKey = `user-${params.id}`
  
  if (dataCache.has(cacheKey)) {
    return dataCache.get(cacheKey)
  }
  
  const data = await fetchUserData(params.id!)
  dataCache.set(cacheKey, data)
  
  return data
}
```

## 🎓 まとめ

React Routerのデータローディングシステムは、Nuxtのasync dataやfetchと似た概念でありながら、より柔軟で型安全なデータ管理を提供します：

1. **loader関数**: ルート表示前のデータ事前取得
2. **action関数**: フォーム送信とデータ更新
3. **自動再取得**: アクション後の関連データ更新
4. **楽観的更新**: レスポンシブなユーザー体験

次章では、ナビゲーションガードと認証について学びます。

---

**🔗 次章**: [ナビゲーションガードと認証](./07-navigation-guards.md)