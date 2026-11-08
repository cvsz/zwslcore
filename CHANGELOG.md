# Changelog

All notable changes to this template are documented here.

The format follows Keep a Changelog conventions; generated projects should adopt an explicit versioning policy appropriate to their product.

## [Unreleased]

### Added

- Supply-chain regression tests for Provider Dockerfile (`tests/test_supply_chain_dockerfile.py`): immutable digest pinning, hash verification, binary-only policy, non-root user, read-only rootfs.
- Complete pull request inventory and disposition documentation (`docs/audit/all-pull-requests-*`).
- Security assessment documentation (`docs/audit/security-assessment.md`, `docs/audit/worktree-security-review.md`, `docs/audit/provider-routing-review.md`, `docs/audit/mcp-security-review.md`, `docs/audit/supply-chain-assessment.md`).
- CVE risk acceptance dispositions (`docs/security/CVE-2026-119586-DISPOSITION.md`, `docs/security/CVE-2026-84243-DISPOSITION.md`).
- WSL2 compatibility review (`docs/audit/wsl2-compatibility.md`).
- Production readiness and residual risks documentation (`docs/audit/production-readiness.md`, `docs/audit/residual-risks.md`).
- Gap analysis and remediation report (`docs/audit/gap-analysis.md`, `docs/audit/remediation-report.md`).
- Test evidence documentation (`docs/audit/test-evidence.md`).
- Executive summary (`docs/audit/executive-summary.md`).
- Repository inventory (`docs/audit/repository-inventory.md`).
- Safe project identity bootstrap with explicit dry-run/apply and idempotence tests.
- Generated README/ABOUT templates and startup/profile documentation.
- CI bootstrap test coverage and fail-closed Makefile placeholders.
- ZEAZ cross-agent engineering execution framework.
- Claude Code and OpenCode adapters.
- Reusable AI guides, playbooks, prompts, skills, component manifests, and plugin-source manifests.
- ECC OSS CLI install configuration with explicit separation from hosted ECC App evidence.
- Repository structure and local Markdown-link validator.
- GitHub administration automation with dry-run, explicit apply, and read-back verification.
- Repository rollout guidance for applying the baseline safely to existing repositories.
- Canonical production-readiness matrix with explicit evidence states and next actions.

### Changed

- Reorganized reusable AI documentation into `guides/`, `playbooks/`, and `prompts/`.
- Updated Provider Dockerfile base image digests for supply-chain vulnerability remediation (issue #108):
  - Build: `cgr.dev/chainguard/python:latest-dev@sha256:01280a9f...` → `sha256:898360ca...`
  - Runtime: `cgr.dev/chainguard/python:latest@sha256:0f474688...` → `sha256:1a009647...`
  - Scan result: 24 vulnerabilities (3 Critical, 5 High) → 4 vulnerabilities (0 Critical, 2 High without fixes).
- Pinned baseline first-party GitHub Actions to immutable commit SHAs.
- Expanded CODEOWNERS coverage for repository policy, AI, ECC, skills, components, and plugin manifests.
- Clarified that release-note configuration is not an artifact-publishing workflow.
- Documented branch/security administration as an explicit evidence gate rather than a documentation-only checklist.

### Fixed

- Preserve the engineering task attempt budget and blocked evidence when Provider transport fails.
- Issue #108: Provider image Critical/Critical supply-chain vulnerabilities remediated by updating Chainguard base image digests (CVE-2026-115557 Python, CVE-2026-114613 pip-wheel, CVE-2026-113351/115506 libexpat1).
- Corrected generated README link validation so template links are resolved from their generated root location.
- Removed stale wording that could imply green CI or configuration files alone establish production readiness.

### Security

- Prevented delegated engineering tasks from expanding a parent's allowed path scope.
- Documented risk acceptance for CVE-2026-119586 (sqlite-libs) and CVE-2026-84243 (glibc-2.44) with compensating controls (non-root user, read-only rootfs, dropped capabilities, loopback binding).
- Added supply-chain regression tests enforcing immutable image digests, hash-verified dependencies, and binary-only install policy.
- Added fail-closed repository-administration verification.
- Added protected-branch controls for required reviews/checks, conversation resolution, force-push prevention, and deletion prevention.
- Added documented verification for Dependabot, private vulnerability reporting, secret scanning/push protection, and least-privilege Actions permissions where supported.
