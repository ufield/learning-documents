# サーバーサイド対応 🔴

## 📖 この章で学ぶこと

- React RouterでのSSR/SSG実装
- React Server Components (RSC)との統合
- Remixフレームワークとの連携
- Nuxt.jsのSSR機能との比較
- SEO最適化とメタデータ管理

**想定読了時間**: 35分

---

## 🎯 サーバーサイドレンダリングの基本概念

### Nuxt.jsとの比較

まず、Nuxt.jsのSSR機能とReact Routerでの実装を比較してみましょう：

```javascript
// Nuxt.js (自動SSR)
export default {
  async asyncData({ $axios, params }) {
    const user = await $axios.$get(`/api/users/${params.id}`)
    return { user }
  },
  
  head() {
    return {
      title: `${this.user.name} - ユーザープロフィール`,
      meta: [
        { name: 'description', content: this.user.bio }
      ]
    }
  }
}

// React Router + Remix (Framework Mode)
export async function loader({ params }: LoaderFunctionArgs) {
  const user = await fetchUser(params.id!)
  return json({ user })
}

export function meta({ data }: MetaArgs) {
  return [
    { title: `${data.user.name} - ユーザープロフィール` },
    { name: "description", content: data.user.bio }
  ]
}

export default function UserPage() {
  const { user } = useLoaderData<typeof loader>()
  return <UserProfile user={user} />
}
```

## 🏗️ React Server Components (RSC)

### 1. 基本的なRSC実装

```tsx
// app/routes/products._index.tsx (Server Component)
import { Suspense } from 'react'
import { ProductGrid } from '~/components/ProductGrid.client'

// サーバー上で実行される
export default async function ProductsPage() {
  // データフェッチはサーバー上で実行
  const products = await db.products.findMany({
    include: { category: true, reviews: true }
  })
  
  const featuredProducts = products.filter(p => p.featured)
  const regularProducts = products.filter(p => !p.featured)
  
  return (
    <div>
      <h1>商品一覧</h1>
      
      {featuredProducts.length > 0 && (
        <section>
          <h2>注目商品</h2>
          <ProductGrid products={featuredProducts} />
        </section>
      )}
      
      <section>
        <h2>すべての商品</h2>
        <Suspense fallback={<ProductGridSkeleton />}>
          <ProductGrid products={regularProducts} />
        </Suspense>
      </section>
    </div>
  )
}

// components/ProductGrid.client.tsx (Client Component)
'use client'
import { useState } from 'react'

export function ProductGrid({ products }: { products: Product[] }) {
  const [sortBy, setSortBy] = useState('name')
  
  // クライアントサイドの対話機能
  const sortedProducts = [...products].sort((a, b) => {
    switch (sortBy) {
      case 'price':
        return a.price - b.price
      case 'rating':
        return b.averageRating - a.averageRating
      default:
        return a.name.localeCompare(b.name)
    }
  })
  
  return (
    <div>
      <select value={sortBy} onChange={e => setSortBy(e.target.value)}>
        <option value="name">名前順</option>
        <option value="price">価格順</option>
        <option value="rating">評価順</option>
      </select>
      
      <div className="grid">
        {sortedProducts.map(product => (
          <ProductCard key={product.id} product={product} />
        ))}
      </div>
    </div>
  )
}
```

### 2. ストリーミングSSR

```tsx
// app/routes/dashboard.tsx
import { Suspense } from 'react'
import { defer } from '@remix-run/node'
import { Await, useLoaderData } from '@remix-run/react'

export async function loader() {
  // 高速なデータは即座に取得
  const user = await getUserProfile()
  
  // 低速なデータは Promise として返す（ストリーミング）
  const analyticsPromise = getAnalyticsData()
  const reportsPromise = getReportsData()
  
  return defer({
    user,
    analytics: analyticsPromise,
    reports: reportsPromise
  })
}

export default function Dashboard() {
  const { user, analytics, reports } = useLoaderData<typeof loader>()
  
  return (
    <div>
      {/* 即座に表示される */}
      <header>
        <h1>Welcome, {user.name}</h1>
      </header>
      
      {/* ストリーミングで順次表示 */}
      <div className="dashboard-grid">
        <Suspense fallback={<AnalyticsSkeleton />}>
          <Await resolve={analytics}>
            {(analyticsData) => (
              <AnalyticsWidget data={analyticsData} />
            )}
          </Await>
        </Suspense>
        
        <Suspense fallback={<ReportsSkeleton />}>
          <Await resolve={reports}>
            {(reportsData) => (
              <ReportsWidget data={reportsData} />
            )}
          </Await>
        </Suspense>
      </div>
    </div>
  )
}
```

## 🔧 SSR実装パターン

### 1. Next.js App Routerとの統合

