# Tests for generate-sbom Skill

このディレクトリには generate-sbom Skill の Python スクリプトのユニットテストが含まれています。

## テストファイル

- `test_merge_baseline_sbom.py` - `merge_baseline_sbom.py` の包括的なテスト（60個のテストケース）

## 実行方法

```bash
# このディレクトリで実行
python3 -m pytest test_merge_baseline_sbom.py -v

# すべてのテストを実行
python3 -m pytest -v

# 特定のテストクラスのみ実行
python3 -m pytest test_merge_baseline_sbom.py::TestMatchComponents -v
```

## テストカバレッジ

`test_merge_baseline_sbom.py` は以下の機能をテストしています：

- コンポーネント名の正規化
- PURL からのバージョン除去
- マージルールテーブルの構築
- コンポーネントのマッチング（PURL、名前、設定ファイル経由の3つの方法）
- コンポーネント属性のマージ（fallback / PR優先）
- BOMレベル属性のマージ
- 完全なSBOMマージ
- マージレポートの生成
- CycloneDX 1.4/1.5 両方の互換性
- CLIインターフェース

## Fixtures

`fixtures/` ディレクトリにはテスト用のサンプルデータが含まれています：

- `previous-sbom.json` - ベースライン SBOM のサンプル
- `scancode-json-pp.json` - ScanCode Toolkit の出力サンプル

## 依存関係

テスト実行には pytest が必要です：

```bash
pip install pytest
```
