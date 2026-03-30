# 設計判断ポイント

このドキュメントは、README.md の要件を実装する前に決定すべき設計判断を整理したものです。技術的な実現可能性は REFERENCES で検証済みですが、**「どう設計するか」の判断**はまだ行われていません。

**作成日**: 2026-03-07
**最終更新**: 2026-03-08
**ステータス**: ✅ 全ての設計判断が完了、実装フェーズへ移行
**目的**: 実装フェーズに入る前に、重要な設計判断を明確にし、議論・合意を得る

---

## このドキュメントの位置づけ

このドキュメントは、slim-sbom-flow プロジェクトの**正式な設計判断の記録**です。

- **技術検証の記録**: `REFERENCES/design-archive/TECHNICAL-VERIFICATION-SUMMARY.md`
- **設計判断の記録**: 本ドキュメント（DESIGN-DECISION-POINTS.md）
- **設計判断のサマリー**: `FAQ.md`（よくある質問形式）

全ての設計判断は本ドキュメントに詳細を記録し、FAQ.md には重要な判断のサマリーのみを記載します。

---

## ⚠️ 重要な方針決定（2026-03-07）

以下の設計判断について方針が決定しました：

### 決定1: デフォルトツールは決定しない（項目1-1）
- **理由**: プロジェクトの言語・依存関係によって最適なツールが異なる
- **対応**: 複数の選択肢とワークフローテンプレートを提供（Trivy、Syft、ScanCode、商用ツール）

### 決定2: 自動判定不可能な項目は人間確認（項目2-3、4-1）
- **対象**: 地政学的リスク、配布形態、改変有無、リンク方法
- **理由**: 技術的に自動判定不可能
- **対応**: GitHub Issue のチェック項目として提供

### 決定3: 脆弱性DBは推奨しない（項目3-1、3-2）
- **理由**: Dependency-Track の機能で完結、検出率はプロジェクト依存
- **対応**: DT で選択可能なことを説明、公式ドキュメントへのリンクを提供

---

## 📋 目次

