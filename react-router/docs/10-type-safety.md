# 型安全なルーティング 🔴

## 📖 この章で学ぶこと

- TypeScriptとReact Routerの深い統合
- 型付きパラメータとクエリの実装
- カスタムフックによる型安全性向上
- Vue 3のTypeScript対応との比較
- 実用的な型安全パターン

**想定読了時間**: 35分

---

## 🎯 型安全ルーティングの基本概念

### Vue 3 TypeScriptとの比較

まず、Vue 3のTypeScriptサポートとReact Routerの比較から始めましょう：

```typescript
// Vue 3 + TypeScript
interface RouteParams {
  id: string
}

// composition API
export default defineComponent({
  setup() {
    const route = useRoute<RouteParams>()
    const router = useRouter()
    
    const userId: string = route.params.id // 型安全
    
    const navigateToUser = (id: string) => {
      router.push(`/users/${id}`)
    }
  }
})

// React Router v7 + TypeScript
interface UserParams {
  id: string
}

function UserDetail() {
  const { id } = useParams<UserParams>()
  const navigate = useNavigate()
  
  // idは string | undefined 型
  const userId = id! // 非null アサーションが必要
  
  const navigateToUser = (id: string) => {
    navigate(`/users/${id}`)
  }
}
```

## 🏗️ 型安全なルート定義システム

### 1. ルート定数とパス生成

```typescript
// types/routes.ts
export const ROUTES = {
  HOME: '/',
  USERS: '/users',
  USER_DETAIL: '/users/:id',
  USER_POSTS: '/users/:id/posts',
  POST_DETAIL: '/users/:userId/posts/:postId',
  ADMIN: '/admin',
  ADMIN_USERS: '/admin/users',
} as const

// ルートパラメータの型定義
export interface RouteParams {
  [ROUTES.USER_DETAIL]: { id: string }
  [ROUTES.USER_POSTS]: { id: string }
  [ROUTES.POST_DETAIL]: { userId: string; postId: string }
}

// パス生成関数
type PathBuilder<T extends keyof RouteParams> = (params: RouteParams[T]) => string

export const buildPath = {
  userDetail: ((params: RouteParams[typeof ROUTES.USER_DETAIL]) => 
    `/users/${params.id}`) as PathBuilder<typeof ROUTES.USER_DETAIL>,
    
  userPosts: ((params: RouteParams[typeof ROUTES.USER_POSTS]) => 
    `/users/${params.id}/posts`) as PathBuilder<typeof ROUTES.USER_POSTS>,
    
  postDetail: ((params: RouteParams[typeof ROUTES.POST_DETAIL]) => 
    `/users/${params.userId}/posts/${params.postId}`) as PathBuilder<typeof ROUTES.POST_DETAIL>,
}

// 使用例
const userDetailPath = buildPath.userDetail({ id: '123' })
const postPath = buildPath.postDetail({ userId: '123', postId: '456' })
```

### 2. 高度な型付きルーター

```typescript
// utils/typedRouter.ts
import { useNavigate, useParams, useSearchParams } from 'react-router-dom'

// 型安全なナビゲーション
export function useTypedNavigate() {
  const navigate = useNavigate()
  
  return {
    // 型安全なパラメータ付きナビゲーション
    toUserDetail: (params: { id: string }) => 
      navigate(buildPath.userDetail(params)),
    
    toUserPosts: (params: { id: string }) => 
      navigate(buildPath.userPosts(params)),
    
    toPostDetail: (params: { userId: string; postId: string }) => 
      navigate(buildPath.postDetail(params)),
    
    // クエリパラメータ付きナビゲーション
    toUsersWithFilter: (filters: { role?: string; status?: string }) => {
      const searchParams = new URLSearchParams()
      Object.entries(filters).forEach(([key, value]) => {
        if (value) searchParams.set(key, value)
      })
      navigate(`/users?${searchParams.toString()}`)
    }
  }
}

// 型安全なパラメータ取得
export function useTypedParams<T extends keyof RouteParams>(): RouteParams[T] | undefined {
  const params = useParams()
  return params as RouteParams[T] | undefined
}

// 使用例
function UserDetail() {
  const params = useTypedParams<typeof ROUTES.USER_DETAIL>()
  const { toUserPosts } = useTypedNavigate()
  
  if (!params) return <div>Invalid route</div>
  
  const handleViewPosts = () => {
    toUserPosts({ id: params.id })
  }
  
  return (
    <div>
      <h1>User: {params.id}</h1>
      <button onClick={handleViewPosts}>投稿を見る</button>
    </div>
  )
}
```

