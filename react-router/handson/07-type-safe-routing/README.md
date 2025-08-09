# 型安全なルーティングシステム

**所要時間: 3時間**  
**レベル: 🔴 上級**

TypeScriptを活用して型安全なルーティングシステムを構築し、開発体験と保守性を向上させる手法を学びます。

## 🎯 学習目標

- TypeScriptによる型安全なルート定義を理解する
- パスパラメータとクエリパラメータの型安全性を確保する
- カスタムフックによる型安全なナビゲーションを実装する
- ルートに基づいた型推論システムを構築する
- 型安全なリンクコンポーネントを作成する
- 開発時の型エラー検出とランタイム検証を実装する

## 🏗️ 作るもの

型安全なルーティングシステム：
- 型定義されたルートマップ
- 型安全なパラメータ取得
- 型付きナビゲーションフック
- 自動補完対応のリンクコンポーネント
- ランタイム検証機能
- 型安全なローダー関数

## 📋 前提条件

- 「SPAのパフォーマンス最適化」を完了していること
- TypeScriptの高度な型機能（Union Types、Mapped Types、Conditional Typesなど）の理解
- React Router v6の深い理解

## 🚀 始め方

### ステップ 1: プロジェクトの準備

```bash
cd starter
npm install
npm run dev
npm run type-check
```

### ステップ 2: 段階的な実装

1. **Step 1**: ルートマップの型定義システム
2. **Step 2**: 型安全なパラメータ抽出
3. **Step 3**: カスタムナビゲーションフック
4. **Step 4**: 型安全なリンクコンポーネント
5. **Step 5**: ランタイム検証とエラーハンドリング

### ステップ 3: 実装開始

#### Step 1: ルートマップの型定義

**src/types/routes.ts**:

```tsx
// ルートパラメータの型定義
export interface RouteParams {
  '/': {}
  '/login': {}
  '/signup': {}
  '/products': {}
  '/products/:id': { id: string }
  '/categories/:category': { category: string }
  '/categories/:category/:subcategory': { 
    category: string
    subcategory: string 
  }
  '/users/:userId/orders/:orderId': {
    userId: string
    orderId: string
  }
  '/admin': {}
  '/admin/users': {}
  '/admin/users/:id': { id: string }
  '/admin/users/:id/edit': { id: string }
  '/search': {}
  '/cart': {}
  '/checkout': {}
  '/profile': {}
  '/orders/:id': { id: string }
}

// クエリパラメータの型定義
export interface RouteSearchParams {
  '/': {}
  '/products': {
    category?: string
    subcategory?: string
    sort?: 'price-low' | 'price-high' | 'rating' | 'newest'
    minPrice?: string
    maxPrice?: string
    brands?: string[]
    page?: string
  }
  '/search': {
    q: string
    category?: string
    page?: string
  }
  '/categories/:category': {
    sort?: 'price-low' | 'price-high' | 'rating' | 'newest'
    minPrice?: string
    maxPrice?: string
    page?: string
  }
  '/categories/:category/:subcategory': {
    sort?: 'price-low' | 'price-high' | 'rating' | 'newest'
    minPrice?: string
    maxPrice?: string
    page?: string
  }
  // 他のルートのデフォルト
  [K in keyof RouteParams]: {}
}

// ルートパスの型
export type RoutePath = keyof RouteParams

// 特定のルートのパラメータを取得する型
export type RouteParamsFor<T extends RoutePath> = RouteParams[T]

// 特定のルートのクエリパラメータを取得する型
export type RouteSearchParamsFor<T extends RoutePath> = T extends keyof RouteSearchParams 
  ? RouteSearchParams[T]
  : {}

// パラメータ付きルートかどうかを判定する型
export type HasParams<T extends RoutePath> = RouteParams[T] extends Record<string, never> 
  ? false 
  : true

// パラメータが必要なルート
export type RouteWithParams = {
  [K in RoutePath]: HasParams<K> extends true ? K : never
}[RoutePath]

// パラメータが不要なルート
export type RouteWithoutParams = {
  [K in RoutePath]: HasParams<K> extends false ? K : never
}[RoutePath]
```

#### Step 2: 型安全なパラメータフック

**src/hooks/useTypedParams.ts**:

