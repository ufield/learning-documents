# React Router サンプルコード集

実際のプロジェクトで使えるReact Routerの実装例をまとめています。

## 📦 サンプル一覧

### 基本的な実装例

1. **[basic-routing](./basic-routing/)**
   - シンプルなルーティング設定
   - ナビゲーションメニューの実装
   - 技術: React Router v6, React 18

2. **[nested-layouts](./nested-layouts/)**
   - 共通レイアウトの実装
   - ネストされたルートの活用
   - 技術: React Router v6, CSS Modules

3. **[auth-flow](./auth-flow/)**
   - ログイン/ログアウト機能
   - 保護されたルートの実装
   - 技術: React Router v6, Context API

### 実用的なアプリケーション

4. **[blog-platform](./blog-platform/)**
   - ブログプラットフォーム
   - 記事のCRUD操作
   - 技術: React Router v6, TypeScript, Tailwind CSS

5. **[e-commerce-spa](./e-commerce-spa/)**
   - ECサイトのSPA実装
   - 商品一覧、詳細、カート機能
   - 技術: React Router v6, Redux Toolkit, Material-UI

6. **[dashboard-app](./dashboard-app/)**
   - 管理ダッシュボード
   - 複雑なルート構造
   - 技術: React Router v6, TypeScript, Ant Design

### 高度な実装例

7. **[lazy-loading-routes](./lazy-loading-routes/)**
   - ルートレベルのコード分割
   - React.lazyとSuspenseの活用
   - 技術: React Router v6, Webpack

8. **[ssr-with-router](./ssr-with-router/)**
   - サーバーサイドレンダリング対応
   - SEO最適化
   - 技術: React Router v6, Next.js

9. **[type-safe-router](./type-safe-router/)**
   - TypeScriptによる型安全なルーティング
   - カスタムフックとユーティリティ
   - 技術: React Router v6, TypeScript, Zod

## 🔧 各サンプルの使い方

```bash
# サンプルディレクトリに移動
cd examples/[サンプル名]

# 依存関係のインストール
npm install

# 開発サーバーの起動
npm run dev
```

## 📝 サンプルの構成

各サンプルには以下が含まれています：

- **README.md**: サンプルの説明と実装のポイント
- **完全に動作するソースコード**
- **package.json**: 必要な依存関係
- **実装の解説コメント**

## 💡 活用方法

1. **参考実装として**: 実際のプロジェクトに組み込む際の参考に
2. **学習教材として**: コードを読んで理解を深める
3. **テンプレートとして**: フォークして自分のプロジェクトのベースに

## 🎯 目的別インデックス

### 認証が必要な場合
- [auth-flow](./auth-flow/)
- [dashboard-app](./dashboard-app/)

### TypeScriptを使いたい場合
- [blog-platform](./blog-platform/)
- [dashboard-app](./dashboard-app/)
- [type-safe-router](./type-safe-router/)

### パフォーマンスを重視する場合
- [lazy-loading-routes](./lazy-loading-routes/)
- [ssr-with-router](./ssr-with-router/)

### 複雑なUIレイアウトの場合
- [nested-layouts](./nested-layouts/)
- [dashboard-app](./dashboard-app/)