# 認証付きTodoアプリ

**所要時間: 2時間**  
**レベル: 🟡 中級**

認証機能とルート保護を実装し、ユーザーごとのTodoリストアプリを作成します。

## 🎯 学習目標

- ルート保護（Protected Routes）の実装方法を理解する
- 認証状態の管理とコンテキストの活用を学ぶ
- リダイレクト処理とナビゲーションガードを実装する
- ローダー関数での認証チェックを覚える
- localStorage を使ったセッション管理を学ぶ

## 🏗️ 作るもの

認証付きTodoアプリ：
- ユーザーログイン/サインアップ
- 認証が必要なTodoリストページ
- ユーザーごとのTodoデータ管理
- ログアウト機能
- 認証状態に応じたナビゲーション

## 📋 前提条件

- 「ネストされたルートで管理画面」を完了していること
- React Context API の基本的な知識
- localStorage の使い方を知っていること

## 🚀 始め方

### ステップ 1: プロジェクトの準備

```bash
cd starter
npm install
npm run dev
```

### ステップ 2: 段階的な実装

1. **Step 1**: 認証コンテキストとプロバイダーの作成
2. **Step 2**: ログイン/サインアップフォーム
3. **Step 3**: ProtectedRoute コンポーネント
4. **Step 4**: Todoリスト機能の実装
5. **Step 5**: 認証ガードとリダイレクト処理

### ステップ 3: 実装開始

#### Step 1: 認証コンテキストの作成

**src/contexts/AuthContext.tsx**:

```tsx
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react'

interface User {
  id: string
  name: string
  email: string
}

interface AuthContextType {
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<boolean>
  signup: (name: string, email: string, password: string) => Promise<boolean>
  logout: () => void
  isAuthenticated: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

// モックユーザーデータ
const mockUsers: Record<string, { id: string; name: string; email: string; password: string }> = {
  'user1@example.com': {
    id: '1',
    name: '田中太郎',
    email: 'user1@example.com',
    password: 'password123'
  },
  'user2@example.com': {
    id: '2',
    name: '佐藤花子',
    email: 'user2@example.com',
    password: 'password456'
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  // 初期化時にlocalStorageから認証情報を復元
  useEffect(() => {
    const token = localStorage.getItem('auth_token')
    const userData = localStorage.getItem('user_data')
    
    if (token && userData) {
      try {
        const parsedUser = JSON.parse(userData)
        setUser(parsedUser)
      } catch (error) {
        console.error('Failed to parse user data:', error)
        localStorage.removeItem('auth_token')
        localStorage.removeItem('user_data')
      }
    }
    
    setIsLoading(false)
  }, [])

  const login = async (email: string, password: string): Promise<boolean> => {
    setIsLoading(true)
    
    // 実際のアプリではAPIを呼び出すが、ここではモックで実装
    await new Promise(resolve => setTimeout(resolve, 1000)) // API呼び出しをシミュレート
    
    const mockUser = mockUsers[email]
    if (mockUser && mockUser.password === password) {
      const userInfo = {
        id: mockUser.id,
        name: mockUser.name,
        email: mockUser.email
      }
      
      setUser(userInfo)
      localStorage.setItem('auth_token', 'mock_token_' + mockUser.id)
      localStorage.setItem('user_data', JSON.stringify(userInfo))
      setIsLoading(false)
      return true
    }
    
    setIsLoading(false)
    return false
  }

  const signup = async (name: string, email: string, password: string): Promise<boolean> => {
    setIsLoading(true)
    
    await new Promise(resolve => setTimeout(resolve, 1000))
    
    // 既存のメールアドレスかチェック
    if (mockUsers[email]) {
      setIsLoading(false)
      return false
    }
    
    // 新しいユーザーを作成
    const newUserId = Date.now().toString()
    const newUser = {
      id: newUserId,
      name,
      email
    }
    
    mockUsers[email] = { ...newUser, password }
    
    setUser(newUser)
    localStorage.setItem('auth_token', 'mock_token_' + newUserId)
    localStorage.setItem('user_data', JSON.stringify(newUser))
    setIsLoading(false)
    return true
  }

  const logout = () => {
    setUser(null)
    localStorage.removeItem('auth_token')
    localStorage.removeItem('user_data')
  }

  const value = {
    user,
    isLoading,
    login,
    signup,
    logout,
    isAuthenticated: !!user
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
```

