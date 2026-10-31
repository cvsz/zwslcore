# Phase F Supply Chain Report

**Repository**: `cvsz/zwslcore`
**Date**: 2026-11-01
**Scanner**: grype 0.121.0
**Image scanned**: `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285`

---

## 1. Image Scan Results

Total vulnerabilities found: 7

| CVE/ID | Package | Version | Severity | Fix Available | Fix Version | Status |
|--------|---------|---------|----------|---------------|-------------|--------|
| CVE-2026-115557 | python-3.15 | N/A | Critical | No | None | UNFIXED |
| CVE-2026-114613 | py3-pip-wheel | N/A | High | Yes | 26.2.2-r1 | NOT APPLICABLE (distroless) |
| CVE-2026-111943 | py3-pip-wheel | N/A | Medium | Yes | 26.2.2-r2 | NOT APPLICABLE (distroless) |
| CVE-2026-114583 | python-3.15 | N/A | Medium | No | None | UNFIXED |
| CVE-2026-103995 | python-3.15 | N/A | Low | No | None | UNFIXED |
| GHSA-j586-36cw-2gc2 | — | N/A | Unknown | Yes | 26.2.2-r1 | NOT APPLICABLE |
| GO-2026-6809 | — | N/A | Unknown | Yes | 26.2.2-r2 | NOT APPLICABLE |

---

## 2. Critical Finding: CVE-2026-115557

- **Package**: python-3.15
- **Severity**: Critical
- **Fix available**: No
- **Impact**: All provider image builds fail `build-scan-sbom`
- **PRs blocked**: #102, #87, #88, #80, #70, #69, #64, #71

### Patched images found locally

| Image Digest | Python Version | CVE-2026-115557 Fix |
|--------------|----------------|---------------------|
| `sha256:3f411b4aac1ed9cd6c9dec1486f92a8898737d9d6f95488dd727ca7d6f5254ee` | 3.14 | 3.14.10_git20261028-r0 |
| `sha256:c07959e43e3edece176d20c32428a53014379790169af4ea5de1dc47277eba75` | 3.14 | 3.14.10_git20261028-r0 |

**Assessment**: Patched Python 3.14 images exist locally but switching from Python 3.15 requires:
- Compatibility testing of provider code
- requirements.lock hash updates
- Dockerfile digest changes
- Full CI re-run

Not yet verified for production use.

---

## 3. Registry Access

- **cgr.dev**: TLS certificate error (`x509: certificate signed by unknown authority`)
- **Cannot pull newer images** for verification
- **Cannot verify vendor advisories** through registry

---

## 4. Affected PRs

| PR | Head SHA | SBOM Status | Primary Blocker |
|-----|----------|-------------|-----------------|
| #102 | 42792aa18167 | FAILURE | CVE-2026-115557 Critical |
| #101 | 3d8c6e07bced | FAILURE | CVE-2026-115557 Critical |
| #100 | f7efe2686bb6 | FAILURE | CVE-2026-115557 Critical |
| #91 | 671e908562ea | FAILURE | CVE-2026-115557 Critical |
| #90 | f528fe05b449 | FAILURE | CVE-2026-115557 Critical |
| #89 | 1fc11aef200a | FAILURE | CVE-2026-115557 Critical |
| #88 | 5ba3f66400e6 | FAILURE | CVE-2026-115557 Critical |
| #87 | b624aae2bb34 | FAILURE | CVE-2026-115557 Critical |
| #86 | bf7568af3c67 | FAILURE | CVE-2026-115557 Critical |
| #85 | 800c407a60a0 | FAILURE | CVE-2026-115557 Critical |
| #84 | 678987786e63 | FAILURE | CVE-2026-115557 Critical |
| #82 | 00b20d07f561 | FAILURE | CVE-2026-115557 Critical |
| #80 | db0bda3e6c4c | FAILURE | CVE-2026-115557 Critical |
| #79 | 62afa1cec740 | FAILURE | CVE-2026-115557 Critical |
| #76 | f8b7c54f944b | FAILURE | CVE-2026-115557 Critical |
| #71 | 5921251d2701 | FAILURE | CVE-2026-115557 Critical |

---

## 5. Recommendations

1. **Do not suppress CVE-2026-115557** to obtain green CI
2. **Do not switch to unverified patched image** without compatibility testing
3. **Wait for upstream Chainguard patched Python 3.15 image** or verify local Python 3.14 images
4. **Document exception** with owner, rationale, expiry, and compensating controls if temporary exception is needed
