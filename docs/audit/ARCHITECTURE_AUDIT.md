# Architecture Audit — cvsz/zwslcore

Audit date: 2026-11-09
Reviewer: cvsz
Repository branch: main (HEAD bc1eb1c)

## Architecture overview

zwslcore is a WSL2-first local AI orchestration stack. It is a reusable GitHub project template providing repository foundations plus an integrated local AI runtime.

### Layers (per docs/architecture.md)

1. Repository governance — AGENTS.md, ZEAZ-INTRODUCTION.md, GOVERNANCE.md, SECURITY.md, CONTRIBUTING.md.
2. GitHub control plane — .github/ (CI, CodeQL, Dependency Review, Supply Chain, CODEOWNERS), scripts/github_admin.py.
3. Validation — scripts/validate_repo.py, tests/.
4. Project initialization — scripts/bootstrap.py (identity/ownership routing only).
5. AI/agent execution — docs/ai/, skills/, components.d/, plugins.d/.
6. Application placeholders — root Dockerfile and Makefile are intentionally non-production placeholders for generated projects to replace.

## Subsystems (shell-verified)

| Subsystem | Location | Language | Key characteristics |
|-----------|----------|----------|---------------------|
| Provider Gateway | services/provider/zeaz_provider/ | Python | Multi-provider AI gateway; Bearer/x-api-key auth; fail-closed; rate limiting; circuit breakers; cost policy (ZERO_COST_ONLY default); SSE streaming; SSRF protection (follow_redirects=False, trust_env=False); JSON constant rejection; trusted proxy policy |
| Provider tests | services/provider/tests/ | Python | test_security.py, test_observability.py |
| Engineering control plane | services/engineering/ | Python | Durable SQLite WAL task state; isolated Git worktrees; bounded secret-aware snapshots; path-scoped agent permissions (fail-closed, last-match-wins); worktree isolation under ~/.zwslcore/worktrees; evidence bundles with SHA-256; bounded retries; subagent delegation depth ≤ 4; no remote push by default |
| Model catalog | services/model_catalog/ | Python | Catalog, inventory, models.dev sync, selector; local-first, zero-cost routing |
| Compose stack | compose.yaml | YAML | Ollama, LiteLLM, Provider, Open WebUI; loopback-only binds; immutable image digests |
| Provider Dockerfile | services/provider/Dockerfile | Dockerfile | Chainguard base (immutable digests), multi-stage build, non-root user 65532:65532, read-only rootfs, cap_drop ALL, no-new-privileges |
| Scripts | scripts/ | Bash + Python | Installer, diagnostics, backup/restore, engineering runtime, Cloud Shell helpers |

## SOLID / Clean Architecture assessment

- Dependency boundaries: Provider depends on Ollama/LiteLLM via loopback internal network; engineering control plane is self-contained (SQLite, no external deps at runtime).
- Separation of concerns: Provider gateway (routing/auth) separate from model catalog (discovery) and engineering control plane (task orchestration).
- API consistency: Provider exposes OpenAI-compatible routes (/v1/models, /v1/chat/completions, /v1/responses).
- Backward compatibility: Cost policy and cloud fallback are opt-in; local-first preserved.

## Security boundaries (verified)

- All service ports bind to 127.0.0.1 by default.
- Provider: ZEAZ_ALLOW_UNAUTHENTICATED=false, client key authentication.
- Non-root container, read-only rootfs, dropped capabilities, no-new-privileges.
- Immutable image digests; hash-pinned Python deps.
- MCP: stdio-only, shell=False, env allowlist, bounded messages; autonomous agents do not receive MCP tool execution.

## Governance gap

- zeaz.md (canonical governance file) is ABSENT from this repository (not on disk, not tracked in git). Per ZEAZ §0: blocker recorded, conservative security defaults applied, no governance requirements invented. Existing controls remain intact.

## Production boundary

Repository-foundation readiness and application production readiness are separate claims. The template verifies repository controls, documentation structure, and baseline automation. A generated application must independently verify runtime architecture, deployment, data, recovery, observability, capacity, security, and incident-response gates.
