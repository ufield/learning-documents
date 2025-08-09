# パフォーマンス最適化 🔴

## 📖 この章で学ぶこと

- コード分割とReact.lazyによる遅延読み込み
- プリフェッチング戦略
- React 18/19の新機能活用
- Vue/Nuxtの最適化技術との比較
- Bundle Analyzerを使った分析方法

**想定読了時間**: 30分

---

## 🚀 コード分割と遅延読み込み

### Vue/Nuxtとの比較

まず、Vue/Nuxtの動的インポートとReact Routerの比較から始めましょう：

```javascript
// Vue Router (Vue 3 + Vite)
const routes = [
  {
    path: '/dashboard',
    component: () => import('@/views/Dashboard.vue')
  }
]

// Nuxt.js (自動コード分割)
// pages/dashboard.vue が自動的にチャンクに分割される

// React Router v7
import { lazy, Suspense } from 'react'

const Dashboard = lazy(() => import('../pages/Dashboard'))

const router = createBrowserRouter([
  {
    path: "/dashboard",
    element: (
      <Suspense fallback={<LoadingSpinner />}>
        <Dashboard />
      </Suspense>
    )
  }
])
```

### 基本的なコード分割実装

```tsx
// utils/lazyLoad.tsx
export function lazyLoad(importFunc: () => Promise<any>, fallback?: React.ComponentType) {
  const Component = lazy(importFunc)
  
  return (props: any) => (
    <Suspense fallback={fallback ? <fallback /> : <div>読み込み中...</div>}>
      <Component {...props} />
    </Suspense>
  )
}

// ルート定義での使用
const Dashboard = lazyLoad(() => import('../pages/Dashboard'))
const UserProfile = lazyLoad(() => import('../pages/UserProfile'), LoadingSkeleton)

const router = createBrowserRouter([
  {
    path: "/dashboard",
    element: <Dashboard />
  },
  {
    path: "/profile/:id", 
    element: <UserProfile />
  }
])
```

### 階層的なコード分割

```tsx
// レイアウトレベルでの分割
const AdminLayout = lazy(() => import('../layouts/AdminLayout'))
const UserLayout = lazy(() => import('../layouts/UserLayout'))

// ページレベルでの分割
const AdminDashboard = lazy(() => import('../pages/admin/Dashboard'))
const AdminUsers = lazy(() => import('../pages/admin/Users'))

const router = createBrowserRouter([
  {
    path: "/admin",
    element: (
      <Suspense fallback={<AdminLoadingSkeleton />}>
        <AdminLayout />
      </Suspense>
    ),
    children: [
      {
        path: "dashboard",
        element: (
          <Suspense fallback={<PageLoading />}>
            <AdminDashboard />
          </Suspense>
        )
      },
      {
        path: "users",
        element: (
          <Suspense fallback={<PageLoading />}>
            <AdminUsers />
          </Suspense>
        )
      }
    ]
  }
])
```

## 📡 プリフェッチング戦略

### 1. インテントベースプリフェッチング

```tsx
// React Router v7の新機能
import { Link } from 'react-router-dom'

function Navigation() {
  return (
    <nav>
      {/* ホバー時にプリフェッチ */}
      <Link to="/dashboard" prefetch="intent">
        ダッシュボード
      </Link>
      
      {/* 表示時にプリフェッチ */}
      <Link to="/reports" prefetch="render">
        レポート
      </Link>
      
      {/* プリフェッチなし */}
      <Link to="/settings" prefetch="none">
        設定
      </Link>
    </nav>
  )
}
```

### 2. カスタムプリフェッチングフック

