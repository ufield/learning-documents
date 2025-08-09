# React Router ドキュメント (Vue/Nuxtユーザー向け)

Vue RouterやNuxt.jsを使い慣れた方のための、React Router v7 (2025年版) の包括的な学習ドキュメントです。
約3〜5時間で読める分量で、Vue/Nuxtとの比較を交えながら解説します。

## 📚 このドキュメントについて

- **対象読者**: Vue.js/Nuxt.jsの経験があり、React Routerを学びたい方
- **バージョン**: React Router v7 (2025年最新)
- **想定学習時間**: 3〜5時間
- **レベル表記**: 🟢 初級 / 🟡 中級 / 🔴 上級

## 📑 目次

### 第1部: 基礎編 (約1時間)

1. **[React Routerとは - Vue Routerとの比較](./01-introduction.md)** 🟢
   - React Routerの哲学と設計思想
   - Vue Routerとの共通点・相違点
   - 2025年の最新機能概要

2. **[インストールと基本セットアップ](./02-installation.md)** 🟢
   - 3つのルーティングモード (Declarative/Data/Framework)
   - Vite/Next.jsでのセットアップ
   - TypeScript設定

3. **[基本的なルーティング](./03-basic-routing.md)** 🟢
   - ルート定義の方法 (Vue Routerとの比較)
   - Link vs NavLink
   - useNavigate (Vue RouterのuseRouterに相当)

4. **[動的ルートとパラメータ](./04-route-parameters.md)** 🟢
   - パスパラメータ (:id)
   - クエリパラメータの扱い
   - useParams/useSearchParams

### 第2部: 中級編 (約1.5時間)

5. **[ネストされたルートとレイアウト](./05-nested-routes.md)** 🟡
   - Outlet (Vue Routerの`<router-view>`に相当)
   - 共通レイアウトパターン
   - 相対パスと絶対パス

6. **[データローディングとActions](./06-data-loading.md)** 🟡
   - loader関数 (Nuxtのasync dataに相当)
   - action関数とフォーム処理
   - useLoaderData/useActionData

7. **[ナビゲーションガードと認証](./07-navigation-guards.md)** 🟡
   - 保護されたルート実装
   - リダイレクト処理
   - Vue RouterのnavigationGuardsとの比較

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

## 🔄 Vue Router → React Router 対応表

| Vue Router | React Router | 説明 |
|------------|--------------|------|
| `<router-view>` | `<Outlet>` | 子ルートの表示 |
| `<router-link>` | `<Link>` / `<NavLink>` | ナビゲーションリンク |
| `useRouter()` | `useNavigate()` | プログラマティックナビゲーション |
| `useRoute()` | `useLocation()` / `useParams()` | 現在のルート情報 |
| `beforeEach` | loader関数 | ルート前処理 |
| `meta` | handle プロパティ | ルートメタデータ |

## 🚀 クイックスタート

```jsx
// Vue Routerでのルート定義
const routes = [
  { path: '/', component: Home },
  { path: '/about', component: About }
]

// React Router v7での同等の実装
const router = createBrowserRouter([
  { path: "/", element: <Home /> },
  { path: "/about", element: <About /> }
]);
```

## 💡 学習のポイント

1. **宣言的アプローチ**: React Routerはより宣言的で、JSXでルートを定義
2. **フックベース**: Vue 3のComposition APIと同様、フックを多用
3. **データフェッチング**: loader/actionパターンは、Nuxtのasync dataより柔軟
4. **型安全性**: TypeScriptサポートが強力（2025年版で更に強化）

## 📊 難易度別学習プラン

### 🏃‍♂️ 速習コース (3時間)
- 第1部: 基礎編をすべて
- 第2部: 5章、6章、7章のみ
- 実装例を中心に学習

### 🚶‍♂️ 標準コース (5時間)
- 第1部〜第3部をすべて
- 各章のサンプルコードを実装
- Vue Routerとの違いを理解

## 🔗 参考資料

- [React Router 公式ドキュメント](https://reactrouter.com/)
- [Vue Router → React Router 移行ガイド](./migration-guide.md)
- [2025年のReact Router新機能まとめ](./whats-new-2025.md)