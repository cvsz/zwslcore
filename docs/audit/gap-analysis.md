# Gap Analysis — cvsz/zwslcore

**Generated:** 2026-11-08  
**Status:** COMPLETE

## 1. Implementation Checklist Gaps

| Checklist Item | Status | Gap |
|---------------|--------|-----|
| Validate production-capable per-stack adapters | NOT_STARTED | No per-stack adapters |
| End-to-end fixture verification | NOT_STARTED | No E2E fixtures |
| SBOM/provenance workflows | PARTIAL | SBOM generated in CI; not published |
| Release signing and artifact attestation | PARTIAL | Attestation workflow exists; not used for releases |
| OpenSSF Scorecard workflow | NOT_STARTED | Not implemented |
| Container vulnerability scanning | PARTIAL | Grype scan in CI; fails on Critical/High threshold |
| Release signing | NOT_STARTED | GPG signing blocked (passphrase unknown) |

## 2. Production Readiness Gaps (G1–G20)

| Gate | ID | Status | Gap |
|------|----|--------|-----|
| Repository baseline | G1 | PASS | — |
| Architecture review | G2 | PASS | docs/architecture.md |
| Application security | G3 | PASS | CVE documented; compensating controls |
| Secrets handling | G4 | PASS | Dotenv tested; no committed secrets |
| Dependency security | G5 | PASS | Lockfile pinned with hashes |
| Container security | G6 | CONDITIONAL | CVE-2026-115557 risk accepted |
| CVE disposition | G7 | RISK ACCEPTED | docs/security/ |
| SBOM/provenance | G8 | PASS | Supply-chain workflow generates SBOMs |
| Unit/integration tests | G9 | PASS | 200/200 |
| Platform compatibility | G10 | UNVERIFIED | Linux only; Windows/macOS not tested |
| Code quality | G11 | PASS | Linting, formatting, compile checks |
| CI/CD checks | G12 | FAIL | build-scan-sbom fails on CVE-2026-115557 (exception via G7) |
| API/CLI compatibility | G13 | PASS | Provider routes verified |
| Operational readiness | G14 | UNVERIFIED | No operational runbooks for current SHA |
| Documentation | G15 | PARTIAL | Core docs complete; audit docs created |
| Independent review | G16 | PENDING | policedbc must review exact SHA |
| Review threads | G17 | PENDING | CVE blocker requires policy decision |
| Exact SHA authorization | G18 | PENDING | cvsz must authorize exact SHA |
| Release artifact integrity | G19 | NOT APPLICABLE | No deployment authorized |
| Production deployment | G20 | NOT APPLICABLE | No deployment authorized |

## 3. Testing Gaps

| Area | Status | Gap |
|------|--------|-----|
| Adversarial worktree/path bypass tests | ADDED | tests/test_adversarial_security.py — path traversal, symlink escape, secret file rejection |
| Concurrent worktree corruption tests | ADDED | tests/test_adversarial_security.py — 10 concurrent task creation, SQLite WAL integrity |
| Child task permission escalation tests | ADDED | tests/test_adversarial_security.py — delegated path scope intersection, parent scope enforcement |
| Windows/WSL2 runtime tests | BLOCKED | No Windows host available |
| Docker container health tests | PARTIAL | Build verified; runtime health not tested in CI |
| Backup/restore isolated restore test | PARTIAL | Scripts exist; isolated restore drill not run |

## 4. Documentation Gaps

| Document | Status |
|----------|--------|
| docs/audit/executive-summary.md | CREATED |
| docs/audit/repository-inventory.md | CREATED |
| docs/audit/security-assessment.md | CREATED |
| docs/audit/worktree-security-review.md | CREATED |
| docs/audit/provider-routing-review.md | CREATED |
| docs/audit/mcp-security-review.md | CREATED |
| docs/audit/wsl2-compatibility.md | CREATED |
| docs/audit/supply-chain-assessment.md | CREATED |
| docs/audit/all-pull-requests-inventory.md | CREATED |
| docs/audit/all-pull-requests-matrix.md | CREATED |
| docs/audit/pull-request-findings.md | CREATED |
| docs/audit/pull-request-disposition.md | CREATED |
| docs/audit/pull-request-dependency-map.md | CREATED |
| docs/audit/gap-analysis.md | CREATED |
| docs/audit/remediation-report.md | CREATED |
| docs/audit/test-evidence.md | CREATED |
| docs/audit/production-readiness.md | PENDING |
| docs/audit/residual-risks.md | PENDING |