```tsx
// hooks/usePrefetch.ts
import { useCallback, useEffect } from 'react'

export function usePrefetch() {
  const prefetchRoute = useCallback(async (routePath: string) => {
    try {
      // ルートコンポーネントを事前に読み込み
      const moduleImport = getRouteImport(routePath)
      if (moduleImport) {
        await moduleImport()
      }
      
      // データも事前に取得
      const loader = getRouteLoader(routePath)
      if (loader) {
        await loader({ params: {}, request: new Request(routePath) })
      }
    } catch (error) {
      console.warn('Prefetch failed:', error)
    }
  }, [])
  
  const prefetchOnHover = useCallback((routePath: string) => {
    return {
      onMouseEnter: () => prefetchRoute(routePath),
      onFocus: () => prefetchRoute(routePath)
    }
  }, [prefetchRoute])
  
  return { prefetchRoute, prefetchOnHover }
}

// 使用例
function ProductCard({ product }: { product: Product }) {
  const { prefetchOnHover } = usePrefetch()
  
  return (
    <div 
      className="product-card"
      {...prefetchOnHover(`/products/${product.id}`)}
    >
      <Link to={`/products/${product.id}`}>
        <img src={product.image} alt={product.name} />
        <h3>{product.name}</h3>
      </Link>
    </div>
  )
}
```

### 3. インターセクション観察によるプリフェッチ

```tsx
// hooks/useIntersectionPrefetch.ts
export function useIntersectionPrefetch(routePath: string, threshold = 0.1) {
  const elementRef = useRef<HTMLElement>(null)
  const { prefetchRoute } = usePrefetch()
  const [hasTriggered, setHasTriggered] = useState(false)
  
  useEffect(() => {
    const element = elementRef.current
    if (!element || hasTriggered) return
    
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            prefetchRoute(routePath)
            setHasTriggered(true)
            observer.unobserve(element)
          }
        })
      },
      { threshold }
    )
    
    observer.observe(element)
    
    return () => observer.disconnect()
  }, [routePath, threshold, hasTriggered, prefetchRoute])
  
  return elementRef
}

// 使用例 - スクロール時のプリフェッチ
function SectionLink({ to, children }: { to: string; children: React.ReactNode }) {
  const ref = useIntersectionPrefetch(to)
  
  return (
    <Link to={to} ref={ref}>
      {children}
    </Link>
  )
}
```

## ⚡ React 18/19の新機能活用

### 1. Concurrent Features

```tsx
// React 18のstartTransitionを活用
import { startTransition } from 'react'
import { useNavigate } from 'react-router-dom'

function NavigationMenu() {
  const navigate = useNavigate()
  
  const handleNavigation = (path: string) => {
    // 低優先度でナビゲーションを実行
    startTransition(() => {
      navigate(path)
    })
  }
  
  return (
    <nav>
      <button onClick={() => handleNavigation('/dashboard')}>
        ダッシュボード
      </button>
    </nav>
  )
}

// useDeferredValueを使った検索最適化
function SearchResults() {
  const [searchParams] = useSearchParams()
  const query = searchParams.get('q') || ''
  const deferredQuery = useDeferredValue(query)
  
  // deferredQueryは緊急度の低い更新として扱われる
  const results = useSearchResults(deferredQuery)
  
  return (
    <div>
      {query !== deferredQuery && <div>検索中...</div>}
      <SearchResultList results={results} />
    </div>
  )
}
```

### 2. React Server Components対応

```tsx
// React 19のServer Components (実験的機能)
// app/routes/products.tsx
export default async function ProductsPage() {
  // サーバー上で実行される
  const products = await db.products.findMany()
  
  return (
    <div>
      <h1>商品一覧</h1>
      <ProductGrid products={products} />
    </div>
  )
}

// Client Component
'use client'
function ProductGrid({ products }: { products: Product[] }) {
  const [selectedCategory, setSelectedCategory] = useState('')
  
  // クライアントサイドの対話機能
  const filteredProducts = products.filter(p => 
    !selectedCategory || p.category === selectedCategory
  )
  
  return (
    <div>
      <CategoryFilter onSelect={setSelectedCategory} />
      <div className="grid">
        {filteredProducts.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  )
}
```

## 📊 バンドル分析と最適化

### 1. Viteでのバンドル分析

