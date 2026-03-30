
# DT の API キーの作成


- DT が提供する Web API を利用すると、GHA (CI/CD パイプライン) から SBOM を登録することが出来ます。
- Web API を利用するには、DT で API キーの作成が必要です
- API キーは、DT のチームごと管理されます
- チームには DT の利用権限が設定されます

このドキュメントでは、API キーを作成して、Web API 経由で DT に SBOM を登録する方法を説明します。

## API キーの作成

### 1. チームの作成

1. DT に管理者権限でログイン
2. `Administration` → `Access Management` → `Teams` をクリック
3. `Create Team` をクリック
4. チーム名に `Automation-SSF` を入力

### 2. API キーの作成

1. `Automation-SSF` チームの `API Keys` の [+] ボタンをクリック
2. 生成された API キーをコピーして安全に保管

### 3. チームの権限設定

`Automation-SSF` チームに以下の権限を付与します:

- `BOM_UPLOAD`: SBOM のアップロード
- `PROJECT_CREATION_UPLOAD`: プロジェクトの自動作成
- `PORTFOLIO_MANAGEMENT`: プロジェクトの管理

### 4. 動作確認: API キーを使った SBOM 登録

1. 動作確認用の CycloneDX 形式の SBOM を用意します

   [CycloneDX 公式サンプル](https://github.com/CycloneDX/bom-examples)をダウンロードします。

   ```bash
   # CycloneDX 公式サンプルのダウンロード
   wget https://raw.githubusercontent.com/CycloneDX/bom-examples/refs/heads/master/SBOM/juice-shop/v11.1.2/bom.json
   ```

2. コピーした API キーを使って DT に SBOM を登録します

   以下のコマンドを実行してください。
   ただし、`odt_xxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx` をコピーした API キーで上書きしてください。
   
   ```bash
   # SBOM 登録
   curl -X "POST" "http://localhost:8081/api/v1/bom" \
   -H "X-Api-Key:odt_xxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" \
   -F "autoCreate=true" \
   -F "projectName=juice-shop" \
   -F "projectVersion=1.0" \
   -F "projectTags=gha" \
   -F "bom=@bom.json" -i -v
   ```

3. DT にログインし、Project 一覧に SBOM が登録されていることを確認します

## GitHub Secrets への API キー登録

GHA から DT の Web API を利用するために、GitHub リポジトリにコピーした API キーを登録します。

1. Settings → Secrets and variables → Actions をクリック
2. 以下を登録してください。

- **Name**: `DT_API_KEY`
- **Value**: コピーした API キー