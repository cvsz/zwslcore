# Phase F Execution Report — Governed PR Recovery & Merge Execution

**Repository**: `cvsz/zwslcore`
**Branch**: `feat/zwslcore-worktree-security-hardening`
**Baseline SHA**: `42792aa181673f772c8791c5c249be3be23c55d4`
**Date**: 2026-11-01
**Execution Mode**: Mode A (Audit) → Mode B (Safe Remediation)
**Status**: PARTIALLY VERIFIED — Stopping before Mode D (Authorized Merge)

---

## 1. Executive Summary

Phase F began with Mode A (Audit) and Mode B (Safe Remediation). The Phase E baseline was verified against live GitHub state — HEAD `42792aa` matches exactly, GPG signed, working tree clean. All 23 open PRs were revalidated.

**Key findings:**
- **2 PRs READY FOR EXPLICIT AUTHORIZATION**: #78, #73 (all gates pass, policedbc APPROVED)
- **1 PR VERIFICATION REQUIRED**: #72 (3 required checks not triggered due to non-main base branch)
- **5 PRs awaiting independent review**: #82, #79, #76, #85, #84 (policedbc review requested)
- **1 PR BLOCKED (unknown state)**: #77 (draft, conflicting, no CI, non-main base)
- **14 PRs BLOCKED (Chainguard CVE or no review)**: #102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #76, #71, #70, #69, #64

**No PRs were merged in Phase F.** Phase F stopped before Mode D (Authorized Merge) per governance rules, awaiting explicit user authorization per PR.

---

## 2. Verified Baseline

| Item | Value |
|------|-------|
| Repository | `cvsz/zwslcore` |
| Branch | `feat/zwslcore-worktree-security-hardening` |
| SHA | `42792aa181673f772c8791c5c249be3be23c55d4` |
| Remote SHA | `42792aa181673f772c8791c5c249be3be23c55d4` (matches) |
| Working tree | Clean |
| GPG key | `8644B3973EA1743EF5D21EBA87A69650EB250939` (cvsz <seaza@msn.com>) |
| GitHub identity | `cvsz` (active) |
| policedbc available | Yes (inactive) |
| Branch protection | 6 required checks, strict=True, 1 required review, dismiss stale, code owner reviews |
| Rulesets | None |

---

## 3. PR Recovery Matrix

See `docs/audit/PHASE-F-PR-RECOVERY-MATRIX.md` for the complete 23-PR matrix.

**Classification summary:**

| Status | Count | PRs |
|--------|-------|-----|
| READY FOR EXPLICIT AUTHORIZATION | 2 | #78, #73 |
| VERIFICATION REQUIRED | 1 | #72 |
| BLOCKED | 20 | All remaining |

---

## 4. Changes Made

No code changes were made in Phase F. All activity was read-only audit plus governance actions:

| Action | PR | Result |
|--------|-----|--------|
| Request policedbc independent review | #82 | Submitted |
| Request policedbc independent review | #79 | Submitted |
| Request policedbc independent review | #76 | Submitted |
| Request policedbc independent review | #85 | Submitted |
| Request policedbc independent review | #84 | Submitted |

Documentation:
- `docs/audit/PHASE-F-PR-RECOVERY-MATRIX.md` — Created (complete 23-PR matrix)
- `docs/audit/PHASE-F-GOVERNANCE-LOG.md` — Created (governance audit trail)

---

## 5. CI / Test / Security Evidence

### PR #78 — `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
| Check | Result |
|-------|--------|
| repository-baseline | SUCCESS |
| Analyze GitHub Actions | SUCCESS |
| dependency-review | SUCCESS |
| build-scan-sbom | SUCCESS |
| attest-trusted-build | SKIPPED |
| windows-installer | SUCCESS |
| CodeQL | SUCCESS |
| policedbc review | APPROVED |

### PR #73 — `44fdf4e72638b51d3e7a4a4ce0a70140700c880a`
| Check | Result |
|-------|--------|
| repository-baseline | SUCCESS |
| Analyze GitHub Actions | SUCCESS |
| dependency-review | SUCCESS |
| build-scan-sbom | SUCCESS |
| attest-trusted-build | SKIPPED |
| windows-installer | SUCCESS |
| CodeQL | SUCCESS |
| policedbc review | APPROVED |

### PR #72 — `15e5de2026afb902fcc729b2e62b80b1e58576fd`
| Check | Result |
|-------|--------|
| repository-baseline | SUCCESS |
| Analyze GitHub Actions | NOT TRIGGERED |
| dependency-review | NOT TRIGGERED |
| build-scan-sbom | SUCCESS |
| attest-trusted-build | SKIPPED |
| windows-installer | SUCCESS |
| CodeQL | NOT TRIGGERED |
| policedbc review | APPROVED |

