# C/C++ Sample Project

`generate-sbom` Agent Skill の検証用 C/C++ プロジェクト。
ScanCode + Bear を組み合わせた SBOM 生成ワークフローの動作確認に使用する。

## プロジェクト構成

```
cpp-sample/
├── src/
│   └── main.c                    # アプリケーション本体 (MIT, Example Corporation)
├── third-party/
│   ├── cjson/                    # cJSON 1.7.15 (MIT, Dave Gamble)
│   ├── zlib/                     # zlib ヘッダのみ (Zlib, Jean-loup Gailly and Mark Adler)
│   └── mbedtls/                  # Mbed TLS ヘッダのみ (Apache-2.0, Arm Limited)
├── Makefile
├── .sbom-config.json             # SBOM 生成オプション設定
└── .github/workflows/pr-check.yml
```

**依存ライブラリ:**

| ライブラリ | バージョン | ライセンス | 形態 |
|---|---|---|---|
| cJSON | 1.7.15 | MIT | ソースをインクルード |
| zlib | 1.2.11 | Zlib | ヘッダのみ（`-lz` でリンク） |
| Mbed TLS | 3.5.0 | Apache-2.0 | ヘッダのみ（`-lssl -lcrypto` でリンク） |

## ビルドとコンパイル情報の収集

```bash
# ビルド
make

# compile_commands.json の生成（Bear が必要）
bear -- make

# クリーンアップ
make clean
```

## ScanCode によるソースコード解析

```bash
scancode -lpc \
  --strip-root --classify --consolidate \
  --license-clarity-score --license-text --license-references \
  --summary --tallies \
  --json-pp scancode-json-pp.json \
  src/ third-party/ Makefile
```

## SBOM チェックのテスト

1. config/ssf.yml を作成（project_name 必須）
2. PR を作成
3. GitHub Actions が自動的に SBOM チェックを実行
   - Bear でリンク情報を収集
   - ScanCode でライセンス情報を抽出
   - generate-sbom Agent Skill で SBOM を生成
4. PR コメントに結果が表示される

## 検証ポイント

- Bear が `-lz`, `-lssl`, `-lcrypto` のリンク情報を検出
- ScanCode が third-party/ 配下の LICENSE ファイルを検出
- Agent Skill がベースライン SBOM とマッチングしてバージョン情報を引き継ぐ

## generate-sbom Skill について

Skill の設計方針は `/home/rnakayama/slim-sbom-flow/design/generate-sbom-skill.md` を参照。
「ソースコード全体を LLM に読ませない」アーキテクチャにより、大規模プロジェクトでもスピード・コスト・精度を両立している。

### Skill の実行（ローカルで手動テスト）

プロジェクトに Skill がある場合、以下のプロンプトで実行できる:

```
このプロジェクトの SBOM を生成してください。
```

Skill が自動的に利用可能なファイルを検出し、SBOM を生成する。

### 入力ファイルの組み合わせ

| 入力 | 効果 |
|---|---|
| `scancode-json-pp.json` のみ | 基本的な SBOM 生成。Makefile があればリンクライブラリも検出 |
| `+ compile_commands.json` | README.md 等のドキュメントからのノイズを除去 |
| `+ .sbom-config.json` | バージョン・著作権者・ライセンスを正確に上書き |
| `+ previous-sbom.json` (ベースライン) | ベースライン SBOM から version, purl 等を引き継ぐ |

### 出力ファイル

| ファイル | 説明 |
|---|---|
| `sbom-spdx.json` | SPDX 2.3 形式 |
| `sbom-cyclonedx.json` | CycloneDX 1.5 形式 |
| `sbom-analysis-report.md` | 人間向けサマリー |

## .sbom-config.json（オプション）

プロジェクト固有の設定を記述することで SBOM の精度が上がる。

詳細は `/.github/skills/generate-sbom/SKILL.md` の Configuration Reference を参照。
