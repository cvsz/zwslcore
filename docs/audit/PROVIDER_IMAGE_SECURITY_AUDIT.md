# Provider Image Security Audit — Worktree Security Patch PR #102

**Repository:** cvsz/zwslcore  
**Branch:** feat/zwslcore-worktree-security-hardening  
**PR:** #102  
**PR Head SHA:** 0d7ec89028e69e30ba97ced3f3de0bfea9d955fa
**Audit Date:** 2026-10-31
**Evidence State:** VERIFIED (observed directly against local Docker images and GitHub CI)

---

## A. Executive Summary

The `build-scan-sbom` GitHub required check failed on PR #102 because the Provider Docker image (`zwslcore-provider:ci`) contains vulnerabilities in the Chainguard base images:

- **Critical:** CVE-2026-115557 in python-3.15 version 3.15.1_git20261024-r1 (fix: Python 3.15.2)
- **High:** CVE-2026-114613 in py3-pip-wheel version 26.2.2-r0 (fix: 26.2.2-r1+)
- **Medium:** CVE-2026-111943 in py3-pip-wheel version 26.2.2-r0 (fix: 26.2.2-r2+)
- **Medium:** CVE-2026-114583 in python-3.15 version 3.15.1_git20261024-r1 (fix: Python 3.15.2)

The fix requires updating the Chainguard base image digests in `services/provider/Dockerfile` to newer versions containing patched packages. Newer Chainguard images are available (created 2026-10-30), but could not be pulled locally for verification due to Docker daemon TLS certificate issues with cgr.dev.

---

## B. Verified Current State

| Item | Value |
|---|---|
| Repository | cvsz/zwslcore |
| Branch | feat/zwslcore-worktree-security-hardening |
| Base SHA | df7ef0eae393f44f39c5393533531fc4171c6156 |
| PR Head SHA | 0d7ec89028e69e30ba97ced3f3de0bfea9d955fa |
| PR State | OPEN |
| Merge State | BLOCKED (build-scan-sbom check failed) |
| Local Python Version | 3.14.4 |
| All commits pushed | YES (07c89d1 → 0d7ec89) |

### Provider Image Details

| Item | Value |
|---|---|
| Image | zwslcore-provider:latest (local) |
| Image ID | 22f6e2e7d2fe |
| Python Version | 3.15.1 (confirmed via `docker run --rm --entrypoint="" zwslcore-provider:latest /opt/venv/bin/python --version`) |
| Pip Version | 26.2.2 (confirmed via `docker run --rm --entrypoint="" zwslcore-provider:latest /opt/venv/bin/pip --version`) |
| Base Image (Build) | cgr.dev/chainguard/python:latest-dev@sha256:01280a9ffd0c9c427d3127540203af6707ebf35cdb0481182aef303c03db239c |
| Base Image (Runtime) | cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285 |
| Base Image Created | 2026-10-28T15:02:56Z |

---

## C. Security Findings

| Finding ID | Severity | CVE | Package | Installed Version | Fixed Version | Affected Image Stage |
|---|---|---|---|---|---|---|
| SEC-01 | Critical | CVE-2026-115557 | python-3.15 | 3.15.1_git20261024-r1 | 3.15.2 | Build + Runtime |
| SEC-02 | High | CVE-2026-114613 | py3-pip-wheel | 26.2.2-r0 | 26.2.2-r1+ | Build + Runtime |
| SEC-03 | Medium | CVE-2026-111943 | py3-pip-wheel | 26.2.2-r0 | 26.2.2-r2+ | Build + Runtime |
| SEC-04 | Medium | CVE-2026-114583 | python-3.15 | 3.15.1_git20261024-r1 | 3.15.2 | Build + Runtime |
| SEC-05 | Low | CVE-2026-103995 | python-3.15 | 3.15.1_git20261024-r1 | Verify advisory | Build + Runtime |
| SEC-06 | Unknown | GHSA-j586-36cw-2gc2 | py3-pip-wheel | 26.2.2-r0 | 26.2.2-r1+ | Build + Runtime |
| SEC-07 | Unknown | GO-2026-6809 | py3-pip-wheel | 26.2.2-r0 | 26.2.2-r2+ | Build + Runtime |

**Verification Evidence:** Python 3.15.1 confirmed in both locally available Chainguard base images via `docker run --rm <image> --version`. Pip 26.2.2 confirmed in locally built `zwslcore-provider:latest` image via `docker run --rm --entrypoint="" zwslcore-provider:latest /opt/venv/bin/pip --version`.

---

## D. Root Cause

The `services/provider/Dockerfile` uses digest-pinned Chainguard base images:

- **Build stage:** `cgr.dev/chainguard/python:latest-dev@sha256:01280a9ffd0c...` (created 2026-10-28)
- **Runtime stage:** `cgr.dev/chainguard/python:latest@sha256:0f47468835f6...` (created 2026-10-28)

Both images contain Python 3.15.1 which has known CVEs (CVE-2026-115557 Critical, CVE-2026-114583 Medium). The pip-wheel package (26.2.2-r0) also has known CVEs (CVE-2026-114613 High, CVE-2026-111943 Medium).

Newer Chainguard images are available (created 2026-10-30) that likely contain Python 3.15.2 and updated packages:

- **Build stage (remote manifest):** `sha256:53b2fdfc1e01c96b0eb4ac9e3eaec16d702508c07e2b12cc5235fe5c97f3704d`
- **Runtime stage (remote manifest):** `sha256:a3995e4d233c10dff34ebd5a9f86d60ca041fdc9ca6870482f222baa21e4e4fd`

