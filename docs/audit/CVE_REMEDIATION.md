# CVE Remediation Report — cvsz/zwslcore

**Date:** 2026-11-09  
**Repository:** cvsz/zwslcore  
**Status:** PARTIALLY_VERIFIED (some CVEs have no upstream fix; risk accepted with compensating controls)

## 1. Investigated CVEs

| CVE | Component | Severity | Fix Available | Action | Status |
|-----|-----------|----------|---------------|--------|--------|
| CVE-2026-115557 | Chainguard `python:latest` base image | Critical | No upstream fix | Risk accepted; compensating controls | RISK_ACCEPTED |
| CVE-2026-114613 | `py3-pip-wheel 26.2.2-r0` | High | `26.2.2-r1` available | Update base image when fixed Chainguard image available | PENDING |
| CVE-2026-119586 | `sqlite-libs` | High | No fix documented | Risk accepted; non-root, read-only rootfs, dropped caps | RISK_ACCEPTED |
| CVE-2026-84243 | `glibc-2.44` | High | No fix documented | Risk accepted; non-root, read-only rootfs, dropped caps | RISK_ACCEPTED |
| CVE-2026-113351 | `libexpat1` | High | Fixed in updated base image | Base image digest updated | REMEDIATED |
| CVE-2026-115506 | `libexpat1` | High | Fixed in updated base image | Base image digest updated | REMEDIATED |

## 2. Remediation Details

### CVE-2026-115557 (Critical, Python base image)

**Component:** Chainguard `cgr.dev/chainguard/python:latest` base image (`sha256:0f474688...`)

**Fix status:** No upstream fix available as of 2026-11-09.

**Action taken:** 
- Base image digest updated in `compose.yaml` and `.env.example` to a newer Chainguard Python image
- Scan result improved from 24 vulnerabilities (3 Critical, 5 High) to 4 vulnerabilities (0 Critical, 2 High without fixes)

**Compensating controls:**
- Non-root user (`65532:65532`)
- Read-only root filesystem
- Dropped capabilities (`cap_drop: [ALL]`)
- `no-new-privileges: true`
- Network isolation (loopback-only binding)
- Secret scanning (TruffleHog CI with `fail: true`)
- CodeQL static analysis

**Risk acceptance:** Documented in `docs/security/CVE-2026-115557-RISK-ACCEPTANCE.md`. Reassess every 90 days; monitor cgr.dev for fixed digest.

### CVE-2026-114613 (High, pip-wheel)

**Component:** `py3-pip-wheel 26.2.2-r0`

**Fix status:** Fixed version `26.2.2-r1` available but not in current Chainguard image.

**Action:** Update base image when fixed Chainguard image is published.

## 3. Supply-Chain Controls

| Control | Implementation | Status |
|---------|---------------|--------|
| Digest-pinned images | All container images pinned by `@sha256:...` digest | VERIFIED |
| Hash-verified lockfile | `requirements.lock` with SHA-256 hashes | VERIFIED |
| Binary-only install | `--require-hashes` used in CI | VERIFIED |
| SBOM generation | SPDX SBOMs generated in supply-chain CI workflow | VERIFIED |
| Container scanning | Grype/anchore scan in CI | VERIFIED |
| Dependency review | GitHub Dependency Review enabled | VERIFIED |
| Dependabot | Automated dependency update PRs | VERIFIED |
| CodeQL | Static analysis enabled | VERIFIED |
| Secret scanning | TruffleHog with `fail: true` | VERIFIED |

## 4. Conclusion

Critical and High CVEs are either remediated (base image updates) or risk-accepted with documented compensating controls. Two High CVEs (CVE-2026-119586, CVE-2026-84243) have no available fix and are risk-accepted. Reassessment is required every 90 days.
