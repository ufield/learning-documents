# 高度なパターンと実装例 🔴

## 📖 この章で学ぶこと

- モーダルルーティングの実装
- アニメーション付きページ遷移
- 無限スクロールとバーチャライゼーション
- Nuxtの高度なパターンとの比較
- 実世界のアプリケーション設計

**想定読了時間**: 40分

---

## 🎯 モーダルルーティング

### Nuxtとの比較

NuxtでのモーダルルーティングとReact Routerのアプローチを比較してみましょう：

**Nuxtの場合（レイアウトベース）:**
```vue
<!-- layouts/modal.vue -->
<template>
  <div>
    <!-- ベースレイアウト -->
    <NuxtPage />
    
    <!-- 条件付きモーダル -->
    <div v-if="$route.query.modal" class="modal-overlay">
      <component :is="getModalComponent()" />
    </div>
  </div>
</template>

<script setup>
const getModalComponent = () => {
  const modalType = useRoute().query.modal
  return resolveComponent(`Modal${modalType}`)
}
</script>
```

**React Routerの場合（Stateベース）:**

```tsx
function App() {
  const location = useLocation()
  const background = location.state?.background
  
  return (
    <>
      <Routes location={background || location}>
        <Route path="/users" element={<UsersList />} />
        <Route path="/users/:id" element={<UserDetail />} />
      </Routes>
      
      {background && (
        <Routes>
          <Route path="/users/:id" element={<UserDetailModal />} />
        </Routes>
      )}
    </>
  )
}
```

### 実用的なモーダルルーティング実装

```tsx
// hooks/useModalRouting.ts
export function useModalRouting() {
  const location = useLocation()
  const navigate = useNavigate()
  
  const openModal = useCallback((path: string) => {
    navigate(path, { 
      state: { 
        background: location,
        isModal: true 
      } 
    })
  }, [location, navigate])
  
  const closeModal = useCallback(() => {
    const background = location.state?.background
    if (background) {
      navigate(background.pathname + background.search)
    } else {
      navigate(-1)
    }
  }, [location, navigate])
  
  const isModalOpen = Boolean(location.state?.background)
  
  return {
    openModal,
    closeModal,
    isModalOpen,
    backgroundLocation: location.state?.background
  }
}

// components/AppRouter.tsx
export function AppRouter() {
  const location = useLocation()
  const { isModalOpen, backgroundLocation } = useModalRouting()
  
  return (
    <>
      {/* メインコンテンツ */}
      <Routes location={backgroundLocation || location}>
        <Route path="/" element={<Home />} />
        <Route path="/users" element={<UsersList />} />
        <Route path="/users/:id" element={<UserDetailPage />} />
        <Route path="/products" element={<ProductsList />} />
        <Route path="/products/:id" element={<ProductDetailPage />} />
      </Routes>
      
      {/* モーダルルート */}
      {isModalOpen && (
        <Routes>
          <Route path="/users/:id" element={<UserDetailModal />} />
          <Route path="/products/:id" element={<ProductDetailModal />} />
          <Route path="/cart" element={<CartModal />} />
        </Routes>
      )}
    </>
  )
}

// components/UserDetailModal.tsx
function UserDetailModal() {
  const { id } = useParams()
  const { closeModal } = useModalRouting()
  const { user } = useLoaderData<UserDetailLoaderData>()
  
  return (
    <Modal isOpen onClose={closeModal}>
      <div className="modal-content">
        <UserProfile user={user} />
        <div className="modal-actions">
          <button onClick={closeModal}>閉じる</button>
          <Link to={`/users/${id}`} onClick={closeModal}>
            詳細ページへ
          </Link>
        </div>
      </div>
    </Modal>
  )
}

// 使用例 - ユーザー一覧での使用
function UserCard({ user }: { user: User }) {
  const { openModal } = useModalRouting()
  
  const handleQuickView = (e: React.MouseEvent) => {
    e.preventDefault()
    openModal(`/users/${user.id}`)
  }
  
  return (
    <div className="user-card">
      <img src={user.avatar} alt={user.name} />
      <h3>{user.name}</h3>
      <div className="actions">
        <Link to={`/users/${user.id}`}>詳細</Link>
        <button onClick={handleQuickView}>クイックビュー</button>
      </div>
    </div>
  )
}
```

## 🎭 アニメーション付きページ遷移

### 1. Framer Motionを使用したページ遷移

