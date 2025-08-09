# SPAのパフォーマンス最適化

**所要時間: 2時間**  
**レベル: 🔴 上級**

React RouterとReact 18/19の最新機能を活用して、SPAのパフォーマンスを最適化する手法を学びます。

## 🎯 学習目標

- コード分割とReact.lazy を使った遅延読み込みを理解する
- React Router のプリフェッチング戦略を学ぶ
- React 18 の Suspense と Concurrent Features を活用する
- バンドルサイズ分析と最適化手法を覚える
- ルートレベルでのデータフェッチング最適化を実装する
- Web Vitals を意識したパフォーマンス改善を学ぶ

## 🏗️ 作るもの

パフォーマンス最適化されたアプリケーション：
- 遅延読み込みされるルートコンポーネント
- スマートなプリフェッチング機能
- サスペンス境界によるローディング UI
- 効率的なデータフェッチング
- バンドルサイズの最適化

## 📋 前提条件

- 「ECサイトのルーティング」を完了していること
- React 18 の Concurrent Features の基本的な理解
- Webpack/Vite のバンドル概念の理解

## 🚀 始め方

### ステップ 1: プロジェクトの準備

```bash
cd starter
npm install
npm run dev
```

### ステップ 2: 段階的な実装

1. **Step 1**: コード分割とReact.lazy の実装
2. **Step 2**: Suspense 境界とローディング UI
3. **Step 3**: プリフェッチング戦略の実装
4. **Step 4**: データフェッチングの最適化
5. **Step 5**: バンドル分析と追加最適化

### ステップ 3: 実装開始

#### Step 1: コード分割とReact.lazy

**src/components/LazyWrapper.tsx**:

```tsx
import { Suspense, ComponentType } from 'react'
import LoadingSpinner from './LoadingSpinner'

interface LazyWrapperProps {
  Component: ComponentType<any>
  fallback?: React.ReactNode
}

function LazyWrapper({ Component, fallback }: LazyWrapperProps) {
  return (
    <Suspense fallback={fallback || <LoadingSpinner />}>
      <Component />
    </Suspense>
  )
}

export default LazyWrapper
```

**src/components/LoadingSpinner.tsx**:

```tsx
interface LoadingSpinnerProps {
  size?: 'small' | 'medium' | 'large'
  text?: string
}

function LoadingSpinner({ size = 'medium', text = 'Loading...' }: LoadingSpinnerProps) {
  const sizeClasses = {
    small: 'w-4 h-4',
    medium: 'w-8 h-8',
    large: 'w-12 h-12'
  }

  return (
    <div className="flex flex-col items-center justify-center min-h-[200px]">
      <div className={`animate-spin rounded-full border-b-2 border-blue-600 ${sizeClasses[size]}`} />
      {text && <p className="mt-4 text-gray-600">{text}</p>}
    </div>
  )
}

export default LoadingSpinner
```

**src/main.tsx** (コード分割の実装):

```tsx
import React, { Suspense } from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'

import Layout from './components/Layout'
import LoadingSpinner from './components/LoadingSpinner'
import ErrorBoundary from './components/ErrorBoundary'

// 遅延読み込みするコンポーネント
const Home = React.lazy(() => 
  import('./pages/Home').then(module => ({ 
    default: module.default 
  }))
)

const ProductList = React.lazy(() => 
  // 意図的に遅延を追加してローディングを見やすくする（開発時のみ）
  new Promise(resolve => {
    setTimeout(() => resolve(import('./pages/ProductList')), 500)
  }).then((module: any) => ({ default: module.default }))
)

const ProductDetail = React.lazy(() => 
  import('./pages/ProductDetail')
)

const Cart = React.lazy(() => 
  import('./pages/Cart')
)

const Checkout = React.lazy(() => 
  import('./pages/Checkout')
)

// 管理画面（大きなチャンク）
const AdminDashboard = React.lazy(() => 
  import('./pages/admin/AdminDashboard')
)

const UserManagement = React.lazy(() => 
  import('./pages/admin/UserManagement')
)

// カスタムサスペンス境界コンポーネント
const PageSuspense = ({ children, fallback }: { children: React.ReactNode, fallback?: React.ReactNode }) => (
  <Suspense fallback={fallback || <LoadingSpinner text="ページを読み込み中..." />}>
    {children}
  </Suspense>
)

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    errorElement: <ErrorBoundary />,
    children: [
      {
        index: true,
        element: (
          <PageSuspense fallback={<LoadingSpinner size="large" text="ホームページを読み込み中..." />}>
            <Home />
          </PageSuspense>
        ),
      },
      {
        path: "categories/:category",
        element: (
          <PageSuspense>
            <ProductList />
          </PageSuspense>
        ),
      },
      {
        path: "categories/:category/:subcategory",
        element: (
          <PageSuspense>
            <ProductList />
          </PageSuspense>
        ),
      },
      {
        path: "products/:id",
        element: (
          <PageSuspense>
            <ProductDetail />
          </PageSuspense>
        ),
      },
      {
        path: "cart",
        element: (
          <PageSuspense>
            <Cart />
          </PageSuspense>
        ),
      },
      {
        path: "checkout",
        element: (
          <PageSuspense>
            <Checkout />
          </PageSuspense>
        ),
      },
    ],
  },
  {
    path: "/admin",
    element: <Layout />, // 管理画面用のレイアウトも遅延読み込み可能
    children: [
      {
        index: true,
        element: (
          <PageSuspense>
            <AdminDashboard />
          </PageSuspense>
        ),
      },
      {
        path: "users",
        element: (
          <PageSuspense>
            <UserManagement />
          </PageSuspense>
        ),
      },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
```

