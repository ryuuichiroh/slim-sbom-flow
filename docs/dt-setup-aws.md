# AWS を利用したシステム構成

このドキュメントでは、AWS を利用した運用可能なシステム構成を紹介します。

実際にシステムを構築する場合は、
[AWS へデプロイするための Terraform 設定](/terraform/README.md)を参照してください。

## システム構成

以下のようにシステムを構成します。

- 負荷に応じてシステムの性能を調整できるように、アプリケーション、データベース、ストレージを分離します
  - アプリケーションは ECS (Fargate) 上にデプロイします
  - データベースには RDS を利用します
  - DT や Trivy Server の使うストレージとして EFS を利用します
- OIDC 準拠の認証基盤を効率的に運用ができるように Cognito を利用します
- 以下を実現するために ALB を配置します
  - 想定していないクライアントからのシステムの保護 (IP アドレスやカスタムヘッダを使ったアクセス制限)
  - システム負荷に応じた負荷分散、自動スケール
- データベースのパスワードなどの機密情報を集中管理するために Secret Manager を利用します
- システムのデータは、RDS や EFS の機能を用いて自動バックアップします

### システム構成図

```mermaid
graph TB
    subgraph Clients[アクセス元]
        GHA[GitHub Actions]
        User[人間 / 社内拠点]
    end

    subgraph Internet
        R53[Route 53<br/>独自ドメイン]
        DockerHub[Docker Hub / ECR Public<br/>初回イメージ取得用]
    end

    subgraph AWS_Cloud[AWS Account]
        subgraph Security_Identity[Security & Identity]
            COG[Amazon Cognito]
            SM[Secrets Manager]
        end

        subgraph Public_Subnet[Public Subnet - Multi-AZ]
            subgraph ALB[ALB: Application Load Balancer]
                direction TB
                Rule_GHA{優先度1: /api/*<br/>+ Custom Header}
                Rule_API_Browser{優先度2: /api/*<br/>+ Office IP}
                Rule_FE{優先度3: /*<br/>+ Office IP}
                Default[デフォルト:<br/>403 Forbidden]
            end
            NGW[NAT Gateway]
        end

        subgraph Private_Subnet[Private Subnet - Multi-AZ]
            subgraph ECS_Service_BE[ECS Service: Backend]
                subgraph API_Task[API Server Task]
                    API[DT API Server]
                    TRV[Trivy Server]
                    API <-->|localhost:8082| TRV
                end
            end

            subgraph ECS_Service_FE[ECS Service: Frontend]
                FE[DT Frontend]
            end

            subgraph Managed_Storage[Storage]
                RDS[(Amazon RDS<br/>Multi-AZ)]
                EFS[Amazon EFS]
            end

            subgraph VPC_Endpoints[VPC Endpoints - Interface型]
                VPCE_ECR[ECR API/DKR]
                VPCE_SM[Secrets Manager]
                VPCE_CWL[CloudWatch Logs]
            end

            subgraph VPC_Endpoints_GW[VPC Endpoints - Gateway型]
                VPCE_S3[S3<br/>無料]
            end
        end

        ECR[Amazon ECR Private<br/>イメージミラー]
    end

    %% Traffic Flow
    GHA -->|HTTPS /api/* + Secret Header| R53
    User -->|HTTPS /* から開始| R53
    R53 --> ALB

    %% ALB Listener Rules (優先度順)
    ALB --> Rule_GHA
    Rule_GHA -->|Match: GHA API Call| API
    Rule_GHA -->|No Match| Rule_API_Browser
    Rule_API_Browser -->|Match: Browser API Call| API
    Rule_API_Browser -->|No Match| Rule_FE
    Rule_FE -->|Match: Frontend Download| FE
    Rule_FE -->|No Match| Default

    %% OIDC Flow
    FE <-->|User Login / Token| COG
    API <-->|Token Validate| COG

    %% Internal
    FE -->|Authorized API Call| API
    API --> RDS
    API --> EFS

    %% VPC Endpoint Usage
    API_Task -.->|Pull Image| VPCE_ECR
    API_Task -.->|Get Secrets| VPCE_SM
    API_Task -.->|Push Logs| VPCE_CWL
    VPCE_ECR -.->|Get Layers| VPCE_S3
    VPCE_ECR -.->|Access| ECR

    %% NAT Gateway Usage (外部通信のみ)
    TRV -.->|脆弱性DB更新| NGW
    NGW -.-> DockerHub

    %% ECR Image Sync (初回のみ)
    DockerHub -.->|初回: イメージコピー| ECR

    %% Infrastructure
    SM -.->|Inject Secrets| API_Task

    classDef aws fill:#FF9900,color:#fff;
    classDef storage fill:#3F8624,color:#fff;
    classDef logic fill:#fff,stroke:#333,stroke-dasharray: 5 5;
    classDef vpce fill:#8C4FFF,color:#fff;
    classDef external fill:#666,color:#fff;
    class API,FE,ALB,COG,TRV,NGW,ECR aws;
    class RDS,EFS,SM storage;
    class Rule_GHA,Rule_API_Browser,Rule_FE,Default logic;
    class VPCE_ECR,VPCE_SM,VPCE_CWL,VPCE_S3 vpce;
    class R53,DockerHub external;
```

### ALB によるトラフィック制御

- 社内拠点からの通信 (送信元 IP アドレスが Office IP の範囲) であれば DT へルーティング
- 有効なカスタムヘッダを持つ通信であれば DT の API サーバーへルーティング
- それ以外の通信を遮断: 403 Forbidden

## 今後の改善項目

効率的にシステムを運用するために、以下の対応を予定しています

### モニタリング（推奨度：高）
- **CloudWatch Alarms**
  - ECS タスク CPU/メモリ使用率の監視
  - RDS CPU/ストレージ使用率の監視
  - ALB エラー率（5xx）のアラート
- **CloudWatch Logs Insights**
  - ECS タスクログの集約・検索
  - アプリケーションエラーの可視化
- **ALB アクセスログ → S3**
  - トラフィック分析、セキュリティ監査用

### セキュリティ強化（推奨度：中）
- **Security Hub / GuardDuty**
  - セキュリティベストプラクティスのチェック
  - 異常なトラフィック検知
- **VPC Flow Logs**
  - ネットワークトラフィック監査

### コスト最適化（推奨度：中）
- **開発環境**
  - Fargate Spot（最大 70% 割引、タスク停止リスクあり）
  - 夜間・休日の自動停止スクリプト
- **本番環境**
  - Savings Plans / Reserved Capacity の検討
  - Cost Explorer での定期的なコスト分析

### CI/CD パイプライン（推奨度：中）
- **Blue/Green デプロイ**
  - ECS の deployment_controller = CODE_DEPLOY
  - 無停止でバージョン切り替え
