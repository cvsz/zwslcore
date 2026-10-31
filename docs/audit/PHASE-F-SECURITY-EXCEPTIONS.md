# Phase F Security Exceptions

**Repository**: `cvsz/zwslcore`
**Date**: 2026-11-01

---

## 1. Active Security Exceptions

No security exceptions have been granted in Phase F.

All CVEs remain unmitigated:
- CVE-2026-115557: Critical, no fix available — 14 PRs blocked
- CVE-2026-114613: High, fix not applicable in distroless — same 14 PRs

---

## 2. Exception Request Template (for future use)

If a temporary exception is needed, document:

| Field | Value |
|-------|-------|
| Exception ID | SEC-EXC-YYYYMMDD-### |
| CVE/ID | |
| Affected PR(s) | |
| Requested by | |
| Approved by | |
| Rationale | |
| Expiry date | |
| Compensating controls | |
| Review date | |

---

## 3. Compensating Controls (existing)

- Build-scan-sbom gate blocks merge when Critical vulnerabilities present
- CodeQL scanning enabled on all PRs targeting `main`
- Dependency review enabled on all PRs targeting `main`
- Secret scanning (TruffleHog) enabled in CI
- GPG commit signing required
- Branch protection with strict mode

---

## 4. Review Schedule

Next review of security exceptions: Upon upstream Chainguard patched image availability or upon explicit user request.
