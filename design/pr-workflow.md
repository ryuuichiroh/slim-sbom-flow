# PR ワークフロー設計書

**作成日**: 2026-03-22
**ステータス**: 承認済み
**関連ドキュメント**: DEV-GHA-PR.md, DESIGN-DECISION-POINTS.md, README.md

---

## 1. 概要

PR 作成時に自動実行される GitHub Actions ワークフローの設計書です。以下の 3 種類のワークフローを提供します。

| # | ワークフロー | 対象 | SBOM 生成 | 脆弱性スキャン |
|---|---|---|---|---|
| 1 | Syft + Grype | パッケージマネージャあり | Syft | Grype |
| 2 | Trivy | パッケージマネージャあり | Trivy | Trivy |
| 3 | ScanCode + Bear + Agent Skills | C/C++（パッケージマネージャなし） | Agent Skills | Agent Skills |

各ワークフローは独立したファイルとして提供し、利用者がプロジェクトに合ったものをコピーして使います（DESIGN-DECISION-POINTS.md 判断1-2）。

---

## 2. PR コメント出力項目

全ワークフロー共通で、以下を PR コメントとして投稿します。

### 2.1 脆弱性サマリ

SBOM から検出された脆弱性をレベルごとに集計して表示します。

```markdown
## 脆弱性サマリ

| レベル | 件数 |
|---|---|
| Critical | 0 |
| High | 2 |
| Medium | 5 |
| Low | 3 |

詳細は[脆弱性レポート](リンク)を参照してください。
```

### 2.2 OSS 差分

ベースライン SBOM と比較した OSS の差分を表示します。

```markdown
## OSS 差分

ベースラインバージョン: 1.0.0

### 追加された OSS (3件)
| パッケージ | バージョン | ライセンス |
|---|---|---|
| axios | 1.6.0 | MIT |
| lodash | 4.17.21 | MIT |
| express | 4.18.2 | MIT |

### 更新された OSS (1件)
| パッケージ | 変更前 | 変更後 | ライセンス |
|---|---|---|---|
| react | 18.2.0 | 18.3.0 | MIT |

### 削除された OSS (1件)
| パッケージ | バージョン | ライセンス |
|---|---|---|
| moment | 2.29.4 | MIT |
```

ベースラインバージョンが未設定（`pre_version` なし）の場合は、差分比較をスキップし「新規プロジェクト（ベースラインなし）」と表示します。

### 2.3 要レビュー OSS の警告

差分に含まれる OSS が `config/review-required-oss.yml` に該当する場合、警告を表示します。

```markdown
## :warning: 要レビュー OSS が検出されました

| パッケージ | 理由 | マッチ条件 |
|---|---|---|
| axios | セキュリティ懸念 | パッケージ名 |
| some-gpl-lib | コピーレフトライセンス | ライセンス (GPL-3.0) |
```

### 2.4 脆弱性レポートへのリンク

脆弱性の詳細レポート（HTML 形式）を zip で GitHub Artifact にアップロードし、そのリンクを PR コメントに含めます。

---

## 3. 設定ファイル

### 3.1 プロジェクト設定: `config/ssf.yml`

```yaml
# slim-sbom-flow プロジェクト設定
project_name: "my-app"       # オプション。未指定時は生成した SBOM の metadata.component.name を使用
pre_version: "1.0.0"         # 比較対象の DT プロジェクトバージョン
                             # 未指定の場合は差分比較をスキップ（全て新規扱い）
```

- `project_name` はオプション。未指定の場合、SBOM 生成後に `metadata.component.name` から取得します
- `pre_version` は新バージョンをリリースして DT に登録した後に更新します
- ファイルが存在しない、または `pre_version` が未指定の場合は差分なし（全て新規）

### 3.2 要レビュー OSS 定義: `config/review-required-oss.yml`

DESIGN-DECISION-POINTS.md 判断2-1, 2-2 に基づきます。

