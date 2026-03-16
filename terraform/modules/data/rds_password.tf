# すべてのシークレットの自動生成と管理

# RDS データベースパスワード
resource "random_password" "db_password" {
  length           = 32
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?" # PostgreSQL で問題を起こす文字を除外
}

# GitHub Actions カスタムヘッダー（ALB 認証用）
resource "random_password" "gha_custom_header" {
  length  = 64
  special = true
}

# OIDC Client Secret（Cognito から取得、後で設定）
# Cognito User Pool Client の client_secret を使用

# Trivy トークン（オプショナル）
resource "random_password" "trivy_token" {
  length  = 32
  special = false # トークンなので記号不要
}

# Secret Manager にすべてのシークレットを保存
resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = var.secrets_manager_secret_id

  secret_string = jsonencode({
    DB_PASSWORD       = random_password.db_password.result
    GHA_CUSTOM_HEADER = random_password.gha_custom_header.result
    TRIVY_TOKEN       = random_password.trivy_token.result
    GITHUB_API_KEY    = "" # 空文字列（後で手動更新可能）
  })

  lifecycle {
    # 手動で値を更新した場合、Terraform で上書きしない
    ignore_changes = [secret_string]
  }
}