```tsx
import { useParams } from 'react-router-dom'
import { RoutePath, RouteParamsFor } from '../types/routes'

export function useTypedParams<T extends RoutePath>(
  _route?: T  // 型推論のためのヒント（実際には使用しない）
): RouteParamsFor<T> {
  const params = useParams()
  
  // 開発環境でのランタイム検証
  if (process.env.NODE_ENV === 'development') {
    validateParams(params)
  }
  
  return params as RouteParamsFor<T>
}

function validateParams(params: any) {
  // パラメータの基本的な検証
  for (const [key, value] of Object.entries(params)) {
    if (typeof value !== 'string' && value !== undefined) {
      console.warn(`Invalid parameter type for ${key}:`, typeof value, value)
    }
  }
}

// 使用例:
// const { id } = useTypedParams<'/products/:id'>() // id は string型
// const { category, subcategory } = useTypedParams<'/categories/:category/:subcategory'>()
```

**src/hooks/useTypedSearchParams.ts**:

```tsx
import { useSearchParams } from 'react-router-dom'
import { useCallback } from 'react'
import { RoutePath, RouteSearchParamsFor } from '../types/routes'

export function useTypedSearchParams<T extends RoutePath>(
  _route?: T
) {
  const [searchParams, setSearchParams] = useSearchParams()
  
  // 型安全なgetter
  const getSearchParam = useCallback(<K extends keyof RouteSearchParamsFor<T>>(
    key: K
  ): RouteSearchParamsFor<T>[K] => {
    const value = searchParams.get(key as string)
    
    // 配列パラメータの処理
    if (key === 'brands') {
      return searchParams.getAll(key as string) as RouteSearchParamsFor<T>[K]
    }
    
    return value as RouteSearchParamsFor<T>[K]
  }, [searchParams])
  
  // 型安全なsetter
  const setSearchParam = useCallback(<K extends keyof RouteSearchParamsFor<T>>(
    key: K,
    value: RouteSearchParamsFor<T>[K] | null
  ) => {
    const newParams = new URLSearchParams(searchParams)
    
    if (value === null || value === undefined) {
      newParams.delete(key as string)
    } else if (Array.isArray(value)) {
      // 配列の場合は全て削除してから追加
      newParams.delete(key as string)
      value.forEach(v => newParams.append(key as string, v))
    } else {
      newParams.set(key as string, value as string)
    }
    
    setSearchParams(newParams)
  }, [searchParams, setSearchParams])
  
  // 複数パラメータの一括設定
  const setSearchParams_ = useCallback((
    params: Partial<RouteSearchParamsFor<T>>
  ) => {
    const newParams = new URLSearchParams()
    
    Object.entries(params).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        if (Array.isArray(value)) {
          value.forEach(v => newParams.append(key, v))
        } else {
          newParams.set(key, value as string)
        }
      }
    })
    
    setSearchParams(newParams)
  }, [setSearchParams])
  
  // 型安全なパラメータオブジェクトの取得
  const getSearchParams = useCallback((): Partial<RouteSearchParamsFor<T>> => {
    const result: any = {}
    
    // 既知のパラメータのみを抽出
    for (const [key, value] of searchParams.entries()) {
      if (result[key]) {
        // 配列化
        if (Array.isArray(result[key])) {
          result[key].push(value)
        } else {
          result[key] = [result[key], value]
        }
      } else {
        result[key] = value
      }
    }
    
    return result
  }, [searchParams])
  
  return {
    getSearchParam,
    setSearchParam,
    setSearchParams: setSearchParams_,
    getSearchParams,
    searchParams // 元のURLSearchParamsも提供
  }
}
```

#### Step 3: 型安全なナビゲーションフック

**src/hooks/useTypedNavigate.ts**:

