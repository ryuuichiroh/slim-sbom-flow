# AWS へデプロイするための Terraform 設定

1. このディレクトリには、AWS 上に Dependency-Track システムを構築するための Terraform 設定が含まれています。
2. 本ドキュメントでは、デプロイ方法をも示します。

## ディレクトリ構成概要

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

## デプロイ前の準備

1. AWS 利用環境のセットアップ
   1. IAM アカウントの作成
   2. AWS リソースを操作可能な アクセスキーの発行
   2. AWS CLI のセットアップ
      
      以下のコマンドを実行し、発行したアクセスキーを設定します。

      ```bash
      aws configure --profile ssf
      ```

2. Terraform インストール

   公式の[インストール手順](https://developer.hashicorp.com/terraform/install)を参考に、
   Terraform をインストールします。

   念のため、正常にインストールできたか確認します。
   ```bash
   # インストール確認
   terraform version  # >= 1.0
   ```

3. ドメインの取得

4. AWS リソースを事前作成

   - [ACM 証明書 (ALB 用)](#acm-証明書の作成)
   - [Route 53 ホストゾーン (独自ドメイン用)](#route-53-ホストゾーンの作成)

### ACM 証明書の作成

1. AWS Certificate Manager → 証明書をリクエスト
2. ドメイン名を設定

   `example.com` の場合は、以下のように2つ設定:
     - *.example.com
     - example.com

### Route 53 ホストゾーンの作成

1. Route 53 → ホストゾーン → ホストゾーンの作成
2. ドメイン名を設定してホストゾーンを作成
3. AWS Certificate Manager → 証明書を一覧 → 証明書を選択
4. Route 53 でレコードを作成
    - レコードを作成できるようになるまで、少し時間がかかります

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
2. ユーザ管理 → グループ → グループを作成
3. ユーザー管理 → ユーザー → ユーザーを作成
4. ユーザーをグループに追加

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

## コスト削減

### ECR Private へのイメージコピー

`terraform/terraform.tfvars.example` の設定のまま運用すると、
DT などの Docker イメージを AWS にデプロイする場合に以下の課題があります。

- Docker イメージのデータ転送量が多くなり、運用コストが割高になる
- Docker Hub の Rate Limit により、デプロイに失敗する可能性がある
- 利用している Docker Image が、知らない間に更新される可能性がある

そのため、Docker Image を ECR の Private レジストリにコピーして利用することを推奨します。
ECR の Private レジストリを利用すると以下のメリットが得られます。
- VPC Endpoint 経由でイメージプル可能（データ転送料ゼロ）
- Docker Hub Rate Limit 回避
- バージョン固定が容易（意図しない更新を防止）

#### ECR の利用手順

1. ECR のプライベートレジストリを作成
   1. `Elastic Container Registry` → `Private registry` → `Repositories` をクリック
   2. `リポジトリを作成` をクリック
   3. `Repository name` を入力して `Create` をクリック

      レジストリは、以下の `Repository name` で 3 つ作成します。
      - `ssf/dt-apiserver`: DT の API サーバ
      - `ssf/dt-frontend`: DT の Frontend
      - `ssf/trivy`: Trivy Server

2. ローカル環境で、以下のコマンドを実施

   `<account-id>` を、あなたのアカウント ID に置き換えて実行してください。

   ```bash
   # AWS CLI ログイン
   aws ecr get-login-password --region ap-northeast-1 | \
     docker login --username AWS --password-stdin <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com

   # Dependency-Track API Server
   docker pull dependencytrack/apiserver
   docker tag dependencytrack/apiserver \
     <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/ssf/dt-apiserver
   docker push <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/ssf/dt-apiserver

   # Dependency-Track Frontend
   docker pull dependencytrack/frontend
   docker tag dependencytrack/frontend \
     <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/ssf/dt-frontend
   docker push <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/ssf/dt-frontend

   # Trivy (ECR Public から)
   docker pull public.ecr.aws/aquasecurity/trivy
   docker tag public.ecr.aws/aquasecurity/trivy \
     <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/ssf/trivy
   docker push <account-id>.dkr.ecr.ap-northeast-1.amazonaws.com/ssf/trivy
   ```
