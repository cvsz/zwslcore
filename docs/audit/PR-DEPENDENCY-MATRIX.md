# PR Dependency Matrix — cvsz/zwslcore

**Generated**: 2026-10-31
**Base SHA**: `df7ef0eae393f44f39c5393533531fc4171c6156`
**Head SHA**: `b19ff81e746ff37f254b76b18189f8748b289f1f`
**Execution Mode**: SUPER ULTRA AI ORC — PHASE C

---

## Open Pull Requests (23 total)

| PR | Title | Author | State | Review | Mergeable | build-scan-sbom | Classification | Dependencies |
|-----|-------|--------|-------|---------|-----------|-----------------|----------------|--------------|
| #102 | harden worktree ownership rollback | cvsz | OPEN | CHANGES_REQUESTED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #101 | build(deps): update fastapi | dependabot[bot] | OPEN | REVIEW_REQUIRED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #100 | build(deps): bump trufflesecurity/trufflehog | dependabot[bot] | OPEN | REVIEW_REQUIRED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #91 | refactor(architecture): runtime/Video Factory | cvsz | OPEN | REVIEW_REQUIRED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #90 | feat: add GGUF model support | cvsz | OPEN | APPROVED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #89 | feat: add MiniMax-H3 GGUF | cvsz | OPEN | APPROVED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #88 | ci(security): provider base-image digest refresh | cvsz | OPEN | CHANGES_REQUESTED | CONFLICTING | FAIL | BLOCKED (CVE + conflict) | Depends on #102 |
| #87 | fix(security): patch critical certifi | cvsz | OPEN | CHANGES_REQUESTED | CONFLICTING | FAIL | BLOCKED (CVE + conflict) | Depends on #102 |
| #86 | fix(ci): synchronize CodeQL | cvsz | OPEN | REVIEW_REQUIRED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #85 | build(deps): bump codeql-action/analyze | dependabot[bot] | OPEN | CHANGES_REQUESTED | MERGEABLE | PASS | Independent | None |
| #84 | build(deps): bump codeql-action/init | dependabot[bot] | OPEN | CHANGES_REQUESTED | MERGEABLE | PASS | Independent | None |
| #82 | fix: move LiteLLM PostgreSQL into Docker | cvsz | OPEN | REVIEW_REQUIRED | CONFLICTING | PASS | Independent (conflict) | Depends on base |
| #80 | feat(cloudshell): recover zcloud connector | cvsz | OPEN | CHANGES_REQUESTED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #79 | fix: harden MCP session | cvsz | OPEN | REVIEW_REQUIRED | CONFLICTING | PASS | Independent (conflict) | Depends on base |
| #78 | fix(ai): load provider credentials safely | cvsz | OPEN | REVIEW_REQUIRED | MERGEABLE | PASS | Independent | None |
| #77 | fix(webhook): bound stalled request-body reads | cvsz | OPEN | (none) | CONFLICTING | (no checks) | Unknown | Depends on feat/cloudshell-ssh-access-mcp-diagnostics-20261017 |
| #76 | feat(cloudshell): Access, MCP diagnostics | cvsz | OPEN | REVIEW_REQUIRED | CONFLICTING | PASS | Independent (conflict) | Depends on base |
| #73 | test(chat-ui): verify Open WebUI Provider Gateway | cvsz | OPEN | REVIEW_REQUIRED | MERGEABLE | PASS | Independent | None |
| #72 | feat(cloudshell): multi-node Ollama pool | cvsz | OPEN | (none) | MERGEABLE | PASS | Independent | None |
| #71 | feat: support optional Ollama installation | cvsz | OPEN | CHANGES_REQUESTED | MERGEABLE | PASS | Independent | None |
| #70 | fix(ai): automatically read secure .env | cvsz | OPEN | REVIEW_REQUIRED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #69 | fix(ai): read private .env safely | cvsz | OPEN | REVIEW_REQUIRED | MERGEABLE | FAIL | BLOCKED (CVE) | None |
| #64 | feat(provider): opt-in free-tier gateways | cvsz | OPEN | REVIEW_REQUIRED | MERGEABLE | FAIL | BLOCKED (CVE) | None |

---

## Dependency Groups

### Group A: Provider Supply Chain Blocked (Chainguard base image CVE)
**PRs**: #102, #87, #88, #80, #70, #69, #64

All these PRs fail `build-scan-sbom` due to Chainguard `python:latest` base image CVEs. None can pass CI until the base image is updated.

**Blocker**: Chainguard has not published a patched `python:latest` image. All locally available Chainguard images still contain the CVEs (CVE-2026-115557 Critical, CVE-2026-114613 High).

### Group B: Independent — Can Progress
**PRs**: #85, #84, #82, #79, #78, #76, #73, #72, #71

