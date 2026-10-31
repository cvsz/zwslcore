# PR Recovery Matrix

**Repository**: `cvsz/zwslcore`  
**Date**: 2026-11-01  
**Actor**: cvsz (engineering operator)  
**Source**: Live GitHub API (`gh pr list --state open --limit 100`)

---

## 1. Complete Open PR Inventory (23 PRs)

| PR | Title | Author | Draft | Base | Head SHA | Mergeable | Review | SBOM | Classification | Next Action |
|-----|-------|--------|-------|------|----------|-----------|--------|------|----------------|-------------|
| #102 | fix(engineering): harden worktree ownership rollback | cvsz | No | main | 42792aa18167 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED_BY_SECURITY | Address policedbc review feedback; resolve CVE blocker |
| #101 | build(deps): update fastapi | dependabot | No | main | 3d8c6e07bced | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED_BY_SECURITY | Request policedbc review; resolve CVE blocker |
| #100 | build(deps): bump trufflesecurity/trufflehog | dependabot | No | main | f7efe2686bb6 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED_BY_SECURITY | Request policedbc review; resolve CVE blocker |
| #91 | refactor(architecture): define runtime/Video Factory boundaries | cvsz | Yes | main | 671e908562ea | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED_BY_SECURITY | Remove draft; request review; resolve CVE blocker |
| #90 | feat: add GGUF model support via Ollama Modelfile import | cvsz | No | main | f528fe05b449 | MERGEABLE | APPROVED | FAILURE | BLOCKED_BY_SECURITY | Request policedbc review; resolve CVE blocker |
| #89 | feat: add MiniMax-H3 GGUF video generation model support | cvsz | No | main | 1fc11aef200a | MERGEABLE | APPROVED | FAILURE | BLOCKED_BY_SECURITY | Request policedbc review; resolve CVE blocker |
| #88 | ci(security): automate reviewed Provider base-image digest refresh | cvsz | Yes | main | 5ba3f66400e6 | CONFLICTING | CHANGES_REQUESTED | FAILURE | BLOCKED_BY_SECURITY | Resolve conflict; address review feedback; resolve CVE blocker |
| #87 | fix(security): patch critical certifi in hashed provider lock | cvsz | Yes | main | b624aae2bb34 | CONFLICTING | CHANGES_REQUESTED | FAILURE | BLOCKED_BY_SECURITY | Resolve conflict; address review feedback; resolve CVE blocker |
| #86 | fix(ci): synchronize CodeQL v4.39.1 actions | cvsz | Yes | main | bf7568af3c67 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED_BY_SECURITY | Remove draft; request review; resolve CVE blocker |
| #85 | build(deps): bump github/codeql-action/analyze | dependabot | No | main | 800c407a60a0 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED_BY_SECURITY | Address policedbc review feedback; resolve CVE blocker |
| #84 | build(deps): bump github/codeql-action/init | dependabot | No | main | 678987786e63 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED_BY_SECURITY | Address policedbc review feedback; resolve CVE blocker |
| #82 | fix: move LiteLLM PostgreSQL into Docker | cvsz | Yes | main | 00b20d07f561 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED_BY_SECURITY | Remove draft; request review; resolve CVE blocker |
| #80 | feat(cloudshell): recover zcloud connector | cvsz | No | main | db0bda3e6c4c | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED_BY_SECURITY | Address policedbc review feedback; resolve CVE blocker |
| #79 | fix: harden MCP session, rate limiter, provider client | cvsz | No | main | 62afa1cec740 | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED_BY_SECURITY | Request policedbc review; resolve CVE blocker |
| #78 | fix(ai): load provider credentials safely | cvsz | No | main | 6f9f45ceb862509b4e539c58c92b618d0db5fba2 | MERGEABLE | APPROVED | FAILURE | BLOCKED_BY_SECURITY | policedbc APPROVED; blocked by build-scan-sbom; needs new authorization for current SHA |
| #77 | fix(webhook): bound stalled request-body reads | cvsz | Yes | cloudshell-ssh-access-mcp-diagnostics-20261017 | 7275144c049c | CONFLICTING | (none) | NO CHECKS | BLOCKED_BY_CONFLICT | Investigate base branch; add CI checks; resolve conflicts |
| #76 | feat(cloudshell): Access, MCP diagnostics | cvsz | No | main | f8b7c54f944b | MERGEABLE | REVIEW_REQUIRED | FAILURE | BLOCKED_BY_SECURITY | Request policedbc review; resolve CVE blocker |
| #73 | test(chat-ui): verify Open WebUI Provider Gateway contract | cvsz | No | main | 44fdf4e72638b51d3e7a4a4ce0a70140700c880a | MERGEABLE | APPROVED | SUCCESS | READY_FOR_AUTHORIZATION | Request policedbc review; verify CI; authorize merge |
| #72 | feat(cloudshell): multi-node Ollama pool | cvsz | No | feat/cloudshell-installer-20261017 | 15e5de2026afb902fcc729b2e62b80b1e58576fd | MERGEABLE | APPROVED | SUCCESS | VERIFICATION_REQUIRED | 3 required checks not triggered (non-main base); policedbc APPROVED |
| #71 | feat: support optional Ollama installation | cvsz | No | main | 5921251d2701 | MERGEABLE | CHANGES_REQUESTED | FAILURE | BLOCKED_BY_SECURITY | Address policedbc review feedback; resolve CVE blocker |
| #70 | fix(ai): automatically read secure .env | cvsz | No | main | 2a0878ea2aae | MERGEABLE | REVIEW_REQUIRED | SUCCESS | BLOCKED_BY_REVIEW | Request policedbc review |
| #69 | fix(ai): read private .env safely | cvsz | Yes | main | 918fab437e0e | MERGEABLE | REVIEW_REQUIRED | SUCCESS | BLOCKED_BY_REVIEW | Remove draft; request policedbc review |
| #64 | feat(provider): opt-in free-tier gateways | cvsz | Yes | main | 2122448c37f1 | MERGEABLE | REVIEW_REQUIRED | SUCCESS | BLOCKED_BY_REVIEW | Remove draft; request policedbc review |

