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

`terraform.tfvars.example` を `terraform.tfvars` にコピーしてください。

シンプルな検証する場合であっても、以下の項目の変更は必須です。

```hcl
# terraform.tfvars の変更必須項目

# Application Domain (REQUIRED)
app_domain = "dependency-track.example.com"

# ACM Certificate (REQUIRED)
acm_certificate_arn = "arn:aws:acm:ap-northeast-1:123456789012:certificate/xxxxx"
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

1. Terraform の出力から ALB の DNS 名を取得：

    ```bash
    terraform output alb_dns_name
    ```

2. Route 53 で A レコード（エイリアス）を作成：
    - 名前: `dependency-track.example.com`
    - タイプ: A - IPv4 address
    - エイリアスターゲット: ALB の DNS 名

### 2. Secrets Manager の確認

機密情報は、AWS の Secret Manager で確認できます:

- DB_PASSWORD: DT が利用する DB のパスワード
- GHA_CUSTOM_HEADER: HTTP ヘッダ (`x-ssf-secret-token`) ヘッダの値
- TRIVY_TOKEN: DT の UI 上で設定する Trivy サーバーのトークン

### 3. Cognito ユーザーの作成

AWS Console から Cognito User Pool にアクセスして、ユーザーを作成：

1. Cognito → User pools → ssf-user-pool を選択
2. ユーザ管理 → グループ → 「グループを作成」をクリック
3. グループを作成
3. ユーザー管理 → ユーザー → 「ユーザーを作成」をクリック
4. ユーザーを作成し、ユーザーをグループに追加

### 4. Dependency-Track の初期設定

1. ブラウザで `https://dependency-track.example.com` にアクセス
2. [Dependency-Track 構築手順書](docs/dependency-track-setup.md)を参考に設定

## クリーンアップ

### 基本的な削除方法

```bash
terraform destroy
```

### 完全に AWS 上のリソースを削除する場合

1. OIDC のユーザー (Cognito のユーザープール) の削除:
    
    1. Cognito のユーザープール ID を確認します
        ```bash
        # ユーザープール ID の取得
        terraform output cognito_user_pool_id
        ```

    2. ユーザープール の削除保護を無効化します
        ```bash
        # 削除保護の無効化
        # --user-pool-id の値を指定してください
        aws cognito-idp update-user-pool \
        --user-pool-id ap-northeast-1_xxxxxxxxx \
        --deletion-protection INACTIVE
        ```

2. リソースの削除:
    ```bash
    terraform destroy
    ```

3. 機密情報 (Secret Manager) の強制削除:
    ```bash
    # Secret Manager の即時削除
    aws secretsmanager delete-secret \
      --secret-id ssf/credentials \
      --force-delete-without-recovery
    ```