```tsx
// components/AnimatedRoutes.tsx
import { AnimatePresence, motion } from 'framer-motion'

const pageVariants = {
  initial: {
    opacity: 0,
    x: '-100vw'
  },
  in: {
    opacity: 1,
    x: 0
  },
  out: {
    opacity: 0,
    x: '100vw'
  }
}

const pageTransition = {
  type: 'tween',
  ease: 'anticipate',
  duration: 0.5
}

export function AnimatedRoutes() {
  const location = useLocation()
  
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        initial="initial"
        animate="in"
        exit="out"
        variants={pageVariants}
        transition={pageTransition}
      >
        <Routes location={location}>
          <Route path="/" element={<HomePage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}

// hooks/usePageTransition.ts
type TransitionType = 'slide' | 'fade' | 'scale' | 'flip'

export function usePageTransition(type: TransitionType = 'slide') {
  const location = useLocation()
  
  const variants = {
    slide: {
      initial: { opacity: 0, x: 300 },
      animate: { opacity: 1, x: 0 },
      exit: { opacity: 0, x: -300 }
    },
    fade: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 }
    },
    scale: {
      initial: { opacity: 0, scale: 0.8 },
      animate: { opacity: 1, scale: 1 },
      exit: { opacity: 0, scale: 1.2 }
    },
    flip: {
      initial: { opacity: 0, rotateY: 90 },
      animate: { opacity: 1, rotateY: 0 },
      exit: { opacity: 0, rotateY: -90 }
    }
  }
  
  return {
    variants: variants[type],
    location
  }
}

// 使用例
function AnimatedPage({ children }: { children: React.ReactNode }) {
  const { variants, location } = usePageTransition('slide')
  
  return (
    <motion.div
      key={location.pathname}
      variants={variants}
      initial="initial"
      animate="animate"
      exit="exit"
      transition={{ duration: 0.3 }}
    >
      {children}
    </motion.div>
  )
}
```

### 2. 条件付きアニメーション

```tsx
// utils/routeTransitions.ts
export function getTransitionDirection(
  fromPath: string, 
  toPath: string
): 'left' | 'right' | 'up' | 'down' | 'none' {
  // ルート階層に基づく遷移方向の決定
  const routes = [
    '/',
    '/products',
    '/categories',
    '/profile',
    '/settings'
  ]
  
  const fromIndex = routes.indexOf(fromPath)
  const toIndex = routes.indexOf(toPath)
  
  if (fromIndex === -1 || toIndex === -1) return 'none'
  
  if (fromIndex < toIndex) return 'left'
  if (fromIndex > toIndex) return 'right'
  return 'none'
}

// components/DirectionalRouter.tsx
export function DirectionalRouter() {
  const location = useLocation()
  const [prevLocation, setPrevLocation] = useState(location)
  
  const direction = getTransitionDirection(
    prevLocation.pathname,
    location.pathname
  )
  
  useEffect(() => {
    setPrevLocation(location)
  }, [location])
  
  const slideVariants = {
    left: {
      initial: { x: '100%' },
      animate: { x: 0 },
      exit: { x: '-100%' }
    },
    right: {
      initial: { x: '-100%' },
      animate: { x: 0 },
      exit: { x: '100%' }
    },
    none: {
      initial: { opacity: 0 },
      animate: { opacity: 1 },
      exit: { opacity: 0 }
    }
  }
  
  return (
    <AnimatePresence mode="wait">
      <motion.div
        key={location.pathname}
        variants={slideVariants[direction]}
        initial="initial"
        animate="animate"
        exit="exit"
        transition={{ type: 'tween', duration: 0.3 }}
        className="page-container"
      >
        <Routes location={location}>
          <Route path="/" element={<HomePage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/categories" element={<CategoriesPage />} />
        </Routes>
      </motion.div>
    </AnimatePresence>
  )
}
```

## 🔄 無限スクロールとバーチャライゼーション

### 1. React Routerでの無限スクロール実装

