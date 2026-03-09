# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**slim-sbom-flow** is a low-cost OSS (Open Source Software) management system design for:
- SBOM (Software Bill of Materials) generation and management
- Vulnerability tracking and compliance
- License compliance workflows
- OSS approval processes

**Current Status:** Planning/design phase. The repository contains design documentation (README.md, DISCUSSION.md) but no implementation code yet.

## Planned Architecture

### Core Components
- **Dependency-Track**: Central vulnerability management dashboard with PostgreSQL backend
- **GitHub Actions**: Automation for SBOM generation, PR comments, issue creation, and Dependency-Track integration
- **SBOM Tools**: Trivy (general), Syft (package managers), ScanCode Toolkit (C/C++)
- **Vulnerability Scanners**: Trivy, Grype
- **TypeScript Scripts**: OSS diff detection, GitHub Issue automation (to be implemented)

### Workflows
1. **PR Workflow**: Detect OSS changes, scan vulnerabilities, comment on PRs with diff and warnings
2. **Tag Workflow**: Generate SBOM, scan vulnerabilities, create approval issues, register to Dependency-Track
3. **Continuous Monitoring**: Dependency-Track monitors for new vulnerabilities and sends notifications

## Key Design Decisions (from DISCUSSION.md)

### Policy Approach
- No hardcoded license or OSS blocklists
- "Review-required OSS" defined per organization in configuration files
- Human approval required for critical decisions (no auto-block based on CVSS)
- License compliance judged by usage context (distribution format, modification, linking method) not just license name

### Approval Workflow
- GitHub Issue-based approval process (no Jira integration planned)
- Approval covers: license compliance, obligation fulfillment, acceptable residual vulnerabilities
- Audit trail maintained through Issues and GitHub Actions artifacts

### SBOM Distribution
- No automatic public release of SBOMs
- Manual export from Dependency-Track after approval for external requests

### Authentication
- Small teams: Dependency-Track basic auth
- Medium/large teams: OIDC integration (KeyCloak, Entra ID, etc.)

## Future Implementation Guidelines

When implementing the TypeScript scripts and GitHub Actions:

### Configuration Files
Create organization-specific policy files like:
- Review-required OSS list (define which OSS needs manual approval)
- License usage guidelines (not blocklists, but guidance for approval)

### GitHub Actions Structure
- Separate workflows for PR events and tag creation
- PR workflow: OSS diff detection → vulnerability scan → comment results
- Tag workflow: SBOM generation → vulnerability scan → approval issue creation → Dependency-Track registration
- Artifact preservation: Store SBOM diffs and review results as workflow artifacts for audit trails

### OSS Diff Detection
Compare current SBOM against baseline (previous version):
- Added/removed/updated packages
- Flag packages matching "review-required" list
- Include transitive dependencies

### Issue Templates
Create structured issues for approval workflow with sections for:
- Common checks (license type, unintended version changes)
- OSS-specific obligations (NOTICE file inclusion, license display location)
- Evidence links for verification

### Vulnerability Scanning
- PR/Tag events only (not scheduled main branch scans)
- Dependency-Track handles continuous monitoring
- Critical/High vulnerabilities flagged in PR comments but don't auto-block

## Important Conventions

### Language
Documentation is in Japanese. Implementation code comments should follow standard practices for the language used (likely English for TypeScript/YAML).

### Security Context
This system is designed for defensive security (vulnerability management, compliance). Any scripts that interact with GitHub APIs, Dependency-Track APIs, or vulnerability databases should follow least-privilege principles.

### Modularity
The design supports different tool combinations based on project type:
- Standard projects: Trivy or Syft/Grype
- C/C++ without package managers: ScanCode + Bear + AI-assisted SBOM generation
Allow tool selection through configuration rather than hardcoding.
