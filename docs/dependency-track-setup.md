# Dependency-Track 構築手順書

このドキュメントでは、Dependency-Track の構築手順を説明します。

## 目次

- [前提条件](#前提条件)
- [基本セットアップ（小規模チーム向け）](#基本セットアップ小規模チーム向け)
- [初期設定](#初期設定)
- [API キーの作成](#api-キーの作成)
- [脆弱性データベースの設定](#脆弱性データベースの設定)
- [Trivy Scanner の設定（オプション）](#trivy-scanner-の設定オプション)
- [OIDC 連携（中規模以上のチーム向け）](#oidc-連携中規模以上のチーム向け)
- [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

- Docker と Docker Compose がインストールされていること
- 最低 8GB の RAM（推奨 12GB 以上）
- ポート 8080（Frontend）と 8081（API Server）が利用可能であること

---

## 基本セットアップ（小規模チーム向け）

基本認証を使用した、最もシンプルな構成です。

### 1. docker-compose.yml の準備

```bash
# slim-sbom-flow リポジトリのルートディレクトリで実行
cp docker-compose/basic/docker-compose.yml /path/to/your/deployment/
cd /path/to/your/deployment/
```

### 2. パスワードの変更

`docker-compose.yml` を編集し、以下のパスワードを変更してください：

```yaml
# API Server のデータベースパスワード
ALPINE_DATABASE_PASSWORD: "changeme"  # ← 変更

# PostgreSQL のパスワード
POSTGRES_PASSWORD: "changeme"  # ← 変更
```

**重要**: 2箇所のパスワードは同じ値にしてください。

### 3. API Base URL の設定

他のマシンからアクセスする場合は、`API_BASE_URL` を変更してください：

```yaml
frontend:
  environment:
    # localhost を実際のサーバーの IP アドレスまたはドメイン名に変更
    API_BASE_URL: "http://192.168.1.100:8081"  # 例
```

### 4. Dependency-Track の起動

```bash
docker compose up -d
```

初回起動時は、データベースの初期化とイメージのダウンロードに数分かかります。

### 5. 起動確認

以下のコマンドでログを確認します：

```bash
docker compose logs -f apiserver
```

`Dependency-Track is ready` というメッセージが表示されたら起動完了です。

### 6. Web UI へのアクセス

ブラウザで以下の URL にアクセスします：

```
http://localhost:8080
```

**初期ログイン情報**:
- Username: `admin`
- Password: `admin`

**重要**: 初回ログイン後、必ずパスワードを変更してください。

---

## 初期設定

### 管理者パスワードの変更

1. 右上のユーザーアイコン → `Administration` をクリック
2. 左メニューの `Access Management` → `Teams` をクリック
3. `Administrators` をクリック
4. `admin` ユーザーをクリック
5. `Change Password` をクリックし、新しいパスワードを設定

### プロジェクトの作成

1. 左メニューの `Projects` をクリック
2. 右上の `+ Create Project` をクリック
3. 以下を入力：
   - **Name**: プロジェクト名（例: `my-app`）
   - **Version**: バージョン（例: `1.0.0`）
   - **Classifier**: `Application` を選択
4. `Create` をクリック

---

## API キーの作成

GitHub Actions から Dependency-Track にアクセスするための API キーを作成します。

### 1. Automation チームの作成

1. `Administration` → `Access Management` → `Teams` をクリック
2. `+ Create Team` をクリック
3. 以下を入力：
   - **Name**: `Automation`
   - **API Keys**: `Generate` をクリック
4. 生成された API キーをコピーして安全に保管

### 2. 権限の設定

`Automation` チームに以下の権限を付与します：

- `BOM_UPLOAD`: SBOM のアップロード
- `PROJECT_CREATION_UPLOAD`: プロジェクトの自動作成
- `PORTFOLIO_MANAGEMENT`: プロジェクトの管理

### 3. GitHub Secrets への登録

GitHub リポジトリの Settings → Secrets and variables → Actions で以下を登録：

- **Name**: `DT_API_KEY`
- **Value**: コピーした API キー

---

## 脆弱性データベースの設定

Dependency-Track は複数の脆弱性データベースをサポートしています。

### 利用可能なデータベース

| データベース | 提供元 | 説明 |
|------------|-------|------|
| GitHub Advisories | GitHub | GitHub Advisory Database |
| OSV | Google | Open Source Vulnerabilities |
| OSS Index | Sonatype | Sonatype OSS Index |
| NVD | NIST | National Vulnerability Database |

### 設定方法

1. `Administration` → `Analyzers` → `Internal` をクリック
2. 有効化したいデータベースのスイッチをオンにする

### 推奨

まず全て有効化して、自分のプロジェクトでの検出状況を確認してください。

検出される脆弱性の数、重複、誤検出率はプロジェクトによって異なります。運用しながら最適な組み合わせを見つけてください。

### 参考リンク

- [Dependency-Track 公式ドキュメント - Analyzers](https://docs.dependencytrack.org/datasources/)

---

## Trivy Scanner の設定（オプション）

Dependency-Track は Trivy を使った追加スキャンをサポートしています。

### メリットとデメリット

**メリット**:
- 脆弱性の検出精度が向上する可能性がある
- コンテナイメージの脆弱性も検出可能

**デメリット**:
- メモリとCPUの消費が増える
- スキャン時間が長くなる

### 有効化手順

#### 1. Trivy Server の起動

`docker-compose.yml` の Trivy セクションのコメントを解除：

```yaml
trivy:
  image: aquasec/trivy:latest
  command:
    - server
    - --listen
    - 0.0.0.0:8082
    - --token
    - changeme  # IMPORTANT: 任意のトークンに変更
  volumes:
    - trivy-cache:/root/.cache/trivy
  ports:
    - "8082:8082"
  restart: unless-stopped
```

volumes セクションも解除：

```yaml
volumes:
  dtrack-data: {}
  postgres-data: {}
  trivy-cache: {}  # この行のコメントを解除
```

#### 2. Trivy Server の再起動

```bash
docker compose up -d
```

#### 3. Dependency-Track での設定

1. `Administration` → `Analyzers` → `Trivy` をクリック
2. 以下を設定：
   - **Enabled**: オン
   - **Base URL**: `http://trivy:8082`
   - **API Token**: docker-compose.yml で設定したトークン
3. `Save` をクリック

### 効果の確認

自分のプロジェクトで Trivy を有効/無効にして、検出結果を比較することを推奨します。

---

## OIDC 連携（中規模以上のチーム向け）

複数のユーザーやチームで Dependency-Track を利用する場合、OIDC（OpenID Connect）による認証を推奨します。

### 対応している認証プロバイダー

- Keycloak
- Microsoft Entra ID（旧 Azure AD）
- Okta
- Auth0
- その他、OpenID Connect 対応プロバイダー

### OIDC 連携のメリット

- **シングルサインオン（SSO）**: 既存の組織アカウントで Dependency-Track にアクセス可能
- **集中管理**: 一元的にユーザー・グループを管理
- **自動プロビジョニング**: ユーザーの追加・削除が自動的に反映
- **チーム同期**: グループに基づいて自動的に権限を割り当て
- **セキュリティ向上**: MFA（多要素認証）などの高度な認証機能を利用可能

### Keycloak を使用した OIDC 連携

**詳細な手順書**: [docs/oidc-setup-keycloak.md](oidc-setup-keycloak.md)

Keycloak を使用した完全な OIDC 連携の手順を説明しています：

- Keycloak のセットアップ
- Realm、Client、User、Group の作成
- Dependency-Track との統合設定
- トラブルシューティング

### クイックスタート

```bash
# OIDC 構成をコピー
cp docker-compose/oidc/docker-compose.yml /path/to/deployment/
cd /path/to/deployment/

# パスワードとホスト名を変更
vim docker-compose.yml

# 起動
docker compose up -d

# 詳細な設定は oidc-setup-keycloak.md を参照
```

### 他の認証プロバイダー

Microsoft Entra ID、Okta、Auth0 などの OIDC プロバイダーも使用できます。

基本的な設定方法は [oidc-setup-keycloak.md](oidc-setup-keycloak.md) の「他の認証プロバイダーとの統合」セクションを参照してください

---

## トラブルシューティング

### API Server が起動しない

**症状**: `docker compose logs apiserver` でエラーが表示される

**原因と対処**:

1. **メモリ不足**
   - エラーメッセージに `OutOfMemoryError` が含まれる場合
   - 対処: `docker-compose.yml` のメモリ設定を減らす、またはホストのメモリを増やす

2. **データベース接続エラー**
   - エラーメッセージに `Connection refused` や `could not connect` が含まれる場合
   - 対処: PostgreSQL のパスワードが API Server と一致しているか確認

3. **ポートの競合**
   - エラーメッセージに `Address already in use` が含まれる場合
   - 対処: `docker-compose.yml` のポート番号を変更

### Web UI にアクセスできない

**症状**: ブラウザで `http://localhost:8080` にアクセスできない

**対処**:

1. コンテナの起動確認：
   ```bash
   docker compose ps
   ```
   全てのコンテナが `Up` になっているか確認

2. Frontend のログ確認：
   ```bash
   docker compose logs frontend
   ```

3. API Base URL の確認：
   - `docker-compose.yml` の `API_BASE_URL` が正しいか確認
   - 他のマシンからアクセスする場合は、`localhost` ではなく実際の IP アドレスを指定

### SBOM のアップロードが失敗する

**症状**: GitHub Actions から SBOM をアップロードできない

**対処**:

1. API キーの確認：
   - GitHub Secrets に `DT_API_KEY` が正しく登録されているか確認
   - Dependency-Track で API キーが有効か確認

2. 権限の確認：
   - `Automation` チームに `BOM_UPLOAD` 権限があるか確認

3. ネットワークの確認：
   - GitHub Actions から Dependency-Track にアクセスできるか確認
   - プライベートネットワークの場合は、VPN やファイアウォールの設定を確認

---

## 参考資料

- [Dependency-Track 公式ドキュメント](https://docs.dependencytrack.org/)
- [Dependency-Track GitHub](https://github.com/DependencyTrack/dependency-track)
- [CycloneDX 仕様](https://cyclonedx.org/)
