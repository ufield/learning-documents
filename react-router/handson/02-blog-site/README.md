# ブログサイトを作ろう

**所要時間: 1時間**  
**レベル: 🟢 初級**

動的ルーティングとパラメータを使って、記事一覧と詳細ページのあるブログサイトを作成します。

## 🎯 学習目標

- 動的ルーティング（パスパラメータ）の使い方を理解する
- useParams フックでパラメータを取得する
- useSearchParams でクエリパラメータを扱う
- ローダー関数でデータを事前取得する
- エラーハンドリングの基本を覚える

## 🏗️ 作るもの

シンプルなブログサイト：
- ブログ記事一覧ページ
- 記事詳細ページ（動的ルート）
- カテゴリーフィルター機能
- 記事検索機能

## 📋 前提条件

- 「はじめてのReact Router」を完了していること
- React と JavaScript/TypeScript の基本的な知識

## 🚀 始め方

### ステップ 1: プロジェクトの準備

```bash
cd starter
npm install
npm run dev
```

### ステップ 2: 段階的な実装

1. **Step 1**: 基本的なルート設定とモックデータ
2. **Step 2**: 記事一覧ページの実装
3. **Step 3**: 動的ルートで記事詳細ページ
4. **Step 4**: クエリパラメータでフィルター機能
5. **Step 5**: エラーハンドリングと404ページ

### ステップ 3: 実装開始

#### Step 1: ルート設定とモックデータ

**src/data/blogPosts.ts** を作成：

```tsx
export interface BlogPost {
  id: number
  title: string
  content: string
  excerpt: string
  category: string
  publishedAt: string
  author: string
  slug: string
}

export const blogPosts: BlogPost[] = [
  {
    id: 1,
    title: "React Router v6の新機能について",
    content: "React Router v6では多くの改善が行われました。主要な変更点は...",
    excerpt: "React Router v6の主要な新機能と変更点を詳しく解説します。",
    category: "React",
    publishedAt: "2024-01-15",
    author: "山田太郎",
    slug: "react-router-v6-new-features"
  },
  {
    id: 2,
    title: "TypeScriptとReactの最適な組み合わせ",
    content: "TypeScriptをReactプロジェクトで効果的に使用する方法を説明します...",
    excerpt: "TypeScriptでReact開発をより安全で効率的に行う方法を紹介します。",
    category: "TypeScript",
    publishedAt: "2024-01-10",
    author: "佐藤花子",
    slug: "typescript-react-best-practices"
  },
  {
    id: 3,
    title: "モダンなCSSアーキテクチャの考え方",
    content: "CSS-in-JSやCSS Modulesなど、現代的なスタイリング手法について...",
    excerpt: "現代のWebフロントエンドで使われるCSSアーキテクチャパターンを解説。",
    category: "CSS",
    publishedAt: "2024-01-05",
    author: "田中次郎",
    slug: "modern-css-architecture"
  },
  {
    id: 4,
    title: "パフォーマンス最適化のベストプラクティス",
    content: "Reactアプリケーションのパフォーマンスを向上させるテクニック...",
    excerpt: "Reactアプリのパフォーマンスを向上させる具体的な手法をまとめました。",
    category: "Performance",
    publishedAt: "2023-12-28",
    author: "山田太郎",
    slug: "react-performance-optimization"
  },
  {
    id: 5,
    title: "ユーザビリティを考慮したフォーム設計",
    content: "使いやすいフォームを作るためのUX/UI設計のポイントを説明...",
    excerpt: "ユーザーにとって使いやすいフォームの設計原則とテクニックを紹介。",
    category: "UX/UI",
    publishedAt: "2023-12-20",
    author: "佐藤花子",
    slug: "user-friendly-form-design"
  }
]

export const getPostBySlug = (slug: string): BlogPost | undefined => {
  return blogPosts.find(post => post.slug === slug)
}

export const getPostsByCategory = (category: string): BlogPost[] => {
  return blogPosts.filter(post => post.category === category)
}

export const searchPosts = (query: string): BlogPost[] => {
  return blogPosts.filter(post => 
    post.title.toLowerCase().includes(query.toLowerCase()) ||
    post.excerpt.toLowerCase().includes(query.toLowerCase())
  )
}

export const getUniqueCategories = (): string[] => {
  return [...new Set(blogPosts.map(post => post.category))]
}
```

**src/main.tsx** を更新：

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'