```tsx
// app/users/[id]/page.tsx (Next.js 13+ App Router)
import { Metadata } from 'next'

interface Props {
  params: { id: string }
  searchParams: { [key: string]: string | string[] | undefined }
}

// メタデータの生成
export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const user = await fetchUser(params.id)
  
  return {
    title: `${user.name} - プロフィール`,
    description: user.bio,
    openGraph: {
      title: user.name,
      description: user.bio,
      images: [user.avatar],
    },
  }
}

// Server Component
export default async function UserPage({ params }: Props) {
  const user = await fetchUser(params.id)
  
  return (
    <div>
      <UserProfile user={user} />
      <UserPosts userId={params.id} />
    </div>
  )
}

// components/UserPosts.tsx
async function UserPosts({ userId }: { userId: string }) {
  const posts = await fetchUserPosts(userId)
  
  return (
    <section>
      <h2>投稿</h2>
      {posts.map(post => (
        <PostCard key={post.id} post={post} />
      ))}
    </section>
  )
}
```

### 2. SvelteKitライクなファイルベースルーティング

```tsx
// routes/products/+layout.server.ts (SvelteKitスタイル)
export async function load({ params, url }) {
  const categories = await fetchCategories()
  
  return {
    categories
  }
}

// routes/products/+page.server.ts
export async function load({ url, parent }) {
  const { categories } = await parent()
  const searchParams = url.searchParams
  
  const filters = {
    category: searchParams.get('category'),
    minPrice: Number(searchParams.get('minPrice')) || undefined,
    maxPrice: Number(searchParams.get('maxPrice')) || undefined,
  }
  
  const products = await fetchProducts(filters)
  
  return {
    products,
    filters
  }
}

// React Router + Vite での同等実装
// vite.config.ts
export default defineConfig({
  plugins: [
    react(),
    // ファイルベースルーティングプラグイン
    {
      name: 'file-based-routing',
      configResolved() {
        // routes/ フォルダーから自動的にルートを生成
      }
    }
  ]
})
```

## 📊 SEO最適化とメタデータ管理

### 1. 動的メタデータ生成

```tsx
// utils/metadata.ts
interface PageMetadata {
  title: string
  description: string
  keywords?: string[]
  ogImage?: string
  canonicalUrl?: string
}

export function generateMetadata(
  data: any,
  template: (data: any) => PageMetadata
): PageMetadata {
  return template(data)
}

// メタデータテンプレート
export const metadataTemplates = {
  userProfile: (user: User): PageMetadata => ({
    title: `${user.name} - ユーザープロフィール`,
    description: user.bio || `${user.name}のプロフィールページです。`,
    keywords: ['ユーザー', 'プロフィール', user.name],
    ogImage: user.avatar,
    canonicalUrl: `/users/${user.id}`
  }),
  
  productDetail: (product: Product): PageMetadata => ({
    title: `${product.name} - ${product.category.name}`,
    description: product.description,
    keywords: [product.name, product.category.name, '商品'],
    ogImage: product.images[0],
    canonicalUrl: `/products/${product.id}`
  }),
  
  blogPost: (post: BlogPost): PageMetadata => ({
    title: post.title,
    description: post.excerpt,
    keywords: post.tags,
    ogImage: post.featuredImage,
    canonicalUrl: `/blog/${post.slug}`
  })
}

// components/SEOHead.tsx
export function SEOHead({ metadata }: { metadata: PageMetadata }) {
  return (
    <Helmet>
      <title>{metadata.title}</title>
      <meta name="description" content={metadata.description} />
      
      {metadata.keywords && (
        <meta name="keywords" content={metadata.keywords.join(', ')} />
      )}
      
      {metadata.canonicalUrl && (
        <link rel="canonical" href={`https://example.com${metadata.canonicalUrl}`} />
      )}
      
      {/* Open Graph */}
      <meta property="og:title" content={metadata.title} />
      <meta property="og:description" content={metadata.description} />
      {metadata.ogImage && (
        <meta property="og:image" content={metadata.ogImage} />
      )}
      
      {/* Twitter Card */}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={metadata.title} />
      <meta name="twitter:description" content={metadata.description} />
      {metadata.ogImage && (
        <meta name="twitter:image" content={metadata.ogImage} />
      )}
    </Helmet>
  )
}
```

### 2. 構造化データの生成

```tsx
// utils/structuredData.ts
export function generateStructuredData(type: string, data: any) {
  const generators = {
    person: (user: User) => ({
      "@context": "https://schema.org",
      "@type": "Person",
      "name": user.name,
      "email": user.email,
      "image": user.avatar,
      "jobTitle": user.jobTitle,
      "worksFor": {
        "@type": "Organization",
        "name": user.company
      }
    }),
    
    product: (product: Product) => ({
      "@context": "https://schema.org",
      "@type": "Product",
      "name": product.name,
      "description": product.description,
      "image": product.images,
      "offers": {
        "@type": "Offer",
        "price": product.price,
        "priceCurrency": "JPY",
        "availability": product.inStock ? "InStock" : "OutOfStock"
      },
      "aggregateRating": {
        "@type": "AggregateRating",
        "ratingValue": product.averageRating,
        "reviewCount": product.reviewCount
      }
    }),
    
    article: (post: BlogPost) => ({
      "@context": "https://schema.org",
      "@type": "Article",
      "headline": post.title,
      "description": post.excerpt,
      "image": post.featuredImage,
      "author": {
        "@type": "Person",
        "name": post.author.name
      },
      "publisher": {
        "@type": "Organization",
        "name": "My Blog"
      },
      "datePublished": post.publishedAt,
      "dateModified": post.updatedAt
    })
  }
  
  return generators[type as keyof typeof generators]?.(data)
}

