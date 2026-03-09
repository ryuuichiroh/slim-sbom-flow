# セットアップ方法

slim-sbom-flow を使用して OSS 管理システムを構築する手順を説明します。

## 目次

- [1. Dependency-Track のセットアップ](#1-dependency-track-のセットアップ)
- [2. GitHub Actions の設定](#2-github-actions-の設定)
- [3. 要レビュー OSS リストのカスタマイズ](#3-要レビュー-oss-リストのカスタマイズ)
- [4. 初回 SBOM の登録](#4-初回-sbom-の登録)

---

## 1. Dependency-Track のセットアップ

Dependency-Track は脆弱性管理の中心となるシステムです。

**詳細な手順書**: [docs/dependency-track-setup.md](docs/dependency-track-setup.md)

### クイックスタート

```bash
# 基本構成（小規模チーム向け）
cp docker-compose/basic/docker-compose.yml /path/to/deployment/
cd /path/to/deployment/

# パスワードを変更
vim docker-compose.yml

# 起動
docker compose up -d

# Web UI にアクセス
# http://localhost:8080
# 初期ログイン: admin / admin
```

### 構成の選択

| 規模 | 構成 | 認証方式 | ドキュメント |
|-----|------|---------|------------|
| 小規模（単一チーム） | Basic | 基本認証 | [dependency-track-setup.md](docs/dependency-track-setup.md#基本セットアップ小規模チーム向け) |
| 中規模以上 | OIDC | OIDC 連携 | [oidc-setup-keycloak.md](docs/oidc-setup-keycloak.md) |

---

## 2. GitHub Actions の設定

**※ 実装中です。以下は予定です。**

GitHub Actions のワークフローを配置して、PR/Tag 作成時の自動チェックを有効化します。

### 提供予定ファイル

- `.github/workflows/pr-sbom-check-trivy.yml`: PR 作成時のチェック（Trivy 版）
- `.github/workflows/pr-sbom-check-syft.yml`: PR 作成時のチェック（Syft 版）
- `.github/workflows/tag-sbom-upload.yml`: Tag 作成時の SBOM 生成・承認フロー

### 設定手順（予定）

1. GitHub Secrets に `DT_API_KEY` を登録
2. 使用するツール（Trivy / Syft）に応じてワークフローをコピー
3. ワークフローの設定をカスタマイズ（プロジェクト名等）

---

## 3. 要レビュー OSS リストのカスタマイズ

**※ 実装中です。以下は予定です。**

組織のポリシーに合わせて、要レビューOSSを定義します。

### 提供予定ファイル

- `config/review-required-oss.yml`: 要レビュー OSS の定義
- `config/license-guidelines.yml`: ライセンス固有のチェック項目

### カスタマイズ手順（予定）

1. slim-sbom-flow をフォーク
2. `config/review-required-oss.yml` を編集
3. 組織のポリシーに合わせてパッケージ名・ライセンスを追加

---

## 4. 初回 SBOM の登録

**※ 実装中です。以下は予定です。**

既存プロジェクトの SBOM をベースラインとして Dependency-Track に登録します。

### 手順（予定）

1. SBOM を生成（Trivy / Syft）
2. Dependency-Track にプロジェクトを作成
3. SBOM をアップロード

---

## 提供予定の成果物

| カテゴリ | ファイル | ステータス |
|---------|---------|-----------|
| ドキュメント | [docs/dependency-track-setup.md](docs/dependency-track-setup.md) | ✅ 完成 |
| ドキュメント | [docs/oidc-setup-keycloak.md](docs/oidc-setup-keycloak.md) | ✅ 完成 |
| Docker Compose | docker-compose/basic/docker-compose.yml | ✅ 完成 |
| Docker Compose | docker-compose/oidc/docker-compose.yml | ✅ 完成 |
| GitHub Actions | .github/workflows/pr-sbom-check-trivy.yml | 🚧 実装中 |
| GitHub Actions | .github/workflows/tag-sbom-upload.yml | 🚧 実装中 |
| TypeScript | scripts/detect-oss-diff.ts | 🚧 実装中 |
| TypeScript | scripts/create-approval-issue.ts | 🚧 実装中 |
| Config | config/review-required-oss.yml | 🚧 実装中 |
| Config | config/license-guidelines.yml | 🚧 実装中 |

---

**※ 現在実装中です。完成次第、このドキュメントを更新します。**
