# SBOM 生成 Skill 設計方針

## 目的

Makefile でコンパイルする C/C++ プロジェクトに適用できる、汎用的な SBOM 生成 Agent Skill を提供する。

## 入力ファイル

| ファイル | 必須/任意 | 用途 |
|---|---|---|
| `scancode-json-pp.json` | **必須** | ライセンス・著作権・ファイル一覧の検出 |
| `compile_commands.json` | 任意 | ビルド対象ファイルの確定、ノイズ除去、インクルードパス依存の解析 |
| `Makefile` | 任意 | リンクライブラリ (`-l` フラグ) の特定 |
| `.sbom-config.json` | 任意 | プロジェクト固有の設定（著作権者、除外パターン、ライセンス上書き等） |

## 出力

- SPDX 2.3 JSON (`sbom-spdx.json`)
- CycloneDX 1.5 JSON (`sbom-cyclonedx.json`)
- 分析レポート (`sbom-analysis-report.md`)

## Skill 構成

```
.github/skills/generate-sbom/
├── SKILL.md                          # ワークフロー手順・オプション説明・拡張ガイド
└── scripts/
    ├── generate_sbom.py              # SPDX 2.3 / CycloneDX 1.5 出力（メイン）
    ├── analyze_copyright_holders.py  # 著作権者の正規化・集計・主要著作権者判定
    └── validate_sbom.py              # 生成 SBOM のバリデーション
```

## LLM（プロンプト）とスクリプトの役割分担

### スクリプトに任せる処理（決定的・仕様準拠が重要）

- SPDX / CycloneDX の JSON 構造生成
- 著作権者名の正規化（法人格接尾辞の除去、文字化け検出）
- 著作権者の集計と主要著作権者の自動判定
- 生成 SBOM のバリデーション（必須フィールド、ID一意性、ライセンスID妥当性）
- compile_commands.json の解釈（インクルードパス抽出、ビルド対象の特定）

### LLM に任せる処理（柔軟な判断が必要）

- scancode JSON の読み取りと概要把握
- Makefile の解釈（LDFLAGS からリンクライブラリの特定）
- コンポーネントの特定と分類（ディレクトリ構造・著作権者・命名規則から判断）
- `.sbom-config.json` の生成提案
- ノイズ除去の判断（README 等ドキュメントからの誤検出の除外）

## オプション（`.sbom-config.json`）の主要フィールド

| フィールド | 用途 |
|---|---|
| `project_name` | SBOM ルートコンポーネント名 |
| `project_type` | `application` / `firmware` / `library` |
| `primary_copyright_holder` | 主要著作権者（自動検出のフォールバック） |
| `deps_directories` | サードパーティライブラリのディレクトリ |
| `exclude_patterns` | 除外するファイルパターン |
| `license_overrides` | ライセンスの手動上書き |
| `component_overrides` | コンポーネント属性の手動上書き |
| `copyright_holder_aliases` | 著作権者の表記ゆれ正規化 |

## アーキテクチャ上のメリット（ツール抽出結果ベースのアプローチ）

本 Skill は「ソースコード全体を LLM に読ませない」設計を採用している。
ScanCode・Bear 等のツールが抽出した構造化データ（JSON）を LLM が解析し、スクリプトで SBOM を生成する。

```
[ソースコード] → ScanCode  → scancode-json-pp.json ──┐
               → Bear     → compile_commands.json  ─┤→ LLM が JSON を解析 → スクリプトで SBOM 生成
               → Makefile  ─────────────────────────┘
```

### 大きなプロジェクトでの比較

| 観点 | ソースコード全読み | 本アプローチ |
|---|---|---|
| **スピード** | 数千ファイルを1つずつ Read → 非常に遅い | ScanCode 実行は1回、LLM は JSON 1ファイルを読むだけ |
| **LLM コスト** | ファイル数 x 平均行数 がトークンに直結 | scancode JSON は集約済みで桁違いに小さい |
| **正確性** | LLM がライセンス文を判定 → 見落としリスク | ScanCode は 30,000 以上のルールでマッチング → 専用ツールの方が高精度 |