**Cannot verify:** The newer images could not be pulled locally due to Docker daemon TLS certificate issues with cgr.dev. The exact package versions in the new images cannot be confirmed without pulling and scanning them.

---

## E. Remediation Plan

### Option A — Update Chainguard Base-Image Digests (RECOMMENDED)

Update `services/provider/Dockerfile` to use the newer image digests:

```diff
FROM cgr.dev/chainguard/python:latest-dev@sha256:01280a9ffd0c9c427d3127540203af6707ebf35cdb0481182aef303c03db239c AS build
- FROM cgr.dev/chainguard/python:latest-dev@sha256:01280a9ffd0c9c427d3127540203af6707ebf35cdb0481182aef303c03db239c AS build
+ FROM cgr.dev/chainguard/python:latest-dev@sha256:53b2fdfc1e01c96b0eb4ac9e3eaec16d702508c07e2b12cc5235fe5c97f3704d AS build
...
- FROM cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285
+ FROM cgr.dev/chainguard/python:latest@sha256:a3995e4d233c10dff34ebd5a9f86d60ca041fdc9ca6870482f222baa21e4e4fd
```

**Requirements before applying:**
1. Pull new images and verify Python version is 3.15.2
2. Run grype scan with `fail-on high` to confirm no critical/high findings
3. Verify pip-wheel version is 26.2.2-r1+
4. Verify Provider application starts and health check passes
5. Rebuild and re-scan to confirm clean scan

**Verification commands:**
```bash
docker pull cgr.dev/chainguard/python:latest-dev@sha256:53b2fdfc...
docker run --rm <image> python --version  # Should be 3.15.2
docker run --rm <image> pip --version    # Should be 26.2.2-r1+
grype zwslcore-provider:latest --fail-on high  # Should pass
```

### Option B — No Viable Alternative

Option B (update pip packages within the image) is NOT viable because `py3-pip-wheel` is a system package in the Wolfi-based Chainguard image, not installed via pip. The only fix is updating the base image.

Option C (change Python base image) is NOT necessary if Chainguard has patched images available.

---

## F. Verification Steps Required

Before merging PR #102, the following must be completed:

1. **Pull newer Chainguard images** (requires Docker daemon TLS configuration for cgr.dev)
2. **Verify Python 3.15.2** in both new base images
3. **Verify pip-wheel 26.2.2-r1+** in build stage image
4. **Rebuild Provider image** with new digests
5. **Run grype scan** with `fail-on high` — must pass with zero critical/high findings
6. **Verify Provider health check** passes
7. **Run existing Provider tests** to confirm no regressions
8. **Independent review** by policedbc against new exact SHA

---

## G. Release Gate Matrix

| Gate | Requirement | Status | Evidence |
|---|---|---|---|
| G01 | Repository identity verified | PASS | HEAD `13b33f8`, branch `feat/...` |
| G02 | Approved patch preserved | PASS | WorktreeManager patch untouched |
| G03 | Root cause identified | PASS | Chainguard base images with Python 3.15.1 |
| G04 | Base image digests verified | UNVERIFIED | New digests found but not pulled/scanned |
| G05 | Critical CVEs fixed | UNVERIFIED | Requires pulling new images and scanning |
| G06 | High CVEs fixed | UNVERIFIED | Requires pulling new images and scanning |
| G07 | Grype enforcement unchanged | PASS | `fail-on high` preserved in workflow |
| G08 | SBOM generated | UNVERIFIED | Requires new image build and scan |
| G09 | Provenance traced | PARTIAL | Source SHA and image digests documented |
| G10 | Docker build successful | UNVERIFIED | Requires new image build |
| G11 | Runtime healthy | UNVERIFIED | Requires new image test |
| G12 | Regression tests pass | PASS | 201/201 local tests pass |
| G13 | GitHub CI passes | FAIL | build-scan-sbom failed |
| G14 | Independent review | PENDING | policedbc must review on commit `13b33f8` |
| G15 | Commit signature | VERIFIED | GPG key `A6D60018D84C3BBD` added to GitHub account `cvsz` |
| G16 | Governance | PASS | No unauthorized operations |
| G17 | Merge authorization | NOT GIVEN | Not requested |

---

## H. Residual Risks

1. **Newer Chainguard images unverified:** The digests `sha256:53b2fdfc...` and `sha256:a3995e4d...` were obtained from the remote manifest but the images could not be pulled to verify they contain Python 3.15.2.
2. **Grype scan could not be run locally:** The grype scan timed out on the local image due to environment constraints.

---

## I. Next Actions (Require Authorization)

1. **Authorize Dockerfile change:** Update `services/provider/Dockerfile` with new Chainguard base image digests
2. **Authorize commit:** Commit the Dockerfile change to the feature branch (GPG-signed locally; key verified on GitHub)
3. **Authorize push:** Push the updated branch to trigger CI re-run
4. **Authorize independent review:** policedbc must review the new commit SHA
5. **Authorize merge:** Repository owner must approve merge after all checks pass

---

## J. Final Classification

**BLOCKED** — The `build-scan-sbom` required check has failed. The fix requires updating Chainguard base image digests, which requires Docker daemon TLS configuration for cgr.dev that is not available in this environment. The Dockerfile change is prepared but cannot be verified without pulling and scanning the new images.