import Layout from './components/Layout'
import Home from './pages/Home'
import BlogList from './pages/BlogList'
import BlogPost from './pages/BlogPost'
import NotFound from './pages/NotFound'

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
        path: "blog",
        element: <BlogList />,
      },
      {
        path: "blog/:slug",
        element: <BlogPost />,
        errorElement: <NotFound />
      },
    ],
    errorElement: <NotFound />
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
)
```

#### Step 2: レイアウトコンポーネント

**src/components/Layout.tsx**:

```tsx
import { Link, Outlet } from 'react-router-dom'

function Layout() {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <nav className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="text-2xl font-bold text-blue-600">
              Tech Blog
            </Link>
            <div className="space-x-6">
              <Link 
                to="/" 
                className="text-gray-600 hover:text-blue-600 transition-colors"
              >
                ホーム
              </Link>
              <Link 
                to="/blog" 
                className="text-gray-600 hover:text-blue-600 transition-colors"
              >
                ブログ
              </Link>
            </div>
          </div>
        </nav>
      </header>
      
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Outlet />
      </main>
      
      <footer className="bg-gray-800 text-white py-8 mt-16">
        <div className="max-w-6xl mx-auto px-4 text-center">
          <p>&copy; 2024 Tech Blog. All rights reserved.</p>
        </div>
      </footer>
    </div>
  )
}

export default Layout
```

#### Step 3: ページコンポーネント

**src/pages/BlogList.tsx**:

```tsx
import { Link, useSearchParams } from 'react-router-dom'
import { blogPosts, getPostsByCategory, searchPosts, getUniqueCategories } from '../data/blogPosts'

function BlogList() {
  const [searchParams, setSearchParams] = useSearchParams()
  
  const category = searchParams.get('category')
  const query = searchParams.get('q')
  
  let filteredPosts = blogPosts
  
  if (category) {
    filteredPosts = getPostsByCategory(category)
  }
  
  if (query) {
    filteredPosts = searchPosts(query)
  }
  
  const categories = getUniqueCategories()

  const handleCategoryFilter = (selectedCategory: string) => {
    if (selectedCategory === 'all') {
      searchParams.delete('category')
    } else {
      searchParams.set('category', selectedCategory)
    }
    searchParams.delete('q') // 検索クエリをクリア
    setSearchParams(searchParams)
  }

  const handleSearch = (searchQuery: string) => {
    if (searchQuery) {
      searchParams.set('q', searchQuery)
    } else {
      searchParams.delete('q')
    }
    searchParams.delete('category') // カテゴリフィルターをクリア
    setSearchParams(searchParams)
  }

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">ブログ記事</h1>
        
        {/* 検索フォーム */}
        <div className="mb-6">
          <input
            type="text"
            placeholder="記事を検索..."
            defaultValue={query || ''}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full max-w-md px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
        
        {/* カテゴリフィルター */}
        <div className="flex flex-wrap gap-2 mb-6">
          <button
            onClick={() => handleCategoryFilter('all')}
            className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
              !category ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
            }`}
          >
            すべて
          </button>
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => handleCategoryFilter(cat)}
              className={`px-4 py-2 rounded-full text-sm font-medium transition-colors ${
                category === cat ? 'bg-blue-600 text-white' : 'bg-gray-200 text-gray-700 hover:bg-gray-300'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>
        
        {/* 結果情報 */}
        <div className="text-gray-600">
          {query && <p>「{query}」の検索結果: {filteredPosts.length}件</p>}
          {category && <p>カテゴリ「{category}」: {filteredPosts.length}件</p>}
          {!query && !category && <p>全記事: {filteredPosts.length}件</p>}
        </div>
      </div>
      
      {/* 記事一覧 */}
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {filteredPosts.map((post) => (
          <article key={post.id} className="bg-white rounded-lg shadow-sm overflow-hidden hover:shadow-md transition-shadow">
            <div className="p-6">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-blue-600 bg-blue-100 px-2 py-1 rounded">
                  {post.category}
                </span>
                <time className="text-xs text-gray-500">
                  {new Date(post.publishedAt).toLocaleDateString('ja-JP')}
                </time>
              </div>
              
              <h2 className="text-xl font-bold text-gray-900 mb-2">
                <Link 
                  to={`/blog/${post.slug}`}
                  className="hover:text-blue-600 transition-colors"
                >
                  {post.title}
                </Link>
              </h2>
              
              <p className="text-gray-600 mb-4 line-clamp-3">
                {post.excerpt}
              </p>
              
              <div className="flex items-center justify-between">
                <span className="text-sm text-gray-500">
                  {post.author}
                </span>
                <Link 
                  to={`/blog/${post.slug}`}
                  className="text-blue-600 hover:text-blue-800 text-sm font-medium"
                >
                  続きを読む →
                </Link>
              </div>
            </div>
          </article>
        ))}
      </div>
      
      {filteredPosts.length === 0 && (
        <div className="text-center py-12">
          <p className="text-gray-500 text-lg">記事が見つかりませんでした。</p>
        </div>
      )}
    </div>
  )
}