## 🔍 型安全なクエリパラメータ管理

### 1. Zodを使った検証付きクエリ管理

```typescript
// utils/typedQuery.ts
import { z } from 'zod'

// クエリパラメータのスキーマ定義
export const UserListQuerySchema = z.object({
  page: z.coerce.number().min(1).default(1),
  limit: z.coerce.number().min(1).max(100).default(20),
  search: z.string().optional(),
  role: z.enum(['admin', 'user', 'moderator']).optional(),
  status: z.enum(['active', 'inactive', 'pending']).optional(),
  sortBy: z.enum(['name', 'email', 'createdAt']).default('name'),
  sortOrder: z.enum(['asc', 'desc']).default('asc'),
})

export type UserListQuery = z.infer<typeof UserListQuerySchema>

// 型安全なクエリ管理フック
export function useTypedQuery<T extends z.ZodSchema>(schema: T) {
  const [searchParams, setSearchParams] = useSearchParams()
  
  // パラメータをパースして型安全な値を取得
  const parsedParams = useMemo(() => {
    const params = Object.fromEntries(searchParams.entries())
    const result = schema.safeParse(params)
    
    if (result.success) {
      return { data: result.data as z.infer<T>, error: null }
    } else {
      return { data: null, error: result.error }
    }
  }, [searchParams, schema])
  
  // 型安全な更新関数
  const updateQuery = useCallback((updates: Partial<z.infer<T>>) => {
    setSearchParams(prev => {
      const newParams = new URLSearchParams(prev)
      
      Object.entries(updates).forEach(([key, value]) => {
        if (value === undefined || value === null || value === '') {
          newParams.delete(key)
        } else {
          newParams.set(key, String(value))
        }
      })
      
      return newParams
    })
  }, [setSearchParams])
  
  return {
    query: parsedParams.data,
    error: parsedParams.error,
    updateQuery,
    resetQuery: () => setSearchParams({}),
  }
}

// 使用例
function UsersList() {
  const { query, error, updateQuery } = useTypedQuery(UserListQuerySchema)
  
  if (error) {
    console.error('Invalid query parameters:', error)
  }
  
  const handleSearch = (search: string) => {
    updateQuery({ search, page: 1 }) // pageリセット
  }
  
  const handlePageChange = (page: number) => {
    updateQuery({ page })
  }
  
  return (
    <div>
      <input 
        value={query?.search || ''} 
        onChange={e => handleSearch(e.target.value)}
        placeholder="ユーザーを検索"
      />
      <UserTable 
        filters={query} 
        onPageChange={handlePageChange}
      />
    </div>
  )
}
```

### 2. 型安全なフィルター管理

```typescript
// hooks/useTypedFilters.ts
interface FilterConfig<T> {
  defaultValues: T
  schema: z.ZodSchema<T>
  persistKey?: string
}

export function useTypedFilters<T extends Record<string, any>>(
  config: FilterConfig<T>
) {
  const { query, updateQuery } = useTypedQuery(config.schema)
  
  // デフォルト値とマージ
  const filters = useMemo(() => ({
    ...config.defaultValues,
    ...query
  }), [config.defaultValues, query])
  
  // 個別フィルター更新
  const setFilter = useCallback(<K extends keyof T>(
    key: K,
    value: T[K]
  ) => {
    updateQuery({ [key]: value } as Partial<T>)
  }, [updateQuery])
  
  // 複数フィルター更新
  const setFilters = useCallback((updates: Partial<T>) => {
    updateQuery(updates)
  }, [updateQuery])
  
  // フィルターリセット
  const resetFilters = useCallback(() => {
    updateQuery(config.defaultValues)
  }, [updateQuery, config.defaultValues])
  
  return {
    filters,
    setFilter,
    setFilters,
    resetFilters,
  }
}

// 使用例: 商品フィルター
const ProductFiltersSchema = z.object({
  category: z.string().optional(),
  minPrice: z.coerce.number().min(0).optional(),
  maxPrice: z.coerce.number().min(0).optional(),
  inStock: z.boolean().optional(),
  brand: z.string().optional(),
})

function ProductFilters() {
  const { filters, setFilter, resetFilters } = useTypedFilters({
    defaultValues: {},
    schema: ProductFiltersSchema
  })
  
  return (
    <div className="filters">
      <select 
        value={filters.category || ''} 
        onChange={e => setFilter('category', e.target.value || undefined)}
      >
        <option value="">すべてのカテゴリ</option>
        <option value="electronics">家電</option>
        <option value="clothing">衣類</option>
      </select>
      
      <input
        type="number"
        placeholder="最低価格"
        value={filters.minPrice || ''}
        onChange={e => setFilter('minPrice', Number(e.target.value) || undefined)}
      />
      
      <button onClick={resetFilters}>フィルターをリセット</button>
    </div>
  )
}
```