```tsx
// hooks/useInfiniteScroll.ts
interface UseInfiniteScrollOptions<T> {
  fetchMore: (page: number) => Promise<{ data: T[]; hasMore: boolean }>
  initialData?: T[]
  pageSize?: number
}

export function useInfiniteScroll<T>({
  fetchMore,
  initialData = [],
  pageSize = 20
}: UseInfiniteScrollOptions<T>) {
  const [data, setData] = useState<T[]>(initialData)
  const [page, setPage] = useState(1)
  const [isLoading, setIsLoading] = useState(false)
  const [hasMore, setHasMore] = useState(true)
  
  const loadMore = useCallback(async () => {
    if (isLoading || !hasMore) return
    
    setIsLoading(true)
    try {
      const response = await fetchMore(page)
      setData(prev => [...prev, ...response.data])
      setHasMore(response.hasMore)
      setPage(prev => prev + 1)
    } catch (error) {
      console.error('Failed to load more data:', error)
    } finally {
      setIsLoading(false)
    }
  }, [fetchMore, page, isLoading, hasMore])
  
  // Intersection Observer for automatic loading
  const observerRef = useRef<IntersectionObserver>()
  const lastElementRef = useCallback((node: HTMLElement | null) => {
    if (isLoading) return
    if (observerRef.current) observerRef.current.disconnect()
    
    observerRef.current = new IntersectionObserver(entries => {
      if (entries[0].isIntersecting && hasMore) {
        loadMore()
      }
    })
    
    if (node) observerRef.current.observe(node)
  }, [isLoading, hasMore, loadMore])
  
  return {
    data,
    isLoading,
    hasMore,
    loadMore,
    lastElementRef
  }
}

// pages/ProductsPage.tsx
function ProductsPage() {
  const [searchParams] = useSearchParams()
  const category = searchParams.get('category')
  const search = searchParams.get('search')
  
  const { data: products, isLoading, hasMore, lastElementRef } = 
    useInfiniteScroll({
      fetchMore: async (page) => {
        const response = await fetch(
          `/api/products?page=${page}&category=${category}&search=${search}`
        )
        return response.json()
      }
    })
  
  return (
    <div>
      <h1>商品一覧</h1>
      <ProductFilters />
      
      <div className="products-grid">
        {products.map((product, index) => (
          <div
            key={product.id}
            ref={index === products.length - 1 ? lastElementRef : null}
          >
            <ProductCard product={product} />
          </div>
        ))}
      </div>
      
      {isLoading && <ProductsSkeleton />}
      {!hasMore && <div>すべての商品を表示しました</div>}
    </div>
  )
}
```

### 2. バーチャライゼーション（仮想スクロール）

```tsx
// hooks/useVirtualization.ts
interface UseVirtualizationOptions {
  itemHeight: number
  containerHeight: number
  itemCount: number
  overscan?: number
}

export function useVirtualization({
  itemHeight,
  containerHeight,
  itemCount,
  overscan = 5
}: UseVirtualizationOptions) {
  const [scrollTop, setScrollTop] = useState(0)
  
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan)
  const endIndex = Math.min(
    itemCount - 1,
    Math.floor((scrollTop + containerHeight) / itemHeight) + overscan
  )
  
  const visibleItems = Array.from(
    { length: endIndex - startIndex + 1 },
    (_, index) => startIndex + index
  )
  
  const totalHeight = itemCount * itemHeight
  const offsetY = startIndex * itemHeight
  
  const handleScroll = (e: React.UIEvent<HTMLDivElement>) => {
    setScrollTop(e.currentTarget.scrollTop)
  }
  
  return {
    visibleItems,
    totalHeight,
    offsetY,
    handleScroll
  }
}

// components/VirtualizedList.tsx
interface VirtualizedListProps<T> {
  items: T[]
  itemHeight: number
  height: number
  renderItem: (item: T, index: number) => React.ReactNode
}

export function VirtualizedList<T>({
  items,
  itemHeight,
  height,
  renderItem
}: VirtualizedListProps<T>) {
  const { visibleItems, totalHeight, offsetY, handleScroll } = 
    useVirtualization({
      itemHeight,
      containerHeight: height,
      itemCount: items.length
    })
  
  return (
    <div 
      className="virtual-list-container"
      style={{ height, overflow: 'auto' }}
      onScroll={handleScroll}
    >
      <div style={{ height: totalHeight, position: 'relative' }}>
        <div style={{ transform: `translateY(${offsetY}px)` }}>
          {visibleItems.map(index => (
            <div key={index} style={{ height: itemHeight }}>
              {renderItem(items[index], index)}
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

// 使用例
function LargeUserList() {
  const { users } = useLoaderData<{ users: User[] }>()
  
  return (
    <VirtualizedList
      items={users}
      itemHeight={80}
      height={600}
      renderItem={(user) => (
        <UserCard key={user.id} user={user} />
      )}
    />
  )
}
```