#### Step 2: ルート設定とメインレイアウト

**src/main.tsx**:

```tsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router-dom'
import './index.css'

import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Home from './pages/Home'
import Login from './pages/Login'
import Signup from './pages/Signup'
import TodoList from './pages/TodoList'
import Profile from './pages/Profile'

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
      {
        path: "signup",
        element: <Signup />,
      },
      {
        path: "todos",
        element: (
          <ProtectedRoute>
            <TodoList />
          </ProtectedRoute>
        ),
      },
      {
        path: "profile",
        element: (
          <ProtectedRoute>
            <Profile />
          </ProtectedRoute>
        ),
      },
    ],
  },
])

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </React.StrictMode>,
)
```

#### Step 3: ProtectedRoute コンポーネント

**src/components/ProtectedRoute.tsx**:

```tsx
import { ReactNode } from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

interface ProtectedRouteProps {
  children: ReactNode
}

function ProtectedRoute({ children }: ProtectedRouteProps) {
  const { isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  // 認証チェック中はローディング表示
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>
    )
  }

  // 未認証の場合はログインページにリダイレクト
  // 現在のパスをstateとして渡すことで、ログイン後に元のページに戻れる
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />
  }

  // 認証済みの場合は子コンポーネントを表示
  return <>{children}</>
}

export default ProtectedRoute
```

#### Step 4: レイアウトコンポーネント

**src/components/Layout.tsx**:

```tsx
import { Link, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

function Layout() {
  const { isAuthenticated, user, logout } = useAuth()
  const navigate = useNavigate()

  const handleLogout = () => {
    logout()
    navigate('/')
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm">
        <nav className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="text-2xl font-bold text-blue-600">
              TodoApp
            </Link>
            
            <div className="flex items-center space-x-6">
              <Link 
                to="/" 
                className="text-gray-600 hover:text-blue-600 transition-colors"
              >
                ホーム
              </Link>
              
              {isAuthenticated ? (
                <>
                  <Link 
                    to="/todos" 
                    className="text-gray-600 hover:text-blue-600 transition-colors"
                  >
                    Todo
                  </Link>
                  <Link 
                    to="/profile" 
                    className="text-gray-600 hover:text-blue-600 transition-colors"
                  >
                    プロフィール
                  </Link>
                  
                  <div className="flex items-center space-x-4">
                    <span className="text-gray-700">
                      こんにちは、{user?.name}さん
                    </span>
                    <button
                      onClick={handleLogout}
                      className="bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700 transition-colors"
                    >
                      ログアウト
                    </button>
                  </div>
                </>
              ) : (
                <>
                  <Link 
                    to="/login" 
                    className="text-gray-600 hover:text-blue-600 transition-colors"
                  >
                    ログイン
                  </Link>
                  <Link 
                    to="/signup" 
                    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 transition-colors"
                  >
                    サインアップ
                  </Link>
                </>
              )}
            </div>
          </div>
        </nav>
      </header>
      
      <main className="max-w-6xl mx-auto px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}

export default Layout
```

#### Step 5: ログインページ

**src/pages/Login.tsx**:

```tsx
import { useState, FormEvent } from 'react'
import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  
  const { login } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  
  // リダイレクト先を取得（ProtectedRouteからのstate）
  const from = location.state?.from?.pathname || '/todos'

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setIsSubmitting(true)

    try {
      const success = await login(email, password)
      if (success) {
        navigate(from, { replace: true })
      } else {
        setError('メールアドレスまたはパスワードが正しくありません')
      }
    } catch (error) {
      setError('ログインに失敗しました')
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="max-w-md mx-auto">
      <div className="bg-white rounded-lg shadow-md p-8">
        <h1 className="text-2xl font-bold text-center text-gray-900 mb-6">
          ログイン
        </h1>
        
        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-4">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
              メールアドレス
            </label>
            <input
              type="email"
              id="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="your@example.com"
              required
            />
          </div>

          <div>
            <label htmlFor="password" className="block text-sm font-medium text-gray-700 mb-1">
              パスワード
            </label>
            <input
              type="password"
              id="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              placeholder="パスワードを入力"
              required
            />
          </div>

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-blue-600 text-white py-2 px-4 rounded-md hover:bg-blue-700 focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {isSubmitting ? 'ログイン中...' : 'ログイン'}
          </button>
        </form>

        <div className="mt-6 text-center">
          <p className="text-gray-600">
            アカウントをお持ちでない方は{' '}
            <Link to="/signup" className="text-blue-600 hover:text-blue-800 font-medium">
              サインアップ
            </Link>
          </p>
        </div>

        {/* デモ用の認証情報 */}
        <div className="mt-6 p-4 bg-gray-50 rounded-md">
          <p className="text-sm text-gray-600 mb-2">デモ用アカウント:</p>
          <div className="text-xs text-gray-500">
            <p>メール: user1@example.com</p>
            <p>パスワード: password123</p>
          </div>
        </div>
      </div>
    </div>
  )
}

export default Login
```

#### Step 6: Todoリストページ

**src/pages/TodoList.tsx**:

```tsx
import { useState, useEffect } from 'react'
import { useAuth } from '../contexts/AuthContext'

interface Todo {
  id: string
  text: string
  completed: boolean
  createdAt: string
  userId: string
}

function TodoList() {
  const { user } = useAuth()
  const [todos, setTodos] = useState<Todo[]>([])
  const [newTodoText, setNewTodoText] = useState('')
  const [filter, setFilter] = useState<'all' | 'active' | 'completed'>('all')

  // localStorageからユーザーのTodoを読み込み
  useEffect(() => {
    if (user) {
      const storedTodos = localStorage.getItem(`todos_${user.id}`)
      if (storedTodos) {
        setTodos(JSON.parse(storedTodos))
      }
    }
  }, [user])

  // Todoの変更をlocalStorageに保存
  const saveTodos = (newTodos: Todo[]) => {
    if (user) {
      localStorage.setItem(`todos_${user.id}`, JSON.stringify(newTodos))
    }
  }

  const addTodo = () => {
    if (newTodoText.trim() && user) {
      const newTodo: Todo = {
        id: Date.now().toString(),
        text: newTodoText.trim(),
        completed: false,
        createdAt: new Date().toISOString(),
        userId: user.id
      }
      const updatedTodos = [...todos, newTodo]
      setTodos(updatedTodos)
      saveTodos(updatedTodos)
      setNewTodoText('')
    }
  }

  const toggleTodo = (id: string) => {
    const updatedTodos = todos.map(todo =>
      todo.id === id ? { ...todo, completed: !todo.completed } : todo
    )
    setTodos(updatedTodos)
    saveTodos(updatedTodos)
  }

  const deleteTodo = (id: string) => {
    const updatedTodos = todos.filter(todo => todo.id !== id)
    setTodos(updatedTodos)
    saveTodos(updatedTodos)
  }

  const filteredTodos = todos.filter(todo => {
    if (filter === 'active') return !todo.completed
    if (filter === 'completed') return todo.completed
    return true
  })

  const completedCount = todos.filter(todo => todo.completed).length
  const activeCount = todos.length - completedCount

  return (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">
            {user?.name}さんのTodoリスト
          </h1>
          <div className="text-sm text-gray-600">
            完了: {completedCount} / 残り: {activeCount} / 全体: {todos.length}
          </div>
        </div>

        {/* 新しいTodo入力 */}
        <div className="flex gap-2 mb-6">
          <input
            type="text"
            value={newTodoText}
            onChange={(e) => setNewTodoText(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && addTodo()}
            className="flex-1 px-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="新しいタスクを入力..."
          />
          <button
            onClick={addTodo}
            disabled={!newTodoText.trim()}
            className="bg-blue-600 text-white px-6 py-2 rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            追加
          </button>
        </div>

        {/* フィルター */}
        <div className="flex gap-2 mb-6">
          {(['all', 'active', 'completed'] as const).map((filterType) => (
            <button
              key={filterType}
              onClick={() => setFilter(filterType)}
              className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                filter === filterType
                  ? 'bg-blue-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              {filterType === 'all' && 'すべて'}
              {filterType === 'active' && '未完了'}
              {filterType === 'completed' && '完了済み'}
            </button>
          ))}
        </div>

        {/* Todoリスト */}
        <div className="space-y-2">
          {filteredTodos.length === 0 ? (
            <p className="text-center text-gray-500 py-8">
              {filter === 'all' && 'まだタスクがありません。新しいタスクを追加してみましょう！'}
              {filter === 'active' && '未完了のタスクはありません。'}
              {filter === 'completed' && '完了したタスクはありません。'}
            </p>
          ) : (
            filteredTodos.map((todo) => (
              <div
                key={todo.id}
                className={`flex items-center gap-3 p-3 border border-gray-200 rounded-md ${
                  todo.completed ? 'bg-gray-50' : 'bg-white'
                }`}
              >
                <input
                  type="checkbox"
                  checked={todo.completed}
                  onChange={() => toggleTodo(todo.id)}
                  className="w-5 h-5 text-blue-600 rounded focus:ring-2 focus:ring-blue-500"
                />
                <span
                  className={`flex-1 ${
                    todo.completed
                      ? 'text-gray-500 line-through'
                      : 'text-gray-900'
                  }`}
                >
                  {todo.text}
                </span>
                <div className="text-xs text-gray-400">
                  {new Date(todo.createdAt).toLocaleDateString('ja-JP')}
                </div>
                <button
                  onClick={() => deleteTodo(todo.id)}
                  className="text-red-600 hover:text-red-800 text-sm font-medium"
                >
                  削除
                </button>
              </div>
            ))
          )}
        </div>

        {todos.length > 0 && (
          <div className="mt-6 flex justify-between items-center text-sm text-gray-500">
            <span>
              {filter === 'all' && `${todos.length}件のタスク`}
              {filter === 'active' && `${activeCount}件の未完了タスク`}
              {filter === 'completed' && `${completedCount}件の完了タスク`}
            </span>
            {completedCount > 0 && (
              <button
                onClick={() => {
                  const activeTodos = todos.filter(todo => !todo.completed)
                  setTodos(activeTodos)
                  saveTodos(activeTodos)
                }}
                className="text-red-600 hover:text-red-800 font-medium"
              >
                完了済みタスクをすべて削除
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  )
}

export default TodoList
```

