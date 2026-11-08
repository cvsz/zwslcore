# Residual Risks — cvsz/zwslcore

**Generated:** 2026-11-08  
**Status:** DOCUMENTED

## 1. Accepted Risks (with Compensating Controls)

| Risk | CVE | Severity | Likelihood | Impact | Control | Review Cadence |
|------|-----|----------|-----------|--------|---------|----------------|
| SQLite command injection | CVE-2026-119586 | High | Low | High | Non-root, read-only rootfs, dropped caps, loopback binding, no .recover exposure | 90 days |
| glibc vulnerability | CVE-2026-84243 | High | Low | High | Non-root, read-only rootfs, dropped caps, loopback binding, Python abstraction | 90 days |
| Chainguard base image CVE | CVE-2026-115557 | Critical | N/A (fixed) | N/A | Fixed in updated digest `1a009647...` | N/A (fixed) |

## 2. Unmitigated Risks

| Risk | Severity | Likelihood | Impact | Mitigation Status |
|------|----------|-----------|--------|-------------------|
| GPG signing blocked | Blocker | Medium | Blocker | Passphrase required; key available but passphrase not in environment |
| Windows/WSL2 untested | Blocker | N/A | Blocker | No Windows host available for testing |
| CI scan failure (accepted CVEs) | Blocker | N/A | Blocker | 2 High CVEs without fixes; risk accepted with compensating controls |
| No operational runbooks | Medium | N/A | Medium | Not created for current SHA |
| Untracked `s3.local.yaml` | Low | Low | Low | File is untracked; operator-local only |

## 3. Risks Requiring Monitor

| Risk | Trigger | Action |
|------|---------|--------|
| Chainguard publishes fixed python digest | New `python:latest` digest available | Evaluate updating Dockerfile again |
| sqlite-libs fix published | New `sqlite-libs` version in Wolfi | Update base image or apply patch |
| glibc fix published | New `glibc` version in Wolfi | Update base image or apply patch |
| GPG passphrase available | Correct passphrase provided | Complete GPG-signed merge |
| Windows host becomes available | Testing environment provisioned | Run Windows/WSL2 verification |
