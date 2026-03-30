# セットアップ方法

slim-sbom-flow を使用して OSS 管理システムを構築する手順を説明します。

システムのセットアップは、以下に分けて説明します。
1. [Dependency-Track のセットアップ](#1-dependency-track-dt-のセットアップ)
2. [GitHub Actions のセットアップ](#2-github-actions-のセットアップ)
3. [プロジェクトに合わせたカスタマイズ](#3-プロジェクトに合わせたカスタマイズ)

## 1. Dependency-Track のセットアップ

Dependency-Track は脆弱性管理の中心となる部分です。

最初に [Dependency-Track のローカル環境の構築手順書](docs/dt-setup-local.md)を参照し、ローカル環境で Dependency-Track の機能を体験します。具体的には、以下の設定方法を学びます。

- [脆弱性データベースの設定](docs/dt-setup-local.md#脆弱性データベースの設定)
- [脆弱性スキャナーの設定](docs/dt-setup-local.md#脆弱性スキャナーの設定)
- GitHub Action と連携するための [API キーの作成](docs/dt-setup-local.md#api-キーの作成)
- 脆弱性検知イベントなどの[通知設定](docs/dt-setup-local.md#通知設定)
- [OIDC 準拠の認証基盤との連携](docs/dt-setup-local.md#oidc-準拠の認証基盤との連携)

Dependency-Track の基本的な設定を学んだあとは、[AWS を利用したシステム構成](docs/dt-setup-aws.md)を参照し、[AWS へデプロイするための Terraform 設定](terraform/README.md)を使って運用環境にシステムを構築します。

## 2. GitHub Actions のセットアップ

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

## 3. プロジェクトに合わせたカスタマイズ

**※ 実装中です。以下は予定です。**

組織のポリシーに合わせて、要レビューOSSを定義します。

### 提供予定ファイル

- `config/review-required-oss.yml`: 要レビュー OSS の定義
- `config/license-guidelines.yml`: ライセンス固有のチェック項目

### カスタマイズ手順（予定）

1. slim-sbom-flow をフォーク
2. `config/review-required-oss.yml` を編集
3. 組織のポリシーに合わせてパッケージ名・ライセンスを追加