## 🎓 学習ポイント

### 1. ProtectedRoute パターン
```tsx
function ProtectedRoute({ children }: { children: ReactNode }) {
  const { isAuthenticated } = useAuth()
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }
  
  return <>{children}</>
}
```

### 2. 認証コンテキスト
```tsx
const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}
```

### 3. リダイレクト処理
```tsx
// ログイン前のページを保存
<Navigate to="/login" state={{ from: location }} replace />

// ログイン後に元のページに戻る
const from = location.state?.from?.pathname || '/todos'
navigate(from, { replace: true })
```

### 4. ユーザー固有のデータ管理
```tsx
// ユーザーIDでデータを分離
localStorage.setItem(`todos_${user.id}`, JSON.stringify(todos))
const storedTodos = localStorage.getItem(`todos_${user.id}`)
```

## 🧪 チャレンジ課題

### チャレンジ 1: パスワードリセット機能
パスワードを忘れた場合のリセット機能を実装してください。

### チャレンジ 2: トークンの有効期限
JWTトークンの有効期限を管理し、自動ログアウト機能を追加してください。

### チャレンジ 3: Todo の共有機能
他のユーザーとTodoを共有できる機能を追加してください。

## 🔗 次のステップ

次は「[ECサイトのルーティング](../05-ecommerce-routing/)」に進みましょう。複雑なルート構造とクエリパラメータの活用を学びます。