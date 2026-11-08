# All Pull Requests Matrix — cvsz/zwslcore

**Generated:** 2026-11-08  
**Total PRs:** 110 | **Open:** 22 | **Merged:** 71 | **Closed unmerged:** 17 | **Draft:** 10

---

## Open PRs Requiring Review

| # | Title | Author | Base | Head SHA | Changed Files | Add/Del | Review Status | CI Status | Recommended Action |
|---|-------|--------|------|----------|---------------|---------|---------------|-----------|-------------------|
| #64 | feat(provider): opt-in free-tier gateways and coding benchmark | cvsz | main@386d0bb884b7 | 2122448c37f1 | 5 | 257/0 | Unreviewed | Not run | Keep DRAFT; verify free provider routing doesn't bypass zero-cost policy |
| #69 | fix(ai): read private .env safely in ai.sh | cvsz | main@bb38ae3c0e63 | 918fab437e0e | 2 | 89/3 | Unreviewed | Not run | Keep DRAFT; security-sensitive dotenv handling needs independent review |
| #70 | fix(ai): automatically read secure .env provider configuration | cvsz | main@bb38ae3c0e63 | 2a0878ea2aae | 2 | 98/1 | Unreviewed | Not run | Review and merge — security hardening for dotenv loading |
| #71 | feat: support optional Ollama installation on Google Cloud Shell | cvsz | main@bb38ae3c0e63 | 5921251d2701 | 2 | 204/15 | Unreviewed | Not run | Review; Cloud Shell opt-in feature |
| #72 | feat(cloudshell): opt-in multi-node Ollama pool and parallel agents | cvsz | feat/cloudshell-installer-20261017@4afbd7a3169c | 15e5de2026af | 3 | 152/0 | Unreviewed | Not run | Depends on #71; review together |
| #73 | test(chat-ui): verify existing Open WebUI Provider Gateway security contract | cvsz | main@bb38ae3c0e63 | 44fdf4e72638 | 3 | 115/0 | Unreviewed | Not run | Review; adds static contract tests for Open WebUI integration |
| #76 | feat(cloudshell): Access, MCP diagnostics, and feature-aware installer | cvsz | main@df7ef0eae393 | f8b7c54f944b | 35 | 4575/3 | Unreviewed | Not run | Large PR; review in sections; security-sensitive MCP + cloudflare |
| #77 | fix(webhook): bound stalled request-body reads | cvsz | feat/cloudshell-ssh-access-mcp-diagnostics-20261017@c3bfaaab105c | 7275144c049c | 7 | 162/14 | Unreviewed | Not run | Depends on #76; review together |
| #79 | fix: harden MCP session, rate limiter, provider client and restore | cvsz | main@df7ef0eae393 | 62afa1cec740 | 18 | 529/51 | Unreviewed | Not run | Security-sensitive; review MCP boundaries and rate limiter |
| #80 | feat(cloudshell): recover zcloud connector after VM reset | cvsz | main@f031984954d1 | db0bda3e6c4c | 4 | 367/4 | Unreviewed | Not run | Cloud Shell recovery script; review for path traversal |
| #82 | fix: move LiteLLM PostgreSQL into Docker and harden local runtime | cvsz | main@df7ef0eae393 | 00b20d07f561 | 72 | 3528/236 | Unreviewed | Not run | DRAFT; major architecture change; review database security |
| #84 | build(deps): bump github/codeql-action/init from 4.38.2 to 4.39.1 | dependabot[bot] | main@2fce8d70803a | 678987786e63 | 1 | 2/2 | Unreviewed | Not run | Dependabot; verify CodeQL v4.39.1 compatibility |
| #85 | build(deps): bump github/codeql-action/analyze from 4.38.2 to 4.39.1 | dependabot[bot] | main@2fce8d70803a | 800c407a60a0 | 1 | 2/2 | Unreviewed | Not run | Dependabot; verify CodeQL v4.39.1 compatibility |
| #86 | fix(ci): synchronize CodeQL v4.39.1 actions and Dependabot grouping | cvsz | main@f031984954d1 | bf7568af3c67 | 2 | 6/2 | Unreviewed | Not run | DRAFT; CodeQL upgrade; review with #84/#85 |
| #87 | fix(security): patch critical certifi in hashed provider lock | cvsz | main@f031984954d1 | b624aae2bb34 | 1 | 3/3 | Unreviewed | Not run | DRAFT; certifi update; insufficient alone for issue #108 |
| #88 | ci(security): automate reviewed Provider base-image digest refresh | cvsz | main@f031984954d1 | 5ba3f66400e6 | 4 | 367/181 | Unreviewed | Not run | DRAFT; creates digestabot workflows; superseded by direct Dockerfile fix |
| #89 | feat: add MiniMax-H3 GGUF video generation model support | cvsz | main@f031984954d1 | 1fc11aef200a | 10 | 332/0 | Unreviewed | Not run | Out of scope for chat gateway; video generation not in mission |
| #90 | feat: add GGUF model support via Ollama Modelfile import | cvsz | main@f031984954d1 | f528fe05b449 | 9 | 162/11 | Unreviewed | Not run | Changes default models; review model catalog impact |
| #91 | refactor(architecture): define zwslcore runtime and Video Factory | cvsz | main@f031984954d1 | 671e908562ea | 5 | 131/39 | Unreviewed | Not run | DRAFT; architecture boundary; review for scope creep |
| #101 | build(deps): update fastapi requirement from <0.143 to <0.163 | dependabot[bot] | main@df7ef0eae393 | 3d8c6e07bced | 1 | 1/1 | Unreviewed | Not run | Dependabot; verify FastAPI compatibility |
| #102 | fix(engineering): harden worktree ownership rollback | cvsz | main@df7ef0eae393 | 263ad014fd7a | 75 | 9676/105 | Unreviewed | Not run | DRAFT; large security hardening PR; needs independent review |
| #107 | build(deps): bump trufflesecurity/trufflehog from 3.99.7 to 3.99.8 | dependabot[bot] | main@c3723f2fb0e2 | 94bf3e8d8615 | 1 | 1/1 | Unreviewed | Not run | Dependabot; low-risk secret scanner update |

