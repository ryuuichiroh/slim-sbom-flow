import { readFile } from 'fs/promises';
import { VulnerabilityResult, VulnerabilitySummary } from './types.js';

export function summarizeVulnerabilities(vulnResult: VulnerabilityResult): VulnerabilitySummary {
  const summary: VulnerabilitySummary = {
    critical: 0,
    high: 0,
    medium: 0,
    low: 0,
    unknown: 0,
    total: 0,
  };

  // Grype format: { matches: [...] }
  if (vulnResult.matches && vulnResult.matches.length > 0) {
    for (const match of vulnResult.matches) {
      const severity = match.vulnerability.severity?.toLowerCase();
      updateSummary(summary, severity);
    }
    return summary;
  }

  // Trivy format: { Results: [{ Vulnerabilities: [...] }] }
  if ((vulnResult as any).Results) {
    const results = (vulnResult as any).Results;
    for (const result of results) {
      if (result.Vulnerabilities && Array.isArray(result.Vulnerabilities)) {
        for (const vuln of result.Vulnerabilities) {
          const severity = vuln.Severity?.toLowerCase();
          updateSummary(summary, severity);
        }
      }
    }
    return summary;
  }

  return summary;
}

function updateSummary(summary: VulnerabilitySummary, severity: string | undefined) {
  switch (severity) {
    case 'critical':
      summary.critical++;
      break;
    case 'high':
      summary.high++;
      break;
    case 'medium':
      summary.medium++;
      break;
    case 'low':
      summary.low++;
      break;
    default:
      summary.unknown++;
  }
  summary.total++;
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const vulnPath = process.argv[2];

  if (!vulnPath) {
    console.error('Usage: vuln-summary.js <vulnerability_result_json>');
    process.exit(1);
  }

  const vulnResult = JSON.parse(await readFile(vulnPath, 'utf-8')) as VulnerabilityResult;
  const summary = summarizeVulnerabilities(vulnResult);

  console.log(JSON.stringify(summary, null, 2));
}
