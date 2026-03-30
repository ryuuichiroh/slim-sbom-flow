# NPM Sample Project

Syft + Grype ワークフローの検証用 Node.js プロジェクト。

## 含まれる脆弱性

- `lodash@4.17.20`: Prototype Pollution (CVE-2021-23337)
- `axios@0.21.1`: Server-Side Request Forgery (CVE-2021-3749)

## セットアップ

```bash
npm install
npm start
```

## SBOM チェックのテスト

1. config/ssf.yml を作成（オプション）
2. PR を作成
3. GitHub Actions が自動的に SBOM チェックを実行
4. PR コメントに結果が表示される
