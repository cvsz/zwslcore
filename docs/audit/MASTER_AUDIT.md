# Master Audit — zwslcore

Audit scope: complete enterprise engineering audit of the zwslcore repository
(cvsz/zwslcore), performed against the ZEAZ governance contract
(zeaz.md / AGENTS.md / SUPER ULTRA AI ORC v2.1).

Audit date: 2026-11-08
Developer identity: cvsz (GPG signing key 3A9C7EB37C2E5B8D2120D02F89995CF911C9BCB3, verified)
Independent reviewer identity: policedbc
Repository branch at audit start: audit/zwslcore-full-hardening-20261108T115454Z
Working tree at audit start: clean
HEAD at audit start: 1ce4bf6 fix: harden Provider Gateway security and timeouts

## Governance files inspected

| File | Status | Notes |
|------|--------|-------|
| zeaz.md | FIXED (P0) | Was saved GitHub HTML; replaced with canonical markdown ZeaZDev policy |
| AGENTS.md | OK | Repository agent contract referencing canonical zeaz.md policy |
| README.md | OK | Project overview + runtime + security defaults |
| CONTRIBUTING.md | OK | Development workflow, branch naming, PR guidance |
| SECURITY.md | OK | Vulnerability reporting + repository security baseline |
| GOVERNANCE.md | OK | Roles, change control, evidence and readiness |
| ROADMAP.md | OK | Template roadmap + future modules |
| IMPLEMENTATION-CHECKLIST.md | OK | Bootstrap/identity/security/development/release checklist |
| ZEAZ-INTRODUCTION.md | OK | Cross-agent execution framework + evidence states |
| .github/CODEOWNERS | OK | Ownership coverage |
| .github/dependabot.yml | OK | Dependabot configuration |
| .github/workflows/ | OK | CI, CodeQL, Dependency Review, Provider Supply Chain, auto-fix, automated-audit |

## Subsystems discovered

| Subsystem | Location | Language | Status |
|-----------|----------|----------|--------|
| Provider Gateway (multi-provider AI gateway) | services/provider/zeaz_provider/ | Python | Well-engineered; auth, rate limiting, circuit breakers, cost policy, SSE streaming |
| Provider tests | services/provider/tests/ | Python | test_security.py, test_observability.py |
| Engineering control plane | services/engineering/ | Python | Tasks, worktrees, snapshots, evidence, security gate, validation, MCP, agents |
| Model catalog | services/model_catalog/ | Python | catalog, inventory, models.dev sync, selector |
| Scripts (install, doctor, smoke, backup, engineer, etc.) | scripts/ | Bash + Python | Installer, diagnostics, engineering runtime |
| Compose stack | compose.yaml | YAML | Ollama, LiteLLM, Provider, Open WebUI |
| Provider Dockerfile | services/provider/Dockerfile | Dockerfile | Chainguard base, immutable digests, non-root, read-only rootfs |
| CI workflows | .github/workflows/ | YAML | CI, CodeQL, Dependency Review, Supply Chain, auto-fix, audit |
| Tests | tests/ | Python + Bash | 211 unit tests, all passing |

## Findings summary by severity

| Severity | Count | Example |
|----------|-------|---------|
| P0 Critical | 1 | zeaz.md was HTML, not markdown policy — FIXED |
| P1 High | 1 | build-scan-sbom FAILURE on current main — BLOCKS ALL PR MERGES |
| P2 Medium | 2 | Ruff lint (resolved via pyproject.toml config); Shellcheck warnings (resolved) |
| P3 Low | 2 | Provider container ZEAZ_HOST=0.0.0.0 (documented); Host PostgreSQL outside backup scope (documented) |
| P4 Informational | 22 | Open PR inventory — ALL stale (based on older main), all REQUEST CHANGES |

## Fixes implemented (3 GPG-signed commits as cvsz)

1. d2b8708 — docs: replace zeaz.md HTML with markdown policy and add audit reports
2. a1fdfe0 — lint: apply ruff check --fix and ruff format across Python code (adds root pyproject.toml)
3. d5743d6 — lint: resolve ShellCheck warnings across shell scripts

All commits GPG-signed and verified (Good signature from cvsz-signer).

## Validation results (all passing)

- validate_repo.py: PASS
- Unit tests: 211/211 PASS
- py_compile / compileall: PASS
- ruff check: PASS (with root pyproject.toml config)
- ruff format: PASS (all files formatted)
- shellcheck -x: PASS (exit 0 on all shell scripts)

## Blocker

build-scan-sbom (Provider image vulnerability scan, severity-cutoff: high) FAILS on
current main. Verified via PR #101 rebase CI run. Blocks all PR merges until the
Chainguard base image digest or a dependency is updated and the scan passes.

## Related audit reports

- docs/audit/ARCHITECTURE_AUDIT.md
- docs/audit/SECURITY_AUDIT.md (includes S1-02 build-scan-sbom P1 blocker)
- docs/audit/PENETRATION_TEST_REPORT.md
- docs/audit/INTEGRATION_TEST_REPORT.md
- docs/audit/BUILD_AND_LINT_REPORT.md
- docs/audit/DEPENDENCY_UPGRADE_REPORT.md
- docs/audit/PULL_REQUEST_AUDIT.md
- docs/audit/INDEPENDENT_REVIEW_REPORT.md
- docs/audit/GPG_VERIFICATION_REPORT.md
- docs/audit/FINAL_VALIDATION_REPORT.md
