# Dependency-Track on AWS - Terraform Configuration

このディレクトリには、AWS 上に Dependency-Track システムを構築するための Terraform 設定が含まれています。

## 構成概要

```
terraform/
├── main.tf                    # メインの設定ファイル（モジュール呼び出し）
├── provider.tf                # AWS プロバイダー設定
├── variables.tf               # 変数定義
├── outputs.tf                 # 出力定義
└── modules/                   # モジュール
    ├── network/               # VPC, Subnet, Route Table, NAT Gateway
    ├── security/              # Security Groups, IAM, Cognito, Secrets Manager
    ├── data/                  # RDS, EFS
    ├── routing/               # ALB, Target Groups, Listeners
    └── compute/               # ECS Cluster, Task Definitions, Services
```

## 前提条件

1. **AWS CLI 設定**
   ```bash
   aws configure --profile ssf
   ```

2. **Terraform インストール**
   ```bash
   terraform version  # >= 1.0
   ```

3. **必要な AWS リソース（事前作成）**
   - ACM 証明書（ALB 用）
   - Route 53 ホストゾーン（独自ドメイン用）

## デプロイ手順

### 1. 変数の設定

`terraform.tfvars` を作成して、環境に合わせて値を設定：

```hcl
# terraform.tfvars

project_name = "ssf"
region       = "ap-northeast-1"

# ネットワーク設定
vpc_cidr             = "10.0.0.0/16"
availability_zones   = ["ap-northeast-1a", "ap-northeast-1c"]
public_subnet_cidrs  = ["10.0.0.0/20", "10.0.16.0/20"]
private_subnet_cidrs = ["10.0.128.0/20", "10.0.144.0/20"]

# セキュリティ設定
office_ip_cidr = "203.0.113.0/24"  # 社内 IP アドレス範囲に変更

# ACM 証明書（事前に作成）
acm_certificate_arn = "arn:aws:acm:ap-northeast-1:123456789012:certificate/xxxxx"

# データベース設定
db_name           = "dtrack"
db_username       = "dtrack"
db_instance_class = "db.t3.micro"

# コンテナイメージ（ECR Private にコピー推奨）
dependency_track_api_image       = "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/dependency-track/apiserver:4.11"
dependency_track_frontend_image  = "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/dependency-track/frontend:4.11"
trivy_image                      = "123456789012.dkr.ecr.ap-northeast-1.amazonaws.com/trivy:latest"

# タグ
tags = {
  Project     = "ssf"
  ManagedBy   = "Terraform"
  Environment = "production"
}
```

### 2. Terraform 初期化

```bash
terraform init
```

### 3. プラン確認

```bash
terraform plan
```

### 4. デプロイ実行

```bash
terraform apply
```

## デプロイ後の設定

### 1. DNS 設定

Terraform の出力から ALB の DNS 名を取得：

```bash
terraform output alb_dns_name
```

Route 53 で A レコード（エイリアス）を作成：
- 名前: `dependency-track.your-domain.com`
- タイプ: A - IPv4 address
- エイリアスターゲット: ALB の DNS 名

### 2. Secrets Manager の確認

**Terraform が自動生成したシークレット：**

以下のシークレットは `terraform apply` で自動的に生成・設定されます：
- ✅ DB_PASSWORD (RDS)
- ✅ GHA_CUSTOM_HEADER (GitHub Actions 認証)
- ✅ TRIVY_TOKEN (Trivy サーバー)
- ✅ OIDC_CLIENT_SECRET (Cognito)

**追加設定が必要なシークレット（オプション）：**

```bash
# GITHUB_API_KEY を追加する場合（オプション）
CURRENT_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id ssf/credentials \
  --profile ssf \
  --query SecretString \
  --output text)

echo $CURRENT_SECRET | jq '. + {"GITHUB_API_KEY": "your-api-key"}' | \
aws secretsmanager put-secret-value \
  --secret-id ssf/credentials \
  --secret-string file:///dev/stdin \
  --profile ssf
```

詳細は [PASSWORD_MANAGEMENT.md](./PASSWORD_MANAGEMENT.md) を参照してください。

### 3. Cognito ユーザーの作成

AWS Console から Cognito User Pool にアクセスして、ユーザーを作成：

1. Cognito → User pools → 「User pool - gpluu」を選択
2. 「Create user」をクリック
3. メールアドレスとパスワードを設定

### 4. Dependency-Track の初期設定

1. ブラウザで `https://dependency-track.your-domain.com` にアクセス
2. Cognito でログイン
3. 初回ログイン時の管理者パスワードを変更（デフォルト: admin/admin）

## モニタリング設定（推奨）

### CloudWatch Logs

ECS タスクログが自動的に CloudWatch Logs に送信されます：

```bash
aws logs tail /ecs/ssf-api-task --follow --profile ssf
aws logs tail /ecs/ssf-frontend-task --follow --profile ssf
```

### CloudWatch Alarms の作成

```bash
# CPU 使用率アラーム
aws cloudwatch put-metric-alarm \
  --alarm-name ssf-ecs-cpu-high \
  --alarm-description "ECS CPU usage > 80%" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --profile ssf
```

## VPC Endpoint の追加（コスト削減）

NAT Gateway の費用を削減するため、VPC Endpoint を追加することを推奨：

```hcl
# network モジュールに追加
resource "aws_vpc_endpoint" "ecr_api" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.ap-northeast-1.ecr.api"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_1a.id, aws_subnet.private_1c.id]
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "ecr_dkr" {
  vpc_id              = aws_vpc.main.id
  service_name        = "com.amazonaws.ap-northeast-1.ecr.dkr"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = [aws_subnet.private_1a.id, aws_subnet.private_1c.id]
  security_group_ids  = [aws_security_group.vpc_endpoint.id]
  private_dns_enabled = true
}

resource "aws_vpc_endpoint" "s3" {
  vpc_id            = aws_vpc.main.id
  service_name      = "com.amazonaws.ap-northeast-1.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = [aws_route_table.private_1a.id, aws_route_table.private_1c.id]
}
```

## トラブルシューティング

### ECS タスクが起動しない

```bash
# タスクの状態確認
aws ecs describe-tasks \
  --cluster ssf-cluster \
  --tasks $(aws ecs list-tasks --cluster ssf-cluster --query 'taskArns[0]' --output text --profile ssf) \
  --profile ssf
```

### RDS 接続エラー

```bash
# セキュリティグループの確認
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=ssf-sg-rds" \
  --profile ssf
```

### ALB のヘルスチェック失敗

```bash
# ターゲットグループの状態確認
aws elbv2 describe-target-health \
  --target-group-arn $(terraform output -raw alb_target_group_api_arn) \
  --profile ssf
```

## クリーンアップ

リソースを削除する場合：

```bash
terraform destroy
```

**注意:** RDS と EFS のデータは削除されます。必要に応じて事前にバックアップを取得してください。

## 参考資料

- [Dependency-Track 公式ドキュメント](https://docs.dependencytrack.org/)
- [AWS ECS Best Practices](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/intro.html)
- [設計ドキュメント](../docs/dependency-track-setup-aws.md)