#### Step 2: スマートプリフェッチング

**src/components/PrefetchLink.tsx**:

```tsx
import { Link, LinkProps } from 'react-router-dom'
import { useEffect, useRef } from 'react'

interface PrefetchLinkProps extends LinkProps {
  prefetch?: 'hover' | 'visible' | 'intent'
  delay?: number
}

const moduleCache = new Map<string, Promise<any>>()

function PrefetchLink({ 
  prefetch = 'hover', 
  delay = 100, 
  to, 
  children, 
  ...props 
}: PrefetchLinkProps) {
  const linkRef = useRef<HTMLAnchorElement>(null)
  const hoverTimeoutRef = useRef<NodeJS.Timeout>()

  const prefetchRoute = async (path: string) => {
    // すでにキャッシュされている場合はスキップ
    if (moduleCache.has(path)) return

    try {
      // パスに基づいて適切なモジュールを事前読み込み
      let modulePromise: Promise<any>

      if (path.includes('/products/')) {
        modulePromise = import('../pages/ProductDetail')
      } else if (path.includes('/categories/')) {
        modulePromise = import('../pages/ProductList')
      } else if (path === '/cart') {
        modulePromise = import('../pages/Cart')
      } else if (path === '/checkout') {
        modulePromise = import('../pages/Checkout')
      } else {
        return // プリフェッチ対象外
      }

      moduleCache.set(path, modulePromise)
      await modulePromise
      console.log(`✅ Prefetched: ${path}`)
    } catch (error) {
      console.warn(`❌ Failed to prefetch: ${path}`, error)
      moduleCache.delete(path)
    }
  }

  // Intersection Observer を使った視覚的プリフェッチング
  useEffect(() => {
    if (prefetch !== 'visible' || !linkRef.current) return

    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const path = typeof to === 'string' ? to : to.pathname || ''
            prefetchRoute(path)
            observer.unobserve(entry.target)
          }
        })
      },
      { rootMargin: '100px' } // 100px手前で事前読み込み
    )

    observer.observe(linkRef.current)

    return () => observer.disconnect()
  }, [prefetch, to])

  const handleMouseEnter = () => {
    if (prefetch === 'hover') {
      hoverTimeoutRef.current = setTimeout(() => {
        const path = typeof to === 'string' ? to : to.pathname || ''
        prefetchRoute(path)
      }, delay)
    }
  }

  const handleMouseLeave = () => {
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current)
    }
  }

  const handleMouseDown = () => {
    if (prefetch === 'intent') {
      const path = typeof to === 'string' ? to : to.pathname || ''
      prefetchRoute(path)
    }
  }

  return (
    <Link
      ref={linkRef}
      to={to}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={handleMouseLeave}
      onMouseDown={handleMouseDown}
      {...props}
    >
      {children}
    </Link>
  )
}

export default PrefetchLink
```

#### Step 3: データフェッチング最適化

**src/hooks/useProductData.ts**:

```tsx
import { useState, useEffect, useRef } from 'react'

interface UseProductDataOptions {
  enabled?: boolean
  staleTime?: number // データが古いと判断するまでの時間（ms）
  cacheTime?: number // キャッシュを保持する時間（ms）
}

const dataCache = new Map<string, { data: any; timestamp: number }>()
const requestQueue = new Map<string, Promise<any>>()

export function useProductData<T>(
  key: string,
  fetcher: () => Promise<T>,
  options: UseProductDataOptions = {}
) {
  const {
    enabled = true,
    staleTime = 5 * 60 * 1000, // 5分
    cacheTime = 10 * 60 * 1000  // 10分
  } = options

  const [data, setData] = useState<T | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<Error | null>(null)
  const mountedRef = useRef(true)

  useEffect(() => {
    mountedRef.current = true
    return () => { mountedRef.current = false }
  }, [])

  useEffect(() => {
    if (!enabled) return

    const fetchData = async () => {
      // キャッシュチェック
      const cached = dataCache.get(key)
      const now = Date.now()

      if (cached && (now - cached.timestamp) < staleTime) {
        setData(cached.data)
        return
      }

      // 同じリクエストが進行中かチェック
      if (requestQueue.has(key)) {
        try {
          const result = await requestQueue.get(key)
          if (mountedRef.current) {
            setData(result)
          }
        } catch (err) {
          if (mountedRef.current) {
            setError(err as Error)
          }
        }
        return
      }

      setLoading(true)
      setError(null)

      const requestPromise = fetcher()
      requestQueue.set(key, requestPromise)

      try {
        const result = await requestPromise
        
        if (mountedRef.current) {
          setData(result)
          setLoading(false)
          
          // キャッシュに保存
          dataCache.set(key, {
            data: result,
            timestamp: now
          })

          // 古いキャッシュエントリを削除
          for (const [cacheKey, cacheEntry] of dataCache.entries()) {
            if (now - cacheEntry.timestamp > cacheTime) {
              dataCache.delete(cacheKey)
            }
          }
        }
      } catch (err) {
        if (mountedRef.current) {
          setError(err as Error)
          setLoading(false)
        }
      } finally {
        requestQueue.delete(key)
      }
    }

    fetchData()
  }, [key, enabled, staleTime, cacheTime, fetcher])

  return { data, loading, error, refetch: () => {
    dataCache.delete(key)
    // 依存配列を変更して再実行をトリガー
  }}
}
```

**src/pages/ProductDetail.tsx** (最適化版):

```tsx
import { useParams } from 'react-router-dom'
import { useProductData } from '../hooks/useProductData'
import { getProductById, getRelatedProducts } from '../data/products'
import LoadingSpinner from '../components/LoadingSpinner'
import PrefetchLink from '../components/PrefetchLink'

function ProductDetail() {
  const { id } = useParams<{ id: string }>()

  // メイン商品データを取得
  const { 
    data: product, 
    loading: productLoading, 
    error: productError 
  } = useProductData(
    `product-${id}`,
    () => getProductById(id!),
    { staleTime: 10 * 60 * 1000 } // 商品データは10分間キャッシュ
  )

  // 関連商品データを遅延取得
  const { 
    data: relatedProducts, 
    loading: relatedLoading 
  } = useProductData(
    `related-${product?.category}`,
    () => getRelatedProducts(product!.category),
    { 
      enabled: !!product,
      staleTime: 30 * 60 * 1000 // 関連商品は30分間キャッシュ
    }
  )

  if (productLoading) {
    return <LoadingSpinner size="large" text="商品情報を読み込み中..." />
  }

  if (productError) {
    return (
      <div className="text-center py-12">
        <p className="text-red-600">商品の読み込みに失敗しました</p>
        <button 
          onClick={() => window.location.reload()}
          className="mt-4 px-4 py-2 bg-blue-600 text-white rounded"
        >
          再読み込み
        </button>
      </div>
    )
  }

  if (!product) {
    return (
      <div className="text-center py-12">
        <p className="text-gray-600">商品が見つかりません</p>
        <PrefetchLink 
          to="/categories/all"
          className="mt-4 inline-block px-4 py-2 bg-blue-600 text-white rounded"
          prefetch="intent"
        >
          商品一覧に戻る
        </PrefetchLink>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto">
      {/* 商品詳細 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-12">
        {/* 商品画像 */}
        <div className="space-y-4">
          <div className="aspect-square bg-gray-100 rounded-lg overflow-hidden">
            <img
              src={`/images/${product.images[0]}`}
              alt={product.name}
              className="w-full h-full object-cover"
              loading="eager" // メイン画像は即座に読み込み
            />
          </div>
          
          {/* サムネイル画像 */}
          <div className="grid grid-cols-4 gap-2">
            {product.images.slice(1).map((image, index) => (
              <div key={index} className="aspect-square bg-gray-100 rounded overflow-hidden">
                <img
                  src={`/images/${image}`}
                  alt={`${product.name} ${index + 2}`}
                  className="w-full h-full object-cover"
                  loading="lazy" // サムネイルは遅延読み込み
                />
              </div>
            ))}
          </div>
        </div>

        {/* 商品情報 */}
        <div className="space-y-6">
          <div>
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              {product.name}
            </h1>
            <p className="text-gray-600">{product.brand}</p>
          </div>

          <div className="text-2xl font-bold text-gray-900">
            ¥{product.price.toLocaleString()}
            {product.originalPrice && (
              <span className="text-lg text-gray-500 line-through ml-2">
                ¥{product.originalPrice.toLocaleString()}
              </span>
            )}
          </div>

          <p className="text-gray-700 leading-relaxed">
            {product.description}
          </p>

          {/* カートに追加ボタン */}
          <button
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg text-lg font-semibold hover:bg-blue-700 transition-colors"
            disabled={product.inStock === 0}
          >
            {product.inStock > 0 ? 'カートに追加' : '在庫切れ'}
          </button>
        </div>
      </div>

      {/* 関連商品（遅延読み込み） */}
      <section>
        <h2 className="text-2xl font-bold text-gray-900 mb-6">関連商品</h2>
        
        {relatedLoading ? (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {[...Array(4)].map((_, i) => (
              <div key={i} className="bg-gray-200 aspect-square rounded-lg animate-pulse" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            {relatedProducts?.slice(0, 4).map(relatedProduct => (
              <PrefetchLink
                key={relatedProduct.id}
                to={`/products/${relatedProduct.id}`}
                prefetch="visible" // 画面に見えたときにプリフェッチ
                className="group"
              >
                <div className="bg-white rounded-lg shadow hover:shadow-md transition-shadow">
                  <div className="aspect-square bg-gray-100 rounded-t-lg overflow-hidden">
                    <img
                      src={`/images/${relatedProduct.images[0]}`}
                      alt={relatedProduct.name}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform"
                      loading="lazy"
                    />
                  </div>
                  <div className="p-4">
                    <h3 className="font-semibold text-gray-900 line-clamp-2">
                      {relatedProduct.name}
                    </h3>
                    <p className="text-gray-600 font-bold">
                      ¥{relatedProduct.price.toLocaleString()}
                    </p>
                  </div>
                </div>
              </PrefetchLink>
            ))}
          </div>
        )}
      </section>
    </div>
  )
}

export default ProductDetail
```