## 🎨 高度なレイアウトパターン

### 1. アダプティブサイドバー

```tsx
// components/AdaptiveSidebar.tsx
type SidebarState = 'collapsed' | 'expanded' | 'overlay'

export function AdaptiveSidebar({ children }: { children: React.ReactNode }) {
  const [sidebarState, setSidebarState] = useState<SidebarState>('expanded')
  const [isMobile, setIsMobile] = useState(false)
  
  useEffect(() => {
    const handleResize = () => {
      const mobile = window.innerWidth < 768
      setIsMobile(mobile)
      
      if (mobile) {
        setSidebarState('overlay')
      } else if (window.innerWidth < 1024) {
        setSidebarState('collapsed')
      } else {
        setSidebarState('expanded')
      }
    }
    
    handleResize()
    window.addEventListener('resize', handleResize)
    return () => window.removeEventListener('resize', handleResize)
  }, [])
  
  const sidebarClasses = {
    collapsed: 'w-16',
    expanded: 'w-64',
    overlay: 'w-64 fixed z-50 md:relative md:z-auto'
  }
  
  return (
    <div className="flex h-screen">
      {/* サイドバー */}
      <aside className={`
        bg-gray-800 text-white transition-all duration-300
        ${sidebarClasses[sidebarState]}
        ${sidebarState === 'overlay' && isMobile ? 'translate-x-0' : ''}
      `}>
        <nav className="p-4">
          <NavigationItems collapsed={sidebarState === 'collapsed'} />
        </nav>
      </aside>
      
      {/* オーバーレイ背景 */}
      {sidebarState === 'overlay' && isMobile && (
        <div 
          className="fixed inset-0 bg-black bg-opacity-50 z-40"
          onClick={() => setSidebarState('collapsed')}
        />
      )}
      
      {/* メインコンテンツ */}
      <main className="flex-1 overflow-auto">
        <div className="p-6">
          {children}
        </div>
      </main>
    </div>
  )
}
```

### 2. マルチパネルレイアウト

```tsx
// components/MultiPanelLayout.tsx
interface Panel {
  id: string
  title: string
  content: React.ReactNode
  minWidth?: number
  defaultWidth?: number
}

export function MultiPanelLayout({ panels }: { panels: Panel[] }) {
  const [widths, setWidths] = useState<Record<string, number>>(
    panels.reduce((acc, panel) => ({
      ...acc,
      [panel.id]: panel.defaultWidth || 300
    }), {})
  )
  
  const handleResize = (panelId: string, width: number) => {
    setWidths(prev => ({
      ...prev,
      [panelId]: Math.max(width, panels.find(p => p.id === panelId)?.minWidth || 200)
    }))
  }
  
  return (
    <div className="flex h-full">
      {panels.map((panel, index) => (
        <div key={panel.id} className="flex">
          <div 
            className="bg-white border-r"
            style={{ width: widths[panel.id] }}
          >
            <div className="border-b p-4 font-semibold">
              {panel.title}
            </div>
            <div className="p-4 overflow-auto">
              {panel.content}
            </div>
          </div>
          
          {index < panels.length - 1 && (
            <ResizeHandle 
              onResize={(delta) => 
                handleResize(panel.id, widths[panel.id] + delta)
              }
            />
          )}
        </div>
      ))}
    </div>
  )
}

// 使用例 - IDEライクなレイアウト
function DeveloperWorkspace() {
  const panels = [
    {
      id: 'explorer',
      title: 'エクスプローラー',
      content: <FileExplorer />,
      minWidth: 200,
      defaultWidth: 250
    },
    {
      id: 'editor',
      title: 'エディター',
      content: <CodeEditor />,
      minWidth: 400,
      defaultWidth: 800
    },
    {
      id: 'terminal',
      title: 'ターミナル',
      content: <Terminal />,
      minWidth: 300,
      defaultWidth: 400
    }
  ]
  
  return <MultiPanelLayout panels={panels} />
}
```

## 🔧 状態管理との統合

### 1. Zustandとの統合

