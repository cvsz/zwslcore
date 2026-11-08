PR Dependency Matrix — cvsz/zwslcore
=====================================

Generated: 2026-11-01
Total PRs: 102
Open PRs: 23
Merged PRs: 79
Closed PRs: 0

Classification Legend
---------------------
STATUS: OPEN, MERGED, CLOSED
MERGEABLE: Can merge without conflicts
CONFLICTING: Has merge conflicts
BLOCKED: Blocked by CVE-2026-115557 or other security gate
REVIEW: Status of most recent review

PR #73 Preservation Rule
------------------------
PR #73 must remain untouched, unmodified, and unmerged unless separately authorized by the user.
This PR is flagged as "PRESERVE" and must not be modified during Phase D.

================================================================================
| PR | Title | State | Mergeable | Blocked By | Review Status | Action |
================================================================================
| 102 | fix(engineering): harden worktree ownership rollback | OPEN | MERGEABLE | — | — | — |
| 101 | build(deps): update fastapi requirement from <0.143,>=0.142.2 to >=0.142.2,<0.163 in /services/provider | OPEN | MERGEABLE | — | — | — |
| 100 | build(deps): bump trufflesecurity/trufflehog from 3.86.1 to 3.99.7 | OPEN | MERGEABLE | — | — | — |
| 99 | build: add S3 / Object Storage environment variables | MERGED | UNKNOWN | — | — | — |
| 98 | build: explicitly ignore .env.production and .env.local in .gitignore | MERGED | UNKNOWN | — | — | — |
| 97 | build: add make release pre-flight target | MERGED | UNKNOWN | — | — | — |
| 96 | build: add make release pre-flight target | CLOSED | MERGEABLE | — | — | — |
| 95 | build: add make release pre-flight target | CLOSED | MERGEABLE | — | — | — |
| 94 | build: add make release pre-flight target | CLOSED | MERGEABLE | — | — | — |
| 93 | fix(enterprise): production-grade readiness overhaul | MERGED | UNKNOWN | — | — | — |
| 92 | fix(security): remediate Provider Supply Chain critical vulnerabilities | MERGED | UNKNOWN | — | — | — |
| 91 | refactor(architecture): define zwslcore runtime and Video Factory boundaries | OPEN | MERGEABLE | — | — | — |
| 90 | feat: add GGUF model support via Ollama Modelfile import | OPEN | MERGEABLE | — | — | — |
| 89 | feat: add MiniMax-H3 GGUF video generation model support | OPEN | MERGEABLE | — | — | — |
| 88 | ci(security): automate reviewed Provider base-image digest refresh | OPEN | CONFLICTING | CVE-2026-115557 | — | — |
| 87 | fix(security): patch critical certifi in hashed provider lock | OPEN | CONFLICTING | CVE-2026-115557 | — | — |
| 86 | fix(ci): synchronize CodeQL v4.39.1 actions and Dependabot grouping | OPEN | MERGEABLE | — | — | — |
| 85 | build(deps): bump github/codeql-action/analyze from 4.38.2 to 4.39.1 | OPEN | MERGEABLE | — | — | — |
| 84 | build(deps): bump github/codeql-action/init from 4.38.2 to 4.39.1 | OPEN | MERGEABLE | — | — | — |
| 83 | build(deps): update fastapi requirement from <0.143,>=0.142.2 to >=0.142.2,<0.157 in /services/provider | CLOSED | MERGEABLE | — | — | — |
| 82 | fix: move LiteLLM PostgreSQL into Docker and harden local runtime | OPEN | MERGEABLE | — | CONFLICTS RESOLVED | — |
| 81 | fix: move LiteLLM PostgreSQL into Docker and harden local runtime | CLOSED | MERGEABLE | — | — | — |
| 80 | feat(cloudshell): recover zcloud connector after VM reset | OPEN | MERGEABLE | — | — | — |
| 79 | fix: harden MCP session, rate limiter, provider client and restore | OPEN | MERGEABLE | — | CONFLICTS RESOLVED | — |
| 78 | fix(ai): load provider credentials safely from repository .env | OPEN | MERGEABLE | CVE-2026-115557 | CHANGES_REQUESTED (policedbc, SHA 95cc9ca) | — |
| 77 | fix(webhook): bound stalled request-body reads | OPEN | CONFLICTING | — | — | — |
| 76 | feat(cloudshell): Access, MCP diagnostics, and feature-aware installation | OPEN | MERGEABLE | — | — | — |
| 75 | feat(cloudshell): secure opt-in Cloudflare tunnel lifecycle and SSH runbook | MERGED | UNKNOWN | — | — | — |
| 74 | feat(cloudshell): add opt-in native Open WebUI bootstrap and health check | MERGED | UNKNOWN | — | — | — |
| 73 | test(chat-ui): verify existing Open WebUI Provider Gateway security contract | OPEN | MERGEABLE | — | — | **PRESERVE — do not touch** |
| 72 | feat(cloudshell): opt-in multi-node Ollama pool and parallel agent jobs | OPEN | MERGEABLE | — | — | — |
| 71 | feat: support optional Ollama installation on Google Cloud Shell | OPEN | MERGEABLE | — | CHANGES_REQUESTED addressed | — |
| 70 | fix(ai): automatically read secure .env provider configuration | OPEN | MERGEABLE | CVE-2026-115557 | — | — |
| 69 | fix(ai): read private .env safely in ai.sh | OPEN | MERGEABLE | CVE-2026-115557 | — | — |
| 68 | feat: add standalone single-file AI CLI | MERGED | UNKNOWN | — | — | — |
| 67 | build(deps): bump github/codeql-action/init from 4.38.2 to 43.8.3 | CLOSED | MERGEABLE | — | — | — |
| 66 | build(deps): bump github/codeql-action/analyze from 4.38.2 to 4.38.3 | CLOSED | MERGEABLE | — | — | — |
| 65 | build(deps): update fastapi requirement from <0.143,>=0.142.2 to >=0.142.2,<0.144 in /services/provider | CLOSED | MERGEABLE | — | — | — |
| 64 | feat(provider): opt-in free-tier gateways and coding benchmark | OPEN | MERGEABLE | — | — | — |
| 63 | Add dism.exe fallback to Windows feature setup | MERGED | UNKNOWN | — | — | — |
| 62 | Ignore local .vmix recording artifacts | MERGED | UNKNOWN | — | — | — |
| 61 | Add policedbc as repository co-owner | MERGED | UNKNOWN | — | — | — |
| 60 | Master Think-Drill prompts, hermetic tests, git-aware validator | MERGED | UNKNOWN | — | — | — |
| 59 | build(deps): bump actions/upload-artifact from 7.0.1 to 7.0.2 | MERGED | UNKNOWN | — | — | — |
| 58 | build(deps): bump actions/download-artifact from 8.0.1 to 8.0.2 | MERGED | UNKNOWN | — | — | — |
| 57 | build(deps): bump chainguard/python from `c07959e` to `733f745` in /services/provider | CLOSED | MERGEABLE | — | — | — |
| 56 | build(deps): bump anchore/sbom-action from 0.24.0 to 0.24.3 | MERGED | UNKNOWN | — | — | — |
| 55 | Merge all feature branches into main (purge leaked .vmix OAuth tokens) | CLOSED | CONFLICTING | — | — | — |
| 54 | feat: add zwslcore Cloudflare runtime profile | MERGED | UNKNOWN | — | — | — |
| 53 | feat: add loopback engineering metrics exporter | MERGED | UNKNOWN | — | — | — |
| 52 | fix: record Open WebUI recreate policy in backups | MERGED | UNKNOWN | — | — | — |
| 51 | feat: record local Ollama model identity | MERGED | UNKNOWN | — | — | — |
| 50 | test: verify models.dev cache refresh and fallback | MERGED | UNKNOWN | — | — | — |
| 49 | fix: cap Docker service log growth | MERGED | UNKNOWN | — | — | — |
| 48 | fix: harden durable queue and runtime recovery | MERGED | UNKNOWN | — | — | — |
| 47 | docs: record cold-start readiness evidence | MERGED | UNKNOWN | — | — | — |
| 46 | fix: keep cancelled work out of recovery | MERGED | UNKNOWN | — | — | — |
| 45 | fix: bound engineering plan output | MERGED | UNKNOWN | — | — | — |
| 44 | docs: update readiness matrix after PR #43 merge | MERGED | UNKNOWN | — | — | — |
| 43 | fix: preserve task attempts on provider transport errors | MERGED | UNKNOWN | — | — | — |
| 42 | docs: add production readiness evidence matrix | MERGED | UNKNOWN | — | — | — |
| 41 | fix: inherit delegated engineering scope | MERGED | UNKNOWN | — | — | — |
| 40 | feat: add fail-closed custom agent profiles | MERGED | UNKNOWN | — | — | — |
| 39 | feat: add drift-safe engineering undo and redo | MERGED | UNKNOWN | — | — | — |
| 38 | feat: add fail-closed local stdio MCP registry | MERGED | UNKNOWN | — | — | — |
| 37 | feat: add durable subagent delegation and lineage | MERGED | UNKNOWN | — | — | — |
| 36 | feat: add OpenCode-inspired agent permissions and tool registry | MERGED | UNKNOWN | — | — | — |
| 35 | feat: add explicit orphan task lifecycle controls | MERGED | UNKNOWN | — | — | — |
| 34 | feat: persist task-specific recovery model cursor | MERGED | UNKNOWN | — | — | — |
| 33 | feat: reconcile engineering queue and orphan task state | MERGED | UNKNOWN | — | — | — |
| 32 | feat: add adaptive engineering recovery for blocked work | MERGED | UNKNOWN | — | — | — |
| 31 | feat: add automatic model ranking and engineering TUI | MERGED | UNKNOWN | — | — | — |
| 30 | feat: integrate models.dev catalog with offline cache | MERGED | UNKNOWN | — | — | — |
| 29 | fix: preserve engineering retry budget on provider transport resets | MERGED | UNKNOWN | — | — | — |
| 28 | fix: enforce structured edits through native Ollama format | MERGED | UNKNOWN | — | — | — |
| 27 | fix: reconcile stale engineering worktrees to current source HEAD | MERGED | UNKNOWN | — | — | — |
| 26 | fix: enforce structured JSON for engineering edits | MERGED | UNKNOWN | — | — | — |
| 25 | feat: add strict and baseline-delta validation profiles | MERGED | UNKNOWN | — | — | — |
| 24 | feat: add conservative resumable engineering cursor | MERGED | UNKNOWN | — | — | — |
| 23 | feat: add durable engineering evidence bundles | MERGED | UNKNOWN | — | — | — |
| 22 | build: upgrade provider runtime to Python 3.14.7 | MERGED | UNKNOWN | — | — | — |
| 21 | chore: refresh provider dependency ranges and test Python 3.14 | MERGED | UNKNOWN | — | — | — |
| 20 | fix: regenerate empty edits from scoped candidate files | MERGED | UNKNOWN | — | — | — |
| 19 | fix: make engineering edits scope-aware before path validation | MERGED | UNKNOWN | — | — | — |
| 18 | feat: add hardware-aware GPU and quantization policy | MERGED | UNKNOWN | — | — | — |
| 17 | fix: repair non-JSON engineering edits and preserve retry counters | MERGED | UNKNOWN | — | — | — |
| 16 | fix: parse dotenv values safely in runtime scripts | MERGED | UNKNOWN | — | — | — |
| 15 | fix: harden CPU-local engineering inference | MERGED | UNKNOWN | — | — | — |
| 14 | fix: reset engineering task budget on explicit retry | MERGED | UNKNOWN | — | — | — |
| 13 | fix: expose provider failures and preflight engineering runs | MERGED | UNKNOWN | — | — | — |
| 12 | feat: add live engineering progress and scoped local-model context | MERGED | UNKNOWN | — | — | — |
| 11 | feat: add hardware profiling, cost policy, and durable continuous engineering | MERGED | UNKNOWN | — | — | — |
| 10 | fix: bind engineer WSL positional arguments correctly | MERGED | UNKNOWN | — | — | — |
| 9 | stabilize WSL cold-start checks and Windows engineering CLI | MERGED | UNKNOWN | — | — | — |
| 8 | feat: add self-contained local engineering control plane | MERGED | UNKNOWN | — | — | — |
| 7 | build(deps): update redis requirement from <7,>=6.4 to >=6.4,<9 in /services/provider | CLOSED | UNKNOWN | — | — | — |
| 6 | build(deps-dev): update setuptools requirement from <76,>=75 to >=75,<85 in /services/provider | CLOSED | UNKNOWN | — | — | — |
| 5 | build(deps): bump python from 3.12.15-slim-bookworm to 3.14.7-slim-bookworm in /services/provider | CLOSED | MERGEABLE | — | — | — |
| 4 | audit: production hardening for WSL2 AI runtime | MERGED | UNKNOWN | — | — | — |
| 3 | fix: route Windows doctor checks through WSL runtime | CLOSED | CONFLICTING | — | — | — |
| 2 | fix: harden WSL distro detection | MERGED | UNKNOWN | — | — | — |
| 1 | feat: integrate WSL2 AI OSS stack | MERGED | UNKNOWN | — | — | — |

