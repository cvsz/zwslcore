# Phase F SBOM Report

**Repository**: `cvsz/zwslcore`
**Date**: 2026-11-01
**Scanner**: grype 0.121.0 (DB v6.1.10)

---

## 1. Provider Image SBOM

**Image**: `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285`
**Scan outcome**: FAILURE (Critical vulnerability present)

---

## 2. Vulnerability Summary

| Severity | Count | CVEs |
|----------|-------|------|
| Critical | 1 | CVE-2026-115557 |
| High | 1 | CVE-2026-114613 |
| Medium | 2 | CVE-2026-111943, CVE-2026-114583 |
| Low | 1 | CVE-2026-103995 |
| Unknown | 2 | GHSA-j586-36cw-2gc2, GO-2026-6809 |

---

## 3. Fix Availability

| Fix Status | Count | Details |
|------------|-------|---------|
| No fix available | 3 | CVE-2026-115557, CVE-2026-114583, CVE-2026-103995 |
| Fix available but N/A (distroless) | 4 | CVE-2026-114613 (26.2.2-r1), CVE-2026-111943 (26.2.2-r2), GHSA-j586-36cw-2gc2, GO-2026-6809 |

---

## 4. SBOM Generation Evidence

- Local grype scan completed successfully
- Image digest: `sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285`
- Scanner database version: v6.1.10
- cgr.dev registry access blocked by TLS certificate error — cannot pull newer images

---

## 5. PRs with SBOM=SUCCESS (not blocked by CVE)

| PR | Head SHA | SBOM | Other Blockers |
|-----|----------|------|----------------|
| #78 | a72fc000284f | SUCCESS | None — READY FOR AUTHORIZATION |
| #73 | 44fdf4e72638 | SUCCESS | None — READY FOR AUTHORIZATION |
| #72 | 15e5de2026af | SUCCESS | 3 required checks not triggered — VERIFICATION REQUIRED |
| #70 | 2a0878ea2aae | SUCCESS | No independent review |
| #69 | 918fab437e0e | SUCCESS | Draft, no review |
| #64 | 2122448c37f1 | SUCCESS | Draft, no review |

---

## 6. Recommendations

1. Preserve SBOM scan evidence for all PRs
2. Do not weaken Grype fail-on severity
3. Do not replace digest-pinned images with mutable tags
4. Document any security exceptions with owner, rationale, expiry
