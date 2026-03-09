# Dependency-Track OIDC 連携（Keycloak）セットアップガイド

このドキュメントでは、Keycloak を使用した Dependency-Track の OIDC 連携の設定方法を説明します。

## 目次

- [前提条件](#前提条件)
- [なぜ OIDC 連携が必要か](#なぜ-oidc-連携が必要か)
- [システム構成](#システム構成)
- [セットアップ手順](#セットアップ手順)
  - [1. Keycloak と Dependency-Track の起動](#1-keycloak-と-dependency-track-の起動)
  - [2. Keycloak の初期設定](#2-keycloak-の初期設定)
  - [3. Realm の作成](#3-realm-の作成)
  - [4. Client の作成](#4-client-の作成)
  - [5. Group の作成](#5-group-の作成)
  - [6. User の作成](#6-user-の作成)
  - [7. Dependency-Track での動作確認](#7-dependency-track-での動作確認)
- [チーム権限の設定](#チーム権限の設定)
- [本番環境への移行](#本番環境への移行)
- [トラブルシューティング](#トラブルシューティング)

---

## 前提条件

- Docker と Docker Compose がインストールされていること
- 基本的な Dependency-Track の構築経験（[dependency-track-setup.md](dependency-track-setup.md) を参照）
- 最低 12GB の RAM（推奨 16GB 以上）

---

## なぜ OIDC 連携が必要か

### 基本認証の課題

基本認証（ユーザー名/パスワード）は小規模チームでは十分ですが、以下の課題があります：

- **ユーザー管理の煩雑さ**: ユーザーごとに Dependency-Track でアカウントを作成・管理する必要がある
- **パスワード管理**: 各ユーザーが Dependency-Track 用のパスワードを別途管理する必要がある
- **権限管理の手間**: チーム異動時に手動で権限を変更する必要がある
- **監査ログの不足**: 既存の認証システムと統合されていないため、監査が困難

### OIDC 連携のメリット

- **シングルサインオン（SSO）**: 既存の組織アカウントで Dependency-Track にアクセス可能
- **集中管理**: Keycloak や Entra ID で一元的にユーザー・グループを管理
- **自動プロビジョニング**: ユーザーの追加・削除が自動的に Dependency-Track に反映される
- **チーム同期**: グループに基づいて自動的に権限を割り当て
- **セキュリティ向上**: MFA（多要素認証）などの高度な認証機能を利用可能

### 適用規模

| 規模 | 構成 | 理由 |
|-----|------|------|
| 小規模（1-5人） | 基本認証 | シンプルで十分 |
| 中規模（6-20人） | OIDC 推奨 | ユーザー管理の手間が増える |
| 大規模（21人以上） | OIDC 必須 | 集中管理とセキュリティが重要 |

---

## システム構成

```
┌──────────────────────────────────────────────────────────┐
│  User's Browser                                          │
└────────┬─────────────────────────────────────────────────┘
         │
         │ 1. Access DT Frontend
         ▼
┌──────────────────────────────────────────────────────────┐
│  Dependency-Track Frontend (Port 8080)                   │
│  - OIDC Client Configuration                             │
└────────┬─────────────────────────────────────────────────┘
         │
         │ 2. Redirect to Keycloak for login
         ▼
┌──────────────────────────────────────────────────────────┐
│  Keycloak (Port 8443)                                    │
│  - Realm: dtrack                                         │
│  - Client: dependency-track                              │
│  - Users & Groups                                        │
└────────┬─────────────────────────────────────────────────┘
         │
         │ 3. Return ID Token & Access Token
         ▼
┌──────────────────────────────────────────────────────────┐
│  Dependency-Track API Server (Port 8081)                 │
│  - Validate Token                                        │
│  - User Provisioning                                     │
│  - Team Synchronization                                  │
└────────┬─────────────────────────────────────────────────┘
         │
         ▼
┌──────────────────────────────────────────────────────────┐
│  PostgreSQL (Port 5432)                                  │
└──────────────────────────────────────────────────────────┘
```

---

## セットアップ手順

### 1. Keycloak と Dependency-Track の起動

#### 1.1. docker-compose.yml の準備

```bash
# OIDC 構成ファイルをコピー
cp docker-compose/oidc/docker-compose.yml /path/to/deployment/
cd /path/to/deployment/
```

#### 1.2. 設定の変更

`docker-compose.yml` を編集し、以下を変更してください：

```yaml
# PostgreSQL のパスワード（2箇所）
ALPINE_DATABASE_PASSWORD: "changeme"  # ← 変更
POSTGRES_PASSWORD: "changeme"  # ← 変更

# Keycloak の管理者パスワード
KC_BOOTSTRAP_ADMIN_PASSWORD: "changeme"  # ← 変更

# ホスト名（他のマシンからアクセスする場合）
ALPINE_OIDC_ISSUER: "https://localhost:8443/realms/dtrack"  # ← your-domain.com に変更
API_BASE_URL: "http://localhost:8081"  # ← your-domain.com に変更
OIDC_ISSUER: "https://localhost:8443/realms/dtrack"  # ← your-domain.com に変更
```

**重要**: `localhost` を使用する場合は、ブラウザから Keycloak と Dependency-Track の両方に同じホスト名（localhost）でアクセスする必要があります。

#### 1.3. 起動

```bash
docker compose up -d
```

初回起動時は5-10分かかります。以下のコマンドでログを確認：

```bash
docker compose logs -f
```

全てのサービスが起動したら、次のステップに進みます。

---

### 2. Keycloak の初期設定

#### 2.1. Keycloak Admin Console へのアクセス

ブラウザで以下の URL にアクセス：

```
https://localhost:8443
```

**注意**: 自己署名証明書を使用している場合、ブラウザで証明書の警告が表示されます。開発環境では「詳細設定」→「localhost にアクセスする（安全ではありません）」を選択してください。

#### 2.2. ログイン

- Username: `admin`
- Password: `docker-compose.yml` で設定したパスワード

---

### 3. Realm の作成

Realm は、ユーザー・グループ・クライアントを管理する単位です。Dependency-Track 専用の Realm を作成します。

#### 3.1. Realm の作成

1. 左上の `master` ドロップダウンをクリック
2. `Create Realm` をクリック
3. 以下を入力：
   - **Realm name**: `dtrack`
   - **Enabled**: オン
4. `Create` をクリック

---

### 4. Client の作成

Client は、Dependency-Track を Keycloak に登録するための設定です。

#### 4.1. Client の作成

1. 左メニューの `Clients` をクリック
2. `Create client` をクリック
3. **General Settings**:
   - **Client type**: `OpenID Connect`
   - **Client ID**: `dependency-track`
4. `Next` をクリック

#### 4.2. Capability config

1. **Client authentication**: `Off`（Public Client）
2. **Authorization**: `Off`
3. **Authentication flow**:
   - `Standard flow`: オン
   - `Implicit flow`: オン（Frontend用）
   - `Direct access grants`: オフ
4. `Next` をクリック

#### 4.3. Login settings

1. **Valid redirect URIs**:
   ```
   http://localhost:8080/*
   https://localhost:8080/*
   ```
   **重要**: 本番環境では実際のドメインを指定してください。

2. **Valid post logout redirect URIs**:
   ```
   http://localhost:8080/*
   https://localhost:8080/*
   ```

3. **Web origins**:
   ```
   http://localhost:8080
   https://localhost:8080
   ```

4. `Save` をクリック

#### 4.4. Client Scopes の設定

Groups クレームを ID Token に含めるための設定を行います。

1. `Clients` → `dependency-track` → `Client scopes` タブをクリック
2. `dependency-track-dedicated` をクリック
3. `Add mapper` → `By configuration` をクリック
4. `Group Membership` を選択
5. 以下を入力：
   - **Name**: `groups`
   - **Token Claim Name**: `groups`
   - **Full group path**: オフ
   - **Add to ID token**: オン
   - **Add to access token**: オン
   - **Add to userinfo**: オン
6. `Save` をクリック

---

### 5. Group の作成

Dependency-Track のチーム（権限グループ）に対応する Group を作成します。

#### 5.1. 管理者グループの作成

1. 左メニューの `Groups` をクリック
2. `Create group` をクリック
3. **Name**: `Administrators`
4. `Create` をクリック

#### 5.2. 開発者グループの作成

同様に、以下のグループを作成します：

- `Developers`（開発者用）
- `Security Team`（セキュリティチーム用）
- その他、組織に応じたグループ

**重要**: グループ名は Dependency-Track のチーム名と一致させてください。

---

### 6. User の作成

#### 6.1. ユーザーの作成

1. 左メニューの `Users` をクリック
2. `Create new user` をクリック
3. 以下を入力：
   - **Username**: `testuser`
   - **Email**: `testuser@example.com`
   - **First name**: `Test`
   - **Last name**: `User`
   - **Email verified**: オン
4. `Create` をクリック

#### 6.2. パスワードの設定

1. 作成したユーザーをクリック
2. `Credentials` タブをクリック
3. `Set password` をクリック
4. 以下を入力：
   - **Password**: 任意のパスワード
   - **Password confirmation**: 同じパスワード
   - **Temporary**: オフ（オンにすると、初回ログイン時にパスワード変更を要求）
5. `Save` をクリック

#### 6.3. グループへの追加

1. `Groups` タブをクリック
2. `Join Group` をクリック
3. `Administrators` を選択
4. `Join` をクリック

---

### 7. Dependency-Track での動作確認

#### 7.1. OIDC ログインのテスト

1. ブラウザで Dependency-Track にアクセス：
   ```
   http://localhost:8080
   ```

2. `Login with OpenID` ボタンをクリック

3. Keycloak のログイン画面が表示されるので、先ほど作成したユーザーでログイン：
   - Username: `testuser`
   - Password: 設定したパスワード

4. 初回ログイン時、Dependency-Track へのアクセス許可を求められる場合があります。`Yes` をクリック

5. Dependency-Track にログインできることを確認

#### 7.2. ユーザー自動プロビジョニングの確認

OIDC ログイン後、Dependency-Track にユーザーとチームが自動作成されます。

1. 右上のユーザーアイコン → `Administration` をクリック
2. 左メニューの `Access Management` → `Teams` をクリック
3. `Administrators` チームが作成されていることを確認
4. `Administrators` チームをクリックし、`testuser` がメンバーとして追加されていることを確認

---

## チーム権限の設定

Keycloak のグループと Dependency-Track のチームが同期されたら、各チームに権限を付与します。

### 主要な権限

| 権限 | 説明 | 推奨チーム |
|-----|------|-----------|
| `BOM_UPLOAD` | SBOM のアップロード | Developers, Automation |
| `VIEW_PORTFOLIO` | プロジェクトの閲覧 | 全てのチーム |
| `PORTFOLIO_MANAGEMENT` | プロジェクトの作成・編集 | Developers, Administrators |
| `POLICY_MANAGEMENT` | ポリシーの管理 | Security Team, Administrators |
| `VULNERABILITY_ANALYSIS` | 脆弱性の分析・対応記録 | Security Team, Developers |
| `SYSTEM_CONFIGURATION` | システム設定 | Administrators のみ |

### 権限の付与手順

1. `Administration` → `Access Management` → `Teams` をクリック
2. チーム名（例: `Developers`）をクリック
3. `Permissions` タブをクリック
4. 必要な権限にチェックを入れる
5. `Update Permissions` をクリック

---

## 本番環境への移行

開発環境（localhost）での動作確認が完了したら、本番環境に移行します。

### 1. ドメイン名の設定

`docker-compose.yml` の以下を実際のドメイン名に変更：

```yaml
# API Server
ALPINE_OIDC_ISSUER: "https://keycloak.example.com/realms/dtrack"

# Frontend
API_BASE_URL: "https://dt.example.com:8081"
OIDC_ISSUER: "https://keycloak.example.com/realms/dtrack"

# Keycloak
KC_HOSTNAME: "keycloak.example.com"
KC_HOSTNAME_STRICT: "true"
KC_HOSTNAME_STRICT_HTTPS: "true"
```

### 2. TLS 証明書の設定

#### Keycloak

```yaml
keycloak:
  environment:
    KC_HTTPS_CERTIFICATE_FILE: /opt/keycloak/conf/tls.crt
    KC_HTTPS_CERTIFICATE_KEY_FILE: /opt/keycloak/conf/tls.key
  volumes:
    - ./tls.crt:/opt/keycloak/conf/tls.crt:ro
    - ./tls.key:/opt/keycloak/conf/tls.key:ro
```

#### Dependency-Track

Nginx や Traefik などのリバースプロキシを使用して TLS を終端することを推奨します。

### 3. Keycloak Client の Redirect URI 更新

1. Keycloak Admin Console → `Clients` → `dependency-track` をクリック
2. **Valid redirect URIs** を本番環境の URL に更新：
   ```
   https://dt.example.com/*
   ```
3. **Web origins** も更新：
   ```
   https://dt.example.com
   ```

### 4. データベースの移行

開発環境では Keycloak が組み込み H2 データベースを使用していますが、本番環境では PostgreSQL を使用することを推奨します。

```yaml
keycloak:
  environment:
    KC_DB: postgres
    KC_DB_URL: jdbc:postgresql://postgres:5432/keycloak
    KC_DB_USERNAME: keycloak
    KC_DB_PASSWORD: changeme

postgres:
  environment:
    POSTGRES_DB: dtrack,keycloak  # 複数DBを作成、または別のPostgreSQLインスタンスを使用
```

---

## トラブルシューティング

### Keycloak にアクセスできない

**症状**: `https://localhost:8443` にアクセスできない

**対処**:

1. Keycloak の起動確認：
   ```bash
   docker compose logs keycloak
   ```

2. `Listening on` メッセージが表示されているか確認

3. ブラウザの証明書警告を許可（開発環境のみ）

### OIDC ログインボタンが表示されない

**症状**: Dependency-Track のログイン画面に `Login with OpenID` ボタンが表示されない

**対処**:

1. API Server の環境変数確認：
   ```bash
   docker compose exec apiserver env | grep OIDC
   ```

2. `ALPINE_OIDC_ENABLED=true` になっているか確認

3. API Server を再起動：
   ```bash
   docker compose restart apiserver
   ```

### ログイン後に "Invalid redirect URI" エラー

**症状**: Keycloak でログイン後、エラーが表示される

**対処**:

1. Keycloak の Client 設定を確認
2. **Valid redirect URIs** に正しい URL が登録されているか確認：
   ```
   http://localhost:8080/*
   ```
3. ワイルドカード（`*`）が含まれているか確認

### ユーザーが自動作成されない

**症状**: OIDC ログイン成功するが、Dependency-Track にユーザーが作成されない

**対処**:

1. API Server の環境変数確認：
   ```bash
   docker compose exec apiserver env | grep PROVISIONING
   ```

2. `ALPINE_OIDC_USER_PROVISIONING=true` になっているか確認

3. API Server のログを確認：
   ```bash
   docker compose logs apiserver | grep -i oidc
   ```

### グループが同期されない

**症状**: Keycloak のグループが Dependency-Track のチームとして同期されない

**対処**:

1. Client Scopes の Mapper 確認：
   - Keycloak Admin Console → `Clients` → `dependency-track` → `Client scopes`
   - `dependency-track-dedicated` → `Mappers`
   - `groups` Mapper が存在するか確認

2. Mapper の設定確認：
   - **Token Claim Name**: `groups`
   - **Add to ID token**: オン

3. API Server の環境変数確認：
   ```bash
   docker compose exec apiserver env | grep TEAMS
   ```
   - `ALPINE_OIDC_TEAMS_CLAIM=groups`
   - `ALPINE_OIDC_TEAM_SYNCHRONIZATION=true`

4. ユーザーを一度ログアウトし、再度ログイン

---

## 参考資料

- [Keycloak 公式ドキュメント](https://www.keycloak.org/documentation)
- [Dependency-Track OIDC Configuration](https://docs.dependencytrack.org/getting-started/openidconnect-configuration/)
- [OpenID Connect 仕様](https://openid.net/connect/)

---

## 他の認証プロバイダーとの統合

Keycloak 以外の OIDC プロバイダーも使用できます。

### Microsoft Entra ID（旧 Azure AD）

1. Entra ID でアプリ登録を作成
2. Redirect URI を設定：`http://localhost:8080/*`
3. ID Token に `groups` クレームを追加
4. `docker-compose.yml` の環境変数を更新：
   ```yaml
   ALPINE_OIDC_ISSUER: "https://login.microsoftonline.com/{tenant-id}/v2.0"
   ALPINE_OIDC_CLIENT_ID: "{client-id}"
   ```

### Okta

1. Okta で OIDC アプリケーションを作成
2. Authorization Code Flow を有効化
3. Redirect URI を設定
4. `docker-compose.yml` の環境変数を更新：
   ```yaml
   ALPINE_OIDC_ISSUER: "https://{your-okta-domain}.okta.com"
   ALPINE_OIDC_CLIENT_ID: "{client-id}"
   ```

詳細は各プロバイダーのドキュメントを参照してください。
