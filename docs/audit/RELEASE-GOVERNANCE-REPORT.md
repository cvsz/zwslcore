# Release Governance Report

**Repository**: `cvsz/zwslcore`  
**Date**: 2026-11-01  
**Actor**: cvsz (engineering operator)

---

## 1. Branch Protection Configuration

**Source**: `GET /repos/cvsz/zwslcore/branches/main/protection` (GitHub API)

| Setting | Observed Value | Required | Status |
|---------|---------------|----------|--------|
| Required status checks | `repository-baseline`, `Analyze GitHub Actions`, `dependency-review`, `CodeQL`, `build-scan-sbom`, `windows-installer` | 6 checks | VERIFIED |
| Strict mode | true | true | VERIFIED |
| Required approving reviews | 1 | >= 1 | VERIFIED |
| Dismiss stale reviews | true | true | VERIFIED |
| Require code owner reviews | true | true | VERIFIED |
| Require last push approval | true | true | VERIFIED |
| Require conversation resolution | null | — | Not configured |
| Enforce admins | true | true | VERIFIED |
| Allow force pushes | false | false | VERIFIED |
| Allow deletions | false | false | VERIFIED |
| Required signatures | false | — | Not enforced |
| Rulesets | None | — | None configured |

**Overall governance status**: VERIFIED — All required controls are enabled and properly configured.

---

## 2. Identity Separation

| Identity | Role | Authorized Operations |
|----------|------|----------------------|
| `cvsz` | Repository owner, engineering operator, authorized merge operator | Repository inspection, engineering changes, PR merges (with authorization) |
| `policedbc` | Independent reviewer, security auditor, independent approval authority | PR reviews, security audits, risk acceptance decisions |

**Identity separation verified**: `cvsz` and `policedbc` are separate GitHub accounts with separate tokens.

---

## 3. Gate Recorder Status

| Gate | Status | Evidence |
|------|--------|----------|
| Exact SHA verification | PASS | PR #78 head SHA verified against authorized SHA |
| Independent approval | PASS | policedbc APPROVED on exact SHA |
| Review threads | PASS | 0 unresolved human threads |
| Required checks | FAIL | build-scan-sbom FAILURE |
| Security scan | FAIL | build-scan-sbom FAILURE (CVE-2026-115557) |
| Branch protection | PASS | Verified via GitHub API |
| Mergeability | PASS | MERGEABLE |

---

## 4. Authorization Boundaries

| PR | Authorized SHA | Current SHA | Authorization Valid | Merge Status |
|-----|---------------|-------------|---------------------|--------------|
| #78 | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | `6f9f45ceb862509b4e539c58c92b618d0db5fba2` | NO (SHA changed) | BLOCKED (SHA mismatch + CI failure) |
| #73 | `44fdf4e72638b51d3e7a4a4ce0a70140700c880a` | `44fdf4e72638b51d3e7a4a4ce0a70140700c880a` | N/A (no authorization yet) | Not authorized |

---

## 5. Rulesets

| Ruleset | Enforcement | Rules | Status |
|---------|-------------|-------|--------|
| None | — | — | No rulesets configured |

---