### トークン消費量の目安

| プロジェクト規模 | ソースコード全体 | scancode JSON |
|---|---|---|
| 100 ファイル | ~50,000 行 (~150K tokens) | ~2,000 行 (~8K tokens) |
| 1,000 ファイル | ~500,000 行 (コンテキスト超過) | ~15,000 行 (~50K tokens) |
| 10,000 ファイル | 不可能 | ~100,000 行 (要約のみなら ~5K tokens) |

### トレードオフ

- ScanCode が検出できないもの（コメントに書かれていないライセンス、暗黙の依存関係）は見落とす。
- compile_commands.json と Makefile の解析がこれを補完する。

## ベースライン SBOM マージルール

GitHub Actions (pr-check.yml) において、Dependency-Track から取得したベースライン SBOM と PR で生成した SBOM をマージするためのルール。

### 目的

Dependency-Track に登録されたベースライン SBOM には、人間が手動で追記した情報（バージョン、PURL 等）が含まれる。これらの情報を PR で生成する SBOM に引き継ぐことで、SBOM の精度を向上させる。

### マージフロー

```
1. PR の SBOM 生成 (generate-sbom)
2. ベースライン SBOM 読み込み (Dependency-Track から取得済み)
3. コンポーネント突合 (下記マッチングルール)
4. 各コンポーネントを分類:
   - マッチあり → 属性ごとに (A)(B) ルール適用
   - PR のみ    → 新規 (そのまま出力)
   - ベースラインのみ → 削除 (出力しない、diff で検出)
5. コンポーネント以外の属性も (A)(B) ルール適用
6. マージ結果を出力、上書き通知をレポートに記録
```

### コンポーネントのマッチングルール

ベースライン SBOM と PR SBOM のコンポーネントを以下の優先度で突合する：

| 優先度 | 方法 | 説明 |
|---|---|---|
| 1 | `purl` 一致 | バージョン部分を除いた `pkg:type/namespace/name` で比較 |
| 2 | `name` 正規化比較 | 小文字化、ハイフン・アンダースコア・スペースの統一後に比較 |
| 3 | `.sbom-config.json` 経由 | PR のディレクトリパス → `component_overrides` の `name` → ベースラインの `name` |

- 優先度 3 は `component_overrides` に `name` が設定されている場合のみ発動
- `.sbom-config.json` がない場合は優先度 1, 2 のみで突合

#### マッチング例

```
ベースライン SBOM:  name = "Mbed TLS"
PR 自動検出:        name = "mbedtls"   (ディレクトリ名ベース)
.sbom-config.json:  "third-party/mbedtls": { "name": "Mbed TLS" }

→ 優先度 2: "mbedtls" vs "mbedtls" (正規化後) → 一致
  または
→ 優先度 3: mbedtls → config の "Mbed TLS" → ベースラインの "Mbed TLS" → 一致
```

### 属性の引き継ぎルール

2 つの基本ルール：

- **(A) fallback**: PR の情報で属性が特定できない場合（値なし / `NOASSERTION` / 空）、ベースラインから引き継ぐ
- **(B) PR 優先**: PR の情報を常に優先する。ベースラインと値が異なる場合は通知を出力する

**デフォルト設定**: 明示的に (B) が指定されていない属性はすべて (A) を採用する。コンポーネント属性では `licenses` と `hashes` のみがデフォルト (B)、コンポーネント以外では `metadata.component`、`metadata.tools`、`dependencies[]` がデフォルト (B) である。ユーザは `.sbom-config.json` で属性ごとに (A)/(B) を上書きできる（「設定ファイルでの例外指定」参照）。

#### コンポーネント属性の分類