```bash
# バンドルアナライザーのインストール
npm install --save-dev rollup-plugin-visualizer

# vite.config.ts
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
          vendor: ['react', 'react-dom', 'react-router-dom'],
          ui: ['@mui/material', '@mui/icons-material'],
          utils: ['lodash', 'date-fns']
        }
      }
    }
  }
})
```

### 2. 最適化されたチャンク分割

```tsx
// utils/chunkOptimization.ts
export const createOptimalChunks = () => ({
  // React関連ライブラリ
  react: ['react', 'react-dom', 'react-router-dom'],
  
  // UI ライブラリ
  ui: ['@mui/material', '@headlessui/react', 'framer-motion'],
  
  // ユーティリティライブラリ
  utils: ['lodash', 'date-fns', 'zod', 'axios'],
  
  // 認証関連
  auth: ['@auth0/nextjs-auth0', 'jsonwebtoken'],
  
  // データ視覚化
  charts: ['recharts', 'd3', 'chart.js'],
  
  // エディター関連（重いライブラリ）
  editor: ['@monaco-editor/react', 'quill', 'slate']
})

// vite.config.ts での使用
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          ...createOptimalChunks(),
          // ページごとのチャンク
          admin: ['src/pages/admin/*'],
          user: ['src/pages/user/*']
        }
      }
    }
  }
})
```

## 🎯 リソース最適化

### 1. 画像の最適化

```tsx
// components/OptimizedImage.tsx
interface OptimizedImageProps {
  src: string
  alt: string
  width?: number
  height?: number
  priority?: boolean
}

function OptimizedImage({ 
  src, 
  alt, 
  width, 
  height, 
  priority = false 
}: OptimizedImageProps) {
  const [isLoaded, setIsLoaded] = useState(false)
  const [error, setError] = useState(false)
  
  // WebP対応チェック
  const [supportsWebP, setSupportsWebP] = useState(false)
  
  useEffect(() => {
    const webp = new Image()
    webp.onload = webp.onerror = () => {
      setSupportsWebP(webp.height === 2)
    }
    webp.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA'
  }, [])
  
  const optimizedSrc = useMemo(() => {
    if (supportsWebP && !src.includes('.svg')) {
      return src.replace(/\.(jpg|jpeg|png)$/, '.webp')
    }
    return src
  }, [src, supportsWebP])
  
  return (
    <div className="optimized-image-container">
      {!isLoaded && <div className="image-placeholder" />}
      <img
        src={optimizedSrc}
        alt={alt}
        width={width}
        height={height}
        loading={priority ? 'eager' : 'lazy'}
        onLoad={() => setIsLoaded(true)}
        onError={() => setError(true)}
        style={{
          opacity: isLoaded ? 1 : 0,
          transition: 'opacity 0.3s ease'
        }}
      />
      {error && <div>画像の読み込みに失敗しました</div>}
    </div>
  )
}
```

### 2. フォントの最適化

```tsx
// utils/fontOptimization.ts
export function preloadFonts() {
  const fonts = [
    {
      family: 'Noto Sans JP',
      weights: [400, 700],
      display: 'swap'
    }
  ]
  
  fonts.forEach(font => {
    font.weights.forEach(weight => {
      const link = document.createElement('link')
      link.rel = 'preload'
      link.as = 'font'
      link.type = 'font/woff2'
      link.crossOrigin = 'anonymous'
      link.href = `/fonts/${font.family}-${weight}.woff2`
      document.head.appendChild(link)
    })
  })
}

// CSS-in-JSでのフォント最適化
const fontFaceRules = `
  @font-face {
    font-family: 'Noto Sans JP';
    font-weight: 400;
    font-display: swap;
    src: url('/fonts/NotoSansJP-Regular.woff2') format('woff2');
    unicode-range: U+3040-309F, U+30A0-30FF, U+4E00-9FAF;
  }
`
```

## 📈 パフォーマンス測定とモニタリング

### 1. Web Vitals の計測