```tsx
import { useNavigate, NavigateOptions } from 'react-router-dom'
import { useCallback } from 'react'
import { 
  RoutePath, 
  RouteParamsFor, 
  RouteSearchParamsFor, 
  HasParams,
  RouteWithParams,
  RouteWithoutParams
} from '../types/routes'

// パラメータが不要なルート用のオーバーロード
export function useTypedNavigate(): {
  navigate<T extends RouteWithoutParams>(
    to: T,
    options?: NavigateOptions & {
      searchParams?: Partial<RouteSearchParamsFor<T>>
    }
  ): void
  
  // パラメータが必要なルート用のオーバーロード
  navigate<T extends RouteWithParams>(
    to: T,
    params: RouteParamsFor<T>,
    options?: NavigateOptions & {
      searchParams?: Partial<RouteSearchParamsFor<T>>
    }
  ): void
  
  // 数値でのナビゲーション（戻る/進む）
  navigate(delta: number): void
}

export function useTypedNavigate() {
  const navigate = useNavigate()
  
  const typedNavigate = useCallback(
    (
      to: RoutePath | number,
      paramsOrOptions?: any,
      options?: NavigateOptions & { searchParams?: any }
    ) => {
      // 数値の場合はそのまま渡す
      if (typeof to === 'number') {
        navigate(to)
        return
      }
      
      let finalPath = to as string
      let finalOptions = options
      
      // パラメータが渡された場合の処理
      if (paramsOrOptions && typeof paramsOrOptions === 'object' && !('replace' in paramsOrOptions)) {
        // パラメータが渡された場合
        const params = paramsOrOptions
        finalOptions = options
        
        // パスパラメータを置換
        for (const [key, value] of Object.entries(params)) {
          finalPath = finalPath.replace(`:${key}`, encodeURIComponent(value as string))
        }
      } else {
        // オプションのみが渡された場合
        finalOptions = paramsOrOptions
      }
      
      // クエリパラメータを追加
      if (finalOptions?.searchParams) {
        const searchParams = new URLSearchParams()
        
        Object.entries(finalOptions.searchParams).forEach(([key, value]) => {
          if (value !== null && value !== undefined) {
            if (Array.isArray(value)) {
              value.forEach(v => searchParams.append(key, v))
            } else {
              searchParams.set(key, value as string)
            }
          }
        })
        
        const queryString = searchParams.toString()
        if (queryString) {
          finalPath += '?' + queryString
        }
      }
      
      // オプションからsearchParamsを除去
      const { searchParams, ...navigateOptions } = finalOptions || {}
      
      navigate(finalPath, navigateOptions)
    },
    [navigate]
  )
  
  return { navigate: typedNavigate }
}

// 使用例:
// const { navigate } = useTypedNavigate()
// 
// navigate('/products')  // パラメータ不要
// navigate('/products/:id', { id: '123' })  // パラメータ必要
// navigate('/search', { searchParams: { q: 'query', category: 'books' } })
```

#### Step 4: 型安全なリンクコンポーネント

**src/components/TypedLink.tsx**:

```tsx
import React, { AnchorHTMLAttributes, forwardRef } from 'react'
import { Link, LinkProps } from 'react-router-dom'
import { 
  RoutePath, 
  RouteParamsFor, 
  RouteSearchParamsFor,
  RouteWithParams,
  RouteWithoutParams
} from '../types/routes'

// パラメータが不要なルート用
type TypedLinkPropsWithoutParams<T extends RouteWithoutParams> = Omit<LinkProps, 'to'> & {
  to: T
  params?: never
  searchParams?: Partial<RouteSearchParamsFor<T>>
}

// パラメータが必要なルート用
type TypedLinkPropsWithParams<T extends RouteWithParams> = Omit<LinkProps, 'to'> & {
  to: T
  params: RouteParamsFor<T>
  searchParams?: Partial<RouteSearchParamsFor<T>>
}

// 統合された型
type TypedLinkProps<T extends RoutePath> = T extends RouteWithoutParams 
  ? TypedLinkPropsWithoutParams<T>
  : T extends RouteWithParams 
  ? TypedLinkPropsWithParams<T>
  : never

function TypedLinkComponent<T extends RoutePath>(
  props: TypedLinkProps<T>,
  ref: React.Ref<HTMLAnchorElement>
) {
  const { to, params, searchParams, ...linkProps } = props
  
  // パスを構築
  let finalPath = to as string
  
  // パスパラメータを置換
  if (params) {
    for (const [key, value] of Object.entries(params)) {
      finalPath = finalPath.replace(`:${key}`, encodeURIComponent(value as string))
    }
  }
  
  // クエリパラメータを追加
  if (searchParams && Object.keys(searchParams).length > 0) {
    const urlSearchParams = new URLSearchParams()
    
    Object.entries(searchParams).forEach(([key, value]) => {
      if (value !== null && value !== undefined) {
        if (Array.isArray(value)) {
          value.forEach(v => urlSearchParams.append(key, v))
        } else {
          urlSearchParams.set(key, value as string)
        }
      }
    })
    
    const queryString = urlSearchParams.toString()
    if (queryString) {
      finalPath += '?' + queryString
    }
  }
  
  return <Link ref={ref} to={finalPath} {...linkProps} />
}

export const TypedLink = forwardRef(TypedLinkComponent) as <T extends RoutePath>(
  props: TypedLinkProps<T> & { ref?: React.Ref<HTMLAnchorElement> }
) => ReactElement

// 使用例のための型定義
type ReactElement = React.ReactElement<any, any>

// 便利なヘルパーコンポーネント
export function ProductLink({ 
  productId, 
  children, 
  ...props 
}: { 
  productId: string 
  children: React.ReactNode 
} & Omit<TypedLinkPropsWithParams<'/products/:id'>, 'to' | 'params' | 'children'>) {
  return (
    <TypedLink to="/products/:id" params={{ id: productId }} {...props}>
      {children}
    </TypedLink>
  )
}

export function CategoryLink({ 
  category, 
  subcategory,
  children, 
  ...props 
}: { 
  category: string
  subcategory?: string
  children: React.ReactNode 
} & Omit<LinkProps, 'to' | 'children'>) {
  const to = subcategory 
    ? '/categories/:category/:subcategory' as const
    : '/categories/:category' as const
    
  const params = subcategory 
    ? { category, subcategory }
    : { category }
  
  return (
    <TypedLink to={to} params={params as any} {...props}>
      {children}
    </TypedLink>
  )
}
```