---

## Closed Without Merge (17)

| # | Title | Author | Closure Reason (from PR body / context) | Head SHA | Superseded By |
|---|-------|--------|-----------------------------------------|----------|---------------|
| #3 | fix: route Windows doctor checks through WSL runtime | cvsz | Superseded by PR #4 | 8ce2f8eb4e4b | #4 |
| #5 | build(deps): bump python 3.12→3.14 | dependabot[bot] | Superseded by PR #22 | 7748b5003e10 | #22 |
| #6 | build(deps-dev): update setuptools | dependabot[bot] | Superseded by later dependency refresh | e655398e48b6 | #21 |
| #7 | build(deps): update redis requirement | dependabot[bot] | Superseded by PR #21 | e8db4f22a0f8 | #21 |
| #55 | Merge all feature branches into main | cvsz | Not merged — feature branches merged individually | 21f068c28a1e | N/A |
| #57 | build(deps): bump chainguard/python | dependabot[bot] | Superseded by direct Dockerfile pin update | a74a0469c201 | Issue #108 fix |
| #65 | build(deps): update fastapi | dependabot[bot] | Superseded by PR #101 | b3c6eb118ca1 | #101 |
| #66 | build(deps): bump CodeQL analyze | dependabot[bot] | Superseded by PR #85 | b35336a96ff3 | #85 |
| #67 | build(deps): bump CodeQL init | dependabot[bot] | Superseded by PR #84 | c1003c76b300 | #84 |
| #81 | fix: move LiteLLM PostgreSQL into Docker | policedbc | Duplicate of #82 (cvsz version) | 774e7bf19749 | #82 |
| #83 | build(deps): update fastapi | dependabot[bot] | Superseded by PR #101 | 66339c5091dc | #101 |
| #94 | build: add make release pre-flight target | cvsz | Duplicate; superseded by #97 | 134ea715ec79 | #97 |
| #95 | build: add make release pre-flight target | cvsz | Duplicate; superseded by #97 | 6138387ee0bc | #97 |
| #96 | build: add make release pre-flight target | policedbc | Duplicate; superseded by #97 | 134ea715ec79 | #97 |
| #100 | build(deps): bump trufflehog 3.86.1→3.99.7 | dependabot[bot] | Superseded by PR #107 | f7efe2686bb6 | #107 |
| #103 | feat: add auto audit/review/approve workflow | cvsz | Not merged — workflow not adopted | 375ebd2748d7 | N/A |
| #104 | feat: add auto-fix open PRs workflow | cvsz | Not merged — workflow not adopted | a151544597be | N/A |

---

## Merged PRs (71)

All 71 merged PRs have been verified as present on `main` at HEAD `bc1eb1c`; the feature branch `feat/zwslcore-enterprise-hardening` is at `40fdd84`. Key merged PRs include:
- #1–#4: Foundation (WSL2 AI stack, WSL hardening, production hardening)
- #8–#22: Engineering control plane (task store, worktrees, MCP, validation, cost policy)
- #23–#47: Engineering resilience (evidence, resume, undo/redo, delegation, queue reconciliation)
- #48–#60: Production readiness (durable queue, backup/restore, metrics, observability)
- #61–#68: Governance and security (CODEOWNERS, AI CLI, CodeQL updates)
- #69–#78: Cloud Shell and dotenv security (open PRs #69, #70, #76–#78)
- #79: Robustness fixes (open)
- #92–#99: Enterprise readiness, S3 env, gitignore hardening
- #105–#111: Workflow hardening, audit doc sync

---

## Dependabot PRs (16)

| # | Title | State | Action |
|---|-------|-------|--------|
| #5 | bump python 3.12→3.14 | Closed unmerged | Superseded by #22 |
| #6 | update setuptools | Closed unmerged | Superseded by #21 |
| #7 | update redis | Closed unmerged | Superseded by #21 |
| #56 | bump sbom-action | Closed merged | Merged |
| #57 | bump chainguard/python | Closed unmerged | Superseded by issue #108 fix |
| #58 | bump download-artifact | Closed merged | Merged |
| #59 | bump upload-artifact | Closed merged | Merged |
| #65 | update fastapi | Closed unmerged | Superseded by #101 |
| #66 | bump CodeQL analyze | Closed unmerged | Superseded by #85 |
| #67 | bump CodeQL init | Closed unmerged | Superseded by #84 |
| #83 | update fastapi | Closed unmerged | Superseded by #101 |
| #84 | bump CodeQL init 4.39.1 | Open | Review and merge |
| #85 | bump CodeQL analyze 4.39.1 | Open | Review and merge |
| #100 | bump trufflehog 3.86.1→3.99.7 | Closed unmerged | Superseded by #107 |
| #101 | update fastapi <0.163 | Open | Review and merge |
| #107 | bump trufflehog 3.99.7→3.99.8 | Open | Review and merge |
