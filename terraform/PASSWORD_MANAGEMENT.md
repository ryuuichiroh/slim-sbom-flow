# シークレット管理の仕組み

## 概要

Terraform はすべてのシークレット（パスワード、トークン、認証ヘッダー）を自動生成し、セキュアに管理しています。

## 自動生成と保存

### 1. すべてのシークレットの自動生成

```hcl
# modules/data/rds_password.tf

# RDS データベースパスワード
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# GitHub Actions カスタムヘッダー（ALB 認証用）
resource "random_password" "gha_custom_header" {
  length  = 64
  special = true
}

# Trivy トークン
resource "random_password" "trivy_token" {
  length  = 32
  special = false  # トークンなので記号不要
}
```

**生成されるシークレット：**
- **DB_PASSWORD**: 32文字（PostgreSQL で問題を起こす文字を除外）
- **GHA_CUSTOM_HEADER**: 64文字（GitHub Actions 認証用）
- **TRIVY_TOKEN**: 32文字（英数字のみ）
- **OIDC_CLIENT_SECRET**: Cognito から自動生成

### 2. RDS への適用

```hcl
# modules/data/rds.tf
resource "aws_db_instance" "main" {
  username = "ssf"
  password = random_password.db_password.result

  lifecycle {
    ignore_changes = [password]  # 後から変更されても上書きしない
  }
}
```

### 3. Secret Manager への保存

```hcl
# modules/data/rds_password.tf
resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = var.secrets_manager_secret_id

  secret_string = jsonencode({
    DB_PASSWORD        = random_password.db_password.result
    GHA_CUSTOM_HEADER  = random_password.gha_custom_header.result
    TRIVY_TOKEN        = random_password.trivy_token.result
    OIDC_CLIENT_SECRET = var.cognito_client_secret
    GITHUB_API_KEY     = ""  # 空文字列（手動設定用）
  })

  lifecycle {
    ignore_changes = [secret_string]  # 手動更新を許可
  }
}
```

**各シークレットの用途：**
- **DB_PASSWORD**: RDS への接続、ECS タスクで使用
- **GHA_CUSTOM_HEADER**: ALB リスナールールで GitHub Actions を認証
- **TRIVY_TOKEN**: Trivy サーバーの認証（オプショナル）
- **OIDC_CLIENT_SECRET**: Dependency-Track の OIDC 認証（Cognito）
- **GITHUB_API_KEY**: GitHub API 呼び出し用（手動設定）

## セキュリティ上の利点

### ✅ 安全な点

1. **パスワードがコードに含まれない**
   - `terraform.tfvars` にパスワードを書く必要がない
   - Git にパスワードがコミットされない

2. **State ファイルの管理が不要**
   - `random_password` はランダムに生成
   - 実際のパスワードは State ファイルに保存されるが、`ignore_changes` で保護

3. **手動更新が可能**
   - `lifecycle.ignore_changes` により、Secret Manager の値を手動で更新しても Terraform で上書きされない

### ⚠️ 注意点

1. **State ファイルにパスワードが保存される**
   - Terraform の state ファイルには生成されたパスワードが含まれる
   - State ファイルへのアクセスを制限する必要がある

2. **初回デプロイ後の変更**
   - 初回デプロイ後、パスワードを変更する場合：
     1. Secret Manager で手動更新
     2. RDS でパスワード変更
     3. ECS タスクを再起動

## デプロイフロー

### 初回デプロイ

```bash
terraform apply
```

**自動実行される処理：**

1. **Cognito User Pool Client** が作成され、client_secret が生成
2. **random_password** が各シークレットを生成
   - DB_PASSWORD (32文字)
   - GHA_CUSTOM_HEADER (64文字)
   - TRIVY_TOKEN (32文字)
3. **Secret Manager** にすべてのシークレットが保存
4. **RDS インスタンス** が作成（DB_PASSWORD 使用）
5. **ALB リスナールール** で GHA_CUSTOM_HEADER が設定
6. **ECS タスク** が起動し、Secret Manager からシークレットを取得

**結果:** すべて自動的に動作し、ECS タスクは正常に起動します！

### パスワード変更（本番運用時）

```bash
# 1. 新しいパスワードを生成
NEW_PASSWORD=$(openssl rand -base64 24)

# 2. Secret Manager を更新
aws secretsmanager put-secret-value \
  --secret-id ssf/credentials \
  --secret-string "{\"DB_PASSWORD\":\"$NEW_PASSWORD\",\"TRIVY_TOKEN\":\"\",\"GITHUB_API_KEY\":\"\"}" \
  --profile ssf

# 3. RDS パスワードを更新
aws rds modify-db-instance \
  --db-instance-identifier ssf-db \
  --master-user-password "$NEW_PASSWORD" \
  --apply-immediately \
  --profile ssf

# 4. ECS タスクを再起動
aws ecs update-service \
  --cluster ssf-cluster \
  --service ssf-api-task-service \
  --force-new-deployment \
  --profile ssf
```

## よくある質問

### Q1: パスワードを確認するには？

```bash
aws secretsmanager get-secret-value \
  --secret-id ssf/credentials \
  --profile ssf \
  --query SecretString \
  --output text | jq -r '.DB_PASSWORD'
```

### Q2: Terraform apply を実行するとパスワードが変わる？

**A:** いいえ、変わりません。

- `lifecycle.ignore_changes` が設定されているため
- 初回作成時のみパスワードが生成され、以降は変更されない

### Q3: Secret Manager の値を手動で変更したら？

**A:** Terraform で上書きされません。

- `lifecycle.ignore_changes = [secret_string]` により保護
- 手動更新が完全に可能

### Q4: State ファイルが漏洩したら？

**A:** パスワードを即座に変更してください。

State ファイルにはパスワードが含まれるため：
1. State ファイルへのアクセスを制限（S3 バックエンド + 暗号化推奨）
2. 漏洩が疑われる場合は、上記の「パスワード変更」手順を実行

### Q5: より安全な方法は？

以下の選択肢があります：

1. **AWS Secrets Manager のローテーション機能を使用**
   ```hcl
   resource "aws_secretsmanager_secret_rotation" "credentials" {
     secret_id           = aws_secretsmanager_secret.credentials.id
     rotation_lambda_arn = aws_lambda_function.rotate_secret.arn

     rotation_rules {
       automatically_after_days = 30
     }
   }
   ```

2. **RDS IAM 認証を使用**
   - パスワード不要で認証
   - より安全だが、設定が複雑

## まとめ

現在の実装は以下のバランスを取っています：

- ✅ **セキュリティ**: パスワードはコードに含まれず、自動生成
- ✅ **利便性**: 初回デプロイで自動的にセットアップ
- ✅ **柔軟性**: 手動更新が可能
- ⚠️ **制限**: State ファイルの管理が必要

本番環境では、S3 バックエンド + 暗号化を強く推奨します。
