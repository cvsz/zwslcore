# Pull Request Audit — zwslcore

Audit date: 2026-11-09
Reviewer: cvsz (developer phase), policedbc (independent review phase)
Repository: cvsz/zwslcore

## Open PR inventory (22 PRs)

| # | Title | Author | Head | Base | Head SHA | Mergeable | Review decision | CI state |
|---|-------|--------|------|------|----------|-----------|-----------------|----------|
| 112 | audit: complete enterprise hardening | cvsz | feat/zwslcore-enterprise-hardening | main | 36b59278 | MERGEABLE | REVIEW_REQUIRED | build-scan-sbom FAILURE |
| 107 | build(deps): bump trufflehog 3.99.7->3.99.8 | dependabot | dependabot/...trufflehog-3.99.8 | main | 800c407a | MERGEABLE | REVIEW_REQUIRED | build-scan-sbom FAILURE |
| 102 | fix(engineering): harden worktree rollback | cvsz | feat/zwslcore-worktree-security-hardening | main | 263ad014 | CONFLICTING | CHANGES_REQUESTED | build-scan-sbom FAILURE |
| 101 | build(deps): update fastapi <0.143-><0.163 | dependabot | dependabot/...fastapi-gte-0.142.2-and-lt-0.163 | main | fd50fd6f (rebased) | MERGEABLE | REVIEW_REQUIRED | build-scan-sbom FAILURE |
| 91 | refactor(architecture): runtime and Video Factory boundaries | cvsz | refactor/runtime-architecture-boundary-20261029 | main | 671e9085 | MERGEABLE | REVIEW_REQUIRED | build-scan-sbom FAILURE |
| 90 | feat: add GGUF model support | cvsz | feat/gguf-model-support | main | f528fe05 | MERGEABLE | APPROVED | build-scan-sbom FAILURE |
| 89 | feat: MiniMax-H3 GGUF video generation | cvsz | feat/minimax-h3-gguf | main | 1fc11aef | MERGEABLE | CHANGES_REQUESTED | build-scan-sbom FAILURE |
| 88 | ci(security): automate Provider base-image digest refresh | cvsz | ci/provider-base-digest-refresh-v488-20261026 | main | 5ba3f664 | CONFLICTING | CHANGES_REQUESTED | repository-baseline FAILURE + build-scan-sbom FAILURE |
| 87 | fix(security): patch critical certifi in hashed provider lock | cvsz | security/provider-certifi-ghsa-6q48-20261025 | main | b624aae2 | CONFLICTING | CHANGES_REQUESTED | build-scan-sbom FAILURE |
| 86 | fix(ci): synchronize CodeQL v4.39.1 actions | cvsz | fix/codeql-paired-v4391-20261024-1456 | main | bf7568af | MERGEABLE | REVIEW_REQUIRED | build-scan-sbom FAILURE |
| 85 | build(deps): bump codeql-action/analyze 4.38.2->4.39.1 | dependabot | dependabot/github_actions/codeql-action/analyze-4.39.1 | main | 800c407a | MERGEABLE | CHANGES_REQUESTED | build-scan-sbom FAILURE |
| 84 | build(deps): bump codeql-action/init 4.38.2->4.39.1 | dependabot | dependabot/github_actions/codeql-action/init-4.39.1 | main | 67898778 | MERGEABLE | CHANGES_REQUESTED | build-scan-sbom FAILURE |
| 82 | fix: move LiteLLM PostgreSQL into Docker | cvsz | fix/postgres-docker-bridge-preflight-cvsz | main | 00b20d07 | CONFLICTING | REVIEW_REQUIRED | repository-baseline FAILURE + build-scan-sbom FAILURE + CodeQL FAILURE |
| 80 | feat(cloudshell): recover zcloud connector after VM reset | cvsz | feat/cloudshell-recovery-script | main | db0bda3e | MERGEABLE | CHANGES_REQUESTED | build-scan-sbom FAILURE |
| 79 | fix: harden MCP session, rate limiter, provider client | cvsz | audit/robustness-fixes-20261018 | main | 62afa1ce | CONFLICTING | REVIEW_REQUIRED | repository-baseline FAILURE + build-scan-sbom FAILURE |
| 77 | fix(webhook): bound stalled request-body reads | cvsz | fix/webhook-request-body-timeout-20261018 | feat/cloudshell-ssh-access-mcp-diagnostics-20261017 | 7275144c | CONFLICTING | (none) | No checks |
| 76 | feat(cloudshell): Access, MCP diagnostics, feature-aware install | cvsz | feat/cloudshell-ssh-access-mcp-diagnostics-20261017 | main | f8b7c54f | MERGEABLE | REVIEW_REQUIRED | build-scan-sbom FAILURE + CodeQL FAILURE |
| 73 | test(chat-ui): verify Open WebUI Provider Gateway security contract | cvsz | feat/openwebui-production-contract-20261017 | main | 44fdf4e7 | MERGEABLE | APPROVED -> CHANGES_REQUESTED | All green at creation (stale) |
| 72 | feat(cloudshell): opt-in multi-node Ollama pool | cvsz | feat/cloudshell-hybrid-cluster-20261017 | feat/cloudshell-installer-20261017 | 15e5de20 | MERGEABLE | APPROVED | All green |
| 71 | feat: optional Ollama installation on Google Cloud Shell | cvsz | feat/cloudshell-installer-20261017 | main | 5921251d | MERGEABLE | CHANGES_REQUESTED | build-scan-sbom FAILURE |
| 70 | fix(ai): automatically read secure .env provider config | cvsz | fix/ai-cli-dotenv-config-20261017 | main | 2a0878ea | CONFLICTING | REVIEW_REQUIRED | repository-baseline FAILURE |
| 69 | fix(ai): read private .env safely in ai.sh | cvsz | fix/ai-cli-env-loader-20261017 | main | 918fab43 | CONFLICTING | REVIEW_REQUIRED | repository-baseline FAILURE |
| 64 | feat(provider): opt-in free-tier gateways | cvsz | feat/free-provider-expansion-20261017 | main | 2122448c | MERGEABLE | REVIEW_REQUIRED | repository-baseline FAILURE |