export default BlogList
```

**src/pages/BlogPost.tsx**:

```tsx
import { Link, useParams, useNavigate } from 'react-router-dom'
import { getPostBySlug } from '../data/blogPosts'

function BlogPost() {
  const { slug } = useParams<{ slug: string }>()
  const navigate = useNavigate()
  
  const post = slug ? getPostBySlug(slug) : null
  
  if (!post) {
    return (
      <div className="text-center py-12">
        <h1 className="text-2xl font-bold text-gray-900 mb-4">記事が見つかりません</h1>
        <p className="text-gray-600 mb-6">指定された記事は存在しないか、削除された可能性があります。</p>
        <Link 
          to="/blog"
          className="inline-block bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
        >
          ブログ一覧に戻る
        </Link>
      </div>
    )
  }
  
  return (
    <article className="max-w-4xl mx-auto">
      {/* パンくずナビ */}
      <nav className="mb-6">
        <ol className="flex items-center space-x-2 text-sm text-gray-600">
          <li>
            <Link to="/" className="hover:text-blue-600">ホーム</Link>
          </li>
          <li>/</li>
          <li>
            <Link to="/blog" className="hover:text-blue-600">ブログ</Link>
          </li>
          <li>/</li>
          <li className="text-gray-900">{post.title}</li>
        </ol>
      </nav>
      
      {/* 記事ヘッダー */}
      <header className="mb-8">
        <div className="flex items-center gap-4 mb-4">
          <span className="text-sm font-medium text-blue-600 bg-blue-100 px-3 py-1 rounded">
            {post.category}
          </span>
          <time className="text-sm text-gray-500">
            {new Date(post.publishedAt).toLocaleDateString('ja-JP')}
          </time>
        </div>
        
        <h1 className="text-3xl md:text-4xl font-bold text-gray-900 mb-4">
          {post.title}
        </h1>
        
        <p className="text-lg text-gray-600 mb-4">
          {post.excerpt}
        </p>
        
        <div className="flex items-center justify-between">
          <span className="text-gray-600">by {post.author}</span>
          <button
            onClick={() => navigate(-1)}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            ← 戻る
          </button>
        </div>
      </header>
      
      {/* 記事本文 */}
      <div className="prose prose-lg max-w-none mb-12">
        <div className="bg-white rounded-lg p-8 shadow-sm">
          {post.content.split('\n').map((paragraph, index) => (
            <p key={index} className="mb-4 text-gray-800 leading-relaxed">
              {paragraph}
            </p>
          ))}
        </div>
      </div>
      
      {/* 関連記事へのリンク */}
      <footer className="border-t pt-8">
        <div className="flex flex-col md:flex-row justify-between items-center gap-4">
          <Link 
            to={`/blog?category=${post.category}`}
            className="text-blue-600 hover:text-blue-800 text-sm"
          >
            {post.category}カテゴリの他の記事を見る →
          </Link>
          <Link 
            to="/blog"
            className="bg-blue-600 text-white px-6 py-3 rounded-lg hover:bg-blue-700 transition-colors"
          >
            ブログ一覧に戻る
          </Link>
        </div>
      </footer>
    </article>
  )
}

export default BlogPost
```

## 🎓 学習ポイント

### 1. 動的ルーティング（パスパラメータ）
```tsx
// ルート定義
{ path: "blog/:slug", element: <BlogPost /> }

// パラメータ取得
const { slug } = useParams<{ slug: string }>()
```

### 2. クエリパラメータの操作
```tsx
const [searchParams, setSearchParams] = useSearchParams()

// 取得
const category = searchParams.get('category')

// 設定
searchParams.set('category', 'React')
setSearchParams(searchParams)
```

### 3. エラーハンドリング
```tsx
if (!post) {
  return <NotFoundComponent />
}
```

## 🧪 チャレンジ課題

### チャレンジ 1: ページネーション
記事一覧にページネーション機能を追加してください。

### チャレンジ 2: 記事のタグ機能
各記事にタグを追加し、タグでの絞り込み機能を実装してください。

### チャレンジ 3: お気に入り機能
localStorage を使って、お気に入り記事の保存機能を追加してください。

## 🔗 次のステップ

次は「[ネストされたルートで管理画面](../03-admin-dashboard/)」に進みましょう。レイアウトの共有とネストルートを学びます。