```yaml
version: "1.0"

packages:
  - name: "axios"
    reason: "セキュリティ懸念"
  - name: "spring-core"
    group: "org.springframework"
    reason: "ビジネスクリティカル"

licenses:
  - id: "GPL-3.0"
    reason: "コピーレフトライセンス"
  - id: "AGPL-3.0"
    reason: "強いコピーレフトライセンス"
```

優先順位: プロジェクト側の config > 組織デフォルトの config（フォーク版）

---

## 4. ワークフロー共通設計

### 4.1 トリガー

```yaml
on:
  pull_request:
    types: [opened, synchronize, reopened]
```

### 4.2 共通 secrets / vars

```yaml
secrets:
  DT_API_KEY:
    description: 'Dependency-Track API key'
    required: false
  SSF_SECRET_TOKEN:
    description: 'ALB routing token (x-ssf-secret-token header)'
    required: false
  COPILOT_PAT:
    description: 'Copilot Requests 権限付き PAT (ScanCode ワークフローのみ)'
    required: false
vars:
  DT_BASE_URL:
    description: 'Dependency-Track base URL'
```

- Node.js は v24（最新 LTS）を固定で使用
- `DT_BASE_URL` は Variables（秘匿不要）
- `DT_API_KEY` / `SSF_SECRET_TOKEN` は Secrets
- `COPILOT_PAT` は ScanCode + Bear + Agent Skills ワークフローでのみ使用（Copilot Requests 権限付き PAT）
- `pre_version` が設定されている場合、DT 関連の secrets/vars は必須（未設定ならエラー）

### 4.3 共通処理フロー

**Syft + Grype / Trivy ワークフロー:**

```
 1. リポジトリのチェックアウト
 2. 設定ファイルの読み込み (config/ssf.yml)
 3. SBOM 生成 ← ワークフローごとに異なる
 4. 脆弱性スキャン ← ワークフローごとに異なる
 5. 脆弱性レポート生成 (HTML)
 6. ベースライン SBOM の取得 (DT から、pre_version 指定時。失敗時はエラー)
 7. OSS 差分検出
 8. 要レビュー OSS の判定
 9. PR コメント投稿
10. Artifact アップロード (SBOM, 差分結果, 脆弱性レポート HTML の zip)
```

**ScanCode + Bear + Agent Skills ワークフロー:**

```
 1. リポジトリのチェックアウト
 2. 設定ファイルの読み込み (config/ssf.yml)
 3. ベースライン SBOM の取得 (DT から、pre_version 指定時。失敗時はエラー)
 4. Bear でリンク情報収集
 5. ScanCode でライセンス・著作権情報抽出
 6. Agent Skills で SBOM 生成 (ベースライン SBOM + Bear + ScanCode の結果を入力)
 7. OSS 差分検出
 8. 要レビュー OSS の判定
 9. PR コメント投稿 (OSS 変更情報のみ、脆弱性はバージョン特定時のみ)
10. Artifact アップロード (SBOM, 差分結果の zip)
```

### 4.4 Artifact 構成

```
sbom-pr-{PR番号}/
  sbom-current.json          # 現在の SBOM (CycloneDX JSON)
  diff-result.json           # OSS 差分結果
  vulnerability-report.html  # 脆弱性レポート (HTML)
```

- zip にまとめて Artifact としてアップロード
- 保持期間: 90 日

---

## 5. ワークフロー別設計

### 5.1 Syft + Grype ワークフロー

**ファイル名**: `.github/workflows/pr-sbom-check-syft.yml`
**対象**: パッケージマネージャを利用するプロジェクト（NPM, Maven, Gradle, pip 等）

#### SBOM 生成

```yaml
- name: Install Syft
  uses: anchore/sbom-action/download-syft@v0

- name: Generate SBOM
  run: syft . -o cyclonedx-json=sbom-current.json
```

#### 脆弱性スキャン

```yaml
- name: Install Grype
  uses: anchore/grype/download-grype@v0

- name: Scan vulnerabilities
  run: grype sbom:sbom-current.json -o json > vulnerability-result.json
```

#### 脆弱性レポート (HTML)