## Key finding: ALL PRs are stale

None of the 22 open PRs has merge-base = current main (bc1eb1c). Every PR is based on an older commit and would delete governance/security files present on current main if merged directly (e.g., `.github/workflows/auto-fix-open-prs.yml`, `automated-audit-review-approve.yml`, `docs/audit/ENTERPRISE-BASELINE.md`, `AGENTS.md`, CVE root-cause reports).

## Blocker: build-scan-sbom FAILURE on current main

The Provider image supply-chain scan fails with `severity-cutoff: high` on current main. This is a required check on every PR. Until remediated (update Chainguard base image digest / affected dependency), NO PR can be merged.

## Independent review decisions (policedbc)

| PR | Decision | Basis |
|----|----------|-------|
| #73 | REQUEST CHANGES | Stale base; deletes governance/security files from main |
| #90 | REQUEST CHANGES | Stale base; deletes governance files; build-scan-sbom FAILURE |
| #101 | REQUEST CHANGES | Rebased OK (fd50fd6f), tests pass, but build-scan-sbom FAILURE blocks |
| #107 | REQUEST CHANGES | Stale base; build-scan-sbom FAILURE |
| #86 | REQUEST CHANGES | Stale base; build-scan-sbom FAILURE |
| #76 | REQUEST CHANGES | Stale base; build-scan-sbom FAILURE + CodeQL FAILURE |
| #64 | REQUEST CHANGES | Stale base; repository-baseline FAILURE |
| #82 | REQUEST CHANGES | Stale base; 3 checks failing; CONFLICTING |
| #79 | REQUEST CHANGES | Stale base; 2 checks failing |
| #70 | REQUEST CHANGES | Stale base; repository-baseline FAILURE; CONFLICTING |
| #69 | REQUEST CHANGES | Stale base; repository-baseline FAILURE; CONFLICTING |
| #89 | REQUEST CHANGES | Stale base; build-scan-sbom FAILURE |
| #88 | REQUEST CHANGES | Stale base; CONFLICTING; 2 checks failing |
| #87 | REQUEST CHANGES | Stale base; CONFLICTING; build-scan-sbom FAILURE |
| #85 | REQUEST CHANGES | Stale base; build-scan-sbom FAILURE |
| #84 | REQUEST CHANGES | Stale base; build-scan-sbom FAILURE |
| #102 | REQUEST CHANGES | Stale base; CONFLICTING; build-scan-sbom FAILURE |
| #80 | REQUEST CHANGES | Stale base; build-scan-sbom FAILURE |
| #72 | APPROVED (conditional) | Stacked PR; only reaches main after #71; all green on its own base |
| #71 | CHANGES_REQUESTED | Stale base; build-scan-sbom FAILURE |
| #112 | REVIEW_REQUIRED | Not yet independently reviewed |
| #77 | (none) | No CI checks; CONFLICTING |

## Merged PRs

None merged during this audit session. All PRs blocked by stale base + build-scan-sbom failure.

## Remaining open PRs

All 22 PRs remain open, all REQUEST CHANGES or REVIEW_REQUIRED, none mergeable-to-main without rebase and build-scan-sbom remediation.
