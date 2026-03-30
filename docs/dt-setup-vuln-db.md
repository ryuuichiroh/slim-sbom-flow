# DT - 脆弱性データベースの連携設定

Dependency-Track は複数の脆弱性データベースをサポートしています。

## 利用可能な脆弱性データベース

| データベース | 提供元 | 説明 |
|------------|-------|------|
| GitHub Advisories | GitHub | GitHub Advisory Database |
| OSV | Google | Open Source Vulnerabilities |
| OSS Index | Sonatype | Sonatype OSS Index |
| NVD | NIST | National Vulnerability Database |

脆弱性データベースごとに登録されている脆弱性は異なります。
プロジェクトの特性に合わせて、適切な脆弱性データベースを利用してください。

## GitHub Advisories の設定手順

### 1. GitHub での PAT の取得

1. GitHub にサインインし、ユーザーメニューを表示します
2. `Settings` → `Developer settings` → `Personal access tokens` → `Tokens (classic)` をクリックします
3. **Note** にトークンの用途 (`for-Dependency-Track` など) を入力し、`Generate token` をクリックし、PAT を取得します

### 2. DT での GitHub Advisories の有効化

1. DT にログインします
2. `Administration` → `Vulnerability Sources` → `GitHub Advisories` をクリックします
3. 以下の設定をします:
   - **Enable GitHub Advisory mirroring**: 有効
   - **Enable vulnerability alias synchronization**: 有効
   - **Personal Access Token**: GitHub で取得した PAT
4. `Update` をクリックします

## OSV の設定手順

DT では、OSV の利用はプレビュー機能です。
Go や Rust などのプログラミング言語を使うプロジェクトがある場合などに利用するといいでしょう。

### DT での OSV の有効化

1. DT にログインします
2. `Administration` → `Vulnerability Sources` → `Google OSV Advisories (Beta)` をクリックします
3. 以下の設定をします:
   - **Ecosystems**: `go` など1つ以上選択してください
   - **Select ecosystem to enable Google OSV Advisory mirroring**: 有効
   - **Enable vulnerability alias synchronization**: 無効 (推奨)
4. `Update` をクリックします

## OSS Index の設定手順

### 1. OSS Index の API Token の取得

1. [Sonatype OSS Index](https://ossindex.sonatype.org/) に Sign-up します
2. OSS Index に Sign-in します
3. `User Settings` を開き、`API Token` を取得します

### 2. DT での OSS Index の連携情報の更新

1. DT にログインします
2. `Administration` → `Analyzers` → `Sonatype OSS Index` をクリックします
3. 以下を設定します:
   - **Registered email address**: OSS Index の Sign-in で利用する E-mail アドレス
   - **API token**: OSS Index で取得した API トークン
4. `Update` をクリックします

## NVD の設定手順

### 1. NVD の API キーの取得

1. [NVD の API キーのリクエストページ](https://nvd.nist.gov/developers/request-an-api-key)を表示します
2. E-mail アドレスを入力し、API キーをリクエストします
3. NVD からのメールを受信します
4. 受信したメールに記載されている URL にアクセスし、UUID を入力して `Confirm` をクリックします
5. API キーが生成されるまで待機し、`Your API Key` の欄に表示されている値をコピーします

### 2. DT での NVD の連携情報の更新

1. DT にログインします
2. `Administration` → `Vulnerability Sources` → `National Vulnerability Database` をクリックします
3. 以下を設定します:
   - **Enable mirroring via API**: 有効
   - **Additionally downloaded feeds**: 有効
   - **API Key**: NVD で取得した API キー
4. `Update` をクリックします