- [優先度：高 - 実装に直結する設計判断](#優先度高---実装に直結する設計判断)
  - [1. SBOM生成ツールの選定基準](#1-sbom生成ツールの選定基準)
  - [2. 要レビューOSS定義ファイルの設計](#2-要レビューoss定義ファイルの設計)
  - [3. 脆弱性データベースの設定方針](#3-脆弱性データベースの設定方針)
  - [4. SBOM編集・補完のワークフロー](#4-sbom編集補完のワークフロー)
- [運用方針の決定事項](#運用方針の決定事項)
- [設計判断の進め方](#設計判断の進め方)

---

## 優先度：高 - 実装に直結する設計判断

### 1. SBOM生成ツールの選定基準

#### 技術的実現可能性（検証済み）
- ✅ Trivy: 脆弱性スキャン、SBOM生成、ミスコンフィグ検出など多機能
- ✅ Syft: SBOM生成に特化、Grype と組み合わせて脆弱性スキャン
- ✅ ScanCode + Bear + AI Agent: パッケージマネージャなしのC/C++プロジェクト対応

**参考**: `REFERENCES/kiro-rsi-app/docs/sbom/01.SBOM_OVERVIEW.md`

#### 未検証の技術事項
- ❓ Trivy vs Syft の SBOM 生成精度・検出漏れの比較
- ❓ パフォーマンス比較（実行時間、メモリ使用量）
- ❓ Dependency-Track での Trivy Scanner の効果測定

#### 設計方針（重要な変更）

**⚠️ デフォルトツールは決定しない**

このプロジェクトでは、特定のツールをデフォルトとして推奨しません。

**理由**:
1. **実装言語や成果物によって最適なツールが異なる**
   - Node.js、Python、Java、Go、コンテナ等で得意・不得意がある
2. **既存の商用ツールとの共存**
   - FOSSID、BLACK DUCK、WIZ、Snyk、MergeBase等を既に利用している組織もある
3. **柔軟性の確保**
   - 現場に応じてツールを切り替えられることが重要
   - README.md の理念「各プロダクトの特性に応じてツールの選択やスクリプトの拡張ができる」と一致

**提供するもの**:
- **複数のツールの選択肢と比較ガイド**
  - Trivy の GitHub Actions ワークフローテンプレート
  - Syft + Grype の GitHub Actions ワークフローテンプレート
  - ScanCode + Bear + AI Agent の手順書（C/C++向け）
  - 商用ツール連携の方法
- **SETUP.md の選択ガイド**
  - 各ツールの特性（得意・不得意、パフォーマンス等）
  - プロジェクトタイプ別の推奨ツール
  - 選択の基準

#### 設計判断ポイント

##### 判断1-1: どのツールの例を提供するか
**選択肢**:
- **A. Trivy と Syft の両方を提供**
  - メリット: ユーザーが選べる、柔軟性が高い
  - デメリット: メンテナンスコストが2倍
- **B. Trivy のみ提供（Syft は将来追加）**
  - メリット: 初期リリースがシンプル
  - デメリット: 柔軟性が低い

**決定**: **A（両方を提供）**
- README.md の理念「ツールの選択やスクリプトの拡張ができる」を実現するため
- 初期リリースから複数の選択肢を提供することで、適用範囲が広がる

---

##### 判断1-2: ツール切り替えの実装方法
**選択肢**:
- **A. ワークフローファイルを丸ごとコピー**
  - ユーザーが使いたいツールのワークフローファイルをコピーして使う
  - メリット: シンプル、分かりやすい
  - デメリット: ツール切り替え時にファイル全体を置き換える必要
- **B. 設定ファイルで指定（`oss-management-system.yml`）**
  - 例: `sbom_generator: trivy` または `sbom_generator: syft`
  - メリット: ツール切り替えが容易
  - デメリット: 実装が複雑、1つのワークフローファイルで複数ツールに対応

**提案**:
- **初期リリースはA（ワークフローファイルをコピー）**
  - `.github/workflows/pr-sbom-check-trivy.yml` をコピーして使う
  - `.github/workflows/pr-sbom-check-syft.yml` をコピーして使う
  - シンプルで理解しやすい
- **将来的にBをサポート（オプション）**
  - 設定ファイルでツールを指定できる機能を追加

---

##### 判断1-3: C/C++プロジェクトと商用ツールの扱い
**決定**: 専用のドキュメント・ワークフローを提供

**C/C++プロジェクト**:
- 専用のワークフローテンプレートを提供（ScanCode + Bear + AI Agent）
- SETUP.md に専用の手順書を記載
- 一般的なプロジェクトとは明確に分離

**商用ツール（FOSSID, BLACK DUCK, WIZ, Snyk, MergeBase等）**:
- SETUP.md に「商用ツール連携」セクションを追加
- 各ツールで生成したSBOMをCycloneDX形式でエクスポート
- Dependency-Track にインポートする手順を記載
- GitHub Actions との連携方法を例示

---

### 2. 要レビューOSS定義ファイルの設計

#### 技術的実現可能性（検証済み）
- ✅ YAML/JSON ファイルで定義可能
- ✅ GitHub Actions から読み込み可能
- ✅ TypeScript スクリプトで判定ロジックを実装可能

**参考**: `REFERENCES/oss-management-system/config/license-guidelines.yml`

#### 設計判断ポイント

##### 判断2-1: 定義ファイルの管理場所

**✅ 決定（2026-03-07）**: 選択肢C（ハイブリッド）

**実装方針**:
1. **組織でのフォーク運用を前提**
   - 組織が slim-sbom-flow をフォーク
   - フォーク版の `config/review-required-oss.yml` に組織デフォルトを設定
   
2. **プロジェクト側で上書き可能**
   - プロジェクトに `config/review-required-oss.yml` があれば、それを使用
   - なければ、フォーク版（組織デフォルト）を使用

3. **優先順位**:
   ```
   プロジェクト側のconfig > 組織デフォルトのconfig
   ```

**reusable workflow の実装**:
```yaml
- name: Load config
  run: |
    # 1. 中央（フォーク版）の config を読み込む
    cp .oss-management/config/review-required-oss.yml config-default.yml
    
    # 2. プロジェクト側の config があれば上書き
    if [ -f config/review-required-oss.yml ]; then
      echo "Using project-specific config"
      cp config/review-required-oss.yml config-merged.yml
    else
      echo "Using organization default config"
      cp config-default.yml config-merged.yml
    fi
```

**SETUP.md に記載する内容**:
- フォークしての組織導入方法
- 組織共通 config の設定方法
- プロジェクト固有ルールの追加方法（オプション）

**理由**:
- README.mdの「組織として注意しておきたいOSS」（中央管理）と「各プロダクトの特性に応じた拡張」（分散管理）の両方を実現
- 組織でフォーク運用することで、カスタマイズしやすい
- プロジェクト側で柔軟に上書き可能

---

##### 判断2-2: 要レビュー判定の粒度

**✅ 決定（2026-03-07）**: パッケージ名 + ライセンス（CVSSスコアは除外）

**実装方針**:

1. **パッケージ名ベースの判定**
   - CycloneDX の構造と一致（`name` + `group`）
   - `name` は必須、`group` はオプション（Maven等で使用）
   
2. **ライセンスベースの判定**
   - GPL-3.0, AGPL-3.0 等、組織ポリシーで要レビューとするライセンス
   
3. **CVSSスコアは要レビュー判定に含めない**
   - 脆弱性は Trivy/Syft で自動検出
   - PR コメント/Issue に情報提供として記録
   - 承認フローで人間が影響範囲を判断

**YAML構造**:
```yaml
# config/review-required-oss.yml
version: "1.0"

# パッケージ名ベース
packages:
  - name: "axios"
    reason: "セキュリティ懸念"
  
  - name: "angular"
    reason: "技術スタック統一（React推奨）"
  
  - name: "spring-core"
    group: "org.springframework"
    reason: "ビジネスクリティカル"

# ライセンスベース
licenses:
  - id: "GPL-3.0"
    requires_review: true
    reason: "コピーレフトライセンス"
  
  - id: "AGPL-3.0"
    requires_review: true
    reason: "強いコピーレフトライセンス"
```

**判定ロジック**:
```typescript
function isReviewRequired(component: Component, rule: PackageRule): boolean {
  // name が一致
  if (rule.name === component.name) {
    // group が指定されている場合は、それも一致する必要がある
    if (rule.group) {
      return rule.group === component.group;
    }
    // group 指定なしなら、name 一致だけで判定
    return true;
  }
  return false;
}
```

**理由**:
- 要レビューOSSとは「ポリシー違反リスク」「組織の意思決定が必要」なもの
- 脆弱性は「注意喚起」であって「使用禁止」ではない
- CVSS スコアだけで機械的に判断すべきではない
- CycloneDX の標準構造（name + group）と一致、シンプル

**将来の拡張**:
- 必要になったら purl サポートを追加可能
- 初期リリースではシンプルさを優先

---

##### 判断2-3: 地政学的リスクの扱い

**✅ 決定（2026-03-07）**: 自動判定しない、人間確認項目として提供

**理由**:
- メンテナーの国籍情報を自動取得する方法がない（GitHub API では提供されない）
- 仮に取得できても、政治的・倫理的に適切な判断基準を設定することが困難

**対応**:
- GitHub Issue のチェック項目として提供:
  - `[ ] この OSS を利用することに地政学的なリスクはないか確認した`
- 組織ごとに判断基準を定義（本システムでは定義しない）

**同様に自動判定しない項目**:
- 配布形態（embedded / cloud / SaaS）
- 改変有無（yes / no）
- リンク方法（static / dynamic）

これらは全て GitHub Issue のチェック項目として人間が確認します。

---

### 3. 脆弱性データベースの設定方針

#### 技術的実現可能性（検証済み）
- ✅ Dependency-Track は複数の脆弱性データベースをサポート
  - GitHub Advisories
  - OSV (Open Source Vulnerabilities)
  - OSS Index (Sonatype)
  - NVD (National Vulnerability Database)

**参考**: `REFERENCES/oss-management/REMAINING-TASK.md`

#### 未検証の技術事項
- ❓ 各データベースの特性（更新頻度、カバレッジ、誤検出率）
- ❓ 複数データベース有効化時の重複処理
- ❓ 実際のプロジェクトでの検出率の違い

#### 設計判断ポイント

##### 判断3-1: どの脆弱性データベースを有効化するか

**✅ 決定（2026-03-07）**: 特定のDBを推奨しない

**理由**:
1. **Dependency-Track の機能で完結**
   - 本システム（slim-sbom-flow）で決めることではない
   - DT の設定画面で選択できる
2. **検出率はプロジェクト依存**
   - 言語、エコシステム、SBOM の品質によって結果が異なる
   - サンプルプロジェクトでの比較は無意味
3. **組織のセキュリティ要件による**
   - 網羅性 vs 誤検出の許容度は組織によって異なる

**対応**:
SETUP.md に以下を記載:
```markdown
## 脆弱性データベースの設定（Dependency-Track）

### 利用可能なデータベース
- GitHub Advisories（GitHub）
- OSV（Google）
- OSS Index（Sonatype）
- NVD（NIST）

### 推奨
まず全て有効化して、自分のプロジェクトでの検出状況を確認してください。
検出される脆弱性の数、重複、誤検出率はプロジェクトによって異なります。

### 参考リンク
- [Dependency-Track 公式ドキュメント](https://docs.dependencytrack.org/)
```

---

##### 判断3-2: Dependency-Track の Trivy Scanner の利用

**✅ 決定（2026-03-07）**: 推奨しない（利用者判断）

**理由**: 判断3-1と同じ
- DT の機能で完結
- 効果はプロジェクト依存
- リソース消費とのトレードオフは組織判断

**対応**:
SETUP.md に以下を記載:
```markdown
### Trivy Scanner（オプション）
Dependency-Track は Trivy を使った追加スキャンをサポートしています。
有効化するとリソース消費が増えますが、検出精度が向上する可能性があります。

設定方法: `Administration` > `Analyzers` > `Trivy`

自分のプロジェクトで有効/無効を試して、効果を確認することを推奨します。
```

---

### 4. SBOM編集・補完のワークフロー

#### 技術的実現可能性（検証済み）
- ✅ Dependency-Track のコンポーネントプロパティで補完情報を保存可能
- ✅ CycloneDX の `properties` フィールドで補完情報を表現可能
- ✅ GitHub Issue で対応記録を収集可能

**参考**: `REFERENCES/oss-management-system/DESIGN.md`

#### 未検証の技術事項
- ❓ 前バージョンからの情報引継ぎの実装方法
- ❓ CycloneDX/SPDX での補完情報の標準的な表現方法

#### 設計判断ポイント

##### 判断4-1: 補完が必要な情報の定義

**✅ 決定（2026-03-07）**: 条件ベースの階層化構造

**実装方針**:

GitHub Issue の制約（動的フォーム制御不可）を考慮し、以下の構造を採用：

1. **条件付き表示を注釈として扱う**
   - `condition: "link_type == 'static'"` → ❌ 削除（動的制御不可）
   - `show_when: "静的リンクの場合のみ"` → ✅ 人間が読む注釈
   - 全ての項目を表示し、該当しない場合は「N/A」と記入

2. **4つのルールカテゴリ**
   - `diff_type_rules`: OSS の差分タイプ（added, updated, deleted）
   - `review_required_rules`: 要レビュー OSS の共通チェック
   - `license_rules`: ライセンス固有のチェック
   - `vulnerability_rules`: 脆弱性検出時のチェック

**新しい YAML 構造**:

```yaml
version: "1.0"

# 差分タイプによるルール
diff_type_rules:
  - condition: "added"
    label: "新規追加OSS"
    rules:
      - label: "意図した追加か確認"
        input_type: "checkbox"
        message: "意図しないOSSの混入でないことを確認してください。"
        required: true
      
      - label: "バージョン確認"
        input_type: "checkbox"
        message: "適切なバージョンが選択されていることを確認してください。"
        required: true
  
  - condition: "updated"
    label: "バージョンアップOSS"
    rules:
      - label: "意図したバージョンアップか確認"
        input_type: "checkbox"
        required: true
      
      - label: "破壊的変更の確認"
        input_type: "text"
        message: "破壊的変更がないか、あれば影響範囲を記載してください。"
        required: false
  
  - condition: "deleted"
    label: "削除されたOSS"
    rules:
      - label: "削除理由"
        input_type: "text"
        required: true
      
      - label: "影響確認"
        input_type: "checkbox"
        message: "他のコードで使用されていないか確認しました。"
        required: true

# 要レビューフラグによるルール
review_required_rules:
  - label: "要レビュー理由の確認"
    input_type: "checkbox"
    message: "なぜ要レビュー対象なのか理由を確認しました。"
    required: true
  
  - label: "法務・管理部門への相談"
    input_type: "checkbox"
    message: "必要に応じて法務や管理部門に相談しました。"
    required: false

# ライセンス固有のルール
license_rules:
  - license_id: "GPL-3.0"
    common_instructions: "GPL-3.0はコピーレフトライセンスです。"
    rules:
      - label: "リンク方法"
        input_type: "select"
        options: ["動的リンク", "静的リンク", "使用しない"]
        required: true
      
      - label: "法務担当への相談"
        input_type: "checkbox"
        message: "静的リンクの場合、製品全体をGPL-3.0でライセンスする必要があります。"
        show_when: "静的リンクの場合のみ"
        required: false
      
      - label: "ソースコード提供方法"
        input_type: "text"
        message: "配布する場合、完全なソースコードを提供する必要があります。"
        show_when: "配布する場合のみ"
        required: false
  
  - license_id: "MIT"
    rules:
      - label: "著作権表示とライセンステキストの同梱"
        input_type: "checkbox"
        required: true
      
      - label: "ライセンス情報の記載場所"
        input_type: "text"
        message: "バイナリ配布の場合、ドキュメントにライセンス情報を含めてください。"
        show_when: "配布する場合のみ"
        required: true
  
  # ... その他のライセンス

# 脆弱性検出時のルール
vulnerability_rules:
  - label: "影響範囲の確認"
    input_type: "text"
    message: "検出された脆弱性の影響範囲を記載してください。"
    required: true
  
  - label: "対応方針"
    input_type: "select"
    options:
      - "影響なし（未使用機能）"
      - "回避策あり"
      - "バージョンアップで対応"
      - "リスク受容"
    required: true
```

**Issue 生成ロジック**:

```typescript
function generateIssueChecks(component: Component, diff: ComponentDiff) {
  const checks = [];
  
  // 1. 差分タイプのルール（必ず適用）
  const diffRule = getDiffTypeRule(diff.changeType);
  checks.push(...diffRule.rules);
  
  // 2. 要レビュー判定（該当する場合）
  if (isReviewRequired(component)) {
    checks.push(...getReviewRequiredRules());
  }
  
  // 3. ライセンス固有のルール（ライセンス情報がある場合）
  if (component.licenses) {
    const licenseRule = getLicenseRule(component.licenses[0].id);
    checks.push(...licenseRule.rules);
  }
  
  // 4. 脆弱性ルール（検出された場合）
  if (component.vulnerabilities?.length > 0) {
    for (const vuln of component.vulnerabilities) {
      checks.push(generateVulnerabilityCheck(vuln));
    }
  }
  
  return checks;
}
```

**Issue 表示例**:

```markdown
## 新規追加OSS: lodash@4.17.21

### 差分チェック（新規追加）
- [ ] 意図した追加か確認
- [ ] バージョン確認

### 要レビューチェック
- [ ] 要レビュー理由の確認（理由: 過去に脆弱性多数）
- [ ] 法務・管理部門への相談

### ライセンスチェック（MIT）
- [ ] 著作権表示とライセンステキストの同梱
- ライセンス情報の記載場所: _____
  ※ 配布する場合のみ記入

### 脆弱性チェック
#### CVE-2021-23337 (CVSS 7.4, HIGH)
- 影響範囲: _____
- 対応方針: [ ] 影響なし [ ] 回避策あり [ ] バージョンアップ [ ] リスク受容
```

**デフォルト設定**:
- REFERENCESの `license-guidelines.yml` をベースに、新構造に変換して提供
- 組織でフォークして、自分のポリシーに合わせてカスタマイズ可能

**理由**:
- GitHub Issue の制約（動的フォーム制御不可）に対応
- ライセンス固有でないチェック項目（差分タイプ、要レビュー、脆弱性）をサポート
- 構造化されたルール定義で、組織でのカスタマイズが容易

---

##### 判断4-2: 補完情報の保存場所

**✅ 決定（2026-03-07）**: SBOM の properties をマスターとする

**実装方針**:

```
GitHub Issue: 監査証跡（永続的、人間が読む）
  ↓ 承認後
SBOM の properties: マスター（情報集約）
  ↓ インポート
Dependency-Track: 保管・脆弱性管理
  - UI では properties は見えない
  - API でダウンロードすれば取得可能
  ↓ 確認・編集が必要な場合
SBOM Editor: GUI での確認・編集
```

**プロパティ命名規則**:

参考: https://github.com/CycloneDX/cyclonedx-property-taxonomy

ネームスペース: `cdx:slim-sbom-flow:*`

```json
"properties": [
  {
    "name": "cdx:slim-sbom-flow:license_display_url",
    "value": "https://example.com/licenses"
  },
  {
    "name": "cdx:slim-sbom-flow:notice_handled",
    "value": "true"
  },
  {
    "name": "cdx:slim-sbom-flow:distribution_type",
    "value": "embedded"
  },
  {
    "name": "cdx:slim-sbom-flow:link_type",
    "value": "dynamic"
  },
  {
    "name": "cdx:slim-sbom-flow:is_modified",
    "value": "false"
  },
  {
    "name": "cdx:slim-sbom-flow:reviewed_by",
    "value": "@manager"
  },
  {
    "name": "cdx:slim-sbom-flow:reviewed_date",
    "value": "2026-03-07"
  },
  {
    "name": "cdx:slim-sbom-flow:approved",
    "value": "true"
  }
]
```

**GitHub Actions Artifact**:
- SBOM 自体（properties 含む）を Artifact として保存
- Artifact には期限があるが、DT に登録されているので問題なし

**理由**:
- 上司の要望（SBOM に情報を集約）を満たす
- CycloneDX 標準の properties フィールドを使用
- SBOM をエクスポートすれば補完情報も含まれる
- SBOM Editor で GUI 確認・編集可能
- GitHub Issue は監査証跡として永続的に保存

**注意点**:
- DT の UI では properties は表示されない
- 確認が必要な場合は、DT API または SBOM Editor を使用

---

##### 判断4-3: 前バージョンからの情報引継ぎ

**✅ 決定（2026-03-07）**: 自動引継ぎ（slim-sbom-flowのプロパティのみ）

**実装方針**:

1. **バージョンが同じ場合のみ引き継ぎ**
   - `name + version (+ group)` で一致判定
   - ハッシュは使わない（ビルド環境で変わるため）

2. **このシステムのプロパティのみ引き継ぎ**
   - `cdx:slim-sbom-flow:*` のプロパティのみ
   - 他のプロパティは新しいSBOMの情報を使う

3. **ユーザー確認は不要**
   - 完全自動引継ぎ
   - Issue に「前回の対応内容」を表示しない

**実装ロジック**:

```typescript
function inheritProperties(
  previousSBOM: SBOM,
  newSBOM: SBOM
): SBOM {
  for (const newComponent of newSBOM.components) {
    const prevComponent = findPreviousComponent(previousSBOM, newComponent);

    if (prevComponent && prevComponent.version === newComponent.version) {
      // slim-sbom-flowのプロパティのみ引き継ぎ
      const inheritedProps = prevComponent.properties?.filter(p =>
        p.name.startsWith('cdx:slim-sbom-flow:')
      ) || [];

      // 新しいSBOMのプロパティとマージ
      const newProps = newComponent.properties?.filter(p =>
        !p.name.startsWith('cdx:slim-sbom-flow:')
      ) || [];

      newComponent.properties = [...newProps, ...inheritedProps];
    }
    // バージョンが違う、または新規追加 → 引継ぎなし
  }

  return newSBOM;
}

function findPreviousComponent(
  previousSBOM: SBOM,
  newComponent: Component
): Component | null {
  return previousSBOM.components.find(c => {
    const nameMatch = c.name === newComponent.name;
    const versionMatch = c.version === newComponent.version;
    const groupMatch = !c.group || !newComponent.group || c.group === newComponent.group;

    return nameMatch && versionMatch && groupMatch;
  });
}
```

**ワークフロー**:

```
1. Tag作成時、前バージョンの SBOM を DT から取得
2. 新しい SBOM を生成（Trivy/Syft）
3. slim-sbom-flow のプロパティを自動引継ぎ
4. GitHub Issue で承認
5. 承認後、新しいプロパティを追加
6. DT にインポート
```

**理由**:
- シンプル: ユーザー確認不要、自動引継ぎ
- クリーン: このシステムのプロパティのみ管理
- 正確: 新しいSBOMの情報（hash、licenses等）を使用
- VEX分離: 脆弱性対応はVEXで管理、SBOMに混ぜない

**注意点**:
- バージョンアップされたOSSは、承認が必要（新規追加と同じ扱い）
- 脆弱性対応記録はVEXで管理（SBOMのpropertiesには含めない）

---

**⚠️ 実装時の再検討事項（2026-03-08）**

現在の設計では「カスタムプロパティ（`cdx:slim-sbom-flow:*`）のみ引き継ぎ」としているが、実装時に以下の懸念を再検討する必要がある：

**懸念1: CycloneDX標準項目の引継ぎ**
- **問題**: デュアルライセンス（MIT or Apache-2.0）の場合、前回承認時に「MIT」を選択したが、新しいSBOMでは両方が列挙される可能性がある
- **現在の設計**: 新しいSBOMの情報を優先 → 前回の選択が失われる
- **影響**: 毎回同じライセンス選択を承認する必要がある（非効率）

**懸念2: 引継ぎ対象項目の拡張**
カスタムプロパティ以外にも引継ぎが必要な可能性がある項目：
- `licenses`: デュアルライセンスで選択したライセンス
- `author`: 自動検出できなかった場合の手動補完値
- `description`: 手動で追加した説明
- `externalReferences`: 手動で追加した参照情報

**引継ぎルールの選択肢**:
1. **項目ごとに引継ぎルールを設定**
   - 例: `licenses`は引継ぐ、`hashes`は引継がない、等
   - メリット: きめ細かい制御が可能
   - デメリット: 設定が複雑、メンテナンスコストが高い

2. **シンプルなルール: 新SBOM が空 かつ 旧SBOM が非空 → 引継ぐ**
   - 全項目に適用される汎用ルール
   - メリット: シンプル、メンテナンスしやすい
   - デメリット: 意図しない引継ぎが発生する可能性

**実装時のアクション**:
1. 実際のSBOMを使って、どの項目が問題になるかを確認
2. 最小限の引継ぎルールを設計（シンプルさを優先）
3. 必要に応じて拡張可能な設計にする

---

##### 判断4-4: C/C++プロジェクトの補完情報

**✅ 決定（2026-03-08）**: 前回SBOM引継ぎ + sbom-editor補正（GitHub Actions基本、ローカル実行もオプション提供）

**実装方針**:

**基本フロー（GitHub Actions）**:
```
1. Tag作成 → GitHub Actions起動
2. ScanCode + Bear → 一時情報収集
3. 前バージョンのSBOM取得（Dependency-Trackから）
4. Agent Skills (sbom-master):
   - 前回SBOMとマッチング（name、ファイルパス等）
   - Version、PURL、License等を自動引継ぎ
   - 新規追加/更新されたOSSをマーク
5. SBOM Artifact保存 + 確認Issue作成
6. 開発者: sbom-editorで新規/更新OSSのみ補正
7. 承認依頼Issue作成
8. 管理者承認 → Dependency-Track登録
```

**オプション（ローカル実行）**:
- 大規模プロジェクト（Redis級）でScanCodeが1時間超
- GitHub Actions料金が懸念される場合
- → ローカルで1-4を実行、Workflow Dispatch手動トリガーで5以降を実行

**`.sbom-config.json` の役割**:
- Agent Skillsでも推定できない情報のヒント（補助的）
- `corrections`: ScanCode/Bear検出結果の補正
- `manual_components`: 検出不可能なコンポーネントの手動追加（バイナリライブラリ等）

**理由**:
- **効率的**: 2回目以降のSBOM作成で、Version/PURL等を自動引継ぎ
- **正確**: 前回承認済みの情報を再利用、人的ミス削減
- **sbom-editorの価値**: GUIで差分確認しながら編集
- **柔軟性**: 標準はGitHub Actions、大規模プロジェクトはローカル実行も可能
- **スケーラブル**: ライブラリ数が増えても作業量は一定

**注意点**:
- ScanCode実行時間はプロジェクト規模で10倍以上変わる（10分〜1時間超）
- `.sbom-config.json` に事前にVersion/PURLを設定する運用は非現実的
- 前回SBOM引継ぎにより、手動作業は新規/更新OSSのみに限定される

---

## 運用方針の決定事項

技術的な設計判断とは別に、運用方針として決定すべき事項があります。

### 運用1: CI/CDゲート条件

**✅ 決定（2026-03-08）**: README.mdの方針通り（自動ブロックなし）

**実装方針**:
- PR: 警告コメントのみ、ワークフロー成功（開発をブロックしない）
- Tag: 承認Issue作成、人が判断
- 自動ブロックは行わない（「最終判断は人が行う設計」）

**理由**:
- README.mdで既に明確に方針が決まっている
- 緊急パッチや誤検知への対応が柔軟
- 低コストで始められるという目的に合致
- 必要になったら後から追加可能

---

### 運用2: 承認フローの複雑さ

**✅ 決定（2026-03-08）**: README.mdの方針通り（シンプルをデフォルト、拡張可能）

**実装方針**:
- 初期実装: シンプルな1段階承認
  - 開発者: 確認Issue → SBOM編集 → 承認依頼Issue作成
  - 管理者: 承認 → Dependency-Track登録
- 拡張性: GitHub Actionsの拡張ポイントを用意
- 複雑な要件（複数承認者の並行承認等）は各組織でカスタマイズ

**理由**:
- README.mdで既に方針が明記されている
- 低コストで始められる（シンプルな実装）
- 大規模組織のニーズにも対応可能（拡張可能な設計）

---

### 運用3: SBOMの配布

**✅ 決定（2026-03-08）**: FAQ.mdの方針通り（自動公開しない）

**実装方針**:
- SBOM は自動公開しない
- 外部提供が必要な場合:
  - 申請を受けて審査
  - 承認後に Dependency-Track からエクスポートして提供
- 外部向け/内部向けでSBOMを分けない（提供が必要と判断されたら完全な情報を渡す）

**理由**:
- FAQ.mdで既に方針が明記されている
- セキュリティリスク低い（無暗に公開しない）
- 外部向け/内部向けの定義が組織ごとに異なり、汎用的な実装が困難
- CRA対応は必要時に手動で対応

---

### 運用4: 脆弱性スキャンの頻度

**✅ 決定（2026-03-08）**: README.mdの方針通り（PR/Tag時のみ、継続監視はDependency-Track）

**実装方針**:
- GitHub Actions: PR/Tag作成時のみ脆弱性スキャン実行
  - PR: 早期フィードバック（開発中に警告）
  - Tag: 承認Issue作成時に脆弱性情報を含める
- Dependency-Track: 継続的な脆弱性監視
  - 新規脆弱性検知時に通知（E-mail / Slack）
  - 脆弱性データベースの定期更新
- オプション: 定期スキャンを追加したい組織向けにREADME.mdで方法を紹介

**理由**:
- README.mdで既に方針が明記されている
- GitHub Actionsコスト低減（PR/Tagイベント時のみ実行）
- Dependency-Trackが継続監視を担当（役割分担が明確）
- シンプルで運用しやすい

---

## 設計判断の進め方（完了済み）

このセクションは、設計判断を行う際に使用したプロセスの記録です。

### 実施したステップ

**ステップ1: 優先順位の決定** → ✅ 完了
- 最小限の機能に必須の判断（判断1-1, 2-1, 2-2, 4-1, 運用1）を優先
- 初期リリース後に決めても良い判断は、必要最小限で決定

**ステップ2: 技術検証** → ✅ 完了
- 全12項目の技術検証を完了（`TECHNICAL-VERIFICATION-SUMMARY.md` 参照）
- 「デフォルトツールは決めない」方針により、一部の比較検証は不要と判断

**ステップ3: 設計判断の記録** → ✅ 完了
- 全ての設計判断を本ドキュメントに記録
- 各判断について、決定内容・理由・トレードオフを明記

### 設計判断の記録方針

- **詳細な記録**: 本ドキュメント（DESIGN-DECISION-POINTS.md）
- **サマリー**: FAQ.md（よくある質問形式）
- **技術検証の記録**: `REFERENCES/design-archive/TECHNICAL-VERIFICATION-SUMMARY.md`

---

## 次のアクション

### ✅ 完了した作業

1. **設計判断の決定** → 完了（2026-03-07〜2026-03-08）
   - 判断1-1〜1-3: SBOM生成ツールの選定
   - 判断2-1〜2-3: 要レビューOSS定義ファイルの設計
   - 判断3-1〜3-2: 脆弱性データベースの設定方針
   - 判断4-1〜4-4: SBOM編集・補完のワークフロー
   - 運用1〜4: 運用方針の決定

2. **技術検証の完了** → 完了（2026-03-07）
   - 全12項目の技術検証が完了
   - 詳細は `REFERENCES/design-archive/TECHNICAL-VERIFICATION-SUMMARY.md` 参照

3. **設計判断の記録** → 完了（本ドキュメント）
   - 全ての設計判断を本ドキュメントに記録

### 🔜 次のステップ: 実装フェーズ

設計判断・技術検証が完了したため、実装フェーズに移行します。

**実装する成果物**:
1. **SETUP.md** - システム構築手順書
   - Dependency-Track のセットアップ
   - GitHub Actions の設定方法
   - ツール選択ガイド（Trivy / Syft / ScanCode / 商用ツール）
   - 認証・権限設定（基本認証 / OIDC）

2. **GitHub Actions ワークフロー**
   - PR ワークフロー（OSS差分検出、脆弱性スキャン、コメント投稿）
   - Tag ワークフロー（SBOM生成、承認Issue作成、DT登録）
   - 複数のツールテンプレート（Trivy / Syft / ScanCode）

3. **TypeScript スクリプト**
   - OSS 差分検出スクリプト
   - GitHub Issue 自動生成スクリプト
   - SBOM プロパティ引継ぎスクリプト

4. **設定ファイルテンプレート**
   - `config/review-required-oss.yml` - 要レビューOSS定義
   - `config/license-guidelines.yml` - ライセンス固有のチェック項目

**実装の優先順位**:
1. 基本的なワークフロー（Trivy版）
2. TypeScript スクリプト
3. SETUP.md
4. 追加のワークフローテンプレート（Syft版、ScanCode版）
