# Master Audit — zwslcore

Audit scope: complete enterprise engineering audit of the zwslcore repository
(cvsz/zwslcore), performed against the ZEAZ governance contract
(zeaz.md / AGENTS.md / SUPER ULTRA AI ORC v2.1).

Audit date: 2026-11-08
Auditor: OpenCode agent operating as cvsz (developer phase), with independent
review phase to be executed as policedbc.

Repository branch at audit start: audit/zwslcore-full-hardening-20261108T115454Z
Working tree at audit start: clean
HEAD: 1ce4bf6 fix: harden Provider Gateway security and timeouts

## Governance files inspected

| File | Status | Notes |
|------|--------|-------|
| zeaz.md | BLOCKER | Contains saved GitHub HTML instead of markdown policy (see P0-01) |
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
| P0 Critical | 1 | zeaz.md is HTML, not markdown policy |
| P1 High | 0 | None confirmed |
| P2 Medium | 1 | Ruff lint: 120 errors across Python code |
| P3 Low | 1 | Ruff format: 51 files unformatted |
| P3 Low | 1 | Shellcheck warnings across shell scripts |
| P4 Informational | 22 | Open PR inventory with mixed review/CI state |

## Definition of Done progress

- [x] zeaz.md and applicable AGENTS.md inspected
- [x] Complete architecture inventory
- [x] Complete bug and TODO assessment
- [ ] Confirmed defects fixed
- [ ] Missing functionality addressed
- [ ] Dependencies reviewed and upgraded where justified
- [ ] Build passed
- [ ] Lint passed
- [ ] Ruff passed
- [ ] ShellCheck passed
- [ ] Pytest passed
- [ ] Integration tests passed
- [ ] Security tests completed
- [ ] Penetration testing completed within authorized scope
- [ ] Regression tests passed
- [ ] All relevant open PRs reviewed
- [ ] Developer commits independently verified
- [ ] GPG status verified
- [ ] Independent review decisions recorded
- [ ] Eligible PRs merged
- [ ] Final repository state verified
- [ ] Reports generated
- [ ] Remaining blockers documented

## Related audit reports

- docs/audit/ARCHITECTURE_AUDIT.md
- docs/audit/SECURITY_AUDIT.md
- docs/audit/PENETRATION_TEST_REPORT.md
- docs/audit/INTEGRATION_TEST_REPORT.md
- docs/audit/BUILD_AND_LINT_REPORT.md
- docs/audit/DEPENDENCY_UPGRADE_REPORT.md
- docs/audit/PULL_REQUEST_AUDIT.md
- docs/audit/INDEPENDENT_REVIEW_REPORT.md
- docs/audit/GPG_VERIFICATION_REPORT.md
- docs/audit/FINAL_VALIDATION_REPORT.md