#### Step 4: バンドル分析と最適化

**vite.config.ts** (最適化設定):

```tsx
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { visualizer } from 'rollup-plugin-visualizer'

export default defineConfig({
  plugins: [
    react(),
    visualizer({
      filename: 'dist/stats.html',
      open: true,
      gzipSize: true,
      brotliSize: true
    })
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          // ベンダーライブラリを分離
          vendor: ['react', 'react-dom'],
          router: ['react-router-dom'],
          
          // 管理画面を別チャンクに
          admin: [
            './src/pages/admin/AdminDashboard.tsx',
            './src/pages/admin/UserManagement.tsx'
          ],
          
          // 大きなライブラリがある場合は分離
          // charts: ['chart.js', 'react-chartjs-2'],
        },
        
        // チャンクサイズの警告しきい値を調整
        chunkSizeWarningLimit: 1000
      }
    },
    
    // 最小化設定
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: true, // console.log を本番環境で削除
        drop_debugger: true,
      },
    },
  },
  
  server: {
    port: 5173
  }
})
```

**src/utils/webVitals.ts**:

```tsx
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals'

export function reportWebVitals(onPerfEntry?: (metric: any) => void) {
  if (onPerfEntry && onPerfEntry instanceof Function) {
    getCLS(onPerfEntry)
    getFID(onPerfEntry)
    getFCP(onPerfEntry)
    getLCP(onPerfEntry)
    getTTFB(onPerfEntry)
  }
}

// パフォーマンス計測をコンソールに出力
export function logWebVitals() {
  reportWebVitals(console.log)
}
```

## 🎓 学習ポイント

### 1. コード分割とReact.lazy
```tsx
const ProductList = React.lazy(() => import('./pages/ProductList'))

<Suspense fallback={<LoadingSpinner />}>
  <ProductList />
</Suspense>
```

### 2. スマートプリフェッチング
```tsx
// ホバー時にプリフェッチ
<PrefetchLink to="/products/1" prefetch="hover">

// 画面に見えたときにプリフェッチ
<PrefetchLink to="/products/1" prefetch="visible">
```

### 3. データキャッシュ戦略
```tsx
const { data, loading } = useProductData(
  'product-1',
  () => fetchProduct(1),
  { staleTime: 10 * 60 * 1000 } // 10分間キャッシュ
)
```

### 4. バンドル最適化
```tsx
// vite.config.ts
output: {
  manualChunks: {
    vendor: ['react', 'react-dom'],
    admin: ['./src/pages/admin/*']
  }
}
```

## 🧪 チャレンジ課題

### チャレンジ 1: Service Worker
Service Workerを実装してオフライン対応を追加してください。

### チャレンジ 2: Virtual Scrolling
大量のデータ表示時にvirtual scrollingを実装してください。

### チャレンジ 3: Web Workers
重い計算処理をWeb Workerに移してメインスレッドを軽量化してください。

## 🔗 次のステップ

最後は「[型安全なルーティングシステム](../07-type-safe-routing/)」に進みましょう。TypeScriptを活用した型安全なルーティングを学びます。