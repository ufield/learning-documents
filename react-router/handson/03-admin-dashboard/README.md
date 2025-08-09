# ネストされたルートで管理画面

**所要時間: 1.5時間**  
**レベル: 🟡 中級**

ネストされたルートとOutletを使って、共通レイアウトを持つ管理画面を作成します。

## 🎯 学習目標

- ネストされたルートの概念と実装方法を理解する
- Outlet コンポーネントの役割と使い方を覚える
- 階層的なナビゲーション構造の設計を学ぶ
- 共通レイアウトパターンの実装方法を覚える
- ルートレベルでのデータ共有方法を理解する

## 🏗️ 作るもの

管理画面ダッシュボード：
- メインダッシュボード
- ユーザー管理セクション
  - ユーザー一覧
  - ユーザー詳細
  - ユーザー作成/編集
- 商品管理セクション
  - 商品一覧
  - 商品詳細
  - 商品作成/編集
- 設定セクション
  - 一般設定
  - セキュリティ設定

## 📋 前提条件

- 「ブログサイトを作ろう」を完了していること
- React の状態管理の基本的な知識

## 🚀 始め方

### ステップ 1: プロジェクトの準備

```bash
cd starter
npm install
npm run dev
```

### ステップ 2: 段階的な実装

1. **Step 1**: 基本的なネストルート構造の設定
2. **Step 2**: サイドバー付きの管理画面レイアウト
3. **Step 3**: ユーザー管理セクションの実装
4. **Step 4**: 商品管理セクションの実装
5. **Step 5**: ブレッドクラムとアクティブナビゲーション

### ステップ 3: 実装開始

#### Step 1: ネストルート構造の設定

**src/main.tsx**:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'

// 公開画面のコンポーネント
import Layout from './components/Layout'
import Home from './pages/Home'
import Login from './pages/Login'

