# Total Recovery Baseline — cvsz/zwslcore

**Program ID**: ZWSLCORE-TOTAL-RECOVERY-001  
**Repository**: `cvsz/zwslcore`  
**Branch**: `feat/zwslcore-worktree-security-hardening`  
**Engineering SHA**: `0db66cb52a7eaa7f67de5a56c371fc42ab4b011c`  
**Date**: 2026-11-01  
**Actor**: cvsz (engineering operator)

---

## 1. Repository Identity

| Item | Value |
|------|-------|
| Repository | `cvsz/zwslcore` |
| Remote | `https://github.com/cvsz/zwslcore.git` |
| Authenticated identity | `cvsz` |
| GPG signing key | `8644B3973EA1743EF5D21EBA87A69650EB250939` |
| GPG signing email | `seaza@msn.com` |
| `commit.gpgsign` | `true` |

---

## 2. Current Branch State

| Item | Value |
|------|-------|
| Current branch | `pr-78-current` (tracking `origin/fix/ai-cli-dotenv-config-rebase`) |
| HEAD SHA | `6f9f45ceb862509b4e539c58c92b618d0db5fba2` |
| Remote SHA | `6f9f45ceb862509b4e539c58c92b618d0db5fba2` (matches) |
| Working tree | Clean (untracked: `docs/audit/`, `services/provider/config/s3.local.yaml`) |
| Merge from main | Applied (PR branch updated with main's 9 commits) |

---

## 3. Open PR Inventory (Live GitHub Data)

All 23 open PRs retrieved via `gh pr list --state open --limit 100`:

| PR | Title | Author | Draft | Base | Head SHA | Mergeable | Review | SBOM | Classification |
|-----|-------|--------|-------|------|----------|-----------|--------|------|----------------|
| #102 | fix(engineering): harden worktree ownership rollback | cvsz | No | main | 42792aa18167 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED (Chainguard CVE + review) |
| #101 | build(deps): update fastapi | dependabot | No | main | 3d8c6e07bced | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #100 | build(deps): bump trufflesecurity/trufflehog | dependabot | No | main | f7efe2686bb6 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #91 | refactor(architecture): define zwslcore runtime/Video Factory | cvsz | Yes | main | 671e908562ea | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED (Chainguard CVE + draft) |
| #90 | feat: add GGUF model support via Ollama Modelfile import | cvsz | No | main | f528fe05b449 | MERGEABLE | APPROVED | FAILURE | BLOCKED (Chainguard CVE) |
| #89 | feat: add MiniMax-H3 GGUF video generation model support | cvsz | No | main | 1fc11aef200a | MERGEABLE | APPROVED | FAILURE | BLOCKED (Chainguard CVE) |
| #88 | ci(security): automate reviewed Provider base-image digest refresh | cvsz | Yes | main | 5ba3f66400e6 | CONFLICTING | CHANGES_REQUESTED | FAILURE | BLOCKED (Chainguard CVE + conflict + review) |
| #87 | fix(security): patch critical certifi in hashed provider lock | cvsz | Yes | main | b624aae2bb34 | CONFLICTING | CHANGES_REQUESTED | FAILURE | BLOCKED (Chainguard CVE + conflict + review) |
| #86 | fix(ci): synchronize CodeQL v4.39.1 actions | cvsz | Yes | main | bf7568af3c67 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED (Chainguard CVE + draft) |
| #85 | build(deps): bump github/codeql-action/analyze | dependabot | No | main | 800c407a60a0 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED (Chainguard CVE + review) |
| #84 | build(deps): bump github/codeql-action/init | dependabot | No | main | 678987786e63 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED (Chainguard CVE + review) |
| #82 | fix: move LiteLLM PostgreSQL into Docker | cvsz | Yes | main | 00b20d07f561 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED (Chainguard CVE + draft) |
| #80 | feat(cloudshell): recover zcloud connector | cvsz | No | main | db0bda3e6c4c | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED (Chainguard CVE + review) |
| #79 | fix: harden MCP session | cvsz | No | main | 62afa1cec740 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #78 | fix(ai): load provider credentials safely | cvsz | No | main | 6f9f45ceb862509b4e539c58c92b618d0db5fba2 | MERGEABLE | APPROVED | FAILURE | BLOCKED (Chainguard CVE - build-scan-sbom) |
| #77 | fix(webhook): bound stalled request-body reads | cvsz | Yes | cloudshell-ssh-access-mcp-diagnostics-20261017 | 7275144c049c | CONFLICTING | (none) | NO CHECKS | BLOCKED (draft + conflict + no CI) |
| #76 | feat(cloudshell): Access, MCP diagnostics | cvsz | No | main | f8b7c54f944b | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED (Chainguard CVE + no review) |
| #73 | test(chat-ui): verify Open WebUI Provider Gateway contract | cvsz | No | main | 44fdf4e72638b51d3e7a4a4ce0a70140700c880a | MERGEABLE | APPROVED | SUCCESS | **READY_FOR_AUTHORIZATION** |
| #72 | feat(cloudshell): multi-node Ollama pool | cvsz | No | feat/cloudshell-installer-20261017 | 15e5de2026afb902fcc729b2e62b80b1e58576fd | MERGEABLE | APPROVED | SUCCESS | **VERIFICATION_REQUIRED** (3 checks not triggered) |
| #71 | feat: support optional Ollama installation | cvsz | No | main | 5921251d2701 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED (Chainguard CVE + review) |
| #70 | fix(ai): automatically read secure .env | cvsz | No | main | 2a0878ea2aae | MERGEABLE | REVIEW_REQUIRED | SUCCESS | BLOCKED (no independent review) |
| #69 | fix(ai): read private .env safely | cvsz | Yes | main | 918fab437e0e | MERGEABLE | REVIEW_REQUIRED | SUCCESS | BLOCKED (draft + no review) |
| #64 | feat(provider): opt-in free-tier gateways | cvsz | Yes | main | 2122448c37f1 | MERGEABLE | REVIEW_REQUIRED | SUCCESS | BLOCKED (draft + no review) |

---

## 4. Primary Blocker: CVE-2026-115557

| Item | Value |
|------|-------|
| CVE ID | CVE-2026-115557 |
| Severity | Critical |
| Affected package | python-3.15 |
| Installed version | 3.15.1_git20261028-r1 |
| Fix available | None (reported) / 3.14.10_git20261028-r0 (Python 3.14 images, unverified) |
| Affected image | `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285` |
| Registry access | cgr.dev blocked by TLS certificate error |
| Build-scan-sbom | FAILURE (severity-cutoff: high, fail-build: true) |

---

## 5. PR #78 Gate Status

| Gate | Required | Observed | Result |
|------|----------|----------|--------|
| Exact SHA | `6f9f45ceb862509b4e539c58c92b618d0db5fba2` | Match | PASS |
| PR state | OPEN | OPEN | PASS |
| Base branch | main | main | PASS |
| Draft | false | false | PASS |
| Mergeable | MERGEABLE | MERGEABLE | PASS |
| Independent approval | policedbc APPROVED | APPROVED on exact SHA | PASS |
| Unresolved threads | 0 | 0 | PASS |
| Required checks | 6/6 SUCCESS | 5/6 SUCCESS, build-scan-sbom FAILURE | **FAIL** |
| Security scan | PASS | build-scan-sbom FAILURE | **FAIL** |
| Branch protection | Verified | Verified via API | PASS |

**blocker**: build-scan-sbom FAILURE due to CVE-2026-115557 Critical in Chainguard base image.

---

## 6. PR #73 Preservation

| Item | Value |
|------|-------|
| PR number | #73 |
| Title | test(chat-ui): verify existing Open WebUI Provider Gateway security contract |
| Head SHA | `44fdf4e72638b51d3e7a4a4ce0a70140700c880a` |
| Base | main |
| State | OPEN |
| Draft | false |
| Mergeable | MERGEABLE |
| Review | APPROVED |
| SBOM | SUCCESS |
| Preservation status | UNCHANGED |

---

## 7. Workstream Status

| Workstream | Status | Notes |
|------------|--------|-------|
| A — Repository discovery | IN_PROGRESS | Baseline documented |
| B — CVE root cause | PENDING | Needs detailed analysis |
| C — Base image remediation | BLOCKED_EXTERNAL | No fix available, registry access blocked |
| D — Docker hardening | PENDING | |
| E — SBOM/scanner repair | PENDING | Depends on C |
| F — Testing | PENDING | |
| G — CI/CD | PENDING | Depends on C |
| H — PR recovery | PENDING | Depends on C for #78 |
| I — PR #78 recovery | BLOCKED | build-scan-sbom failure |
| J — PR #73 preservation | PENDING | Read-only |
| K — Governance | PENDING | |
| L — Production readiness | PENDING | |

---

## 8. Available Local Images for Remediation Evaluation

| Image | Digest | Size | Critical CVEs | High CVEs | Notes |
|-------|--------|------|---------------|-----------|-------|
| cgr.dev/chainguard/python:latest | 0f47468835f6 | 106MB | 1 (CVE-2026-115557, no fix) | 1 (CVE-2026-114613, fix 26.2.2-r1) | Current base image |
| cgr.dev/chainguard/python:latest-dev | 01280a9ffd0c | 937MB | 1 (CVE-2026-115557, no fix) | 1 (CVE-2026-114613) | Build image |
| cgr.dev/chainguard/python@sha256:3f411b4aac1e | 3f411b4aac1e | 102MB | 6 (incl CVE-2026-115557) | 1 | Has fix for CVE-2026-115557 but other Critical CVEs |
| cgr.dev/chainguard/python@sha256:c07959e43e3e | c07959e43e3e | 989MB | 8 (incl CVE-2026-115557) | 4 | Has fix for CVE-2026-115557 but other Critical CVEs |
| cgr.dev/chainguard/python@sha256:733f745e7ec1 | 733f745e7ec1 | 992MB | 5 (incl CVE-2026-115557) | 3 | Has fix for CVE-2026-115557 but other Critical CVEs |
| python:3.15-slim-bookworm | 4e03260adeee | 189MB | 3 | 74 | Debian-based, more CVEs |
| python:3.14.7-slim-bookworm | 82bc3c539b88 | 186MB | Unknown | Unknown | Not yet scanned |

**Conclusion**: No available base image passes `severity-cutoff: high` (zero Critical AND zero High CVEs). All Chainguard images have at least one Critical CVE. Debian images have more.

---
