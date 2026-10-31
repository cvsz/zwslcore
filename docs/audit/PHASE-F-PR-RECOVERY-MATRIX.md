# Phase F PR Recovery Matrix — All 23 Open PRs

**Repository**: `cvsz/zwslcore`
**Branch**: `feat/zwslcore-worktree-security-hardening`
**Baseline SHA**: `42792aa181673f772c8791c5c249be3be23c55d4`
**Verified against**: live GitHub data via `gh pr list --state open --limit 100`
**Date**: 2026-11-01

---

## Branch Protection Requirements (main)

| Setting | Value |
|---------|-------|
| Required status checks | `repository-baseline`, `Analyze GitHub Actions`, `dependency-review`, `CodeQL`, `build-scan-sbom`, `windows-installer` |
| Strict mode | True |
| Enforce admins | True |
| Required approving reviews | 1 |
| Dismiss stale reviews | True |
| Require code owner reviews | True |
| Required conversation resolution | False |
| Rulesets | None |

---

## Complete Open PR Inventory

| PR | Title | Author | Draft | Base | Head SHA | Mergeable | Review | Reviewer | SBOM | Classification |
|-----|-------|--------|-------|------|----------|-----------|--------|----------|------|----------------|
| #102 | fix(engineering): harden worktree ownership rollback | cvsz | No | main | 42792aa18167 | MERGEABLE | CHANGES_REQUESTED | policedbc | FAILURE | BLOCKED (Chainguard CVE + review feedback) |
| #101 | build(deps): update fastapi | dependabot | No | main | 3d8c6e07bced | MERGEABLE | REVIEW_REQUIRED | — | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #100 | build(deps): bump trufflesecurity/trufflehog | dependabot | No | main | f7efe2686bb6 | MERGEABLE | REVIEW_REQUIRED | — | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #91 | refactor(architecture): define zwslcore runtime/Video Factory boundaries | cvsz | Yes | main | 671e908562ea | MERGEABLE | REVIEW_REQUIRED | — | FAILURE | BLOCKED (Chainguard CVE + draft + no review) |
| #90 | feat: add GGUF model support via Ollama Modelfile import | cvsz | No | main | f528fe05b449 | MERGEABLE | APPROVED | — | FAILURE | BLOCKED (Chainguard CVE) |
| #89 | feat: add MiniMax-H3 GGUF video generation model support | cvsz | No | main | 1fc11aef200a | MERGEABLE | APPROVED | — | FAILURE | BLOCKED (Chainguard CVE) |
| #88 | ci(security): automate reviewed Provider base-image digest refresh | cvsz | Yes | main | 5ba3f66400e6 | CONFLICTING | CHANGES_REQUESTED | policedbc | FAILURE | BLOCKED (Chainguard CVE + conflict + review feedback) |
| #87 | fix(security): patch critical certifi in hashed provider lock | cvsz | Yes | main | b624aae2bb34 | CONFLICTING | CHANGES_REQUESTED | policedbc | FAILURE | BLOCKED (Chainguard CVE + conflict + review feedback) |
| #86 | fix(ci): synchronize CodeQL v4.39.1 actions and Dependabot grouping | cvsz | Yes | main | bf7568af3c67 | MERGEABLE | REVIEW_REQUIRED | — | FAILURE | BLOCKED (Chainguard CVE + draft + no review) |
| #85 | build(deps): bump github/codeql-action/analyze | dependabot | No | main | 800c407a60a0 | MERGEABLE | CHANGES_REQUESTED | policedbc | FAILURE | BLOCKED (Chainguard CVE + review feedback) |
| #84 | build(deps): bump github/codeql-action/init | dependabot | No | main | 678987786e63 | MERGEABLE | CHANGES_REQUESTED | policedbc | FAILURE | BLOCKED (Chainguard CVE + review feedback) |
| #82 | fix: move LiteLLM PostgreSQL into Docker and harden local runtime | cvsz | Yes | main | 00b20d07f561 | MERGEABLE | REVIEW_REQUIRED | — | FAILURE | BLOCKED (Chainguard CVE + draft + no review) |
| #80 | feat(cloudshell): recover zcloud connector after VM reset | cvsz | No | main | db0bda3e6c4c | MERGEABLE | CHANGES_REQUESTED | policedbc | FAILURE | BLOCKED (Chainguard CVE + review feedback) |
| #79 | fix: harden MCP session, rate limiter, provider client and restore | cvsz | No | main | 62afa1cec740 | MERGEABLE | REVIEW_REQUIRED | — | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #78 | fix(ai): load provider credentials safely from repository .env | cvsz | No | main | a72fc000284f | MERGEABLE | APPROVED | policedbc | SUCCESS | **READY FOR EXPLICIT AUTHORIZATION** |
| #77 | fix(webhook): bound stalled request-body reads | cvsz | Yes | cloudshell-ssh-access-mcp-diagnostics-20261017 | 7275144c049c | CONFLICTING | (none) | — | NO CHECKS | BLOCKED (draft + conflict + no CI + unknown base) |
| #76 | feat(cloudshell): Access, MCP diagnostics, and feature-aware installation | cvsz | No | main | f8b7c54f944b | MERGEABLE | REVIEW_REQUIRED | — | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #73 | test(chat-ui): verify existing Open WebUI Provider Gateway security contract | cvsz | No | main | 44fdf4e72638 | MERGEABLE | APPROVED | policedbc | SUCCESS | **READY FOR EXPLICIT AUTHORIZATION** |
| #72 | feat(cloudshell): opt-in multi-node Ollama pool and parallel agent jobs | cvsz | No | feat/cloudshell-installer-20261017 | 15e5de2026af | MERGEABLE | APPROVED | policedbc | SUCCESS | BLOCKED (3 required checks not triggered) |
| #71 | feat: support optional Ollama installation on Google Cloud Shell | cvsz | No | main | 5921251d2701 | MERGEABLE | CHANGES_REQUESTED | policedbc | FAILURE | BLOCKED (Chainguard CVE + review feedback) |
| #70 | fix(ai): automatically read secure .env provider configuration | cvsz | No | main | 2a0878ea2aae | MERGEABLE | REVIEW_REQUIRED | — | SUCCESS | BLOCKED (no independent review) |
| #69 | fix(ai): read private .env safely in ai.sh | cvsz | Yes | main | 918fab437e0e | MERGEABLE | REVIEW_REQUIRED | — | SUCCESS | BLOCKED (draft + no review) |
| #64 | feat(provider): opt-in free-tier gateways and coding benchmark | cvsz | Yes | main | 2122448c37f1 | MERGEABLE | REVIEW_REQUIRED | — | SUCCESS | BLOCKED (draft + no review) |