Grype の公式テンプレート機能を使用します。

```yaml
- name: Generate HTML vulnerability report
  run: |
    grype sbom:sbom-current.json -o template -t /path/to/html.tmpl > vulnerability-report.html
```

テンプレートは [Grype 公式テンプレート](https://github.com/anchore/grype/tree/main/templates) を使用するか、 [grype#724](https://github.com/anchore/grype/issues/724#issuecomment-1139563814) のアプローチを参考にします。公式テンプレートで不足する場合は TypeScript で JSON → HTML 変換スクリプトを作成します。

### 5.2 Trivy ワークフロー

**ファイル名**: `.github/workflows/pr-sbom-check-trivy.yml`
**対象**: パッケージマネージャを利用するプロジェクト

#### SBOM 生成

```yaml
- name: Generate SBOM with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    format: 'cyclonedx'
    output: 'sbom-current.json'
```

#### 脆弱性スキャン

```yaml
- name: Scan vulnerabilities with Trivy
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    format: 'json'
    output: 'vulnerability-result.json'
```

#### 脆弱性レポート (HTML)

Trivy の HTML テンプレート機能を使用します。

```yaml
- name: Generate HTML vulnerability report
  uses: aquasecurity/trivy-action@master
  with:
    scan-type: 'fs'
    format: 'template'
    template: '@/contrib/html.tpl'
    output: 'vulnerability-report.html'
```

### 5.3 ScanCode + Bear + Agent Skills ワークフロー

**ファイル名**: `.github/workflows/pr-sbom-check-scancode.yml`
**対象**: パッケージマネージャを利用しない C/C++ プロジェクト

#### 処理フロー

```
1. ベースライン SBOM を DT から取得（pre_version 指定時）
2. Bear でビルドを実行し、リンク情報を収集
3. ScanCode Toolkit でライセンス・著作権情報を抽出
4. Agent Skills (LLM) でベースライン SBOM + Bear + ScanCode の結果を統合し、SBOM を生成
5. SBOM 差分検出
6. 変更のあった OSS 情報を PR にコメント
```

**LLM によるバージョン特定の制約**:
- Bear / ScanCode ではバージョン情報を確実に取得できない
- LLM でもバージョンの正確な推定は困難
- ベースライン SBOM があれば、前バージョンの確定情報（バージョン、PURL、ライセンス等）を引き継いで精度を向上できる
- バージョンが特定できない OSS については脆弱性スキャンは実施しない
- PR コメントには OSS の変更情報（追加・削除）のみ表示し、脆弱性サマリは「バージョン未特定のため省略」とする

#### Bear によるリンク情報収集

```yaml
- name: Install Bear
  run: sudo apt-get install -y bear

- name: Build with Bear
  run: bear -- make
  # compile_commands.json が生成される

- name: Extract link information
  run: |
    # compile_commands.json からリンクされるライブラリを抽出
    node scripts/extract-link-info.js compile_commands.json > link-info.json
```

#### ScanCode によるスキャン

```yaml
- name: Install ScanCode Toolkit
  run: |
    pip install scancode-toolkit

- name: Run ScanCode
  run: |
    scancode --license --copyright --package --json-pp scancode-result.json .
```

#### Agent Skills による SBOM 生成

GitHub Copilot CLI と `.github/skills/` に定義した Skill を使用して SBOM を生成します。

**Skill ファイル**: `.github/skills/generate-sbom.md`

Bear のリンク情報、ScanCode の結果、およびベースライン SBOM（存在する場合）を入力として、CycloneDX 形式の SBOM を生成するプロンプトを定義します。

```yaml
- name: Install Copilot CLI
  run: npm install -g @github/copilot

- name: Generate SBOM with Agent Skills
  env:
    COPILOT_GITHUB_TOKEN: ${{ secrets.COPILOT_PAT }}
  run: |
    copilot -p "link-info.json, scancode-result.json, previous-sbom.json を読み込み、
    .github/skills/generate-sbom.md の指示に従って CycloneDX SBOM を sbom-current.json に生成してください" \
    --allow-tool=read --allow-tool=write --no-ask-user
```

#### 実行時間に関する注意

ScanCode はプロジェクト規模によって実行時間が大きく変わります（10分〜1時間超）。

- **基本方針**: PR ごとに毎回実行（リリース直前の意図しない OSS 混入を防ぐ）
- **代替案（実行時間が問題になる場合）**:
  - ローカル環境で ScanCode + Bear を実行
  - 結果を `workflow_dispatch` で手動トリガーしてワークフローに渡す
  - この場合のワークフローは、SBOM 生成済みの結果を受け取り、差分検出・コメント投稿のみ実行

---

## 6. TypeScript スクリプト設計

ワークフローから呼び出す TypeScript スクリプトの一覧です。

### 6.1 スクリプト一覧

| スクリプト | 用途 | 入力 | 出力 |
|---|---|---|---|
| `config-reader.ts` | ssf.yml の読み込み | `config/ssf.yml` | project_name, pre_version |
| `dt-client.ts` | DT API クライアント | project_name, version | SBOM (JSON) |
| `diff-checker.ts` | SBOM 差分検出 | current SBOM, previous SBOM | diff-result.json |
| `review-checker.ts` | 要レビュー OSS 判定 | diff-result, review-required-oss.yml | 判定結果 |
| `pr-commenter.ts` | PR コメント生成・投稿 | diff-result, vulnerability-result, 判定結果 | PR コメント |
| `vuln-summary.ts` | 脆弱性サマリ集計 | vulnerability-result.json | レベル別件数 |
| `extract-link-info.ts` | Bear 結果からリンク情報抽出 | compile_commands.json | link-info.json |

ScanCode ワークフローの SBOM 生成は Copilot CLI + Agent Skills (`.github/skills/generate-sbom.md`) で実行するため、専用の TypeScript スクリプトは不要です。

### 6.2 diff-checker.ts の差分検出ロジック

CycloneDX の `components` 配列を比較します。

**コンポーネントの一致判定**:
- `name` + `version` (+ `group`、存在する場合) で一致判定
- `purl` が両方に存在する場合は `purl` で一致判定（より正確）

**差分タイプ**:
- `added`: current にあり previous にない
- `removed`: previous にあり current にない
- `updated`: name (+ group) が一致し version が異なる

**出力フォーマット (diff-result.json)**:

```json
{
  "baseline_version": "1.0.0",
  "has_baseline": true,
  "summary": {
    "added": 3,
    "removed": 1,
    "updated": 1,
    "unchanged": 42
  },
  "changes": [
    {
      "type": "added",
      "component": {
        "name": "axios",
        "version": "1.6.0",
        "group": null,
        "purl": "pkg:npm/axios@1.6.0",
        "licenses": ["MIT"]
      }
    },
    {
      "type": "updated",
      "component": {
        "name": "react",
        "version": "18.3.0",
        "group": null,
        "purl": "pkg:npm/react@18.3.0",
        "licenses": ["MIT"]
      },
      "previous_version": "18.2.0"
    },
    {
      "type": "removed",
      "component": {
        "name": "moment",
        "version": "2.29.4",
        "group": null,
        "purl": "pkg:npm/moment@2.29.4",
        "licenses": ["MIT"]
      }
    }
  ]
}
```

### 6.3 review-checker.ts の判定ロジック

```typescript
// パッケージ名による判定
function isPackageReviewRequired(component, rules): boolean {
  return rules.packages.some(rule => {
    const nameMatch = rule.name === component.name;
    if (rule.group) {
      return nameMatch && rule.group === component.group;
    }
    return nameMatch;
  });
}

// ライセンスによる判定（licenses セクションに記載されていれば要レビュー）
function isLicenseReviewRequired(component, rules): boolean {
  return rules.licenses.some(rule => {
    return component.licenses?.includes(rule.id);
  });
}
```

---

## 7. 動作検証用テストプロジェクト

### 7.1 NPM プロジェクト（Syft ワークフロー検証用）

**ディレクトリ**: `test-projects/npm-sample/`

シンプルな Node.js プロジェクト。脆弱性を含む依存関係を意図的に追加します。

```json
{
  "name": "npm-sample",
  "version": "1.0.0",
  "dependencies": {
    "express": "^4.17.1",
    "lodash": "4.17.20",
    "axios": "^0.21.1"
  }
}
```

- `lodash@4.17.20`: 既知の脆弱性あり（Prototype Pollution, CVE-2021-23337）
- `axios@0.21.1`: 既知の脆弱性あり

### 7.2 Android プロジェクト（Trivy ワークフロー検証用）

**ディレクトリ**: `test-projects/android-sample/`

シンプルな Android プロジェクト（Gradle ベース）。脆弱性を含む依存関係を追加します。

```groovy
// build.gradle
dependencies {
    implementation 'com.squareup.okhttp3:okhttp:3.12.0'
    implementation 'com.google.code.gson:gson:2.8.5'
    implementation 'org.apache.logging.log4j:log4j-core:2.14.1'
}
```

- `log4j-core@2.14.1`: Log4Shell (CVE-2021-44228)
- `okhttp@3.12.0`: 既知の脆弱性あり

### 7.3 C/C++ プロジェクト（ScanCode + Bear ワークフロー検証用）

**ディレクトリ**: `test-projects/cpp-sample/`

Bear でリンク情報を検出でき、ScanCode でライセンス・著作権情報を検出できるプロジェクト。

**構成**:

```
cpp-sample/
  Makefile
  src/
    main.c                    # アプリケーション本体
  third-party/
    cjson/                    # cJSON (MIT License)
      cJSON.c
      cJSON.h
      LICENSE                 # MIT ライセンスファイル
    zlib/                     # zlib (zlib License)
      zlib.h
      zconf.h
      LICENSE                 # zlib ライセンスファイル
    mbedtls/                  # Mbed TLS (Apache-2.0)
      ssl.h
      LICENSE                 # Apache-2.0 ライセンスファイル
```

**Makefile**:

```makefile
CC = gcc
CFLAGS = -I./third-party/cjson -I./third-party/zlib -I./third-party/mbedtls
LDFLAGS = -lz -lssl -lcrypto

all: app
app: src/main.c third-party/cjson/cJSON.c
	$(CC) $(CFLAGS) -o app src/main.c third-party/cjson/cJSON.c $(LDFLAGS)
```

**検証ポイント**:
- Bear: `compile_commands.json` から `-lz`, `-lssl`, `-lcrypto` のリンク情報を検出
- ScanCode: `third-party/` 配下の LICENSE ファイルからライセンス情報（MIT, zlib, Apache-2.0）を検出
- ScanCode: ソースファイルのヘッダコメントから著作権情報を検出
- Agent Skills: Bear + ScanCode の結果を統合し、CycloneDX SBOM を生成

---

## 8. ディレクトリ構成（実装後）

```
slim-sbom-flow/
  .github/
    workflows/
      pr-sbom-check-syft.yml       # Syft + Grype ワークフロー
      pr-sbom-check-trivy.yml      # Trivy ワークフロー
      pr-sbom-check-scancode.yml   # ScanCode + Bear + Agent Skills ワークフロー
    skills/
      generate-sbom.md              # SBOM 生成用 Agent Skill (C/C++ 向け)
  config/
    ssf.yml                         # プロジェクト設定（利用者が編集）
    review-required-oss.yml         # 要レビュー OSS 定義（利用者が編集）
  scripts/
    src/
      config-reader.ts
      dt-client.ts
      diff-checker.ts
      review-checker.ts
      pr-commenter.ts
      vuln-summary.ts
      extract-link-info.ts
    package.json
    tsconfig.json
  test-projects/
    npm-sample/                     # NPM テストプロジェクト
    android-sample/                 # Android テストプロジェクト
    cpp-sample/                     # C/C++ テストプロジェクト
  docs/                             # セットアップ・運用ガイド
    dt-setup-*.md
    docker-setup.md
  design/                           # 設計ドキュメント
    pr-workflow.md                  # 本設計書
    generate-sbom-skill.md
```

---

## 9. reusable workflow としての設計

既存の REFERENCES 実装と同様に、reusable workflow として設計します。利用者のリポジトリから `workflow_call` で呼び出す形式です。

### 9.1 呼び出し側の例（Syft 版）

```yaml
# 利用者リポジトリの .github/workflows/pr-check.yml
name: PR SBOM Check
on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  sbom-check:
    uses: {org}/slim-sbom-flow/.github/workflows/pr-sbom-check-syft.yml@main
    secrets:
      DT_API_KEY: ${{ secrets.DT_API_KEY }}
      SSF_SECRET_TOKEN: ${{ secrets.SSF_SECRET_TOKEN }}
```

### 9.2 ワークフロー内部の処理順序（Syft/Trivy 版）

```
 1. 利用者リポジトリのチェックアウト
 2. slim-sbom-flow リポジトリのチェックアウト (.ssf/ に配置)
 3. ツールのインストール (Syft/Grype or Trivy)
 4. Node.js v24 セットアップ + スクリプトのビルド
 5. config/ssf.yml の読み込み
 6. SBOM 生成
 7. 脆弱性スキャン
 8. 脆弱性レポート (HTML) 生成
 9. ベースライン SBOM 取得 (DT から、pre_version 指定時。失敗時はエラー)
10. OSS 差分検出
11. 要レビュー OSS 判定
12. PR コメント投稿
13. Artifact アップロード (SBOM + 差分結果 + 脆弱性レポート zip)
```

### 9.3 ワークフロー内部の処理順序（ScanCode 版）

```
 1. 利用者リポジトリのチェックアウト
 2. slim-sbom-flow リポジトリのチェックアウト (.ssf/ に配置)
 3. ツールのインストール (ScanCode/Bear/Copilot CLI)
 4. Node.js v24 セットアップ + スクリプトのビルド
 5. config/ssf.yml の読み込み
 6. ベースライン SBOM 取得 (DT から、pre_version 指定時。失敗時はエラー)
 7. Bear でリンク情報収集
 8. ScanCode でライセンス・著作権情報抽出
 9. Copilot CLI + Agent Skills で SBOM 生成 (ベースライン SBOM を入力に含む)
10. OSS 差分検出
11. 要レビュー OSS 判定
12. PR コメント投稿 (OSS 変更情報のみ)
13. Artifact アップロード (SBOM + 差分結果 zip)
```

---

## 10. 制約事項・注意点

### 10.1 DT 接続に関する動作

| `pre_version` | DT 接続 | 動作 |
|---|---|---|
| 未指定 | - | 差分なし（全て新規）、正常終了 |
| 指定あり | 成功 | ベースライン SBOM 取得、差分比較 |
| 指定あり | 失敗（環境変数未設定含む） | **エラーで停止** |

`pre_version` が未指定の場合のみ、DT への接続をスキップします。脆弱性スキャンと要レビュー判定は DT 接続の有無に関わらず実行します。

### 10.2 ワークフローの終了ステータス

DESIGN-DECISION-POINTS.md 運用1 に基づき、ワークフローは常に成功で終了します。脆弱性や要レビュー OSS が検出されても、PR をブロックしません（警告コメントのみ）。

### 10.3 ScanCode ワークフローの実行時間

- 基本: PR ごとに毎回 ScanCode を実行
- 代替: ローカル実行 + `workflow_dispatch` 手動トリガー（大規模プロジェクト向け）
- `workflow_dispatch` トリガーは同一ワークフローファイル内にコメントアウトして記載し、必要に応じて利用者が有効化する

### 10.4 Grype HTML レポートの実装方針

1. Grype 公式テンプレート (`grype -o template`) を試行
2. [grype#724](https://github.com/anchore/grype/issues/724#issuecomment-1139563814) のアプローチを検討
3. 上記で不足する場合、TypeScript で JSON → HTML 変換スクリプトを作成