These PRs pass `build-scan-sbom` and are not affected by the Chainguard base image issue. However:
- #82, #79, #76 have merge conflicts with `main` branch
- #78 needs policedbc re-review
- #73 needs first review
- #71 needs changes addressed (CHANGES_REQUESTED)
- #72 is a DRAFT

### Group C: Unknown / Needs Investigation
**PR**: #77 — No CI check results available, mergeable=CONFLICTING

---

## PR #102 Scope Analysis

**37 files changed across multiple workstreams:**

| Category | Files | Count | Recommendation |
|----------|-------|-------|----------------|
| **SECURITY_CRITICAL (core worktree feature)** | `services/engineering/worktree.py`, `tests/test_engineering_change_snapshot.py` | 2 | Keep in PR #102 |
| **SECURITY_CRITICAL (blocked by Chainguard CVE)** | `services/provider/Dockerfile`, `services/provider/requirements.lock` | 2 | Separate or keep blocked |
| **DOCUMENTATION_ONLY** | ORC_MASTER_PROMPT.md, docs/audit/* (11 files), docs/anthropic-compatibility.md, docs/LITELLM-CLIENTS.md, docs/opencode-config.md, docs/operations/claude-code-setup.md, docs/security/local-only-routing.md, run-zeaz-orc.sh, zeaz-orc.sh | 15 | Separate documentation PR |
| **RELATED_BUT_SEPARABLE** | .gitignore, scripts/test-*.py (3), services/provider/config/providers.yaml, services/provider/pyproject.toml, services/provider/tests/*.py (5), services/provider/zeaz_provider/*.py (4), tests/test_backup_restore.py, tests/test_engineering_mcp.py | 18 | Separate provider PR |

### Proposed PR Splitting

| New PR | Files | Purpose |
|--------|-------|---------|
| PR #102a (keep) | `services/engineering/worktree.py`, `tests/test_engineering_change_snapshot.py` | Worktree ownership rollback hardening — original PR intent |
| PR #102b | `services/provider/Dockerfile`, `services/provider/requirements.lock`, `services/provider/zeaz_provider/*.py`, `services/provider/config/providers.yaml`, services/provider/tests/*.py | Provider supply chain + provider code changes |
| PR #102c | All docs/*, scripts/test-*.py, .gitignore, run-zeaz-orc.sh, zeaz-orc.sh | Documentation and CI scripts |

### Approval Status

- policedbc's review on `b19ff81` is **CHANGES_REQUESTED** with 3 blocking findings:
  1. PR scope mismatch (37 files vs stated 2-file scope)
  2. Provider Supply Chain FAILURE (Chainguard base image CVEs)
  3. Commit provenance `bad_email` (git config email vs GPG key email mismatch)

**Workstream A can proceed independently** — scope separation does not depend on Chainguard image availability.

---

## Conflict Recovery Priority

| PR | Status | Mergeable | Conflict With | Recovery Action |
|-----|--------|-----------|---------------|-----------------|
| #87 | CHANGES_REQUESTED | CONFLICTING | base branch | Resolve after Chainguard fix |
| #88 | CHANGES_REQUESTED | CONFLICTING | base branch | Resolve after Chainguard fix |
| #82 | REVIEW_REQUIRED | CONFLICTING | base branch | Resolve independently |
| #79 | REVIEW_REQUIRED | CONFLICTING | base branch | Resolve independently |
| #76 | REVIEW_REQUIRED | CONFLICTING | base branch | Resolve independently |

---

## Independent PRs Ready for Review (after CI fix)

| PR | Title | Review Decision | Next Action |
|-----|-------|-----------------|-------------|
| #78 | fix(ai): load provider credentials safely | REVIEW_REQUIRED | policedbc re-review on exact SHA `a72fc00` |
| #73 | test(chat-ui): verify Open WebUI Provider Gateway | REVIEW_REQUIRED | policedbc first review |
| #72 | feat(cloudshell): multi-node Ollama pool | (none) | Remove draft, then review |
| #71 | feat: support optional Ollama installation | CHANGES_REQUESTED | Address changes requested |
| #85 | build(deps): bump codeql-action/analyze | CHANGES_REQUESTED | Address review comments |
| #84 | build(deps): bump codeql-action/init | CHANGES_REQUESTED | Address review comments |
| #82 | fix: move LiteLLM PostgreSQL into Docker | REVIEW_REQUIRED | Resolve conflict, then review |
| #79 | fix: harden MCP session | REVIEW_REQUIRED | Resolve conflict, then review |
| #76 | feat(cloudshell): Access, MCP diagnostics | REVIEW_REQUIRED | Resolve conflict, then review |

---
