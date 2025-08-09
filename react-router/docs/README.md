# React Router ドキュメント (Vue/Nuxtユーザー向け)

Vue.jsやNuxt.jsを使い慣れた方のための、React Router v7 (2025年版) の包括的な学習ドキュメントです。
約3〜5時間で読める分量で、Nuxtの機能と対比しながら詳しく解説します。

## 📚 このドキュメントについて

- **対象読者**: Vue.js/Nuxt.jsの経験があり、React Routerを学びたい方
- **バージョン**: React Router v7 (2025年最新)
- **想定学習時間**: 3〜5時間
- **レベル表記**: 🟢 初級 / 🟡 中級 / 🔴 上級
- **特徴**: Nuxtの機能との対応関係を示しながら、実践的なコード例で学習

## 📑 目次

### 第1部: 基礎編 (約1時間)

1. **[React Routerとは - Nuxtとの対比](./01-introduction.md)** 🟢
   - React Routerの哲学と設計思想  
   - Nuxtのルーティングとの違い
   - 2025年の最新機能概要

2. **[インストールと基本セットアップ](./02-installation.md)** 🟢
   - 3つのルーティングモード (Declarative/Data/Framework)
   - Vite/Next.jsでのセットアップ
   - TypeScript設定

3. **[基本的なルーティング](./03-basic-routing.md)** 🟢
   - ルート定義の方法（宣言的 vs 設定ベース）
   - Link vs NavLink の使い分け
   - useNavigate によるプログラム的ナビゲーション

4. **[動的ルートとパラメータ](./04-route-parameters.md)** 🟢
   - パスパラメータ (:id)
   - クエリパラメータの扱い
   - useParams/useSearchParams

### 第2部: 中級編 (約1.5時間)

5. **[ネストされたルートとレイアウト](./05-nested-routes.md)** 🟡
   - Outletコンポーネントの役割と使い方
   - 共通レイアウトパターンの実装
   - 階層的なルート構造の設計

6. **[データローディングとActions](./06-data-loading.md)** 🟡
   - loader関数によるデータ事前取得（Nuxtのasync dataに相当）
   - action関数によるフォーム処理とデータ更新
   - useLoaderData/useActionData フックの活用

7. **[ナビゲーションガードと認証](./07-navigation-guards.md)** 🟡
   - 保護されたルートの実装パターン
   - 認証チェックとリダイレクト処理
   - 権限ベースのアクセス制御

8. **[エラー処理とフォールバック](./08-error-handling.md)** 🟡
   - errorElement
   - useRouteError
   - エラーバウンダリー

### 第3部: 上級編 (約1.5時間)

9. **[パフォーマンス最適化](./09-performance.md)** 🔴
   - コード分割とReact.lazy
   - プリフェッチング戦略
   - React 18/19の新機能活用

10. **[型安全なルーティング](./10-type-safety.md)** 🔴
    - TypeScript統合
    - 型付きパラメータ
    - カスタムフックの作成

11. **[サーバーサイド対応](./11-server-side.md)** 🔴
    - SSR/SSG対応
    - React Server Components
    - Remixとの統合

12. **[高度なパターンと実装例](./12-advanced-patterns.md)** 🔴
    - モーダルルーティング
    - アニメーション遷移
    - メタデータ管理

## 🔄 Nuxt.js → React Router 対応表

| Nuxt.js | React Router | 説明 |
|---------|--------------|------|
| `pages/` ディレクトリ | ルート設定オブジェクト | ページとルートの対応 |
| `<NuxtPage />` | `<Outlet>` | 子ページの表示 |
| `<NuxtLink>` | `<Link>` / `<NavLink>` | ナビゲーションリンク |
| `navigateTo()` | `useNavigate()` | プログラム的ナビゲーション |
| `$route` | `useLocation()` / `useParams()` | 現在のルート情報 |
| `asyncData` / `fetch` | loader関数 | データの事前取得 |
| middleware | loader関数 | ルート前処理 |

## 🚀 クイックスタート

```jsx
// Nuxtでのファイルベースルーティング
// pages/index.vue → /
// pages/about.vue → /about

// React Router v7での同等のルート定義
const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/about", element: <About /> }
]);
```

## 💡 学習のポイント

1. **宣言的アプローチ**: React RouterはJSXでルートを宣言的に定義します
2. **フックベース**: useNavigate、useParamsなど、React Hooksを中心とした設計
3. **データフェッチング**: loader/actionパターンで、Nuxtのasync dataより柔軟な制御が可能
4. **型安全性**: TypeScriptサポートが強力（2025年版で更に強化）
5. **コンポーネント中心**: 全てがReactコンポーネントとして構成される

## 📊 難易度別学習プラン

### 🏃‍♂️ 速習コース (3時間)
- 第1部: 基礎編をすべて
- 第2部: 5章、6章、7章のみ
- 実装例を中心に学習

### 🚶‍♂️ 標準コース (5時間)
- 第1部〜第3部をすべて
- 各章のサンプルコードを実装
- Nuxtとの違いを理解

## 🔗 参考資料

- [React Router 公式ドキュメント](https://reactrouter.com/)
- [Nuxt.js → React Router 移行ガイド](./migration-guide.md)
- [2025年のReact Router新機能まとめ](./whats-new-2025.md)