---

## 2. Classification Summary

| Classification | Count | PRs |
|----------------|-------|-----|
| READY_FOR_AUTHORIZATION | 1 | #73 |
| VERIFICATION_REQUIRED | 1 | #72 |
| BLOCKED_BY_SECURITY | 14 | #102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #78, #71 |
| BLOCKED_BY_REVIEW | 3 | #70, #69, #64 |
| BLOCKED_BY_CONFLICT | 1 | #77 |
| **Total** | **20** | **All 23 open PRs** |

Wait, that sums to 19. Let me recount:
- READY_FOR_AUTHORIZATION: 1 (#73)
- VERIFICATION_REQUIRED: 1 (#72)
- BLOCKED_BY_SECURITY: 14 (#102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #78, #71)
- BLOCKED_BY_REVIEW: 3 (#70, #69, #64)
- BLOCKED_BY_CONFLICT: 1 (#77)

Total: 1 + 1 + 14 + 3 + 1 = 20. But there are 23 PRs. Let me check which ones I'm missing.

Looking at the table again:
- #102: BLOCKED_BY_SECURITY
- #101: BLOCKED_BY_SECURITY
- #100: BLOCKED_BY_SECURITY
- #91: BLOCKED_BY_SECURITY
- #90: BLOCKED_BY_SECURITY
- #89: BLOCKED_BY_SECURITY
- #88: BLOCKED_BY_SECURITY
- #87: BLOCKED_BY_SECURITY
- #86: BLOCKED_BY_SECURITY
- #85: BLOCKED_BY_SECURITY
- #84: BLOCKED_BY_SECURITY
- #82: BLOCKED_BY_SECURITY
- #80: BLOCKED_BY_SECURITY
- #79: BLOCKED_BY_SECURITY
- #78: BLOCKED_BY_SECURITY
- #77: BLOCKED_BY_CONFLICT
- #76: BLOCKED_BY_SECURITY
- #73: READY_FOR_AUTHORIZATION
- #72: VERIFICATION_REQUIRED
- #71: BLOCKED_BY_SECURITY
- #70: BLOCKED_BY_REVIEW
- #69: BLOCKED_BY_REVIEW
- #64: BLOCKED_BY_REVIEW

That's 23 PRs. BLOCKED_BY_SECURITY count: #102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #78, #76, #71 = 17 PRs.

Let me fix the count:
- READY_FOR_AUTHORIZATION: 1 (#73)
- VERIFICATION_REQUIRED: 1 (#72)
- BLOCKED_BY_SECURITY: 17 (#102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #78, #76, #71)
- BLOCKED_BY_REVIEW: 3 (#70, #69, #64)
- BLOCKED_BY_CONFLICT: 1 (#77)

Total: 1 + 1 + 17 + 3 + 1 = 23. Correct.

---

## 3. PR #78 Status Detail

| Field | Value |
|-------|-------|
| Number | 78 |
| Title | fix(ai): load provider credentials safely from repository .env |
| Author | cvsz |
| Base | main |
| Head SHA | `6f9f45ceb862509b4e539c58c92b618d0db5fba2` |
| Authorized SHA | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` (previous authorization — INVALID for current SHA) |
| Draft | No |
| Mergeable | MERGEABLE |
| Review Decision | APPROVED (policedbc on `6f9f45ceb862509b4e539c58c92b618d0db5fba2`) |
| CI Checks | 5/6 pass; build-scan-sbom FAILURE |
| Unresolved Threads | 0 |
| Authorization Status | NEW AUTHORIZATION REQUIRED for current SHA |

**blocker**: `build-scan-sbom` FAILURE due to CVE-2026-115557. Cannot merge until CVE is resolved or risk acceptance is granted.

---

## 4. PR #73 Preservation

| Field | Value |
|-------|-------|
| Number | 73 |
| Title | test(chat-ui): verify existing Open WebUI Provider Gateway security contract |
| Author | cvsz |
| Base | main |
| Head SHA | `44fdf4e72638b51d3e7a4a4ce0a70140700c880a` |
| Draft | No |
| Mergeable | MERGEABLE |
| Review Decision | APPROVED |
| CI Checks | All pass (including build-scan-sbom) |
| Preservation | UNCHANGED |

---
