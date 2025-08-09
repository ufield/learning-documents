# 動的ルートとパラメータ 🟢

## 📖 この章で学ぶこと

- パスパラメータの定義と取得
- クエリパラメータ（URLSearchParams）の扱い
- useParams と useSearchParams の使用方法
- Vue Routerとの実装比較
- 実用的なパラメータ処理パターン

**想定読了時間**: 20分

---

## 🎯 パスパラメータ（Dynamic Segments）

### 基本的な動的ルート定義

Vue Routerの動的セグメントと同様に、React Routerでもコロン（`:`）を使ってパラメータを定義します：

```tsx
// Vue Router
const routes = [
  { path: '/users/:id', component: UserDetail },
  { path: '/posts/:id/comments/:commentId', component: Comment }
]

// React Router
<Routes>
  <Route path="/users/:id" element={<UserDetail />} />
  <Route path="/posts/:id/comments/:commentId" element={<Comment />} />
</Routes>
```

### useParams フックでパラメータを取得

```tsx
import { useParams } from 'react-router-dom'

function UserDetail() {
  // Vue: this.$route.params.id
  const { id } = useParams()
  
  // パラメータは常にstring型（またはundefined）
  const userId = id // string | undefined

  return (
    <div>
      <h1>User ID: {userId}</h1>
    </div>
  )
}

// 複数パラメータの場合
function CommentDetail() {
  const { id, commentId } = useParams()
  
  return (
    <div>
      <h1>Post: {id}, Comment: {commentId}</h1>
    </div>
  )
}
```

### TypeScriptでの型安全なパラメータ

```tsx
// パラメータの型を明示的に定義
interface UserParams {
  id: string
}

function UserDetail() {
  const { id } = useParams<UserParams>()
  // idは string | undefined 型

  // 型アサーションを使う場合（パラメータの存在が確実な場合）
  const userId = useParams().id!
  
  return <div>User: {userId}</div>
}

// カスタムフックで型安全性を向上
function useTypedParams<T extends Record<string, string>>() {
  return useParams() as T
}

function ProductDetail() {
  const { productId } = useTypedParams<{ productId: string }>()
  // productIdは確実にstring型として扱える
}
```

## 🔍 クエリパラメータ（URLSearchParams）

### useSearchParams フック

Vue Routerの`$route.query`に相当する機能です：

```tsx
import { useSearchParams } from 'react-router-dom'

function ProductList() {
  const [searchParams, setSearchParams] = useSearchParams()
  
  // Vue: this.$route.query.category
  const category = searchParams.get('category')
  const sortBy = searchParams.get('sortBy')
  const page = searchParams.get('page') || '1'

  // クエリパラメータを更新
  const handleFilterChange = (newCategory: string) => {
    // Vue: this.$router.push({ query: { ...this.$route.query, category: newCategory }})
    setSearchParams(prev => {
      prev.set('category', newCategory)
      return prev
    })
  }

  // 複数のパラメータを一度に更新
  const handleSearch = (filters: Record<string, string>) => {
    setSearchParams(filters)
  }

  return (
    <div>
      <h1>商品一覧</h1>
      <p>カテゴリ: {category || 'すべて'}</p>
      <p>並び順: {sortBy || 'デフォルト'}</p>
      <p>ページ: {page}</p>
      
      <button onClick={() => handleFilterChange('electronics')}>
        家電製品
      </button>
    </div>
  )
}
```

### URLSearchParams の実用的な使用例