#### Step 5: ランタイム検証とデバッグ支援

**src/utils/routeValidation.ts**:

```tsx
import { RoutePath, RouteParams } from '../types/routes'

// ルートパターンからパラメータ名を抽出
export function extractParamNames(route: string): string[] {
  const matches = route.match(/:(\w+)/g)
  return matches ? matches.map(match => match.substring(1)) : []
}

// ルートとパラメータの検証
export function validateRouteParams<T extends RoutePath>(
  route: T,
  params: any
): params is RouteParams[T] {
  const expectedParams = extractParamNames(route)
  const providedParams = Object.keys(params || {})
  
  // 不足しているパラメータをチェック
  const missingParams = expectedParams.filter(param => !providedParams.includes(param))
  if (missingParams.length > 0) {
    console.error(`Missing required parameters for route ${route}:`, missingParams)
    return false
  }
  
  // 余分なパラメータをチェック
  const extraParams = providedParams.filter(param => !expectedParams.includes(param))
  if (extraParams.length > 0) {
    console.warn(`Extra parameters provided for route ${route}:`, extraParams)
  }
  
  return true
}

// 開発時のルートデバッグヘルパー
export function debugRoute(route: RoutePath, params?: any, searchParams?: any) {
  if (process.env.NODE_ENV !== 'development') return
  
  console.group(`🛣️ Route Debug: ${route}`)
  console.log('Expected params:', extractParamNames(route))
  console.log('Provided params:', params)
  console.log('Search params:', searchParams)
  console.log('Valid:', validateRouteParams(route, params))
  console.groupEnd()
}
```

**src/components/RouteDebugger.tsx** (開発時のみ表示):

```tsx
import { useLocation, useParams } from 'react-router-dom'
import { useTypedSearchParams } from '../hooks/useTypedSearchParams'

function RouteDebugger() {
  const location = useLocation()
  const params = useParams()
  const { searchParams } = useTypedSearchParams()
  
  if (process.env.NODE_ENV !== 'development') return null
  
  return (
    <div className="fixed bottom-4 right-4 bg-gray-900 text-white p-4 rounded-lg shadow-lg text-sm max-w-md z-50">
      <div className="font-bold mb-2">🛣️ Route Debugger</div>
      <div><strong>Path:</strong> {location.pathname}</div>
      <div><strong>Params:</strong> {JSON.stringify(params)}</div>
      <div><strong>Search:</strong> {searchParams.toString()}</div>
      <div><strong>Hash:</strong> {location.hash}</div>
      <div><strong>State:</strong> {JSON.stringify(location.state)}</div>
    </div>
  )
}

export default RouteDebugger
```

#### Step 6: 実際の使用例

**src/pages/TypeSafeProductList.tsx**:

```tsx
import { useTypedParams } from '../hooks/useTypedParams'
import { useTypedSearchParams } from '../hooks/useTypedSearchParams'
import { useTypedNavigate } from '../hooks/useTypedNavigate'
import { TypedLink, CategoryLink } from '../components/TypedLink'

function TypeSafeProductList() {
  // 型安全なパラメータ取得
  const { category, subcategory } = useTypedParams<'/categories/:category/:subcategory'>()
  
  // 型安全なクエリパラメータ
  const { 
    getSearchParam, 
    setSearchParam, 
    getSearchParams 
  } = useTypedSearchParams<'/categories/:category/:subcategory'>()
  
  const { navigate } = useTypedNavigate()
  
  const currentSort = getSearchParam('sort') // 型: 'price-low' | 'price-high' | 'rating' | 'newest' | undefined
  const currentPage = getSearchParam('page') // 型: string | undefined
  const minPrice = getSearchParam('minPrice') // 型: string | undefined
  
  const handleSortChange = (sort: 'price-low' | 'price-high' | 'rating' | 'newest') => {
    setSearchParam('sort', sort)
    setSearchParam('page', null) // ページをリセット
  }
  
  const handleCategoryChange = (newCategory: string, newSubcategory?: string) => {
    if (newSubcategory) {
      navigate('/categories/:category/:subcategory', {
        category: newCategory,
        subcategory: newSubcategory
      }, {
        searchParams: getSearchParams() // 現在の検索パラメータを維持
      })
    } else {
      navigate('/categories/:category', {
        category: newCategory
      }, {
        searchParams: getSearchParams()
      })
    }
  }
  
  return (
    <div>
      <h1>商品一覧: {category} {subcategory && `> ${subcategory}`}</h1>
      
      {/* 型安全なリンク */}
      <nav>
        <TypedLink to="/categories/:category" params={{ category: 'electronics' }}>
          電子機器
        </TypedLink>
        
        <CategoryLink category="books" subcategory="programming">
          プログラミング書籍
        </CategoryLink>
      </nav>
      
      {/* ソート機能 */}
      <select 
        value={currentSort || 'newest'}
        onChange={(e) => handleSortChange(e.target.value as any)}
      >
        <option value="newest">新着順</option>
        <option value="price-low">価格の安い順</option>
        <option value="price-high">価格の高い順</option>
        <option value="rating">評価の高い順</option>
      </select>
      
      {/* 商品一覧... */}
    </div>
  )
}

export default TypeSafeProductList
```

## 🎓 学習ポイント

### 1. 型安全なルート定義
```tsx
interface RouteParams {
  '/products/:id': { id: string }
  '/categories/:category/:subcategory': { 
    category: string
    subcategory: string 
  }
}
```

### 2. 型推論による自動補完
```tsx
const { id } = useTypedParams<'/products/:id'>() // idはstring型
const sort = getSearchParam('sort') // 定義された型のUnion型
```

### 3. コンパイル時の型チェック
```tsx
// ✅ 正しい使用法
navigate('/products/:id', { id: '123' })

// ❌ コンパイルエラー
navigate('/products/:id') // パラメータが不足
navigate('/products/:id', { wrongParam: '123' }) // 間違ったパラメータ
```

### 4. オーバーロードによる型安全性
```tsx
// パラメータ不要なルート
navigate('/products')

// パラメータ必要なルート  
navigate('/products/:id', { id: '123' })
```

## 🧪 チャレンジ課題

### チャレンジ 1: 型安全なフォームルーティング
フォームの送信先URLを型安全に管理するシステムを構築してください。

### チャレンジ 2: 動的ルート生成
設定ファイルから動的にルート定義を生成し、型安全性を保つシステムを実装してください。

### チャレンジ 3: Multi-language対応
多言語対応のルーティングシステムを型安全に実装してください。

## 🎉 完了！

お疲れ様でした！React Routerの7つのハンズオンをすべて完了されました。

### 🎓 習得したスキル

- **基礎**: ルーティング、Link、useNavigate
- **応用**: 動的ルート、クエリパラメータ、ネストルート
- **実践**: 認証、複雑なECサイト構造
- **上級**: パフォーマンス最適化、型安全性

これらの知識を活かして、より高度なWebアプリケーションを構築してください！