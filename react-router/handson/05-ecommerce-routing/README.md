# ECサイトのルーティング

**所要時間: 2.5時間**  
**レベル: 🟡 中級**

複雑なルート構造とクエリパラメータを活用したECサイトを作成し、実用的なナビゲーションパターンを学びます。

## 🎯 学習目標

- 複雑なURLパターンの設計と実装を学ぶ
- クエリパラメータを活用した検索・フィルター機能を理解する
- ページネーション機能の実装方法を覚える
- カート機能とセッション管理を学ぶ
- SEO対応のURLデザインを理解する
- 商品詳細の動的ルーティングを実装する

## 🏗️ 作るもの

ECサイト：
- 商品一覧ページ（カテゴリ別、検索、フィルター、ソート）
- 商品詳細ページ
- ショッピングカート
- チェックアウトページ
- ユーザーアカウント管理
- 注文履歴

## 📋 前提条件

- 「認証付きTodoアプリ」を完了していること
- ECサイトの基本的なUX/UIを理解していること

## 🚀 始め方

### ステップ 1: プロジェクトの準備

```bash
cd starter
npm install
npm run dev
```

### ステップ 2: 段階的な実装

1. **Step 1**: 商品データとルート構造の設定
2. **Step 2**: 商品一覧ページと検索・フィルター機能
3. **Step 3**: 商品詳細ページと関連商品
4. **Step 4**: ショッピングカート機能
5. **Step 5**: チェックアウトプロセス

### ステップ 3: 実装開始

#### Step 1: 商品データとルート構造

**src/data/products.ts**:

```tsx
export interface Product {
  id: string
  name: string
  description: string
  price: number
  originalPrice?: number
  category: string
  subcategory: string
  brand: string
  images: string[]
  tags: string[]
  rating: number
  reviewCount: number
  inStock: number
  createdAt: string
  featured: boolean
}

export const categories = [
  {
    id: 'electronics',
    name: '電子機器',
    subcategories: [
      { id: 'smartphones', name: 'スマートフォン' },
      { id: 'laptops', name: 'ノートパソコン' },
      { id: 'headphones', name: 'ヘッドフォン' },
    ]
  },
  {
    id: 'fashion',
    name: 'ファッション',
    subcategories: [
      { id: 'mens', name: 'メンズ' },
      { id: 'womens', name: 'レディース' },
      { id: 'accessories', name: 'アクセサリー' },
    ]
  },
  {
    id: 'books',
    name: '書籍',
    subcategories: [
      { id: 'programming', name: 'プログラミング' },
      { id: 'design', name: 'デザイン' },
      { id: 'business', name: 'ビジネス' },
    ]
  }
]

export const products: Product[] = [
  {
    id: '1',
    name: 'iPhone 15 Pro',
    description: '最新のA17 Proチップを搭載したプロフェッショナル向けスマートフォン',
    price: 159800,
    originalPrice: 179800,
    category: 'electronics',
    subcategory: 'smartphones',
    brand: 'Apple',
    images: ['iphone15pro-1.jpg', 'iphone15pro-2.jpg'],
    tags: ['新商品', 'セール', '高性能'],
    rating: 4.8,
    reviewCount: 142,
    inStock: 25,
    createdAt: '2024-01-15',
    featured: true
  },
  {
    id: '2',
    name: 'MacBook Pro 16インチ',
    description: 'M3 Maxチップ搭載の最強ノートパソコン',
    price: 398000,
    category: 'electronics',
    subcategory: 'laptops',
    brand: 'Apple',
    images: ['macbook-pro-1.jpg', 'macbook-pro-2.jpg'],
    tags: ['プロ向け', '高性能', 'クリエイター'],
    rating: 4.9,
    reviewCount: 89,
    inStock: 12,
    createdAt: '2024-01-10',
    featured: true
  },
  {
    id: '3',
    name: 'AirPods Pro (第2世代)',
    description: '進化したアクティブノイズキャンセリング機能',
    price: 39800,
    originalPrice: 42800,
    category: 'electronics',
    subcategory: 'headphones',
    brand: 'Apple',
    images: ['airpods-pro-1.jpg', 'airpods-pro-2.jpg'],
    tags: ['ノイズキャンセリング', 'ワイヤレス'],
    rating: 4.7,
    reviewCount: 256,
    inStock: 48,
    createdAt: '2024-01-05',
    featured: false
  },
  // ... 追加の商品データ
]

export const getProductsByCategory = (category: string, subcategory?: string) => {
  return products.filter(product => {
    if (subcategory) {
      return product.category === category && product.subcategory === subcategory
    }
    return product.category === category
  })
}

export const searchProducts = (query: string) => {
  const lowercaseQuery = query.toLowerCase()
  return products.filter(product =>
    product.name.toLowerCase().includes(lowercaseQuery) ||
    product.description.toLowerCase().includes(lowercaseQuery) ||
    product.brand.toLowerCase().includes(lowercaseQuery) ||
    product.tags.some(tag => tag.toLowerCase().includes(lowercaseQuery))
  )
}

export const getProductById = (id: string) => {
  return products.find(product => product.id === id)
}

export const getFeaturedProducts = () => {
  return products.filter(product => product.featured)
}
```