```tsx
// フィルター機能付き商品一覧
function ProductList() {
  const [searchParams, setSearchParams] = useSearchParams()
  
  // クエリパラメータから初期値を取得
  const filters = {
    category: searchParams.get('category') || '',
    minPrice: Number(searchParams.get('minPrice')) || 0,
    maxPrice: Number(searchParams.get('maxPrice')) || Infinity,
    search: searchParams.get('search') || '',
    sort: searchParams.get('sort') || 'name'
  }

  // フィルターを更新する汎用的な関数
  const updateFilter = (key: string, value: string | null) => {
    setSearchParams(prev => {
      if (value === null || value === '') {
        prev.delete(key)
      } else {
        prev.set(key, value)
      }
      // ページをリセット
      prev.delete('page')
      return prev
    })
  }

  // 複数フィルターをリセット
  const clearFilters = () => {
    setSearchParams({})
  }

  return (
    <div>
      <div className="filters">
        <input
          type="text"
          placeholder="商品を検索"
          value={filters.search}
          onChange={(e) => updateFilter('search', e.target.value)}
        />
        
        <select 
          value={filters.category}
          onChange={(e) => updateFilter('category', e.target.value)}
        >
          <option value="">すべてのカテゴリ</option>
          <option value="electronics">家電</option>
          <option value="clothing">衣類</option>
        </select>

        <button onClick={clearFilters}>
          フィルターをクリア
        </button>
      </div>
    </div>
  )
}
```

## 🔧 パラメータの組み合わせパターン

### パスパラメータ + クエリパラメータ

```tsx
// ルート: /users/:userId/posts?page=1&sort=date
function UserPosts() {
  const { userId } = useParams<{ userId: string }>()
  const [searchParams] = useSearchParams()
  
  const page = Number(searchParams.get('page')) || 1
  const sort = searchParams.get('sort') || 'date'
  
  // Vue Router同等の処理
  // this.$route.params.userId + this.$route.query
  
  useEffect(() => {
    // パラメータが変更されたときにデータを再取得
    fetchUserPosts(userId!, { page, sort })
  }, [userId, page, sort])

  return (
    <div>
      <h1>User {userId} の投稿</h1>
      <p>ページ: {page}, 並び順: {sort}</p>
    </div>
  )
}
```

### オプショナルパラメータの実装

```tsx
// オプショナルセグメント（React Router v6.4+）
<Route path="/products/:category?" element={<ProductList />} />

function ProductList() {
  const { category } = useParams()
  
  // categoryがundefinedの場合は全カテゴリ表示
  const isAllCategories = !category
  
  return (
    <div>
      <h1>
        {isAllCategories ? '全商品' : `${category}カテゴリ`}
      </h1>
    </div>
  )
}
```

## 🛠️ 実用的なユーティリティ関数

### カスタムフック: useRouteParams

```tsx
// パラメータとクエリを統合して扱うカスタムフック
function useRouteParams<P extends Record<string, string>>() {
  const params = useParams<P>()
  const [searchParams, setSearchParams] = useSearchParams()
  
  const query = Object.fromEntries(searchParams.entries())
  
  const setQuery = (updates: Record<string, string | null>) => {
    setSearchParams(prev => {
      Object.entries(updates).forEach(([key, value]) => {
        if (value === null) {
          prev.delete(key)
        } else {
          prev.set(key, value)
        }
      })
      return prev
    })
  }
  
  return {
    params,
    query,
    setQuery,
    searchParams,
    setSearchParams
  }
}

// 使用例
function ProductDetail() {
  const { params, query, setQuery } = useRouteParams<{ id: string }>()
  
  const productId = params.id
  const variant = query.variant
  
  const selectVariant = (variantId: string) => {
    setQuery({ variant: variantId })
  }
}
```

### パラメータバリデーション

```tsx
import { z } from 'zod'

// Zodを使った型安全なパラメータバリデーション
const UserParamsSchema = z.object({
  userId: z.string().regex(/^\d+$/, 'User IDは数値である必要があります')
})

const ProductQuerySchema = z.object({
  page: z.coerce.number().min(1).default(1),
  limit: z.coerce.number().min(1).max(100).default(20),
  category: z.string().optional(),
  sort: z.enum(['name', 'price', 'date']).default('name')
})

function useValidatedParams<T>(schema: z.ZodSchema<T>) {
  const rawParams = useParams()
  const [searchParams] = useSearchParams()
  
  try {
    const params = schema.parse({
      ...rawParams,
      ...Object.fromEntries(searchParams.entries())
    })
    return { params, error: null }
  } catch (error) {
    return { params: null, error }
  }
}

// 使用例
function UserDetail() {
  const { params, error } = useValidatedParams(UserParamsSchema)
  
  if (error) {
    return <div>無効なパラメータです</div>
  }
  
  return <div>User: {params.userId}</div>
}
```