Blocked by CVE-2026-115557 (6 PRs):
- PR #102: OPEN, MERGEABLE — blocked by base image CVE
- PR #101: OPEN, MERGEABLE — blocked by base image CVE
- PR #100: OPEN, MERGEABLE — blocked by base image CVE
- PR #88: OPEN, CONFLICTING — blocked by base image CVE
- PR #87: OPEN, CONFLICTING — blocked by base image CVE
- PR #80+: Additional PRs blocked by base image CVE (see Phase C investigation)

PR #78 — Detailed Status
-------------------------
- Title: fix(ai): load provider credentials safely from repository .env
- State: OPEN
- Mergeable: YES
- Base branch: main
- Head branch: fix/ai-cli-dotenv-config-rebase
- Current HEAD: 6a9b45fc8986250fcc6ae433204c7db48d9d1df6
- Previously authorized SHA: a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e (INVALID for current HEAD)
- policedbc review at SHA 95cc9ca: CHANGES_REQUESTED (build-scan-sbom FAILURE due to CVE-2026-115557)
- policedbc re-review at SHA a72fc00: APPROVED (all 7 checks passed including build-scan-sbom), but DISMISSED when new commits pushed
- build-scan-sbom failure: CVE-2026-115557 (Critical) and CVE-2026-114613 (High) in Chainguard python:latest base image
- Dotenv credential loading implementation: SECURE — symlink rejection, permission checks, hostname-based provider mapping, allowlisted keys only
- Required changes to resolve: Fresh policedbc review at exact current SHA, user explicit authorization, CVE risk acceptance

