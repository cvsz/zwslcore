# Phase F Governance Log

**Repository**: `cvsz/zwslcore`
**Branch**: `feat/zwslcore-worktree-security-hardening`
**Baseline SHA**: `42792aa181673f772c8791c5c249be3be23c55d4`
**Date**: 2026-11-01
**Mode**: Mode A (Audit) → Mode B (Safe Remediation)

---

## F0 — Baseline Verification

| Check | Result | Evidence |
|-------|--------|----------|
| Repository identity | Verified | `cvsz/zwslcore` |
| Current branch | `feat/zwslcore-worktree-security-hardening` | Matches Phase E |
| Local HEAD | `42792aa181673f772c8791c5c249be3be23c55d4` | Matches Phase E baseline |
| Remote HEAD | `42792aa181673f772c8791c5c249be3be23c55d4` | Matches local |
| Working tree | Clean | `git status --short` empty |
| GitHub identity | `cvsz` | `gh auth status` |
| GPG signing | Active | key `8644B3973EA1743EF5D21EBA87A69650EB250939` |
| Latest commit verified | Good signature | `git verify-commit HEAD` |
| Branch protection | 6 checks, strict=True | `gh api branches/main/protection` |
| Rulesets | None | `gh api rulesets` |

---

## F1 — PR Reconciliation

All 23 open PRs retrieved via `gh pr list --state open --limit 100`. See `docs/audit/PHASE-F-PR-RECOVERY-MATRIX.md` for full matrix.

**Classification:**
- READY FOR EXPLICIT AUTHORIZATION: #78, #73
- VERIFICATION REQUIRED: #72
- BLOCKED: #102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #77, #76, #71, #70, #69, #64

---

## F2 — Priority A: Previously Approved PRs

### PR #78 — `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
- Review: policedbc APPROVED (2026-10-31T22:21:36Z)
- CI: All 7 checks SUCCESS
- Mergeable: MERGEABLE
- Draft: No
- Status: **READY FOR EXPLICIT AUTHORIZATION**

### PR #73 — `44fdf4e72638b51d3e7a4a4ce0a70140700c880a`
- Review: policedbc APPROVED (2026-10-31T22:22:18Z)
- CI: All 7 checks SUCCESS
- Mergeable: MERGEABLE
- Draft: No
- Status: **READY FOR EXPLICIT AUTHORIZATION**

### PR #72 — `15e5de2026afb902fcc729b2e62b80b1e58576fd`
- Review: policedbc APPROVED (2026-10-31T22:22:32Z)
- CI: 4/7 checks pass; 3 NOT TRIGGERED
- Missing checks: Analyze GitHub Actions, dependency-review, CodeQL
- Root cause: PR targets `feat/cloudshell-installer-20261017` (not `main`); all 3 workflows limited to `branches: [main]`
- Stacked on: PR #71 branch (which is blocked by Chainguard CVE)
- Status: **VERIFICATION REQUIRED / BLOCKED**

---

## F3 — Priority B: Review and Conflict Recovery

### Review requests submitted (policedbc)
| PR | SHA | Reviewer requested | Status |
|-----|-----|-------------------|--------|
| #82 | `00b20d07f56161ef7c66fcc46f8589103d59b516` | policedbc | Pending |
| #79 | `62afa1cec74042cbd7297942c1f5d8ca72212c64` | policedbc | Pending |
| #76 | `f8b7c54f944b7d9c2a22617e467a7b5bf342d1fa` | policedbc | Pending |
| #85 | `800c407a60a0` | policedbc (+cvsz) | Pending |
| #84 | `678987786e63` | policedbc (+cvsz) | Pending |

### CodeQL pairing verification (PRs #85, #84)
- PR #85: `init` and `analyze` both at `9b3254085494b55a0f7c4c2b3d2d52cc712ce370` # v4
- PR #84: `init` and `analyze` both at `9b3254085494b55a0f7c4c2b3d2d52cc712ce370` # v4
- Both PRs correctly pair CodeQL actions on same v4.39.1 SHA
- However, SBOM=FAILURE due to Chainguard CVE → still BLOCKED

---

## F4 — Priority D: PR #77 Investigation

**PR #77**: `fix(webhook): bound stalled request-body reads`
- Base branch: `feat/cloudshell-ssh-access-mcp-diagnostics-20261017` (NOT `main`)
- Head branch: `fix/webhook-request-body-timeout-20261018`
- Head SHA: `7275144c049c13c89ccdf944e08b7aaa9d5b2d0f`
- Draft: Yes
- Mergeable: CONFLICTING
- Review: None
- CI checks: 0 (no workflows triggered)
- Classification: **BLOCKED**
- Reason: Draft, conflicting with base, no CI checks, no review, base branch is not `main`

**Recommendation**: Do not retarget or close without documented reason and explicit authorization. Investigate whether base branch `feat/cloudshell-ssh-access-mcp-diagnostics-20261017` is still active and whether the feature is still needed.

---

## F4 — Priority D: Supply Chain Revalidation

**Chainguard base image**: `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285`

| CVE | Package | Severity | Fix Available | Notes |
|-----|---------|----------|---------------|-------|
| CVE-2026-115557 | python-3.15 | Critical | None | Blocks all provider image builds |
| CVE-2026-114613 | py3-pip-wheel | High | 26.2.2-r1 | Not applicable in distroless |
| CVE-2026-111943 | py3-pip-wheel | Medium | 26.2.2-r2 | Not applicable in distroless |
| CVE-2026-114583 | python-3.15 | Medium | None | |
| CVE-2026-103995 | python-3.15 | Low | None | |
| GHSA-j586-36cw-2gc2 | — | Unknown | 26.2.2-r1 | |
| GO-2026-6809 | — | Unknown | 26.2.2-r2 | |

**Registry access**: cgr.dev TLS certificate error persists — cannot pull newer images for verification.

**Patched images found locally** (Python 3.14-based):
- `sha256:3f411b4aac1e` — CVE-2026-115557 fix=3.14.10_git20261028-r0
- `sha256:c07959e43e3e` — CVE-2026-115557 fix=3.14.10_git20261028-r0

**Assessment**: Patched Python 3.14 images exist locally but switching from Python 3.15 requires compatibility testing and is not yet verified for production use.

---

## F5 — Changes Made in Phase F

No code changes were made in Phase F. All work was read-only audit plus review requests:

| Action | PR | Target | Result |
|--------|-----|--------|--------|
| Request policedbc review | #82 | policedbc | Submitted |
| Request policedbc review | #79 | policedbc | Submitted |
| Request policedbc review | #76 | policedbc | Submitted |
| Request policedbc review | #85 | policedbc | Submitted |
| Request policedbc review | #84 | policedbc | Submitted |

Documentation created:
- `docs/audit/PHASE-F-PR-RECOVERY-MATRIX.md`