## 🎨 Loader/Actionの型安全性

### 1. 型付きLoader関数

```typescript
// types/loaders.ts
import { LoaderFunctionArgs } from 'react-router-dom'

// Loaderの戻り値の型定義
export interface UserDetailLoaderData {
  user: User
  permissions: Permission[]
  recentActivity: Activity[]
}

export interface UserListLoaderData {
  users: User[]
  totalCount: number
  currentPage: number
  filters: UserListQuery
}

// 型安全なLoader作成ヘルパー
export function createTypedLoader<T>(
  loaderFn: (args: LoaderFunctionArgs) => Promise<T>
) {
  return loaderFn
}

// loaders/userLoaders.ts
export const userDetailLoader = createTypedLoader<UserDetailLoaderData>(
  async ({ params }) => {
    const userId = params.id!
    
    const [user, permissions, recentActivity] = await Promise.all([
      fetchUser(userId),
      fetchUserPermissions(userId),
      fetchUserActivity(userId)
    ])
    
    return {
      user,
      permissions,
      recentActivity
    }
  }
)

export const userListLoader = createTypedLoader<UserListLoaderData>(
  async ({ request }) => {
    const url = new URL(request.url)
    const queryParams = UserListQuerySchema.parse(
      Object.fromEntries(url.searchParams.entries())
    )
    
    const [users, totalCount] = await Promise.all([
      fetchUsers(queryParams),
      fetchUsersCount(queryParams)
    ])
    
    return {
      users,
      totalCount,
      currentPage: queryParams.page,
      filters: queryParams
    }
  }
)
```

### 2. 型安全なフック

```typescript
// hooks/useTypedLoaderData.ts
export function useTypedLoaderData<T>(): T {
  return useLoaderData() as T
}

// カスタムフック
export function useUserDetail() {
  return useTypedLoaderData<UserDetailLoaderData>()
}

export function useUserList() {
  return useTypedLoaderData<UserListLoaderData>()
}

// コンポーネントでの使用
function UserDetailPage() {
  const { user, permissions, recentActivity } = useUserDetail()
  
  // すべて型安全に利用可能
  return (
    <div>
      <h1>{user.name}</h1>
      <UserPermissions permissions={permissions} />
      <RecentActivity activities={recentActivity} />
    </div>
  )
}
```

### 3. 型安全なAction関数

