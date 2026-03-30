# Android Sample Project

Trivy ワークフローの検証用 Android プロジェクト。

## 含まれる脆弱性

- `log4j-core@2.14.1`: Log4Shell (CVE-2021-44228) - Critical
- `okhttp@3.12.0`: 複数の既知の脆弱性
- `gson@2.8.5`: DoS 脆弱性

## セットアップ

このプロジェクトは `app/gradle.lockfile` を使用して依存関係を定義しています。
Android SDK や Gradle のインストールは不要で、GitHub Actions で直接 SBOM 生成と脆弱性スキャンが可能です。

## SBOM チェックのテスト

1. config/ssf.yml を作成（オプション）
2. PR を作成
3. GitHub Actions が自動的に SBOM チェックを実行
4. PR コメントに結果が表示される

## 補足

### `app/gradle.lockfile` の作成・更新

依存関係を変更した場合は、以下のコマンドで lockfile を再生成してください：

```bash
docker run --rm \
  -v "$PWD":/home/gradle/project \
  -w /home/gradle/project \
  gradle:7.5-jdk17 \
  gradle :app:dependencies --write-locks
```
