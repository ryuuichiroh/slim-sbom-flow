# Copilot Instructions

## Project Overview

**slim-sbom-flow** is an SBOM (Software Bill of Materials) management system built around [Dependency-Track](https://dependencytrack.org/). It automates OSS vulnerability detection, license compliance, and supply chain risk management via GitHub Actions workflows. Documentation is primarily in Japanese.

The system provides **template GitHub Actions workflows** (in `test-projects/`) that project teams copy into their own repositories. The TypeScript scripts in `scripts/` are the utilities those workflows call.

## Build, Lint, and Test

All commands run from `scripts/`:

```bash
cd scripts
npm run build    # Compile TypeScript → dist/
npm run lint     # ESLint on src/**/*.ts
npm run clean    # Remove dist/
```

**Node.js v24+ is required.**

There is no unit test suite. Validation is done end-to-end via the test projects:
- `test-projects/npm-sample/` — Syft + Grype workflow
- `test-projects/android-sample/` — Trivy workflow
- `test-projects/cpp-sample/` — ScanCode + Bear workflow

Each test project has its own `.github/workflows/pr-check.yml` that exercises the full workflow.

## Architecture

### Component Map

```
GitHub Actions (in user repos)
    ↓ runs
scripts/dist/*.js          ← compiled from scripts/src/
    ↓ reads
config/ssf.yml             ← project name, baseline version
config/review-required-oss.yml  ← review-trigger rules
    ↓ talks to
Dependency-Track API       ← vulnerability DB + SBOM storage
    ↓ posts to
GitHub PR comments / Issues
```

### Infrastructure

- **Local**: Docker Compose (`docker-compose/http/` or `docker-compose/https/` with KeyCloak OIDC)
- **AWS**: Terraform modules in `terraform/modules/` — ECS Fargate, RDS PostgreSQL, ALB, Cognito, Secrets Manager

### SBOM Toolchain

Available tools:

| Tool | Role |
|---|---|
| Syft | SBOM generation |
| Trivy | SBOM generation + vulnerability scanning |
| Grype | Vulnerability scanning (used against Syft-generated SBOMs) |
| ScanCode + Bear | SBOM generation for C/C++ projects |

The samples in `test-projects/` exist to **demonstrate each tool**, not to prescribe which tool to use for a given project type. Using Syft for Android or Trivy for npm is equally valid.

SBOM format is **CycloneDX 1.5** throughout. SPDX 2.3 is planned but not implemented.

## TypeScript Scripts (`scripts/src/`)

Each script is both a **CLI tool** (invoked directly by GHA) and an **importable module**. The pattern is consistent across all files:

```typescript
// Named exports for module use
export async function myFunction(...): Promise<Result> { ... }

// CLI entry point at the bottom
if (import.meta.url === `file://${process.argv[1]}`) {
  // parse args, call function, console.log result
}
```

Key scripts and their roles:
- `diff-checker.ts` — compares two CycloneDX SBOMs, returns added/removed/updated components
- `review-checker.ts` — checks components against `review-required-oss.yml` rules (by package name or license SPDX ID)
- `vuln-summary.ts` — aggregates Grype/Trivy JSON output into severity counts
- `dt-client.ts` — fetches SBOMs from Dependency-Track; uses env vars `DT_BASE_URL`, `DT_API_KEY`, `SSF_SECRET_TOKEN`
- `pr-commenter.ts` — formats and posts results to GitHub PRs via `@octokit/rest`
- `config-reader.ts` — reads YAML config files

## Key Conventions

### Configuration Files

`ssf.yml` (placed in each user project **after the first release tag**; may not exist during initial development):
```yaml
project_name: "my-app"   # optional; falls back to SBOM metadata
pre_version: "1.0.0"     # baseline version for diff comparison
```

When `ssf.yml` is absent, scripts fall back to SBOM metadata for the project name and skip baseline diff comparison.

`review-required-oss.yml`:
```yaml
version: "1.0"
packages:
  - name: "axios"
    group: "com.example"  # optional; used for Maven/Gradle group IDs
    reason: "Past security issues"
licenses:
  - id: "GPL-3.0"
    reason: "Copyleft license"
```

### TypeScript Types

Core domain types live in `scripts/src/types.ts`. When adding new scripts, import from there rather than redefining structures. Key types: `CycloneDXBom`, `Component`, `DiffResult`, `VulnerabilityMatch`, `ReviewRequiredOSS`.

### Terraform

Modules are in `terraform/modules/{network,security,data,routing,compute}/`. Required variables: `app_domain`, `acm_certificate_arn`. Default region: `ap-northeast-1`.

Copy `terraform/terraform.tfvars.example` to `terraform.tfvars` before deploying.

### Environment Variables (GHA Secrets)

| Variable | Used By |
|---|---|
| `DT_BASE_URL` | dt-client.ts |
| `DT_API_KEY` | dt-client.ts |
| `SSF_SECRET_TOKEN` | dt-client.ts (SSF webhook auth) |
| `GITHUB_TOKEN` | pr-commenter.ts (auto-provided by GHA) |

## Key Documents

- **`DESIGN-DECISION-POINTS.md`** — Important design decisions made during development of this repository. Read before changing tool choices (e.g., Trivy vs Syft, SBOM format) or architectural direction.
- **`FAQ.md`** — Common questions about design decisions.
- **`DEV-GHA-*.md`** — Development request documents for implementing GHA workflows (e.g., `DEV-GHA-PR.md` for PR create/update, `DEV-GHA-TAG.md` for tag creation). Each is paired with design documents in `design/` and workflow implementations in `test-projects/`.
- **`REFERENCES/design-archive/`** — Archive of information reviewed and discussed when making design decisions.
- **`REFERENCES/` (other subdirectories)** — Feasibility verification for CI/CD pipelines using GitHub Actions, Dependency-Track API usage research, and similar technical investigations.