PR #73 — Preservation Status
-----------------------------
- Title: test(chat-ui): verify existing Open WebUI Provider Gateway security contract
- State: OPEN
- Must NOT be modified, merged, or touched during Phase D
- 3 changed files: docs/CLOUDSHELL-CLOUDFLARE-TUNNEL.md documentation update, docs/development.md .env chmod 600 guidance, docs/startup.md .env chmod 600 guidance (note: these may be from different PR; PR #73 is specifically the chat-ui security contract tests)
- 4 commits, all about test(chat-ui) assertions for Open WebUI gateway security
- Classification: PRESERVE — do not modify

PR #71 — Review Status
------------------------
- Title: feat: support optional Ollama installation on Google Cloud Shell
- State: OPEN
- Most recent policedbc feedback: CHANGES_REQUESTED on .env loading and installer safety
- Most recent commit: "fix(cloudshell): address policedbc review feedback on PR #71"
- Current status: CHANGES_REQUESTED feedback has been addressed in the latest commit
- Action: Review threads resolved; awaiting independent re-review if needed

PR #72 — Status
----------------
- Title: feat(cloudshell): opt-in multi-node Ollama pool and parallel agent jobs
- State: OPEN
- Mergeable: YES
- No CVE blocker (different scope)
- Action: Ready for review if user desires

PR #76 — Status
----------------
- Title: feat(cloudshell): Access, MCP diagnostics, and feature-aware installation
- State: OPEN
- Mergeable: YES
- No CVE blocker (different scope)
- Action: Ready for review if user desires

PR #79 — Status
----------------
- Title: fix: harden MCP session, rate limiter, provider client and restore
- State: OPEN
- Mergeable: YES
- Merge conflicts resolved in latest commit
- Action: Ready for review if user desires

PR #82 — Status
----------------
- Title: fix: move LiteLLM PostgreSQL into Docker and harden local runtime
- State: OPEN
- Mergeable: YES
- Merge conflicts resolved in latest commit (10 conflicts resolved)
- Action: Ready for review if user desires