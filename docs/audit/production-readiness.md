# Production Readiness — cvsz/zwslcore

**Generated:** 2026-11-08  
**Status:** NOT_PRODUCTION_READY (blocking gates below)

## 1. Readiness Gate Summary (G1–G20)

| Gate | ID | Status | Evidence |
|------|----|--------|----------|
| Repository baseline | G1 | PASS | HEAD bc1eb1c matches origin/main |
| Architecture review | G2 | PASS | docs/architecture.md |
| Application security | G3 | PASS | CVE documented; compensating controls |
| Secrets handling | G4 | PASS | Dotenv tested; no committed secrets |
| Dependency security | G5 | PASS | Lockfile pinned with hashes |
| Container security | G6 | CONDITIONAL | CVE-2026-115557 risk accepted |
| CVE disposition | G7 | RISK ACCEPTED | docs/security/ dispositions |
| SBOM/provenance | G8 | PASS | Supply-chain workflow generates SBOMs |
| Unit/integration tests | G9 | PASS | 200/200 |
| Platform compatibility | G10 | UNVERIFIED | Linux only; Windows not tested |
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

## 2. Blocking Items

| Item | Severity | Required Action |
|------|----------|----------------|
| G16 Independent review | Blocker | policedbc must review exact SHA on feature branch |
| G18 Exact SHA authorization | Blocker | cvsz must authorize and GPG-sign merge |
| G10 Platform compatibility | Blocker | Windows/WSL2 testing required |
| G12 CI/CD checks | Blocker | Grype scan fails at high threshold (2 accepted-risk CVEs) |
| G14 Operational readiness | Blocker | No operational runbooks |

## 3. Risk Acceptance

The following risks are formally accepted with compensating controls:

- **CVE-2026-119586** (sqlite-libs, High): No fix available; container hardening, no SQL exposure
- **CVE-2026-84243** (glibc-2.44, High): No fix available; container hardening, Python abstraction

## 4. Path to Production Readiness

1. Complete independent security review (G16)
2. CVsz GPG-signed merge (G18)
3. Address Windows/WSL2 testing gap (G10) or document as NOT_APPLICABLE
4. Resolve CI scan failure or formally accept 2 remaining CVEs (G12)
5. Create operational runbooks (G14)