---

## Classification Summary

| Status | Count | PRs |
|--------|-------|-----|
| READY FOR EXPLICIT AUTHORIZATION | 2 | #78, #73 |
| VERIFICATION REQUIRED | 1 | #72 (missing 3 required checks) |
| BLOCKED | 20 | All remaining |

---

## PR #72 — Missing Required Checks Analysis

PR #72 has `policedbc` APPROVED at SHA `15e5de2026afb902fcc729b2e62b80b1e58576fd`, all 4 triggered checks pass, but 3 required branch protection checks are **not triggered**:

| Required Check | Status on PR #72 |
|----------------|------------------|
| repository-baseline | SUCCESS |
| Analyze GitHub Actions | NOT TRIGGERED |
| dependency-review | NOT TRIGGERED |
| CodeQL | NOT TRIGGERED |
| build-scan-sbom | SUCCESS |
| windows-installer | SUCCESS |

**Impact**: With strict branch protection, all 6 required checks must pass. Missing 3 checks means PR #72 **cannot be merged** until these checks are triggered and pass.

**Next action**: Investigate workflow trigger conditions to determine if checks can be triggered. If not, PR #72 remains BLOCKED pending workflow changes or branch protection adjustment (requires explicit authorization).

---

## Next Actions by Priority

1. **PR #78** — READY FOR EXPLICIT AUTHORIZATION (all gates pass)
2. **PR #73** — READY FOR EXPLICIT AUTHORIZATION (all gates pass)
3. **PR #72** — VERIFICATION REQUIRED (missing 3 required checks)
4. **PRs #82, #79, #76, #85, #84** — Request independent policedbc review
5. **PR #77** — Investigate draft/conflicting/no CI state
6. **Chainguard CVE blocked PRs** — Revalidate supply chain blockers