**src/main.tsx**:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'

import { CartProvider } from './contexts/CartContext'
import Layout from './components/Layout'
import Home from './pages/Home'
import ProductList from './pages/ProductList'
import ProductDetail from './pages/ProductDetail'
import Cart from './pages/Cart'
import Checkout from './pages/Checkout'
import OrderConfirmation from './pages/OrderConfirmation'
import SearchResults from './pages/SearchResults'

const router = createBrowserRouter([
  {
    path: "/",
    element: <Layout />,
    children: [
      {
        index: true,
        element: <Home />,
      },
      {
        path: "search",
        element: <SearchResults />,
      },
      {
        path: "categories/:category",
        element: <ProductList />,
      },
      {
        path: "categories/:category/:subcategory",
        element: <ProductList />,
      },
      {
        path: "products/:id",
        element: <ProductDetail />,
      },
      {
        path: "cart",
        element: <Cart />,
      },
      {
        path: "checkout",
        element: <Checkout />,
      },
      {
        path: "order-confirmation/:orderId",
        element: <OrderConfirmation />,
      },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <CartProvider>
      <RouterProvider router={router} />
    </CartProvider>
  </React.StrictMode>,
)
```

#### Step 2: カートコンテキスト

**src/contexts/CartContext.tsx**:

```tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

export interface CartItem {
  id: string
  name: string
  price: number
  image: string
  quantity: number
}

interface CartContextType {
  items: CartItem[]
  addToCart: (product: { id: string; name: string; price: number; image: string }) => void
  removeFromCart: (id: string) => void
  updateQuantity: (id: string, quantity: number) => void
  clearCart: () => void
  getTotalPrice: () => number
  getTotalItems: () => number
}

const CartContext = createContext<CartContextType | undefined>(undefined)

export function CartProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<CartItem[]>([])

  // localStorage からカートデータを復元
  useEffect(() => {
    const savedCart = localStorage.getItem('shopping_cart')
    if (savedCart) {
      setItems(JSON.parse(savedCart))
    }
  }, [])

  // カートの変更を localStorage に保存
  useEffect(() => {
    localStorage.setItem('shopping_cart', JSON.stringify(items))
  }, [items])

  const addToCart = (product: { id: string; name: string; price: number; image: string }) => {
    setItems(prev => {
      const existingItem = prev.find(item => item.id === product.id)
      
      if (existingItem) {
        return prev.map(item =>
          item.id === product.id
            ? { ...item, quantity: item.quantity + 1 }
            : item
        )
      }
      
      return [...prev, { ...product, quantity: 1 }]
    })
  }

  const removeFromCart = (id: string) => {
    setItems(prev => prev.filter(item => item.id !== id))
  }

  const updateQuantity = (id: string, quantity: number) => {
    if (quantity <= 0) {
      removeFromCart(id)
      return
    }
    
    setItems(prev =>
      prev.map(item =>
        item.id === id ? { ...item, quantity } : item
      )
    )
  }

  const clearCart = () => {
    setItems([])
  }

  const getTotalPrice = () => {
    return items.reduce((total, item) => total + (item.price * item.quantity), 0)
  }

  const getTotalItems = () => {
    return items.reduce((total, item) => total + item.quantity, 0)
  }

  const value = {
    items,
    addToCart,
    removeFromCart,
    updateQuantity,
    clearCart,
    getTotalPrice,
    getTotalItems
  }

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>
}

export function useCart() {
  const context = useContext(CartContext)
  if (context === undefined) {
    throw new Error('useCart must be used within a CartProvider')
  }
  return context
}
```

#### Step 3: 商品一覧ページ

**src/pages/ProductList.tsx**:

```tsx
import { useState, useEffect } from 'react'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { products, categories, getProductsByCategory, Product } from '../data/products'
import ProductCard from '../components/ProductCard'

function ProductList() {
  const { category, subcategory } = useParams<{ category: string; subcategory?: string }>()
  const [searchParams, setSearchParams] = useSearchParams()
  
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([])
  const [sortBy, setSortBy] = useState(searchParams.get('sort') || 'newest')
  const [minPrice, setMinPrice] = useState(searchParams.get('minPrice') || '')
  const [maxPrice, setMaxPrice] = useState(searchParams.get('maxPrice') || '')
  const [selectedBrands, setSelectedBrands] = useState<string[]>(
    searchParams.getAll('brands') || []
  )
  const [currentPage, setCurrentPage] = useState(Number(searchParams.get('page')) || 1)
  
  const ITEMS_PER_PAGE = 12

  // カテゴリ情報を取得
  const currentCategory = categories.find(cat => cat.id === category)
  const currentSubcategory = currentCategory?.subcategories.find(sub => sub.id === subcategory)

  useEffect(() => {
    let filtered = category ? getProductsByCategory(category, subcategory) : products

    // 価格フィルター
    if (minPrice) {
      filtered = filtered.filter(product => product.price >= Number(minPrice))
    }
    if (maxPrice) {
      filtered = filtered.filter(product => product.price <= Number(maxPrice))
    }

    // ブランドフィルター
    if (selectedBrands.length > 0) {
      filtered = filtered.filter(product => selectedBrands.includes(product.brand))
    }

    // ソート
    filtered = [...filtered].sort((a, b) => {
      switch (sortBy) {
        case 'price-low':
          return a.price - b.price
        case 'price-high':
          return b.price - a.price
        case 'rating':
          return b.rating - a.rating
        case 'popular':
          return b.reviewCount - a.reviewCount
        case 'newest':
        default:
          return new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()
      }
    })

    setFilteredProducts(filtered)
  }, [category, subcategory, sortBy, minPrice, maxPrice, selectedBrands])

  // URLパラメータを更新
  useEffect(() => {
    const newSearchParams = new URLSearchParams()
    
    if (sortBy !== 'newest') newSearchParams.set('sort', sortBy)
    if (minPrice) newSearchParams.set('minPrice', minPrice)
    if (maxPrice) newSearchParams.set('maxPrice', maxPrice)
    if (selectedBrands.length > 0) {
      selectedBrands.forEach(brand => newSearchParams.append('brands', brand))
    }
    if (currentPage > 1) newSearchParams.set('page', currentPage.toString())

    setSearchParams(newSearchParams)
  }, [sortBy, minPrice, maxPrice, selectedBrands, currentPage, setSearchParams])

  // ブランド一覧を取得
  const allBrands = [...new Set(products.map(product => product.brand))].sort()

  // ページネーション
  const totalPages = Math.ceil(filteredProducts.length / ITEMS_PER_PAGE)
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
  const paginatedProducts = filteredProducts.slice(startIndex, startIndex + ITEMS_PER_PAGE)

  const handleBrandFilter = (brand: string) => {
    setSelectedBrands(prev => {
      if (prev.includes(brand)) {
        return prev.filter(b => b !== brand)
      } else {
        return [...prev, brand]
      }
    })
    setCurrentPage(1)
  }

  const clearFilters = () => {
    setSortBy('newest')
    setMinPrice('')
    setMaxPrice('')
    setSelectedBrands([])
    setCurrentPage(1)
  }

  return (
    <div className="flex gap-8">
      {/* サイドバー (フィルター) */}
      <aside className="w-64 space-y-6">
        <div className="bg-white p-6 rounded-lg shadow">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">フィルター</h3>
            <button
              onClick={clearFilters}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              クリア
            </button>
          </div>

          {/* 価格フィルター */}
          <div className="mb-6">
            <h4 className="font-medium text-gray-700 mb-3">価格</h4>
            <div className="space-y-2">
              <input
                type="number"
                placeholder="最小価格"
                value={minPrice}
                onChange={(e) => setMinPrice(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
              />
              <input
                type="number"
                placeholder="最大価格"
                value={maxPrice}
                onChange={(e) => setMaxPrice(e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded text-sm"
              />
            </div>
          </div>

          {/* ブランドフィルター */}
          <div>
            <h4 className="font-medium text-gray-700 mb-3">ブランド</h4>
            <div className="space-y-2">
              {allBrands.map(brand => (
                <label key={brand} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={selectedBrands.includes(brand)}
                    onChange={() => handleBrandFilter(brand)}
                    className="mr-2"
                  />
                  <span className="text-sm text-gray-700">{brand}</span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* カテゴリナビゲーション */}
        <div className="bg-white p-6 rounded-lg shadow">
          <h3 className="font-semibold text-gray-900 mb-4">カテゴリ</h3>
          <nav className="space-y-2">
            {categories.map(cat => (
              <div key={cat.id}>
                <Link
                  to={`/categories/${cat.id}`}
                  className={`block py-2 px-3 rounded text-sm ${
                    category === cat.id && !subcategory
                      ? 'bg-blue-50 text-blue-600 font-medium'
                      : 'text-gray-700 hover:bg-gray-50'
                  }`}
                >
                  {cat.name}
                </Link>
                {cat.subcategories.map(sub => (
                  <Link
                    key={sub.id}
                    to={`/categories/${cat.id}/${sub.id}`}
                    className={`block py-1 px-6 text-sm ${
                      category === cat.id && subcategory === sub.id
                        ? 'text-blue-600 font-medium'
                        : 'text-gray-600 hover:text-gray-900'
                    }`}
                  >
                    {sub.name}
                  </Link>
                ))}
              </div>
            ))}
          </nav>
        </div>
      </aside>

      {/* メインコンテンツ */}
      <main className="flex-1">
        {/* ヘッダー */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {currentSubcategory?.name || currentCategory?.name || '全商品'}
          </h1>
          <div className="flex items-center justify-between">
            <p className="text-gray-600">
              {filteredProducts.length}件の商品が見つかりました
            </p>
            
            {/* ソート */}
            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              className="px-4 py-2 border border-gray-300 rounded"
            >
              <option value="newest">新着順</option>
              <option value="popular">人気順</option>
              <option value="price-low">価格の安い順</option>
              <option value="price-high">価格の高い順</option>
              <option value="rating">評価の高い順</option>
            </select>
          </div>
        </div>

        {/* 商品グリッド */}
        {paginatedProducts.length > 0 ? (
          <>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
              {paginatedProducts.map(product => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>

            {/* ページネーション */}
            {totalPages > 1 && (
              <div className="flex justify-center items-center space-x-2">
                <button
                  onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                  disabled={currentPage === 1}
                  className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
                >
                  前へ
                </button>
                
                {[...Array(totalPages)].map((_, i) => (
                  <button
                    key={i + 1}
                    onClick={() => setCurrentPage(i + 1)}
                    className={`px-3 py-1 border border-gray-300 rounded ${
                      currentPage === i + 1
                        ? 'bg-blue-600 text-white border-blue-600'
                        : 'hover:bg-gray-50'
                    }`}
                  >
                    {i + 1}
                  </button>
                ))}
                
                <button
                  onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                  disabled={currentPage === totalPages}
                  className="px-3 py-1 border border-gray-300 rounded disabled:opacity-50"
                >
                  次へ
                </button>
              </div>
            )}
          </>
        ) : (
          <div className="text-center py-12">
            <p className="text-gray-500">条件に合う商品が見つかりませんでした。</p>
          </div>
        )}
      </main>
    </div>
  )
}

export default ProductList
```

#### Step 4: 商品カードコンポーネント

**src/components/ProductCard.tsx**:

```tsx
import { Link } from 'react-router-dom'
import { Product } from '../data/products'
import { useCart } from '../contexts/CartContext'

interface ProductCardProps {
  product: Product
}

function ProductCard({ product }: ProductCardProps) {
  const { addToCart } = useCart()

  const handleAddToCart = (e: React.MouseEvent) => {
    e.preventDefault()
    addToCart({
      id: product.id,
      name: product.name,
      price: product.price,
      image: product.images[0]
    })
  }

  const discountPercentage = product.originalPrice
    ? Math.round((1 - product.price / product.originalPrice) * 100)
    : 0

  return (
    <Link to={`/products/${product.id}`} className="group">
      <div className="bg-white rounded-lg shadow-sm hover:shadow-md transition-shadow overflow-hidden">
        {/* 商品画像 */}
        <div className="aspect-square bg-gray-100 relative overflow-hidden">
          <img
            src={`/images/${product.images[0]}`}
            alt={product.name}
            className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
            onError={(e) => {
              e.currentTarget.src = '/images/placeholder.jpg'
            }}
          />
          
          {/* バッジ */}
          <div className="absolute top-2 left-2 space-y-1">
            {product.tags.map(tag => (
              <span
                key={tag}
                className="inline-block px-2 py-1 text-xs font-medium text-white bg-red-600 rounded"
              >
                {tag}
              </span>
            ))}
          </div>

          {/* 割引率 */}
          {discountPercentage > 0 && (
            <div className="absolute top-2 right-2">
              <span className="inline-block px-2 py-1 text-sm font-bold text-white bg-red-600 rounded">
                -{discountPercentage}%
              </span>
            </div>
          )}
        </div>

        {/* 商品情報 */}
        <div className="p-4">
          <div className="mb-2">
            <h3 className="font-semibold text-gray-900 line-clamp-2 group-hover:text-blue-600">
              {product.name}
            </h3>
            <p className="text-sm text-gray-500">{product.brand}</p>
          </div>

          {/* 評価 */}
          <div className="flex items-center gap-1 mb-2">
            <div className="flex text-yellow-400">
              {[...Array(5)].map((_, i) => (
                <span key={i} className="text-sm">
                  {i < Math.floor(product.rating) ? '★' : '☆'}
                </span>
              ))}
            </div>
            <span className="text-sm text-gray-500">
              ({product.reviewCount})
            </span>
          </div>

          {/* 価格 */}
          <div className="flex items-center gap-2 mb-3">
            <span className="text-lg font-bold text-gray-900">
              ¥{product.price.toLocaleString()}
            </span>
            {product.originalPrice && (
              <span className="text-sm text-gray-500 line-through">
                ¥{product.originalPrice.toLocaleString()}
              </span>
            )}
          </div>

          {/* 在庫状況 */}
          <div className="text-sm mb-3">
            {product.inStock > 0 ? (
              <span className="text-green-600">在庫あり ({product.inStock}個)</span>
            ) : (
              <span className="text-red-600">在庫切れ</span>
            )}
          </div>

          {/* カートに追加ボタン */}
          <button
            onClick={handleAddToCart}
            disabled={product.inStock === 0}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
          >
            {product.inStock > 0 ? 'カートに追加' : '在庫切れ'}
          </button>
        </div>
      </div>
    </Link>
  )
}

export default ProductCard
```

## 🎓 学習ポイント

### 1. 複雑なURLパラメータ設計
```tsx
// カテゴリ → /categories/electronics
// サブカテゴリ → /categories/electronics/smartphones
{
  path: "categories/:category",
  element: <ProductList />,
},
{
  path: "categories/:category/:subcategory",
  element: <ProductList />,
}
```

### 2. クエリパラメータでの状態管理
```tsx
const [searchParams, setSearchParams] = useSearchParams()

// 取得
const sortBy = searchParams.get('sort') || 'newest'
const brands = searchParams.getAll('brands') || []

// 設定
const newSearchParams = new URLSearchParams()
newSearchParams.set('sort', sortBy)
brands.forEach(brand => newSearchParams.append('brands', brand))
setSearchParams(newSearchParams)
```

### 3. ページネーション実装
```tsx
const totalPages = Math.ceil(filteredProducts.length / ITEMS_PER_PAGE)
const startIndex = (currentPage - 1) * ITEMS_PER_PAGE
const paginatedProducts = filteredProducts.slice(startIndex, startIndex + ITEMS_PER_PAGE)
```

### 4. SEO対応のURL設計
```tsx
// 良い例
/categories/electronics/smartphones?sort=price-low&minPrice=10000

// 悪い例
/products?cat=1&sub=2&s=1&min=10000
```

## 🧪 チャレンジ課題

### チャレンジ 1: 無限スクロール
ページネーションを無限スクロールに変更してください。

### チャレンジ 2: 商品比較機能
複数の商品を比較できる機能を追加してください。

### チャレンジ 3: 最近見た商品
ユーザーが最近見た商品を表示する機能を実装してください。

## 🔗 次のステップ

次は「[SPAのパフォーマンス最適化](../06-performance-optimization/)」に進みましょう。コード分割と遅延読み込みを学びます。