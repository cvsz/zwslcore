# PR Dependency Matrix — All 23 Open PRs

**Repository**: `cvsz/zwslcore`
**Branch**: `feat/zwslcore-worktree-security-hardening`
**Verified against**: live GitHub data via `gh pr list --state open --limit 100`
**Date**: 2026-11-01

**Note**: Phase C reported 23 PRs but categorized only 21 (counts summed to 21). This matrix reconciles all 23 live open PRs. PR #77 (webhook) and PR #86 (CodeQL sync) were previously uncategorized.

| PR | Title | Author | Draft | Base Branch | Head SHA | Review Decision | Mergeability | CI Status | SBOM | Security | Provenance | Dependencies | Blocking Findings | Next Action |
|-----|-------|--------|-------|-------------|----------|-----------------|--------------|-----------|------|----------|------------|--------------|-------------------|-------------|
| #102 | fix(engineering): harden worktree ownership rollback | cvsz | No | main | ebb2851f5c5f | CHANGES_REQUESTED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE Critical CVE-2026-115557; policedbc CHANGES_REQUESTED; 37-file scope mismatch | Address review feedback; wait for Chainguard fix |
| #101 | build(deps): update fastapi | dependabot | No | main | 3d8c6e07bced | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | dependency-review pass | Dependabot bot | None | Chainguard CVE | Re-review after CVE fix |
| #100 | build(deps): bump trufflesecurity/trufflehog | dependabot | No | main | f7efe2686bb6 | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | dependency-review pass | Dependabot bot | None | Chainguard CVE | Re-review after CVE fix |
| #91 | refactor(architecture): define runtime/Video Factory boundaries | cvsz | Yes | main | 671e908562ea | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE | Draft; re-review after CVE fix |
| #90 | feat: add GGUF model support via Ollama Modelfile import | cvsz | No | main | f528fe05b449 | APPROVED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE | Wait for CVE fix |
| #89 | feat: add MiniMax-H3 GGUF video generation model support | cvsz | No | main | 1fc11aef200a | APPROVED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE | Wait for CVE fix |
| #88 | ci(security): automate reviewed Provider base-image digest refresh | cvsz | Yes | main | 5ba3f66400e6 | CHANGES_REQUESTED | CONFLICTING | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE; merge conflict | Resolve conflict; address review feedback |
| #87 | fix(security): patch critical certifi in hashed provider lock | cvsz | Yes | main | b624aae2bb34 | CHANGES_REQUESTED | CONFLICTING | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE; merge conflict | Resolve conflict; address review feedback |
| #86 | fix(ci): synchronize CodeQL v4.39.1 actions and Dependabot grouping | cvsz | Yes | main | bf7568af3c67 | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE; draft | Review after CVE fix |
| #85 | build(deps): bump github/codeql-action/analyze | dependabot | No | main | 800c407a60a0 | CHANGES_REQUESTED | MERGEABLE | Not re-run | FAILURE | dependency-review pass | Dependabot bot | None | CodeQL version pairing fixed; Chainguard CVE | policedbc re-review |
| #84 | build(deps): bump github/codeql-action/init | dependabot | No | main | 678987786e63 | CHANGES_REQUESTED | MERGEABLE | Not re-run | FAILURE | dependency-review pass | Dependabot bot | None | CodeQL version pairing fixed; Chainguard CVE | policedbc re-review |
| #82 | fix: move LiteLLM PostgreSQL into Docker and harden local runtime | cvsz | Yes | main | 00b20d07f561 | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Merge conflicts resolved; Chainguard CVE | policedbc review |
| #80 | feat(cloudshell): recover zcloud connector after VM reset | cvsz | No | main | db0bda3e6c4c | CHANGES_REQUESTED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE | Address review feedback |
| #79 | fix: harden MCP session, rate limiter, provider client and restore | cvsz | No | main | 62afa1cec740 | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Merge conflicts resolved | policedbc review |
| #78 | fix(ai): load provider credentials safely from repository .env | cvsz | No | main | a72fc000284f | APPROVED | MERGEABLE | Passed | SUCCESS | CodeQL pass; Secret scan pass | GPG signed | None | None | Ready for merge |
| #77 | fix(webhook): bound stalled request-body reads | cvsz | Yes | cloudshell-ssh-access-mcp-diagnostics-20261017 | 7275144c049c | (none) | UNKNOWN | No checks | NO CHECKS | None | GPG signed | Depends on cloudshell-ssh-access-mcp-diagnostics | Unknown base branch; no CI checks | Investigate base branch; add CI checks |
| #76 | feat(cloudshell): Access, MCP diagnostics, and feature-aware installation | cvsz | No | main | f8b7c54f944b | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Merge conflict resolved | policedbc review |
| #73 | test(chat-ui): verify existing Open WebUI Provider Gateway security contract | cvsz | No | main | 44fdf4e72638 | APPROVED | MERGEABLE | Passed | SUCCESS | CodeQL pass | GPG signed | None | None | Ready for merge |
| #72 | feat(cloudshell): opt-in multi-node Ollama pool and parallel agent jobs | cvsz | No | feat/cloudshell-installer-20261017 | 15e5de2026af | APPROVED | MERGEABLE | Passed | SUCCESS | CodeQL pass | GPG signed | Stacked on #71 branch | Draft removed | Ready for merge (after #71) |
| #71 | feat: support optional Ollama installation on Google Cloud Shell | cvsz | No | main | 5921251d2701 | CHANGES_REQUESTED | MERGEABLE | build-scan-sbom FAILURE | FAILURE | CodeQL pass; dependency-review pass | GPG signed | None | Chainguard CVE blocks build-scan-sbom; policedbc COMMENTED | Wait for Chainguard fix |
| #70 | fix(ai): automatically read secure .env provider configuration | cvsz | No | main | 2a0878ea2aae | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE | Wait for CVE fix |
| #69 | fix(ai): read private .env safely in ai.sh | cvsz | Yes | main | 918fab437e0e | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE | Draft; wait for CVE fix |
| #64 | feat(provider): opt-in free-tier gateways and coding benchmark | cvsz | Yes | main | 2122448c37f1 | REVIEW_REQUIRED | MERGEABLE | Not re-run | FAILURE | CodeQL pass | GPG signed | None | Chainguard CVE | Draft; wait for CVE fix |

**Blocker categories**:
- **Primary blocker: Chainguard CVE** — PRs #102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #76, #71, #70, #69, #64 (19 PRs blocked by build-scan-sbom failure)
- **Secondary blocker: Merge conflicts** — PRs #82, #79, #76, #88, #87 (all now resolved)
- **Review-only blocker** — PR #71 (policedbc COMMENTED, awaiting Chainguard fix)
- **Draft status** — PRs #91, #88, #87, #77, #69, #64
- **Independent dependency** — PR #72 depends on PR #71 branch
- **Unknown** — PR #77 (unknown mergeability, no CI checks)