```tsx
// stores/navigationStore.ts
import { create } from 'zustand'
import { persist } from 'zustand/middleware'

interface NavigationState {
  history: string[]
  favorites: string[]
  recentlyVisited: Array<{ path: string; timestamp: number; title: string }>
  addToHistory: (path: string) => void
  addToFavorites: (path: string, title: string) => void
  removeFromFavorites: (path: string) => void
  addToRecent: (path: string, title: string) => void
}

export const useNavigationStore = create<NavigationState>()(
  persist(
    (set, get) => ({
      history: [],
      favorites: [],
      recentlyVisited: [],
      
      addToHistory: (path) => {
        set((state) => ({
          history: [path, ...state.history.filter(h => h !== path)].slice(0, 50)
        }))
      },
      
      addToFavorites: (path, title) => {
        set((state) => ({
          favorites: [...state.favorites.filter(f => f !== path), path]
        }))
      },
      
      removeFromFavorites: (path) => {
        set((state) => ({
          favorites: state.favorites.filter(f => f !== path)
        }))
      },
      
      addToRecent: (path, title) => {
        set((state) => ({
          recentlyVisited: [
            { path, title, timestamp: Date.now() },
            ...state.recentlyVisited.filter(r => r.path !== path)
          ].slice(0, 10)
        }))
      }
    }),
    { name: 'navigation-storage' }
  )
)

// hooks/useNavigationTracking.ts
export function useNavigationTracking() {
  const location = useLocation()
  const { addToHistory, addToRecent } = useNavigationStore()
  
  useEffect(() => {
    addToHistory(location.pathname)
    
    // ページタイトルを取得してrecentlyVisitedに追加
    const title = document.title
    addToRecent(location.pathname, title)
  }, [location.pathname, addToHistory, addToRecent])
}
```

### 2. React Queryとの統合

```tsx
// hooks/useRouteCaching.ts
import { useQuery, useQueryClient } from '@tanstack/react-query'

export function useRouteCaching<T>(
  queryKey: string[],
  fetcher: () => Promise<T>,
  options: {
    staleTime?: number
    cacheTime?: number
    prefetchRelated?: string[][]
  } = {}
) {
  const queryClient = useQueryClient()
  const location = useLocation()
  
  const query = useQuery({
    queryKey,
    queryFn: fetcher,
    staleTime: options.staleTime || 5 * 60 * 1000, // 5分
    cacheTime: options.cacheTime || 10 * 60 * 1000, // 10分
  })
  
  // 関連データのプリフェッチ
  useEffect(() => {
    if (options.prefetchRelated) {
      options.prefetchRelated.forEach(relatedKey => {
        queryClient.prefetchQuery({
          queryKey: relatedKey,
          queryFn: () => fetchRelatedData(relatedKey)
        })
      })
    }
  }, [queryClient, options.prefetchRelated])
  
  return query
}

// 使用例
function ProductDetail() {
  const { id } = useParams()
  
  const { data: product, isLoading } = useRouteCaching(
    ['product', id!],
    () => fetchProduct(id!),
    {
      prefetchRelated: [
        ['products', 'related', id!],
        ['reviews', id!]
      ]
    }
  )
  
  if (isLoading) return <ProductSkeleton />
  
  return <ProductDetailView product={product} />
}
```

## 🔄 Nuxt.js → React Router 高度パターン比较

| パターン | Nuxt.js | React Router |
|----------|------------|--------------|
| モーダルルート | クエリベース + レイアウト | Location State + Conditional |
| ページ遷移 | `<Transition>` + CSS | Framer Motion + AnimatePresence |
| 無限スクロール | `@nuxtjs/infinite-loading` | カスタムフック + Intersection Observer |
| 状態管理統合 | Pinia + composables | Zustand/Redux + カスタムフック |
| キャッシュ戦略 | Nitroキャッシュ | React Query + カスタムフック |
| 動的インポート | 自動コード分割 | `lazy()` + `Suspense` |
| SEOメタデータ | `useSeoMeta()` | Remix `meta()` + Helmet |

## 🎓 まとめ

React Routerの高度なパターンは、Nuxtとは異なるアプローチでありながら、Reactエコシステムとの深い統合と柔軟なカスタマイズ性を提供します：

1. **モーダルルーティング**: Location Stateを活用した柔軟な実装
2. **アニメーション**: Framer Motionとの深い統合
3. **パフォーマンス**: 無限スクロールとバーチャライゼーション
4. **状態管理**: 現代的な状態管理ライブラリとの統合

これで React Router v7 の包括的な学習ドキュメントが完成しました。Nuxtの経験を活かしながら、React Routerの強力な機能を習得できる内容となっています。

---

**🎉 学習完了**: これでReact Router v7の全機能を網羅しました！実際のプロジェクトで活用してみてください。