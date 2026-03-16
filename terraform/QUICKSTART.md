# クイックスタートガイド

このガイドでは、Terraform を使って AWS 上に Dependency-Track システムを最短でデプロイする手順を説明します。

## 前提条件

- ✅ AWS CLI がインストール済み（`aws --version`）
- ✅ Terraform がインストール済み（`terraform --version`）
- ✅ AWS プロファイル `ssf` が設定済み（`aws configure --profile ssf`）
- ✅ Route 53 でドメインのホストゾーンを作成済み
- ✅ ACM で SSL/TLS 証明書を取得済み

## ステップ1: terraform.tfvars の設定

`terraform.tfvars` ファイルを開いて、以下の値を更新してください：

```hcl
# セキュリティ設定（必須）
office_ip_cidr = "YOUR_OFFICE_IP/32"  # 例: "203.0.113.100/32"

# ACM 証明書（確認）
acm_certificate_arn = "arn:aws:acm:..."  # すでに設定済みか確認

# その他は既存の値でOK
```

### 社内 IP アドレスの確認方法

```bash
# 現在のグローバル IP を確認
curl ifconfig.me

# terraform.tfvars に設定
office_ip_cidr = "203.0.113.100/32"  # 上記で確認した IP に変更
```

## ステップ2: Terraform 初期化

```bash
cd terraform
terraform init
```

**期待される出力:**
```
Terraform has been successfully initialized!
```

## ステップ3: 構文チェック

```bash
terraform validate
```

**期待される出力:**
```
Success! The configuration is valid.
```

## ステップ4: デプロイプラン確認（Dry Run）

```bash
terraform plan
```

このコマンドで、実際に作成されるリソースを確認できます。約36個のリソースが表示されます。

**注意:** 既存の AWS リソースと競合がある場合、エラーが表示されます。その場合は README.md を参照してください。

## ステップ5: デプロイ実行

```bash
terraform apply
```

確認プロンプトが表示されたら `yes` と入力してください。

**所要時間:** 約10-15分

## ステップ6: デプロイ後の設定

### 6-1. 自動生成されたシークレットの確認

Terraform は以下のシークレットを自動生成し、Secret Manager に保存しています：

- **DB_PASSWORD**: RDS データベースパスワード（32文字）
- **GHA_CUSTOM_HEADER**: GitHub Actions 認証用カスタムヘッダー（64文字）
- **OIDC_CLIENT_SECRET**: Cognito User Pool Client Secret
- **TRIVY_TOKEN**: Trivy トークン（32文字、オプショナル）
- **GITHUB_API_KEY**: 空文字列（手動設定用）

確認する場合：

```bash
# すべてのシークレットを確認
aws secretsmanager get-secret-value \
  --secret-id ssf/credentials \
  --profile ssf \
  --query SecretString \
  --output text | jq '.'

# GitHub Actions 用のカスタムヘッダーのみ確認
terraform output -raw gha_custom_header
```

**重要:** `lifecycle.ignore_changes` が設定されているため、Secret Manager の値を手動で更新しても、Terraform で上書きされません。

### 6-2. 追加のシークレットの設定（オプション）

TRIVY_TOKEN や GITHUB_API_KEY を追加する場合：

```bash
# 現在の値を取得
CURRENT_SECRET=$(aws secretsmanager get-secret-value \
  --secret-id ssf/credentials \
  --profile ssf \
  --query SecretString \
  --output text)

# 値を更新（DB_PASSWORD は保持しつつ、他の値を追加）
echo $CURRENT_SECRET | jq '. + {"TRIVY_TOKEN": "your-token", "GITHUB_API_KEY": "your-api-key"}' | \
aws secretsmanager put-secret-value \
  --secret-id ssf/credentials \
  --secret-string file:///dev/stdin \
  --profile ssf
```

### 6-3. DNS の設定

Terraform の出力から ALB の DNS 名を取得：

```bash
terraform output alb_dns_name
```

Route 53 で A レコード（エイリアス）を作成：
- **名前:** `dependency-track.your-domain.com`
- **タイプ:** A - IPv4 address
- **エイリアスターゲット:** ALB の DNS 名

### 6-5. ECS タスクの状態確認

ECS タスクが正常に起動しているか確認：

```bash
# タスクの状態確認
aws ecs describe-services \
  --cluster ssf-cluster \
  --services ssf-api-task-service ssf-frontend-task-service \
  --profile ssf \
  --query 'services[*].[serviceName,runningCount,desiredCount]' \
  --output table
```

**注意:** Secret Manager の値を手動で更新した場合のみ、ECS タスクの再起動が必要です：

```bash
# シークレット更新後のみ実行
aws ecs update-service \
  --cluster ssf-cluster \
  --service ssf-api-task-service \
  --force-new-deployment \
  --profile ssf
```

### 6-6. Cognito ユーザーの作成

AWS Console から Cognito User Pool にアクセスして、ユーザーを作成：

1. Cognito → User pools → 「User pool - gpluu」を選択
2. 「Create user」をクリック
3. メールアドレスとパスワードを設定

### 6-7. GitHub Actions の設定

GitHub Actions から Dependency-Track API にアクセスする場合：

1. **GitHub リポジトリの Secrets に登録**
   ```bash
   # カスタムヘッダーを取得
   terraform output -raw gha_custom_header
   ```

   GitHub リポジトリ → Settings → Secrets and variables → Actions → New repository secret
   - Name: `DT_CUSTOM_HEADER`
   - Value: 上記で取得した値

2. **GitHub Actions ワークフローで使用**
   ```yaml
   - name: Upload SBOM to Dependency-Track
     run: |
       curl -X POST https://dependency-track.your-domain.com/api/v1/bom \
         -H "Content-Type: multipart/form-data" \
         -H "X-Api-Key: ${{ secrets.DT_API_KEY }}" \
         -H "x-ssf-secret-token: ${{ secrets.DT_CUSTOM_HEADER }}" \
         -F "project=${{ secrets.DT_PROJECT_UUID }}" \
         -F "bom=@sbom.json"
   ```

## ステップ7: アクセス確認

1. ブラウザで `https://dependency-track.your-domain.com` にアクセス
2. Cognito でログイン
3. Dependency-Track の UI が表示されることを確認

## トラブルシューティング

### ECS タスクが起動しない

```bash
# タスクの状態確認
aws ecs describe-tasks \
  --cluster ssf-cluster \
  --tasks $(aws ecs list-tasks --cluster ssf-cluster --service-name ssf-api-task-service --query 'taskArns[0]' --output text --profile ssf) \
  --profile ssf
```

### CloudWatch Logs でエラー確認

```bash
aws logs tail /ecs/ssf-api-task --follow --profile ssf
```

### ターゲットグループのヘルスチェック失敗

```bash
# ターゲットの状態確認
terraform output alb_target_group_api_arn | xargs -I {} \
  aws elbv2 describe-target-health --target-group-arn {} --profile ssf
```

## リソースの削除

テスト環境を削除する場合：

```bash
terraform destroy
```

**注意:** RDS と EFS のデータは削除されます。事前にバックアップを取得してください。

## 次のステップ

- [ ] VPC Endpoint を追加してコスト削減（README.md 参照）
- [ ] CloudWatch Alarms を設定
- [ ] RDS のバックアップ設定を確認
- [ ] ECR Private にイメージをコピー（本番環境推奨）
- [ ] モニタリングダッシュボードの作成

## 参考資料

- [詳細ドキュメント](./README.md)
- [アーキテクチャ設計](../docs/dependency-track-setup-aws.md)
- [Dependency-Track 公式ドキュメント](https://docs.dependencytrack.org/)
