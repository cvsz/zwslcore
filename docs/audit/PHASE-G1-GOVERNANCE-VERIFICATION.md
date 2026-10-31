# Phase G.1 — Governance Verification

**Repository**: `cvsz/zwslcore`
**PR**: #78 — fix(ai): load provider credentials safely from repository .env
**Authorized Head SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**Base Branch**: `main`
**Date**: 2026-11-01
**API Identity**: cvsz (repository owner)

---

## 1. Branch Protection Verification

**API endpoint**: `GET /repos/cvsz/zwslcore/branches/main/protection`
**Result**: SUCCESS (200 OK)

| Setting | Observed Value | Required | Status |
|---------|---------------|----------|--------|
| Protected branch | main | — | ✓ |
| Strict status checks | true | true | ✓ |
| Required status checks | 6 contexts | 6 contexts | ✓ |
| Required approving reviews | 1 | 1 | ✓ |
| Dismiss stale reviews | true | true | ✓ |
| Require code owner reviews | true | true | ✓ |
| Require last push approval | true | true | ✓ |
| Require conversation resolution | null | — | — |
| Enforce admins | true | true | ✓ |
| Allow force pushes | false | false | ✓ |
| Allow deletions | false | false | ✓ |
| Required signatures | false | — | — |
| Rulesets | None | — | ✓ |

**Required status check contexts**:
1. repository-baseline
2. Analyze GitHub Actions
3. dependency-review
4. CodeQL
5. build-scan-sbom
6. windows-installer

---

## 2. Ruleset Verification

**API endpoint**: `GET /repos/cvsz/zwslcore/rulesets`
**Result**: Empty array — no rulesets configured.

---

## 3. Required Check Run Verification

**API endpoint**: `GET /repos/cvsz/zwslcore/commits/a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e/check-runs`
**Result**: 7 check runs, all on exact authorized SHA

| Check | SHA Match | Conclusion | Required | Result |
|-------|-----------|------------|----------|--------|
| repository-baseline | ✓ | SUCCESS | Yes | PASS |
| Analyze GitHub Actions | ✓ | SUCCESS | Yes | PASS |
| dependency-review | ✓ | SUCCESS | Yes | PASS |
| CodeQL | ✓ | SUCCESS | Yes | PASS |
| build-scan-sbom | ✓ | SUCCESS | Yes | PASS |
| windows-installer | ✓ | SUCCESS | Yes | PASS |
| attest-trusted-build | ✓ | SKIPPED | No | N/A |

**All 6 required checks: PASS ✓**

---

## 4. PR #78 Verification

| Field | Observed | Expected | Match |
|-------|----------|----------|-------|
| State | OPEN | OPEN | ✓ |
| Draft | false | false | ✓ |
| Merged | false | false | ✓ |
| Base | main | main | ✓ |
| Head SHA | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | ✓ |
| Mergeable | MERGEABLE | MERGEABLE | ✓ |
| Review Decision | APPROVED | APPROVED | ✓ |
| Reviewer | policedbc | policedbc | ✓ |
| Reviewed SHA | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | ✓ |
| Dismissed | No | No | ✓ |

---

## 5. PR #73 Preservation

| Field | Observed | Expected | Changed |
|-------|----------|----------|---------|
| Head SHA | `44fdf4e72638b51d3e7a4a4ce0a70140700c880a` | Same | NO |
| State | OPEN | Same | NO |
| Draft | false | Same | NO |
| Mergeable | MERGEABLE | Same | NO |
| Review Decision | APPROVED | Same | NO |

**PR #73 preserved: YES**

---

## 6. Local Repository State

| Item | Value |
|------|-------|
| Branch | `feat/zwslcore-worktree-security-hardening` |
| HEAD | `c68f9d5a5ede8110ab2bf088058f825596d03c8f` |
| Remote HEAD | `c68f9d5a5ede8110ab2bf088058f825596d03c8f` (matches) |
| Working tree | Clean |
| GPG signing | Active |
| GPG key | `8644B3973EA1743EF5D21EBA87A69650EB250939` |

---

## 7. Conclusion

All governance gates verified:
- Branch protection correctly configured ✓
- All 6 required checks SUCCESS on exact SHA ✓
- policedbc APPROVED current on exact SHA ✓
- 0 unresolved review threads ✓
- PR #78 OPEN, MERGEABLE ✓
- PR #73 preserved ✓

**Governance status**: VERIFIED ✓
