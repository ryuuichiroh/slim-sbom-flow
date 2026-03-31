import { readFile } from 'fs/promises';
import yaml from 'js-yaml';
import { Component, ReviewRequiredOSS, ReviewCheckResult, PackageRule, LicenseRule } from './types.js';

function isPackageReviewRequired(component: Component, rules: PackageRule[]): { matched: boolean; rule?: PackageRule } {
  for (const rule of rules) {
    const nameMatch = rule.name === component.name;
    if (rule.group) {
      if (nameMatch && rule.group === component.group) {
        return { matched: true, rule };
      }
    } else if (nameMatch) {
      return { matched: true, rule };
    }
  }
  return { matched: false };
}

function isLicenseReviewRequired(component: Component, rules: LicenseRule[]): { matched: boolean; rule?: LicenseRule } {
  if (!component.licenses || component.licenses.length === 0) {
    return { matched: false };
  }

  for (const license of component.licenses) {
    const licenseId = license.license?.id || license.license?.name || license.expression;
    if (!licenseId) continue;

    for (const rule of rules) {
      if (rule.id === licenseId) {
        return { matched: true, rule };
      }
    }
  }

  return { matched: false };
}

export async function loadReviewRules(configPath: string): Promise<ReviewRequiredOSS> {
  try {
    const content = await readFile(configPath, 'utf-8');
    return yaml.load(content) as ReviewRequiredOSS;
  } catch (error) {
    if ((error as NodeJS.ErrnoException).code === 'ENOENT') {
      return { version: '1.0', packages: [], licenses: [] };
    }
    throw error;
  }
}

export function checkReviewRequired(component: Component, rules: ReviewRequiredOSS): ReviewCheckResult {
  const packageCheck = isPackageReviewRequired(component, rules.packages || []);
  if (packageCheck.matched) {
    return {
      component,
      is_review_required: true,
      matched_rule: packageCheck.rule,
      match_type: 'package',
    };
  }

  const licenseCheck = isLicenseReviewRequired(component, rules.licenses || []);
  if (licenseCheck.matched) {
    return {
      component,
      is_review_required: true,
      matched_rule: licenseCheck.rule,
      match_type: 'license',
    };
  }

  return {
    component,
    is_review_required: false,
  };
}

// CLI entry point
if (import.meta.url === `file://${process.argv[1]}`) {
  const configPath = process.argv[2] || 'config/review-required-oss.yml';
  const componentJson = process.argv[3];

  if (!componentJson) {
    console.error('Usage: review-checker.js <config_path> <component_json>');
    process.exit(1);
  }

  const rules = await loadReviewRules(configPath);
  const component = JSON.parse(componentJson) as Component;
  const result = checkReviewRequired(component, rules);

  console.log(JSON.stringify(result, null, 2));
}