```typescript
// types/actions.ts
export interface UpdateUserActionData {
  success: boolean
  user?: User
  errors?: Record<string, string>
}

// Actionの入力データ検証スキーマ
export const UpdateUserSchema = z.object({
  name: z.string().min(1, '名前は必須です'),
  email: z.string().email('有効なメールアドレスを入力してください'),
  role: z.enum(['admin', 'user', 'moderator']),
})

// actions/userActions.ts
export const updateUserAction = async ({ 
  request, 
  params 
}: ActionFunctionArgs): Promise<UpdateUserActionData> => {
  const userId = params.id!
  const formData = await request.formData()
  
  const data = {
    name: formData.get('name') as string,
    email: formData.get('email') as string,
    role: formData.get('role') as string,
  }
  
  // 入力データの検証
  const validation = UpdateUserSchema.safeParse(data)
  
  if (!validation.success) {
    return {
      success: false,
      errors: validation.error.flatten().fieldErrors
    }
  }
  
  try {
    const updatedUser = await updateUser(userId, validation.data)
    return {
      success: true,
      user: updatedUser
    }
  } catch (error) {
    return {
      success: false,
      errors: { general: 'ユーザーの更新に失敗しました' }
    }
  }
}

// フォームでの使用
function UserEditForm() {
  const { user } = useUserDetail()
  const actionData = useActionData() as UpdateUserActionData | undefined
  const navigation = useNavigation()
  
  const isSubmitting = navigation.state === 'submitting'
  
  return (
    <Form method="post">
      <div>
        <label>
          名前:
          <input 
            name="name" 
            defaultValue={user.name}
            className={actionData?.errors?.name ? 'error' : ''}
          />
          {actionData?.errors?.name && (
            <span className="error">{actionData.errors.name}</span>
          )}
        </label>
      </div>
      
      <button type="submit" disabled={isSubmitting}>
        {isSubmitting ? '更新中...' : '更新'}
      </button>
    </Form>
  )
}
```

## 🛡️ 実行時型チェック

### 1. ランタイム検証パターン

```typescript
// utils/runtimeValidation.ts
export function createRuntimeValidator<T>(schema: z.ZodSchema<T>) {
  return {
    parse: (data: unknown): T => {
      const result = schema.safeParse(data)
      if (!result.success) {
        console.error('Runtime validation failed:', result.error)
        throw new Error(`Validation failed: ${result.error.message}`)
      }
      return result.data
    },
    
    safeParse: (data: unknown): { success: true; data: T } | { success: false; error: z.ZodError } => {
      return schema.safeParse(data)
    },
    
    isValid: (data: unknown): data is T => {
      return schema.safeParse(data).success
    }
  }
}

// APIレスポンスの検証
const UserResponseValidator = createRuntimeValidator(z.object({
  id: z.string(),
  name: z.string(),
  email: z.string().email(),
  role: z.enum(['admin', 'user', 'moderator']),
  createdAt: z.string().datetime(),
}))

// Loaderでの使用
export const userDetailLoader = createTypedLoader<UserDetailLoaderData>(
  async ({ params }) => {
    const response = await fetch(`/api/users/${params.id}`)
    const rawData = await response.json()
    
    // ランタイム検証
    const user = UserResponseValidator.parse(rawData)
    
    return { user, permissions: [], recentActivity: [] }
  }
)
```

### 2. 型ガード関数

```typescript
// utils/typeGuards.ts
export function isUser(obj: unknown): obj is User {
  return (
    typeof obj === 'object' &&
    obj !== null &&
    'id' in obj &&
    'name' in obj &&
    'email' in obj &&
    typeof (obj as any).id === 'string' &&
    typeof (obj as any).name === 'string' &&
    typeof (obj as any).email === 'string'
  )
}

export function isUserArray(obj: unknown): obj is User[] {
  return Array.isArray(obj) && obj.every(isUser)
}

// カスタムフックでの使用
export function useSafeUserData() {
  const data = useLoaderData()
  
  if (!isUser(data)) {
    throw new Error('Invalid user data received')
  }
  
  return data
}
```

## 🔄 Vue 3 → React Router 型安全性比較

| 機能 | Vue 3 | React Router |
|------|-------|--------------|
| ルートパラメータ | `useRoute<T>()` | `useParams<T>()` |
| クエリパラメータ | `route.query` | `useSearchParams()` + Zod |
| ナビゲーション | `router.push()` | `useNavigate()` |
| 型付きパス生成 | 手動実装 | カスタムビルダー |
| スキーマ検証 | 手動実装 | Zod統合 |
| 実行時検証 | 手動実装 | Zodバリデーター |

## 🎓 まとめ

React Routerの型安全性は、Vue 3のTypeScriptサポートを上回る柔軟性と厳密性を提供します：

1. **型付きルート管理**: 定数とパスビルダーによる型安全なナビゲーション
2. **スキーマ駆動開発**: Zodによる実行時検証との統合
3. **カスタムフック**: 再利用可能な型安全なAPI
4. **実行時安全性**: TypeScriptとランタイム検証の組み合わせ

次章では、サーバーサイド対応について学びます。

---

**🔗 次章**: [サーバーサイド対応](./11-server-side.md)