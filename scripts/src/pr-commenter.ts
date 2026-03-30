import { readFile } from 'fs/promises';
import { Octokit } from '@octokit/rest';
import { DiffResult, VulnerabilitySummary, ReviewRequiredOSS, Component } from './types.js';
import { checkReviewRequired } from './review-checker.js';
import { summarizeVulnerabilities } from './vuln-summary.js';

function formatVulnerabilitySummaryTable(summary: VulnerabilitySummary): string {
  return `| レベル | 件数 |
|---|---|
| Critical | ${summary.critical} |
| High | ${summary.high} |
| Medium | ${summary.medium} |
| Low | ${summary.low} |

合計: ${summary.total} 件`;
}

function formatDiffSummary(diff: DiffResult): string {
  let result = '## OSS 差分\n\n';

  if (!diff.has_baseline) {
    result += '**ベースラインなし（新規プロジェクト）**\n\n';
  } else {
    result += `ベースラインバージョン: ${diff.baseline_version}\n\n`;
  }

  const added = diff.changes.filter(c => c.type === 'added');
  const updated = diff.changes.filter(c => c.type === 'updated');
  const removed = diff.changes.filter(c => c.type === 'removed');

  if (added.length > 0) {
    const title = !diff.has_baseline ? '検出された OSS' : '追加された OSS';
    result += `### ${title} (${added.length}件)\n\n`;
    result += '| パッケージ | バージョン | ライセンス |\n';
    result += '|---|---|---|\n';
    for (const change of added) {
      const licenses = change.component.licenses?.map(l => l.license?.id || l.license?.name || 'Unknown').join(', ') || 'Unknown';
      result += `| ${change.component.name} | ${change.component.version || 'N/A'} | ${licenses} |\n`;
    }
    result += '\n';
  }

  if (updated.length > 0) {
    result += `### 更新された OSS (${updated.length}件)\n\n`;
    result += '| パッケージ | 変更前 | 変更後 | ライセンス |\n';
    result += '|---|---|---|---|\n';
    for (const change of updated) {
      const licenses = change.component.licenses?.map(l => l.license?.id || l.license?.name || 'Unknown').join(', ') || 'Unknown';
      result += `| ${change.component.name} | ${change.previous_version || 'N/A'} | ${change.component.version || 'N/A'} | ${licenses} |\n`;
    }
    result += '\n';
  }

  if (removed.length > 0) {
    result += `### 削除された OSS (${removed.length}件)\n\n`;
    result += '| パッケージ | バージョン | ライセンス |\n';
    result += '|---|---|---|\n';
    for (const change of removed) {
      const licenses = change.component.licenses?.map(l => l.license?.id || l.license?.name || 'Unknown').join(', ') || 'Unknown';
      result += `| ${change.component.name} | ${change.component.version || 'N/A'} | ${licenses} |\n`;
    }
    result += '\n';
  }

  if (added.length === 0 && updated.length === 0 && removed.length === 0) {
    result += '**変更なし**\n';
  }

  return result;
}

function formatReviewRequiredWarnings(components: Component[], rules: ReviewRequiredOSS): string {
  const warnings: Array<{ component: Component; reason: string; matchType: string }> = [];

  for (const component of components) {
    const result = checkReviewRequired(component, rules);
    if (result.is_review_required && result.matched_rule) {
      const matchType = result.match_type === 'package'
        ? 'パッケージ名'
        : `ライセンス (${'id' in result.matched_rule ? result.matched_rule.id : ''})`;

      warnings.push({
        component,
        reason: result.matched_rule.reason,
        matchType,
      });
    }
  }

  if (warnings.length === 0) {
    return '';
  }

  let result = '## :warning: 要レビュー OSS が検出されました\n\n';
  result += '| パッケージ | 理由 | マッチ条件 |\n';
  result += '|---|---|---|\n';

  for (const warning of warnings) {
    result += `| ${warning.component.name} | ${warning.reason} | ${warning.matchType} |\n`;
  }

  return result + '\n';
}

export async function generatePRComment(
  diff: DiffResult,
  vulnSummary: VulnerabilitySummary | null,
  reviewRules: ReviewRequiredOSS,
  artifactUrl: string
): Promise<string> {
  let comment = '# SBOM チェック結果\n\n';

  if (vulnSummary) {
    comment += '## 脆弱性サマリ\n\n';
    comment += formatVulnerabilitySummaryTable(vulnSummary);
    comment += '\n\n';
  }

  comment += formatDiffSummary(diff);
  comment += '\n';

  const changedComponents = diff.changes
    .filter(c => c.type === 'added' || c.type === 'updated')
    .map(c => c.component);

  const reviewWarnings = formatReviewRequiredWarnings(changedComponents, reviewRules);
  if (reviewWarnings) {
    comment += reviewWarnings;
  }

  comment += '\n## 📦 関連リンク\n\n';
  comment += `- [GitHub Actions アーティファクト](${artifactUrl})\n`;
  if (vulnSummary && vulnSummary.total > 0) {
    comment += '  - `vulnerability-report.html` で詳細な脆弱性レポートを確認できます\n';
  }

  comment += '\n---\n';
  comment += '*このコメントは slim-sbom-flow により自動生成されました*\n';

  return comment;
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const prNumber = parseInt(process.argv[2]);
  const diffPath = process.argv[3];
  const vulnPath = process.argv[4];
  const reviewRulesPath = process.argv[5];
  const artifactUrl = process.argv[6];

  if (!prNumber || !diffPath || !reviewRulesPath || !artifactUrl) {
    console.error('Usage: pr-commenter.js <pr_number> <diff_path> <vuln_path|null> <review_rules_path> <artifact_url>');
    process.exit(1);
  }

  const githubToken = process.env.GITHUB_TOKEN;
  const repo = process.env.GITHUB_REPOSITORY;

  if (!githubToken || !repo) {
    console.error('GITHUB_TOKEN and GITHUB_REPOSITORY environment variables are required');
    process.exit(1);
  }

  const [owner, repoName] = repo.split('/');

  const diff = JSON.parse(await readFile(diffPath, 'utf-8')) as DiffResult;

  let vulnSummary: VulnerabilitySummary | null = null;
  if (vulnPath && vulnPath !== 'null') {
    const vulnResult = JSON.parse(await readFile(vulnPath, 'utf-8'));
    vulnSummary = summarizeVulnerabilities(vulnResult);
  }

  const yaml = await import('js-yaml');
  const reviewRulesContent = await readFile(reviewRulesPath, 'utf-8');
  const reviewRules = yaml.default.load(reviewRulesContent) as ReviewRequiredOSS;

  const comment = await generatePRComment(diff, vulnSummary, reviewRules, artifactUrl);

  const octokit = new Octokit({ auth: githubToken });

  await octokit.issues.createComment({
    owner,
    repo: repoName,
    issue_number: prNumber,
    body: comment,
  });

  console.log(`Comment posted to PR #${prNumber}`);
}
