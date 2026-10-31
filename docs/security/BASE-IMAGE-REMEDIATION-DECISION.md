# Base Image Remediation Decision

**Repository**: `cvsz/zwslcore`  
**Dockerfile**: `services/provider/Dockerfile`  
**Current base image**: `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285`  
**CVE**: CVE-2026-115557 (Critical, no fix available for Python 3.15)  
**Date**: 2026-11-01  
**Actor**: cvsz (engineering operator)

---

## 1. Candidate Evaluation

All locally available images were scanned with `grype 0.121.0`. The `build-scan-sbom` CI workflow uses `anchore/scan-action` with `fail-build: true` and `severity-cutoff: high`, meaning ANY Critical or High severity vulnerability causes build failure.

### Candidate A — Patched Python 3.15 Chainguard Image

| Criterion | Finding |
|-----------|---------|
| Image available locally | `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285` |
| CVE-2026-115557 fix | **None available** |
| Other Critical CVEs | None |
| Other High CVEs | CVE-2026-114613 (fix: 26.2.2-r1) |
| Passes `severity-cutoff: high` | NO |
| Registry access | BLOCKED (TLS certificate error on cgr.dev) |
| Decision | **REJECTED** — Critical CVE with no fix |

### Candidate B — Python 3.14 Chainguard Image

Three Python 3.14 Chainguard images available locally:

| Image | Digest | Size | Critical CVEs | High CVEs | CVE-2026-115557 Fix | Passes Cutoff |
|-------|--------|------|---------------|-----------|---------------------|---------------|
| sha256:3f411b4aac1e | 3f411b4aac1e | 102MB | 6 | 1 | Listed as `3.14.10_git20261028-r0` but installed version is 3.14.8 | NO |
| sha256:c07959e43e3e | c07959e43e3e | 989MB | 8 | 4 | Listed as `3.14.10_git20261028-r0` but installed version not determined | NO |
| sha256:733f745e7ec1 | 733f745e7ec1 | 992MB | 5 | 3 | Fix: None | NO |

**Decision**: **REJECTED** — All Python 3.14 images still have multiple Critical CVEs (CVE-2026-111497, CVE-2026-91403, etc.) that would fail `severity-cutoff: high`.

### Candidate C — Google Distroless Python

| Criterion | Finding |
|-----------|---------|
| Image | `gcr.io/distroless/python3:latest@sha256:0db804f397ca` |
| Size | 90MB |
| Critical CVEs | 1 (CVE-2026-19445, won't fix) |
| High CVEs | 6 (all won't fix) |
| Passes `severity-cutoff: high` | NO |
| Decision | **REJECTED** — Critical CVE with won't fix status |

### Candidate D — Debian Slim Python

| Criterion | Finding |
|-----------|---------|
| Image | `python:3.15-slim-bookworm@sha256:4e03260adeeebafccd084f3584e6b84823aba5651cfb53ef8a078ed441ddf9cd` |
| Critical CVEs | 3 |
| High CVEs | 74 |
| Passes `severity-cutoff: high` | NO |
| Decision | **REJECTED** — Significantly more CVEs than Chainguard |

---

## 2. Decision

**No available base image passes `severity-cutoff: high`** (zero Critical AND zero High CVEs). All Chainguard images have at least one Critical CVE. Debian-based images have significantly more.

**Selected remediation**: None technically available at this time.

**Required action**: Formal security exception process.

---

## 3. Security Exception Request

| Field | Value |
|-------|-------|
| Exception ID | SEC-EXC-20261101-001 |
| CVE | CVE-2026-115557 |
| Severity | Critical |
| Affected PRs | #102, #87, #88, #80, #70, #69, #64, #71, #78 |
| Root cause | No upstream fix for `python-3.15`; no alternative base image passes scan policy |
| Compensating controls | CodeQL scanning, dependency review, secret scanning, runtime non-root user, read-only filesystem, dropped capabilities, no-new-privileges |
| Exploitability | Unknown — requires vendor advisory analysis |
| Required approval | policedbc (independent security auditor) |
| Status | PENDING_REVIEW |

---

## 4. Evidence

- Grype scan results for all locally available images (retained)
- Docker image digests recorded in TOTAL-RECOVERY-BASELINE.md
- CI workflow definition in `.github/workflows/provider-supply-chain.yml`
- Provider Dockerfile in `services/provider/Dockerfile`

---