**Root cause for missing checks**: All 3 missing workflows are limited to `on: pull_request: branches: [main]`. PR #72 targets `feat/cloudshell-installer-20261017`, not `main`. With strict branch protection, all 6 required checks must pass.

### Chainguard CVE Revalidation
Scanned `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285` with grype 0.121.0:
- CVE-2026-115557: Critical, Fix: None
- CVE-2026-114613: High, Fix: 26.2.2-r1 (not applicable in distroless)
- 5 additional findings (Medium/Low/Unknown)

cgr.dev registry access blocked by TLS certificate error — cannot verify newer images.

---

## 6. Independent Review Status

| PR | SHA | Reviewer | State | Date |
|-----|-----|----------|-------|------|
| #78 | `a72fc000` | policedbc | APPROVED | 2026-10-31T22:21:36Z |
| #73 | `44fdf4e7` | policedbc | APPROVED | 2026-10-31T22:22:18Z |
| #72 | `15e5de20` | policedbc | APPROVED | 2026-10-31T22:22:32Z |
| #82 | `00b20d0` | policedbc | Requested | Pending |
| #79 | `62afa1c` | policedbc | Requested | Pending |
| #76 | `f8b7c54` | policedbc | Requested | Pending |
| #85 | `800c407` | policedbc | Requested | Pending |
| #84 | `6789877` | policedbc | Requested | Pending |

---

## 7. Supply Chain Findings

| CVE | Severity | Fix | Blocks |
|-----|----------|-----|--------|
| CVE-2026-115557 | Critical | None | 7 PRs (#102, #87, #88, #80, #70, #69, #64) + #71 build-scan-sbom |
| CVE-2026-114613 | High | 26.2.2-r1 (N/A distroless) | Same 7 PRs |

Patched Python 3.14 Chainguard images exist locally (`sha256:3f411b4aac1e`, `sha256:c07959e43e3e`) with fix `3.14.10_git20261028-r0`, but switching from Python 3.15 requires compatibility testing.

---

## 8. Governance Findings

| Requirement | Status |
|-------------|--------|
| No self-approval | COMPLIANT |
| No bypass branch protection | COMPLIANT |
| No bypass required checks | COMPLIANT |
| No force-push | COMPLIANT |
| No history rewriting | COMPLIANT |
| No merge without authorization | COMPLIANT |
| Review decisions reference exact SHA | COMPLIANT |
| policedbc review requested for all Priority B | COMPLIANT |

---

## 9. Merge Readiness

| PR | SHA | Ready for Authorization? | Blocker |
|-----|-----|-------------------------|---------|
| #78 | `a72fc000284f` | YES | None |
| #73 | `44fdf4e72638` | YES | None |
| #72 | `15e5de2026af` | NO | 3 required checks not triggered |
| #82 | `00b20d07f561` | NO | Awaiting policedbc review; SBOM FAILURE |
| #79 | `62afa1cec740` | NO | Awaiting policedbc review; SBOM FAILURE |
| #76 | `f8b7c54f944b` | NO | Awaiting policedbc review; SBOM FAILURE |
| #85 | `800c407a60a0` | NO | Awaiting policedbc review; SBOM FAILURE |
| #84 | `678987786e63` | NO | Awaiting policedbc review; SBOM FAILURE |

---

## 10. Blockers and Residual Risks

| Blocker | PRs Affected | Severity | Resolution Required |
|---------|-------------|----------|-------------------|
| Chainguard CVE-2026-115557 (Critical, no fix) | #102, #87, #88, #80, #70, #69, #64, #71 | Critical | Upstream Chainguard patched image |
| Missing required checks on non-main base | #72 | High | Retarget to main or adjust branch protection |
| PR #77 unknown state | #77 | Medium | Investigate base branch validity |
| Awaiting policedbc review | #82, #79, #76, #85, #84 | Medium | Independent review completion |
| No independent review | #70, #69, #64 | Medium | policedbc review |

---

## 11. Rollback Plan

No merges occurred in Phase F. No rollback needed.

If a future merge requires rollback:
1. Identify exact merge commit SHA
2. Create dedicated revert branch
3. Use `git revert` (not `git reset --hard` or `git push --force`)
4. Run regression tests
5. Open corrective PR with independent review
6. Merge through normal governance

---

## 12. Recommended Next Actions

### Immediate (requires explicit user authorization):
1. **Authorize merge of PR #78** (head `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`) — all gates pass
2. **Authorize merge of PR #73** (head `44fdf4e72638b51d3e7a4a4ce0a70140700c880a`) — all gates pass

### Pending policedbc review:
3. Review PRs #82, #79, #76, #85, #84

### Requires investigation/remediation:
4. Resolve PR #72's 3 missing required checks (non-main base branch)
5. Investigate PR #77 (draft, conflicting, no CI)
6. Wait for Chainguard patched base image for CVE-blocked PRs

**Phase F status: PARTIALLY VERIFIED — Ready for explicit authorization on PRs #78 and #73.**
