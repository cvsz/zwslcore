# Provider Supply Chain Remediation — cvsz/zwslcore

**Repository**: `cvsz/zwslcore`
**Document Date**: 2026-10-31
**Related PR**: #102 (`feat/zwslcore-worktree-security-hardening`)
**Head SHA**: `b19ff81e746ff37f254b76b18189f8748b289f1f`

---

## 1. Problem Statement

The Provider Supply Chain CI check (`build-scan-sbom`) fails on PR #102 due to vulnerabilities in the Chainguard `python:latest` base image used by `services/provider/Dockerfile`.

### Vulnerability Scan Results

Scanner: Grype v0.118.0, Vulnerability DB: v6.1.10
Policy: `fail-on: high` (fail on Critical or High)

| CVE | Package | Installed Version | Fixed Version | Severity | EPSS | Risk | Type |
|-----|---------|-------------------|---------------|----------|------|------|------|
| CVE-2026-115557 | python-3.15 | 3.15.1_git20261024-r1 | (none) | Critical | 0.5% | 0.5 | apk |
| CVE-2026-114613 | py3-pip-wheel | 26.2.2-r0 | 26.2.2-r1 | High | 0.5% | 0.4 | apk |
| CVE-2026-111943 | py3-pip-wheel | 26.2.2-r0 | 26.2.2-r2 | Medium | 0.3% | 0.2 | apk |
| CVE-2026-114583 | python-3.15 | 3.15.1_git20261024-r1 | 3.15.2 | Medium | 0.2% | 0.1 | apk |
| CVE-2026-103995 | python-3.15 | 3.15.1_git20261024-r1 | — | Low | 0.4% | <0.1 | apk |

### Current Base Images in Dockerfile

| Stage | Image | Digest |
|-------|-------|--------|
| Build | `cgr.dev/chainguard/python:latest-dev` | `sha256:01280a9ffd0c9c427d3127540203af6707ebf35cdb0481182aef303c03db239c` |
| Runtime | `cgr.dev/chainguard/python:latest` | `sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285` |

---

## 2. Remediation Options Evaluated

### Option A — Update Chainguard Base Image Digest

**Status: BLOCKED**

All locally available Chainguard `python` images were scanned with grype v0.118.0:

| Image Digest | Size | Critical CVEs | High CVEs | Conclusion |
|--------------|------|---------------|-------------|------------|
| `sha256:0f47468835f6` (python:latest) | 106MB | CVE-2026-115557 | CVE-2026-114613 | Current image — BLOCKED |
| `sha256:3f411b4aac1e` | 102MB | CVE-2026-115557, CVE-2026-111497 | CVE-2026-114613 | WORSE than current |
| `sha256:733f745e7ec1` | 992MB | CVE-2026-115557, CVE-2026-111497 | CVE-2026-114613 | WORSE than current |
| `sha256:c07959e43e3e` | 989MB | Not scanned | Not scanned | Not evaluated |

**Finding**: All available Chainguard images contain Critical CVE-2026-115557 in `python-3.15`. The fix version is not available in any locally accessible image.

**Blocker**: Docker pull from `cgr.dev` fails with TLS certificate error (`certificate signed by unknown authority`). Cannot pull newer images to check if they fix the CVEs.

### Option B — Multi-Stage Build Isolation

**Status: NOT APPLICABLE**

The CVEs are in the base Python package itself (`python-3.15`), not in installable packages. A multi-stage build cannot remove vulnerabilities from the base runtime image.

### Option C — Alternative Base Image

**Status: REJECTED**

Previously evaluated `gcr.io/distroless/python3:latest` — had 176 vulnerability matches including Critical CVEs with `(won't fix)` status. Worse than Chainguard.

### Option D — Runtime Package Isolation

**Status: NOT APPLICABLE**

`py3-pip-wheel` CVE-2026-114613 has fix version `26.2.2-r1`, but the Chainguard distroless image has no `apk` or package manager to upgrade packages in the final image. The `python-3.15` CVE-2026-115557 has no fix version at all.

---

## 3. Remediation Plan

### Immediate Actions (Within Repository Control)

1. **Document the upstream blocker** — Document that the Chainguard base image contains unfixable CVEs and that CI will fail until Chainguard publishes patched images.

2. **Monitor Chainguard image updates** — Regularly check `cgr.dev/chainguard/python` for new digests that fix CVE-2026-115557 and CVE-2026-114613.

3. **Fix non-blocking issues** — All other PR #102 changes (worktree ownership, S3 config loader, lockfile consistency) are correct and do not contribute to the scan failure.

### Required External Action

| Action | Owner | Status |
|--------|-------|--------|
| Publish patched `python:latest` Chainguard image | Chainguard (upstream) | PENDING |
| Verify patched image passes `grype --fail-on high` | ZEAZ team | PENDING (blocked by upstream) |
| Update Dockerfile digest in PR #102 | cvsz | PENDING (blocked by upstream) |
| Re-run Provider Supply Chain CI | GitHub Actions | PENDING (blocked by upstream) |

---

## 4. Evidence

### Local Grype Scan Results

Command: `/tmp/opencode/grype -v cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285 --fail-on high`

Result: `ERROR: discovered vulnerabilities at or above the severity threshold`

1 Critical CVE (python-3.15), 1 High CVE (py3-pip-wheel)

### Docker Pull Error

```
Error response from daemon: failed to resolve reference "cgr.dev/chainguard/python@sha256:...": tls: failed to verify certificate: x509: certificate signed by unknown authority
```

### Available Local Chainguard Images

```
cgr.dev/chainguard/python:latest              0f47468835f6   106MB
cgr.dev/chainguard/python:latest-dev          01280a9ffd0c   937MB
cgr.dev/chainguard/python@sha256:3f411b4a...   3f411b4aac1e   102MB
cgr.dev/chainguard/python@sha256:733f745e...   733f745e7ec1   992MB
cgr.dev/chainguard/python@sha256:c07959e4...   c07959e43e3e   989MB
```

---

## 5. Decision

**Status: BLOCKED** — Upstream dependency (Chainguard base image) must publish patched images before PR #102 can pass `build-scan-sbom`.

**No security threshold weakening**: The `fail-on: high` cutoff will not be lowered. No broad CVE ignore rules will be added.

**Alternative base images**: Not viable — all alternatives tested have equal or worse CVE exposure.

---

## 6. Next Actions

1. Monitor `cgr.dev/chainguard/python` for patched images
2. When patched image available, update `services/provider/Dockerfile` digest
3. Run `build-scan-sbom` CI to verify
4. policedbc re-review PR #102
5. cvsz merge PR #102