// components/StructuredData.tsx
export function StructuredData({ type, data }: { type: string; data: any }) {
  const structuredData = generateStructuredData(type, data)
  
  if (!structuredData) return null
  
  return (
    <script
      type="application/ld+json"
      dangerouslySetInnerHTML={{
        __html: JSON.stringify(structuredData)
      }}
    />
  )
}
```

## 🚀 パフォーマンス最適化

### 1. 段階的水和 (Progressive Hydration)

```tsx
// components/ProgressiveHydration.tsx
export function ProgressiveHydration({ 
  children, 
  fallback,
  condition = 'visible' 
}: {
  children: React.ReactNode
  fallback?: React.ReactNode
  condition?: 'visible' | 'idle' | 'immediate'
}) {
  const [shouldHydrate, setShouldHydrate] = useState(
    condition === 'immediate'
  )
  
  useEffect(() => {
    if (condition === 'idle') {
      requestIdleCallback(() => setShouldHydrate(true))
    } else if (condition === 'visible') {
      const observer = new IntersectionObserver(
        (entries) => {
          if (entries[0].isIntersecting) {
            setShouldHydrate(true)
            observer.disconnect()
          }
        },
        { threshold: 0.1 }
      )
      
      // 実装は簡略化
    }
  }, [condition])
  
  if (!shouldHydrate) {
    return <>{fallback}</>
  }
  
  return <>{children}</>
}

// 使用例
function ProductPage() {
  return (
    <div>
      {/* 即座に表示される重要なコンテンツ */}
      <ProductHeader product={product} />
      
      {/* 遅延水和される対話的コンポーネント */}
      <ProgressiveHydration 
        condition="visible"
        fallback={<ReviewsSkeleton />}
      >
        <InteractiveReviews productId={product.id} />
      </ProgressiveHydration>
      
      {/* アイドル時に水和される */}
      <ProgressiveHydration 
        condition="idle"
        fallback={<RecommendationsSkeleton />}
      >
        <ProductRecommendations />
      </ProgressiveHydration>
    </div>
  )
}
```

### 2. 部分水和 (Partial Hydration)

```tsx
// utils/islandHydration.tsx
export function Island({ 
  component: Component, 
  props = {},
  containerId 
}: {
  component: React.ComponentType<any>
  props?: any
  containerId: string
}) {
  useEffect(() => {
    // 特定のDOMノードのみを水和
    const container = document.getElementById(containerId)
    if (container && !container.hasAttribute('data-hydrated')) {
      const root = createRoot(container)
      root.render(<Component {...props} />)
      container.setAttribute('data-hydrated', 'true')
    }
  }, [Component, props, containerId])
  
  // サーバーサイドでは何も返さない
  return null
}

// 使用例 - 静的コンテンツ中の対話的要素
export default function BlogPost({ post }: { post: BlogPost }) {
  return (
    <article>
      <h1>{post.title}</h1>
      <div dangerouslySetInnerHTML={{ __html: post.content }} />
      
      {/* 対話的なコメントセクションのみ水和 */}
      <div id="comments-section">
        <CommentsSkeleton />
      </div>
      <Island 
        component={CommentsSection} 
        props={{ postId: post.id }}
        containerId="comments-section"
      />
    </article>
  )
}
```

## 🔄 Nuxt.js → React Router SSR移行チートシート

| 機能 | Nuxt.js | React Router (Remix) |
|------|---------|---------------------|
| データフェッチ | `asyncData` | `loader` |
| メタデータ | `head()` | `meta()` |
| サーバーミドルウェア | `server/middleware` | Remix action |
| 静的生成 | `generate` | Remix static export |
| レイアウト | `layouts/` | ネストされたルート |
| プラグイン | `plugins/` | Root loader |
| エラーページ | `error.vue` | `ErrorBoundary` |

## 🎓 まとめ

React Routerのサーバーサイド対応は、Nuxt.jsと同等以上の機能を提供しながら、より柔軟なアーキテクチャ選択を可能にします：

1. **React Server Components**: 最新のSSR実装パターン
2. **ストリーミングSSR**: 段階的なページ読み込み
3. **SEO最適化**: 動的メタデータと構造化データ
4. **パフォーマンス**: 段階的・部分水和による最適化

最後に、高度なパターンと実装例について学びます。

---

**🔗 次章**: [高度なパターンと実装例](./12-advanced-patterns.md)