## 🔄 Vue Router → React Router チートシート

| 操作 | Vue Router | React Router |
|------|------------|--------------|
| パスパラメータ取得 | `this.$route.params.id` | `useParams().id` |
| クエリパラメータ取得 | `this.$route.query.page` | `useSearchParams()[0].get('page')` |
| クエリパラメータ更新 | `this.$router.push({ query: {...}})` | `setSearchParams({...})` |
| 全パラメータ監視 | `watch: { $route() {} }` | `useEffect(() => {}, [params, searchParams])` |
| パラメータ存在チェック | `!!this.$route.params.id` | `!!useParams().id` |

## 💡 ベストプラクティス

### 1. パラメータの型安全性

```tsx
// 定数でルートパターンを管理
export const ROUTES = {
  USER_DETAIL: '/users/:userId',
  POST_DETAIL: '/posts/:postId',
  USER_POSTS: '/users/:userId/posts'
} as const

// 型安全なナビゲーション関数
export const createUserDetailPath = (userId: string) => 
  `/users/${userId}`

export const createUserPostsPath = (userId: string, page?: number) => {
  const path = `/users/${userId}/posts`
  return page ? `${path}?page=${page}` : path
}
```

### 2. パラメータの初期化と同期

```tsx
function useProductFilters() {
  const [searchParams, setSearchParams] = useSearchParams()
  
  // デフォルト値を定義
  const defaultFilters = {
    category: '',
    minPrice: '',
    maxPrice: '',
    sort: 'name'
  }
  
  // URLからフィルターを復元
  const filters = {
    category: searchParams.get('category') || defaultFilters.category,
    minPrice: searchParams.get('minPrice') || defaultFilters.minPrice,
    maxPrice: searchParams.get('maxPrice') || defaultFilters.maxPrice,
    sort: searchParams.get('sort') || defaultFilters.sort
  }
  
  const setFilters = useCallback((newFilters: Partial<typeof filters>) => {
    setSearchParams(prev => {
      Object.entries(newFilters).forEach(([key, value]) => {
        if (value && value !== defaultFilters[key as keyof typeof defaultFilters]) {
          prev.set(key, value)
        } else {
          prev.delete(key)
        }
      })
      return prev
    })
  }, [setSearchParams])
  
  return { filters, setFilters }
}
```

### 3. パラメータのパフォーマンス最適化

```tsx
// パラメータ変更時の不要な再レンダリングを防ぐ
function ProductDetail() {
  const { id } = useParams()
  
  // パラメータが変更されたときのみAPIを呼び出す
  const product = useMemo(async () => {
    if (id) {
      return fetchProduct(id)
    }
  }, [id])
  
  // クエリパラメータの変更は製品データに影響しないため分離
  const [searchParams] = useSearchParams()
  const selectedVariant = searchParams.get('variant')
  
  return (
    <div>
      {/* 製品情報 */}
      {/* バリエーション選択UI */}
    </div>
  )
}
```

## 🎓 まとめ

React Routerの動的ルーティングは、Vue Routerと同様の概念でありながら、Reactのフックベースアプローチの恩恵を受けています：

1. **useParams**: シンプルなパスパラメータの取得
2. **useSearchParams**: 強力なクエリパラメータ管理
3. **型安全性**: TypeScriptとの優れた統合
4. **リアクティブ性**: パラメータ変更の自動監視

次章では、ネストされたルートとレイアウトパターンについて学びます。

---

**🔗 次章**: [ネストされたルートとレイアウト](./05-nested-routes.md)