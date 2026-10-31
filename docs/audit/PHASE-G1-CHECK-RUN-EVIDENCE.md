# Phase G.1 — Check Run Evidence

**Repository**: `cvsz/zwslcore`
**PR**: #78 — fix(ai): load provider credentials safely from repository .env
**Authorized Head SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**Date**: 2026-11-01
**API Identity**: cvsz (repository owner)

---

## 1. Check Runs on Exact SHA

**API endpoint**: `GET /repos/cvsz/zwslcore/commits/a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e/check-runs`

**Total check runs**: 7

| Check | head_sha | Conclusion | Status | Required Branch Protection Context |
|-------|----------|------------|--------|-----------------------------------|
| repository-baseline | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | SUCCESS | COMPLETED | Yes |
| Analyze GitHub Actions | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | SUCCESS | COMPLETED | Yes |
| dependency-review | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | SUCCESS | COMPLETED | Yes |
| CodeQL | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | SUCCESS | COMPLETED | Yes |
| build-scan-sbom | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | SUCCESS | COMPLETED | Yes |
| windows-installer | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | SUCCESS | COMPLETED | Yes |
| attest-trusted-build | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | SKIPPED | COMPLETED | No |

---

## 2. Required Check Summary

| Required Check | Required? | Conclusion | Result |
|----------------|-----------|------------|--------|
| repository-baseline | Yes | SUCCESS | PASS ✓ |
| Analyze GitHub Actions | Yes | SUCCESS | PASS ✓ |
| dependency-review | Yes | SUCCESS | PASS ✓ |
| CodeQL | Yes | SUCCESS | PASS ✓ |
| build-scan-sbom | Yes | SUCCESS | PASS ✓ |
| windows-installer | Yes | SUCCESS | PASS ✓ |

**All 6 required checks: PASS ✓**

**Optional check**: attest-trusted-build — SKIPPED (not in required contexts, not counted)

---

## 3. SHA Verification

All 7 check runs have `head_sha` equal to the authorized SHA `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`. No stale or mismatched check runs.

---

## 4. Conclusion

All required branch protection check contexts are satisfied on the exact authorized SHA. The PR is mergeable from a governance perspective.
