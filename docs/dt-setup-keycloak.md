# DT と KeyCloak の連携手順書

このドキュメントでは、簡易的な検証のために DT と KeyCloak を連携させる方法を説明します。

## 注意

簡易的な検証環境は
- 開発モード (`start-dev` コマンド) で起動しており、運用フェーズで必要な設定をしていません
- システムの負荷に応じた柔軟な調整はできません。全てのアプリ・サービスを一つのマシンで動作させます

## 1. 事前準備

### クライアント端末での HOST 設定

自分の端末上にシステムを構築している場合 (`docker-compose/http/docker-compose.yaml` を利用している場合)、
hosts ファイルの設定が必要です。

`docker-compose/http/docker-compose.yaml` では、KeyCloak のアドレスに `keycloak.local` を指定しています。
そのため、hosts ファイルで `keycloak.local` に KeyCloak の IP アドレスを対応させます。

#### Windows の場合

1. `C:\windows\system32\drivers\etc\hosts` を管理者権限で開きます
2. ファイルの最後の行に `127.0.0.1  keycloak.local` を追加します
3. 上書き保存します。

## 2. Keycloak への管理者ログイン

ブラウザで、以下の URL にアクセスします
- 自分の端末上にシステムを構築している場合: http://keycloak.local:8083
- 他の端末からシステムにアクセスする場合: https://{{ システムの IP アドレス }}:8443

デフォルトの管理者アカウントは以下の通りです。
- Username: `admin`
- Password: `admin`

## 3. Realm の作成

Realm は、ユーザー・グループ・クライアントを管理する単位です。Dependency-Track 専用の Realm を作成します。

1. 左上の `master` ドロップダウンをクリック
2. `Create Realm` をクリック
3. 以下を入力：
   - **Realm name**: `dtrack`
   - **Enabled**: オン
4. `Create` をクリック

## 4. Client の作成

Client は、Dependency-Track を Keycloak に登録するための設定です。

### 4.1. Client の作成

1. 左メニューの `Clients` をクリック
2. `Create client` をクリック
3. **General Settings**:
   - **Client type**: `OpenID Connect`
   - **Client ID**: `dependency-track`
4. `Next` をクリック

### 4.2. Capability config

1. **Client authentication**: `Off`（Public Client）
2. **Authorization**: `Off`
3. **Authentication flow**:
   - `Standard flow`: オン
   - `Direct access grants`: オフ
4. `Next` をクリック

### 4.3. Login settings

1. 以下を入力:

   注意: 他の端末上にシステムが構築されている場合は、`localhost` をシステムの IP アドレスに置換してください
   - **Root URL**: `http://localhost:8080`
   - **Home URL**: `http://localhost:8080`
   - **Valid redirect URIs**: `http://localhost:8080/*`
   - **Valid post logout redirect URIs**: `http://localhost:8080/*`
   - **Web origins**: `http://localhost:8080`
2. `Save` をクリック

### 4.4. Client Scopes の設定

Groups クレームを ID Token に含めるための設定を行います。

1. `Clients` → `dependency-track` → `Client scopes` タブをクリック
2. `dependency-track-dedicated` をクリック
3. `Configure a new mapper` をクリック
4. `Group Membership` を選択
5. 以下を入力：
   - **Name**: `groups`
   - **Token Claim Name**: `groups`
   - **Full group path**: オフ
   - **Add to ID token**: オン
   - **Add to access token**: オン
   - **Add to userinfo**: オン
6. `Save` をクリック

## 5. Group の作成

Dependency-Track のチーム（権限グループ）に対応する Group を作成します。

1. 左メニューの `Groups` をクリック
2. `Create group` をクリック
3. **Name**: `dtrack-users`
4. `Create` をクリック

## 6. User の作成

DT にログインできるユーザーを作成します。

### 6.1. ユーザーの作成

1. 左メニューの `Users` をクリック
2. `Create new user` をクリック
3. 以下を入力：
   - **Username**: `testuser`
   - **Email**: `testuser@example.com`
   - **First name**: `Test`
   - **Last name**: `User`
   - **Email verified**: オン
4. `Create` をクリック

### 6.2. パスワードの設定

1. 作成したユーザーをクリック
2. `Credentials` タブをクリック
3. `Set password` をクリック
4. 以下を入力：
   - **Password**: 任意のパスワード
   - **Password confirmation**: 同じパスワード
   - **Temporary**: オフ
5. `Save` をクリック

### 6.3. グループへの追加

1. `Groups` タブをクリック
2. `Join Group` をクリック
3. `dtrack-users` を選択
4. `Join` をクリック

### 6.4 KeyCloak でのユーザー認証設定の確認

以下の URL にブラウザでアクセスし、作成したユーザーで KeyCloak への認証に成功することを確認します。

- 自分の端末上にシステムを構築している場合: http://keycloak.local:8083/realms/dtrack/account
- 他の端末からシステムにアクセスする場合: https://{{ システムの IP アドレス }}:8443/realms/dtrack/account

## 7. Dependency-Track での動作確認

KeyCloak で作成したユーザーで DT にログインするための設定をします。

### 7.1 OIDC 認証設定

1. DT に管理者ログイン
2. Administration → Access Management → OpenID Connect Groups をクリック
3. keycloak で作成したグループ名と同じグループ (`dtrack-users`) を登録
4. 作成したグループに Teams を紐づける
    - 動作確認では、あらかじめ DT に用意されている Team: `Portfolio Managers` を紐づけます

### 7.2. OIDC ログインのテスト

1. ブラウザで Dependency-Track にアクセス
   - 自分の端末上にシステムを構築している場合: http://localhost:8080
   - 他の端末からシステムにアクセスする場合: https://{{ システムの IP アドレス }}:8080

2. `Login with OpenID` ボタンをクリック

3. Keycloak のログイン画面が表示されるので、KeyCloak で作成したユーザーでログイン
   - Username: `testuser`
   - Password: 設定したパスワード

4. Dependency-Track にユーザーでログインできることを確認