// 管理画面のコンポーネント
import AdminLayout from './components/AdminLayout'
import Dashboard from './pages/admin/Dashboard'
import UserList from './pages/admin/users/UserList'
import UserDetail from './pages/admin/users/UserDetail'
import UserForm from './pages/admin/users/UserForm'
import ProductList from './pages/admin/products/ProductList'
import ProductDetail from './pages/admin/products/ProductDetail'
import ProductForm from './pages/admin/products/ProductForm'
import GeneralSettings from './pages/admin/settings/GeneralSettings'
import SecuritySettings from './pages/admin/settings/SecuritySettings'

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
        path: "login",
        element: <Login />,
      },
    ],
  },
  {
    path: "/admin",
    element: <AdminLayout />,
    children: [
      {
        index: true,
        element: <Dashboard />,
      },
      {
        path: "users",
        children: [
          {
            index: true,
            element: <UserList />,
          },
          {
            path: "new",
            element: <UserForm />,
          },
          {
            path: ":id",
            element: <UserDetail />,
          },
          {
            path: ":id/edit",
            element: <UserForm />,
          },
        ],
      },
      {
        path: "products",
        children: [
          {
            index: true,
            element: <ProductList />,
          },
          {
            path: "new",
            element: <ProductForm />,
          },
          {
            path: ":id",
            element: <ProductDetail />,
          },
          {
            path: ":id/edit",
            element: <ProductForm />,
          },
        ],
      },
      {
        path: "settings",
        children: [
          {
            index: true,
            element: <GeneralSettings />,
          },
          {
            path: "security",
            element: <SecuritySettings />,
          },
        ],
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

#### Step 2: 管理画面レイアウト

**src/components/AdminLayout.tsx**:

```tsx
import { Link, Outlet, useLocation } from 'react-router-dom'
import { useState } from 'react'

// アイコンコンポーネント（簡単な実装）
const Icon = ({ name }: { name: string }) => (
  <span className="w-5 h-5 inline-block">{name}</span>
)

function AdminLayout() {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(true)

  const navigation = [
    { name: 'ダッシュボード', href: '/admin', icon: '📊', exact: true },
    { 
      name: 'ユーザー管理', 
      href: '/admin/users', 
      icon: '👥',
      children: [
        { name: 'ユーザー一覧', href: '/admin/users' },
        { name: '新規ユーザー', href: '/admin/users/new' },
      ]
    },
    { 
      name: '商品管理', 
      href: '/admin/products', 
      icon: '📦',
      children: [
        { name: '商品一覧', href: '/admin/products' },
        { name: '新規商品', href: '/admin/products/new' },
      ]
    },
    { 
      name: '設定', 
      href: '/admin/settings', 
      icon: '⚙️',
      children: [
        { name: '一般設定', href: '/admin/settings' },
        { name: 'セキュリティ', href: '/admin/settings/security' },
      ]
    },
  ]

  const isActive = (href: string, exact = false) => {
    if (exact) {
      return location.pathname === href
    }
    return location.pathname.startsWith(href)
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* サイドバー */}
      <div className={`bg-gray-900 text-white transition-all duration-300 ${
        sidebarOpen ? 'w-64' : 'w-20'
      }`}>
        <div className="p-4">
          <div className="flex items-center justify-between">
            <Link to="/admin" className="text-xl font-bold">
              {sidebarOpen ? 'Admin Panel' : 'AP'}
            </Link>
            <button
              onClick={() => setSidebarOpen(!sidebarOpen)}
              className="p-1 rounded hover:bg-gray-700"
            >
              {sidebarOpen ? '◀' : '▶'}
            </button>
          </div>
        </div>

        <nav className="mt-8">
          {navigation.map((item) => (
            <div key={item.name}>
              <Link
                to={item.href}
                className={`flex items-center px-4 py-3 text-sm hover:bg-gray-700 transition-colors ${
                  isActive(item.href, item.exact) ? 'bg-gray-700 border-r-2 border-blue-500' : ''
                }`}
              >
                <Icon name={item.icon} />
                {sidebarOpen && <span className="ml-3">{item.name}</span>}
              </Link>
              
              {/* サブナビゲーション */}
              {sidebarOpen && item.children && isActive(item.href) && (
                <div className="bg-gray-800">
                  {item.children.map((child) => (
                    <Link
                      key={child.href}
                      to={child.href}
                      className={`block px-12 py-2 text-sm text-gray-300 hover:text-white hover:bg-gray-700 transition-colors ${
                        location.pathname === child.href ? 'text-white bg-gray-700' : ''
                      }`}
                    >
                      {child.name}
                    </Link>
                  ))}
                </div>
              )}
            </div>
          ))}
        </nav>

        {/* ユーザー情報 */}
        <div className="absolute bottom-4 left-0 right-0 px-4">
          <div className="flex items-center">
            <div className="w-8 h-8 bg-blue-500 rounded-full flex items-center justify-center">
              👤
            </div>
            {sidebarOpen && (
              <div className="ml-3">
                <p className="text-sm font-medium">管理者</p>
                <Link 
                  to="/login" 
                  className="text-xs text-gray-400 hover:text-white"
                >
                  ログアウト
                </Link>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* メインコンテンツ */}
      <div className="flex-1 flex flex-col">
        {/* ヘッダー */}
        <header className="bg-white shadow-sm border-b">
          <div className="px-6 py-4">
            <div className="flex items-center justify-between">
              {/* ブレッドクラム */}
              <Breadcrumb />
              
              {/* ヘッダーアクション */}
              <div className="flex items-center space-x-4">
                <button className="p-2 text-gray-500 hover:text-gray-700">
                  🔔
                </button>
                <Link 
                  to="/" 
                  className="text-blue-600 hover:text-blue-800 text-sm"
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  サイトを確認
                </Link>
              </div>
            </div>
          </div>
        </header>

        {/* メインコンテンツエリア */}
        <main className="flex-1 overflow-y-auto p-6">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

// ブレッドクラムコンポーネント
function Breadcrumb() {
  const location = useLocation()
  
  const getBreadcrumbs = (pathname: string) => {
    const pathSegments = pathname.split('/').filter(Boolean)
    const breadcrumbs = []
    
    let currentPath = ''
    for (const segment of pathSegments) {
      currentPath += `/${segment}`
      
      let name = segment
      if (segment === 'admin') name = '管理画面'
      else if (segment === 'users') name = 'ユーザー管理'
      else if (segment === 'products') name = '商品管理'
      else if (segment === 'settings') name = '設定'
      else if (segment === 'new') name = '新規作成'
      else if (segment === 'security') name = 'セキュリティ設定'
      else if (/^\d+$/.test(segment)) name = `詳細 (#${segment})`
      
      breadcrumbs.push({ name, path: currentPath })
    }
    
    return breadcrumbs
  }
  
  const breadcrumbs = getBreadcrumbs(location.pathname)
  
  return (
    <nav className="flex">
      <ol className="flex items-center space-x-2 text-sm text-gray-600">
        {breadcrumbs.map((crumb, index) => (
          <li key={crumb.path} className="flex items-center">
            {index > 0 && <span className="mx-2">/</span>}
            {index === breadcrumbs.length - 1 ? (
              <span className="text-gray-900 font-medium">{crumb.name}</span>
            ) : (
              <Link 
                to={crumb.path} 
                className="hover:text-blue-600 transition-colors"
              >
                {crumb.name}
              </Link>
            )}
          </li>
        ))}
      </ol>
    </nav>
  )
}

export default AdminLayout
```

#### Step 3: ダッシュボードページ

**src/pages/admin/Dashboard.tsx**:

```tsx
import { Link } from 'react-router-dom'

function Dashboard() {
  const stats = [
    { name: '総ユーザー数', value: '1,234', change: '+12%', link: '/admin/users' },
    { name: '商品数', value: '567', change: '+5%', link: '/admin/products' },
    { name: '今月の売上', value: '¥1,234,567', change: '+18%', link: '#' },
    { name: 'アクティブセッション', value: '89', change: '-2%', link: '#' },
  ]

  const recentActivities = [
    { id: 1, action: 'ユーザー「田中太郎」が登録', time: '2分前' },
    { id: 2, action: '商品「MacBook Pro」が更新', time: '15分前' },
    { id: 3, action: '設定が変更されました', time: '1時間前' },
    { id: 4, action: '新規注文 #1234 が作成', time: '2時間前' },
  ]

  return (
    <div>
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900">ダッシュボード</h1>
        <p className="text-gray-600">システムの概要と最新の活動状況</p>
      </div>

      {/* 統計カード */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {stats.map((stat) => (
          <div key={stat.name} className="bg-white rounded-lg shadow p-6">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
              </div>
              <div className="flex flex-col items-end">
                <span className={`text-sm font-medium ${
                  stat.change.startsWith('+') ? 'text-green-600' : 'text-red-600'
                }`}>
                  {stat.change}
                </span>
                {stat.link !== '#' && (
                  <Link 
                    to={stat.link}
                    className="text-xs text-blue-600 hover:text-blue-800 mt-1"
                  >
                    詳細を見る →
                  </Link>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 最近のアクティビティ */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">最近のアクティビティ</h3>
          </div>
          <div className="p-6">
            <div className="space-y-4">
              {recentActivities.map((activity) => (
                <div key={activity.id} className="flex items-center justify-between">
                  <p className="text-sm text-gray-800">{activity.action}</p>
                  <span className="text-xs text-gray-500">{activity.time}</span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* クイックアクション */}
        <div className="bg-white rounded-lg shadow">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-semibold text-gray-900">クイックアクション</h3>
          </div>
          <div className="p-6">
            <div className="space-y-3">
              <Link
                to="/admin/users/new"
                className="block w-full text-center bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition-colors"
              >
                新規ユーザー作成
              </Link>
              <Link
                to="/admin/products/new"
                className="block w-full text-center bg-green-600 text-white py-2 px-4 rounded hover:bg-green-700 transition-colors"
              >
                新規商品登録
              </Link>
              <Link
                to="/admin/settings"
                className="block w-full text-center bg-gray-600 text-white py-2 px-4 rounded hover:bg-gray-700 transition-colors"
              >
                システム設定
              </Link>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Dashboard
```

#### Step 4: ユーザー管理セクション

**src/pages/admin/users/UserList.tsx**:

```tsx
import { Link } from 'react-router-dom'

interface User {
  id: number
  name: string
  email: string
  role: string
  status: 'active' | 'inactive'
  createdAt: string
}

const mockUsers: User[] = [
  { id: 1, name: '田中太郎', email: 'tanaka@example.com', role: 'admin', status: 'active', createdAt: '2024-01-15' },
  { id: 2, name: '佐藤花子', email: 'sato@example.com', role: 'user', status: 'active', createdAt: '2024-01-10' },
  { id: 3, name: '山田次郎', email: 'yamada@example.com', role: 'user', status: 'inactive', createdAt: '2023-12-20' },
]

function UserList() {
  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">ユーザー管理</h1>
          <p className="text-gray-600">システムのユーザー一覧と管理</p>
        </div>
        <Link
          to="/admin/users/new"
          className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
        >
          新規ユーザー追加
        </Link>
      </div>

      {/* フィルター */}
      <div className="bg-white rounded-lg shadow mb-6 p-4">
        <div className="flex items-center gap-4">
          <input
            type="text"
            placeholder="ユーザーを検索..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
          <select className="px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500">
            <option value="">すべてのロール</option>
            <option value="admin">管理者</option>
            <option value="user">一般ユーザー</option>
          </select>
          <select className="px-4 py-2 border border-gray-300 rounded focus:ring-2 focus:ring-blue-500">
            <option value="">すべてのステータス</option>
            <option value="active">アクティブ</option>
            <option value="inactive">非アクティブ</option>
          </select>
        </div>
      </div>

      {/* ユーザー一覧テーブル */}
      <div className="bg-white rounded-lg shadow">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-gray-50 border-b">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ユーザー
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ロール
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  ステータス
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                  登録日
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
                  アクション
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-200">
              {mockUsers.map((user) => (
                <tr key={user.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div>
                      <div className="text-sm font-medium text-gray-900">{user.name}</div>
                      <div className="text-sm text-gray-500">{user.email}</div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.role === 'admin' 
                        ? 'bg-purple-100 text-purple-800' 
                        : 'bg-green-100 text-green-800'
                    }`}>
                      {user.role === 'admin' ? '管理者' : '一般ユーザー'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={`inline-flex px-2 py-1 text-xs font-semibold rounded-full ${
                      user.status === 'active' 
                        ? 'bg-green-100 text-green-800' 
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {user.status === 'active' ? 'アクティブ' : '非アクティブ'}
                    </span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                    {new Date(user.createdAt).toLocaleDateString('ja-JP')}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                    <div className="flex items-center justify-end space-x-2">
                      <Link
                        to={`/admin/users/${user.id}`}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        詳細
                      </Link>
                      <Link
                        to={`/admin/users/${user.id}/edit`}
                        className="text-green-600 hover:text-green-900"
                      >
                        編集
                      </Link>
                      <button className="text-red-600 hover:text-red-900">
                        削除
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}

export default UserList
```

## 🎓 学習ポイント

### 1. ネストされたルート構造
```tsx
{
  path: "/admin",
  element: <AdminLayout />,
  children: [
    {
      path: "users",
      children: [
        { index: true, element: <UserList /> },
        { path: ":id", element: <UserDetail /> },
      ]
    }
  ]
}
```

### 2. Outlet コンポーネント
```tsx
// 親コンポーネント
function AdminLayout() {
  return (
    <div>
      <Sidebar />
      <main>
        <Outlet /> {/* 子ルートがここに表示される */}
      </main>
    </div>
  )
}
```

### 3. 階層的なナビゲーション
```tsx
const isActive = (href: string) => {
  return location.pathname.startsWith(href)
}
```

## 🧪 チャレンジ課題

### チャレンジ 1: データローダー
各ページにローダー関数を追加して、データの事前取得を実装してください。

### チャレンジ 2: 権限制御
ユーザーのロールに基づいてアクセス制御機能を追加してください。

### チャレンジ 3: レスポンシブサイドバー
モバイル対応のサイドバーメニューを実装してください。

## 🔗 次のステップ

次は「[認証付きTodoアプリ](../04-todo-with-auth/)」に進みましょう。ルートの保護と認証処理を学びます。