```tsx
// utils/webVitals.ts
import { getCLS, getFID, getFCP, getLCP, getTTFB } from 'web-vitals'

export function measureWebVitals() {
  getCLS(console.log)
  getFID(console.log)
  getFCP(console.log)
  getLCP(console.log)
  getTTFB(console.log)
}

// hooks/usePerformanceMonitoring.ts
export function usePerformanceMonitoring() {
  useEffect(() => {
    // Route変更時のパフォーマンス測定
    const startTime = performance.now()
    
    return () => {
      const endTime = performance.now()
      const navigationTime = endTime - startTime
      
      // 分析サービスに送信
      analytics.track('route_performance', {
        path: window.location.pathname,
        duration: navigationTime
      })
    }
  }, [])
}
```

### 2. リアルタイムパフォーマンス監視

```tsx
// components/PerformanceMonitor.tsx
function PerformanceMonitor() {
  const navigation = useNavigation()
  const [metrics, setMetrics] = useState({
    loadTime: 0,
    renderTime: 0,
    memoryUsage: 0
  })
  
  useEffect(() => {
    const observer = new PerformanceObserver((list) => {
      list.getEntries().forEach((entry) => {
        if (entry.entryType === 'navigation') {
          const nav = entry as PerformanceNavigationTiming
          setMetrics(prev => ({
            ...prev,
            loadTime: nav.loadEventEnd - nav.loadEventStart
          }))
        }
      })
    })
    
    observer.observe({ entryTypes: ['navigation', 'measure'] })
    
    return () => observer.disconnect()
  }, [])
  
  // 開発環境でのみ表示
  if (process.env.NODE_ENV !== 'development') return null
  
  return (
    <div className="performance-monitor">
      <div>読み込み: {metrics.loadTime}ms</div>
      <div>状態: {navigation.state}</div>
    </div>
  )
}
```

## 🔄 Vue/Nuxt → React Router パフォーマンス比較

| 機能 | Vue/Nuxt | React Router |
|------|----------|--------------|
| 動的インポート | `() => import()` | `lazy()` + `Suspense` |
| プリフェッチング | `<nuxt-link prefetch>` | `prefetch="intent"` |
| コード分割 | 自動（Nuxt） | 手動設定 |
| バンドル分析 | `nuxi analyze` | Rollup Visualizer |
| 画像最適化 | `@nuxt/image` | カスタム実装 |
| フォント最適化 | `@nuxtjs/google-fonts` | カスタム実装 |

## 💡 ベストプラクティス

### 1. 適切な分割粒度

```tsx
// ❌ 細かすぎる分割
const Button = lazy(() => import('./Button'))
const Input = lazy(() => import('./Input'))

// ✅ 適切な分割
const AdminPages = lazy(() => import('./admin'))
const UserPages = lazy(() => import('./user'))

// ✅ 機能単位の分割
const ReportingModule = lazy(() => import('./modules/Reporting'))
```

### 2. プリフェッチングの戦略的使用

```tsx
// 優先度に基づくプリフェッチング
function NavigationMenu() {
  return (
    <nav>
      {/* 高頻度アクセス - 積極的プリフェッチ */}
      <Link to="/dashboard" prefetch="render">
        ダッシュボード
      </Link>
      
      {/* 中頻度アクセス - インテントベース */}
      <Link to="/reports" prefetch="intent">
        レポート
      </Link>
      
      {/* 低頻度アクセス - プリフェッチなし */}
      <Link to="/admin" prefetch="none">
        管理者
      </Link>
    </nav>
  )
}
```

## 🎓 まとめ

React Routerでのパフォーマンス最適化は、Vue/Nuxtと同様の概念でありながら、より細かい制御と現代的なReactの機能を活用できます：

1. **コード分割**: 戦略的なチャンク分割による初期読み込み高速化
2. **プリフェッチング**: インテリジェントな事前読み込み
3. **React 18/19**: Concurrent FeaturesとServer Componentsの活用
4. **監視**: Web Vitalsとリアルタイム性能監視

次章では、型安全なルーティングについて学びます。

---

**🔗 次章**: [型安全なルーティング](./10-type-safety.md)