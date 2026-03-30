# DT の通知設定

DT に SBOM が登録された場合や、新しい脆弱性が検出されたときに E メールや Slack で通知できます。
JIRA に脆弱性対応チケットを作成することもできます。

このドキュメントでは、検証用に Gmail を使った通知の方法を説明します。

## 注意

- タグを使った通知の制限がうまく機能しない場合、既知の制限や障害ではないかインターネットで検索してください
- この文書で示す手順は v4.14.0 で検証済みです

## Gmail の通知設定

### 1. Gmail のアプリパスワードの作成

- DT から Gmail を使うためには、Gmail のアプリパスワードが必要です
- [Sign in with app passwords](https://support.google.com/mail/answer/185833?hl=en) を参考にしてアプリパスワードを作成してください
- ブラウザに表示されるアプリパスワードにはスペースが含まれますが、利用するときはスペースは除外してください
  - `xxxx xxxx xxxx xxxx` → `xxxxxxxxxxxxxxxx`

### 2. DT でのメール設定

1. DT に管理者ログイン
2. `Administration` → `Configuration` → `Email` をクリック
3. 以下を設定
   - `From email address`: あなたの Gmail アドレス (xxxxxx@gmail.com)
   - `SMTP server`: `smtp.gmail.com`
   - `SMTP server port`: `587`
   - `SMTP username`: あなたの Gmail アドレス (xxxxxx@gmail.com)
   - `SMTP password`: 作成したアプリパスワード
   - `Enable SSL/TLS encryption`: ON
   - `Trust the certificate provided by the SMTP server`: ON
4. `Update` をクリック

### 3. DT でのメール通知設定

1. DT に管理者ログイン
2. `Administrator` → `Configuration` → `Alerts` をクリック
3. `Create Alert` をクリック
4. 以下を設定
   - `Name`: `email-test`
   - `Publisher`: `Email`
5. `Create` をクリック
6. 作成された `email-test` をクリックし、以下を設定
   - `Enabled`: ON
   - `Destination`: 受信できる任意の Email アドレス (xxxxxx@yahoo.co.jp)
   - `Group`: [`PROJECT_AUDIT_CHANGE`]
7. `Limit To` の `Limit to tags` に `gha` を登録
8. `Submit` をクリック

### 4. `PROJECT_AUDIT_CHANGE` イベント発生時の E メール通知の確認

1. [API キーのセットアップ手順](dt-setup-apikey.md)を参考に "juice-shop" のプロジェクトを DT に登録
   - プロジェクトの TAG に `gha` を付与
2. DT にログインし、`Projects` 画面の "juice-shop" のリンクを開く
3. `Audito Vulnerabilities` のタブをクリックし、任意の脆弱性の `>` をクリックする
   - 各 `Component` のリンクではありません
   - juice-shop" プロジェクトの脆弱性が表示されない場合、トラブルシューティングを参照してください
4. `Analysis` を `Resolved` に設定する
5. 設定した通知先の Email アドレスにメールが届くことを確認

## トラブルシューティング

### juice-shop" プロジェクトで脆弱性が検出されていない場合

1. Trivy の有効化手順を確認
2. `Audito Vulnerabilities` タブに表示されている `Reanalyze` をクリック
3. 少し待ってから、再度、`Audito Vulnerabilities` タブを確認する