| 属性 | 分類 | 理由 |
|---|---|---|
| `name` | **(A)** fallback | ベースラインの正式名称を優先 |
| `version` | **(A)** fallback | 自動検出が困難、人手情報が価値高い |
| `licenses` | **(B)** PR 優先 | ソースコードのライセンスヘッダが正。ベースラインと異なる場合は通知 |
| `purl` | **(A)** fallback | 自動生成が困難 |
| `cpe` | **(A)** fallback | 自動生成が困難 |
| `supplier` | **(A)** fallback | copyright から推測可能だが不完全 |
| `author` | **(A)** fallback | 同上 |
| `description` | **(A)** fallback | 自動生成しない |
| `hashes` | **(B)** PR 優先 | ファイルの実態を反映すべき |
| `externalReferences` | **(A)** fallback | URL 等は自動検出困難 |
| `properties` | **(A)** fallback | 人手設定を尊重 |

#### コンポーネント以外の属性の分類

```
BOM
├── metadata
│   ├── component     ← (B) PR 優先 (ルートコンポーネント)
│   ├── tools         ← (B) PR 優先 (生成ツール情報)
│   ├── authors       ← (A) fallback
│   ├── supplier      ← (A) fallback
│   └── properties    ← (A) fallback (カスタムメタデータ)
├── components[]      ← 上記コンポーネント属性ルール適用
├── dependencies[]    ← (B) PR 優先 (依存関係グラフ)
├── services[]        ← (A) fallback
└── vulnerabilities[] ← 引き継がない (Dependency-Track 側で管理、SBOM に含まれていても無視)
```

### コンポーネントの新規・削除・更新の判断

| 分類 | 条件 | 処理 |
|---|---|---|
| **新規** | PR で検出、ベースラインにない | そのまま出力（`NOASSERTION` の属性は人間のレビュー対象） |
| **削除** | ベースラインにあり、PR で検出されない | 出力しない（diff-checker で削除として検出される） |
| **更新** | 両方に存在、属性に差異あり | (A)(B) ルールでマージ |

### (B) PR 優先で上書きした場合の通知

PR の情報がベースラインの値を上書きした場合、`sbom-analysis-report.md` に以下の形式で記録する：

```
## ベースラインからの変更
- cJSON の licenses を上書きしました (ベースライン: MIT → PR: MIT AND ISC)
- zlib の hashes を上書きしました
```

### 設定ファイルでの例外指定

`.sbom-config.json` の `merge_overrides` フィールドで、属性ごとにデフォルトの (A)/(B) ルールを上書きできる。

```json
{
  "merge_overrides": {
    "component_attributes": {
      "version": "pr",
      "description": "pr"
    },
    "bom_attributes": {
      "metadata.authors": "pr",
      "services": "pr"
    }
  }
}
```

#### ルール

- `merge_overrides` がなければデフォルト設定をそのまま使う
- 指定できる値は `"baseline"`（ベースライン優先 = fallback）または `"pr"`（PR 優先）
- `component_attributes` のキーは「コンポーネント属性の分類」表の属性名（`name`, `version`, `licenses` 等）
- `bom_attributes` のキーは「コンポーネント以外の属性の分類」ツリーのパス（`metadata.component`, `metadata.tools`, `dependencies` 等）
- `vulnerabilities` は常に引き継がない（上書き不可）

#### デフォルト (B) 一覧（`merge_overrides` 未指定時）

| 分類 | 属性 | デフォルト |
|---|---|---|
| コンポーネント | `licenses` | `"pr"` |
| コンポーネント | `hashes` | `"pr"` |
| BOM | `metadata.component` | `"pr"` |
| BOM | `metadata.tools` | `"pr"` |
| BOM | `dependencies` | `"pr"` |

上記以外の属性はすべてデフォルト `"baseline"` である。

## 拡張性

- ベース Skill はそのままコピーしてどのプロジェクトでも使える
- 精度を上げたい場合は `.sbom-config.json` を追加
- それでも足りない場合は Skill 自体（SKILL.md やスクリプト）を自由に編集
