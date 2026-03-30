// CycloneDX SBOM types
export interface CycloneDXBOM {
  bomFormat: string;
  specVersion: string;
  version: number;
  metadata?: {
    component?: {
      name: string;
      version?: string;
      [key: string]: unknown;
    };
    [key: string]: unknown;
  };
  components?: Component[];
  [key: string]: unknown;
}

export interface Component {
  name: string;
  version?: string;
  group?: string;
  purl?: string;
  licenses?: LicenseChoice[];
  properties?: Property[];
  [key: string]: unknown;
}

export interface License {
  id?: string;
  name?: string;
  [key: string]: unknown;
}

export interface LicenseChoice {
  license?: License;
  expression?: string;
  [key: string]: unknown;
}

export interface Property {
  name: string;
  value: string;
}

// Config types
export interface SSFConfig {
  project_name?: string;
  pre_version?: string;
}

export interface ReviewRequiredOSS {
  version: string;
  packages?: PackageRule[];
  licenses?: LicenseRule[];
}

export interface PackageRule {
  name: string;
  group?: string;
  reason: string;
}

export interface LicenseRule {
  id: string;
  reason: string;
}

// Diff types
export type DiffType = 'added' | 'removed' | 'updated';

export interface ComponentDiff {
  type: DiffType;
  component: Component;
  previous_version?: string;
}

export interface DiffResult {
  baseline_version?: string;
  has_baseline: boolean;
  summary: {
    added: number;
    removed: number;
    updated: number;
    unchanged: number;
  };
  changes: ComponentDiff[];
}

// Review check types
export interface ReviewCheckResult {
  component: Component;
  is_review_required: boolean;
  matched_rule?: PackageRule | LicenseRule;
  match_type?: 'package' | 'license';
}

// Vulnerability types
export interface VulnerabilityResult {
  matches?: VulnerabilityMatch[];
  [key: string]: unknown;
}

export interface VulnerabilityMatch {
  vulnerability: {
    id: string;
    severity?: string;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}

export interface VulnerabilitySummary {
  critical: number;
  high: number;
  medium: number;
  low: number;
  unknown: number;
  total: number;
}
