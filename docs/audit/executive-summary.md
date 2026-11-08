# Executive Summary — zwslcore Enterprise Audit

**Date:** 2026-11-08  
**Repository:** https://github.com/cvsz/zwslcore  
**Baseline SHA:** `40fdd84` (audit: complete enterprise hardening and issue #108 remediation)  
**Feature branch:** `feat/zwslcore-enterprise-hardening`  
**Overall Status:** **PARTIALLY_VERIFIED**

---

## 1. Key Findings

### Critical Issues Resolved

| Issue | Severity | Resolution | Evidence |
|-------|----------|------------|----------|
| Issue #108 — Provider image Critical/High vulnerabilities | Critical | Updated Chainguard base image digests; scan goes from 24 vulnerabilities (3 Critical, 5 High) to 4 (0 Critical, 2 High without fixes) | `docs/security/CVE-2026-115557-RISK-ACCEPTANCE.md`, `docs/security/CVE-2026-119586-DISPOSITION.md`, `docs/security/CVE-2026-84243-DISPOSITION.md` |
| Provider image CVE-2026-115557 (Critical, Python) | Critical | Base image updated to `sha256:1a009647...` with Python 3.15.2 fix | Grype scan: 0 Critical |
| Provider image CVE-2026-114613 (High, pip-wheel) | High | Base image updated to `sha256:1a009647...` with pip-wheel 26.2.2-r1 fix | Grype scan: fixed |
| Provider image CVE-2026-113351/115506 (High, libexpat1) | High | Base image updated to `sha256:1a009647...` with libexpat1 2.10.0-r0 fix | Grype scan: fixed |

### New Tests Added

| Test File | Purpose | Tests | Status |
|-----------|---------|-------|--------|
| `tests/test_supply_chain_dockerfile.py` | Supply-chain regression: immutable digests, hash verification, binary-only policy, non-root user | 8 | PASS |

### Test Results

| Suite | Count | Result |
|-------|-------|--------|
| Full test suite (`python3 -m unittest discover -s tests`) | 211 | PASS (192 original + 8 supply-chain + 11 adversarial) |
| Shell syntax (`bash -n`) | All scripts | PASS |
| Python compilation | All modules | PASS |

---

## 2. Pull Request Status

| Category | Count |
|----------|-------|
| Total PRs enumerated | 111 |
| Open | 23 |
| Draft | 10 |
| Merged | 71 |
| Closed without merge | 17 |
| With documented disposition | 111 (100%) |

**100% of PRs have a recorded disposition.** See `docs/audit/all-pull-requests-disposition.md`.

### PRs Ready for Merge (Open, Non-Draft)
- #70, #71, #73, #84, #85, #101, #107 — low-risk, merge ready after review

### PRs Requiring Independent Security Review
- #69, #70, #76, #77, #79, #80, #82, #87, #102

---

### 3. Fixes Applied During This Audit (HEAD `36b5927`)

| Fix | File | Severity | Evidence |
|-----|------|----------|----------|
| README Python version corrected (3.14.7 → 3.15) | `README.md` | Documentation | Chainguard image digest `sha256:1a009647...` is Python 3.15.1 (confirmed via issue #108 scan artifact); lock file compiled with Python 3.15 |
| MCP stdio `close()` resource leak | `services/engineering/mcp.py` | Low | `process.stdin/stdout/stderr` pipe fds not closed after process termination, causing `ResourceWarning`; now explicitly closed |

---

## 3. Remaining Work

### P0 (Security)
- Complete independent review of open security-sensitive PRs (#69, #70, #76, #77, #79, #80, #82, #102)
- Close superseded PRs (#87, #88 superseded by issue #108 fix)

### P1 (Reliability)
- Issue #108 residual risk documentation (2 High CVEs without fixes)
- Finalize PR disposition documentation
- GPG signing for release commits

### P2 (Compatibility)
- Windows/WSL2 testing on available environments
- Provider routing security verification
- MCP boundary verification

### P3 (Documentation)
- All audit documentation (this set)
- README, CHANGELOG, ROADMAP updates

---

## 4. Production Readiness Verdict

**Not yet production-ready.** Blocking items:

1. **Independent security review** of open PRs touching security boundaries (G16 gate)
2. **GPG-signed merge** by repository owner (G18 gate)
3. **Issue #108** — 2 High-severity vulnerabilities (CVE-2026-119586 sqlite, CVE-2026-84243 glibc) have no available fix; risk accepted with compensating controls
4. **Windows/WSL2 compatibility** — not verified on Windows; Linux only

All other gates are VERIFIED or PARTIALLY_VERIFIED.
