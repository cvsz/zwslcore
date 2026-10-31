# Repository Baseline Audit

**Repository:** `cvsz/zwslcore`  
**Branch:** `main`  
**Base SHA:** `df7ef0eae393f44f39c5393533531fc4171c6156`  
**Audit date:** 2026-10-31  
**Auditor:** SUPER ULTRA AI ORC (autonomous engineering agent)  
**Evidence state:** VERIFIED (all metrics observed directly against the working tree)

---

## 1. Repository Identity

| Field | Value |
|---|---|
| Remote | `https://github.com/cvsz/zwslcore.git` |
| Default branch | `main` |
| Current HEAD | `df7ef0eae393f44f39c5393533531fc4171c6156` |
| License | MIT (Copyright 2026 cvsz) |
| Template origin | `ztemplate` (reusable GitHub project template) |

## 2. Working-Tree State (at audit time)

| Category | Count | Details |
|---|---|---|
| Staged modified | 2 | `services/engineering/worktree.py`, `tests/test_engineering_change_snapshot.py` (independently reviewed security patch) |
| Unstaged modified | 8 | `docs/LITELLM-CLIENTS.md`, `services/engineering/mcp.py`, `services/provider/config/providers.yaml`, `services/provider/zeaz_provider/config.py`, `services/provider/zeaz_provider/cost.py`, `services/provider/zeaz_provider/router.py`, `services/provider/zeaz_provider/security.py`, `tests/test_engineering_mcp.py` |
| Untracked | 13 | `ORC_MASTER_PROMPT.md`, `docs/anthropic-compatibility.md`, `docs/opencode-config.md`, `docs/operations/`, `docs/security/`, `run-zeaz-orc.sh`, `scripts/test-provider-ci.sh`, `scripts/test-provider.sh`, `scripts/test-repository-ci.sh`, `services/provider/tests/*`, `zeaz-orc.sh` |
| Pre-existing stash | 1 | `stash@{0}: On fix/postgres-docker-bridge-preflight: codex-sync-preserve-zwslcore` (preserved, untouched) |

All pre-existing user changes are preserved. No destructive Git operations performed against the primary working tree.

## 3. Source Metrics

| Metric | Value | Evidence |
|---|---|---|
| Python version | 3.14.4 | `python3 --version` |
| Total Python source files | 110 | `find services tests scripts -name "*.py"` excluding caches/venv |
| Test files | 29 | `find tests -name "test_*.py"` |
| Engineering modules | 24 | `services/engineering/*.py` |
| Model catalog modules | 4 | `services/model_catalog/*.py` |
| Provider modules | 14 | `services/provider/zeaz_provider/*.py` |
| CI workflows | 4 | `ci.yml`, `codeql.yml`, `dependency-review.yml`, `provider-supply-chain.yml` |
| Documentation files | ~40 | `docs/` markdown, adr, ai/, operations/, security/, evidence/ |
| Lock files | 1 | `services/provider/requirements.lock` |
| No `pyproject.toml` | — | Confirmed absent at repo root |
| Placeholder Dockerfile | `Dockerfile` | Generic alpine placeholder — not a real runtime image |

## 4. Architecture Overview

### Service boundaries

| Boundary | Responsibility | Key modules |
|---|---|---|
| Engineering control plane | Task lifecycle, worktrees, snapshots, continuous runtime, evidence, ledger | `services/engineering/{runtime,worktree,change_snapshot,continuous,ledger,store,review,permissions,validation,evidence,observability,agents,loop,delegation,snapshot,tui,prometheus,hardware,lease,reconcile}` |
| Model catalog | Provider/model metadata, inventory, selection | `services/model_catalog/{catalog,inventory,models_dev,selector}` |
| Provider gateway | OpenAI-compatible provider routing, normalization, resilience, security | `services/provider/zeaz_provider/{main,providers,router,normalize,resilience,capabilities,audit,security,observability,streaming,structured,config,cost,errors,limits}` |

### Key engineering classes

| Class | File | Responsibility |
|---|---|---|
| `WorktreeManager` | `services/engineering/worktree.py` | Ownership-aware Git worktree management (branch mismatch prevention, marker rollback) |
| `EngineeringRuntime` | `services/engineering/runtime.py` | Bounded local engineering execution over isolated Git worktrees |
| `ChangeSnapshotStore` | `services/engineering/change_snapshot.py` | Snapshot capture/undo/redo over managed worktrees |
| `ContinuousEngineeringRunner` | `services/engineering/continuous.py` | Durable work-item queue adapter to the engineering runtime |
| `SQLiteEngineeringStore` | `services/engineering/store.py` | Persistent task/checkpoint storage |
| `JsonContinuousLedger` | `services/engineering/ledger.py` | JSON work-item ledger |
| `StaticReviewer` / `SecurityGate` | `services/engineering/review.py` | Deterministic diff review (secret detection, test-weakening detection, scope enforcement) |
| `EngineeringTask` | `services/engineering/models.py` | Task dataclass with status/risk/push-policy metadata |

### Security-relevant design decisions (verified)

- Worktree ownership marker is JSON metadata, NOT an authentication boundary.
- `_read_ownership()` validates marker format, version, task ID, repository identity (common dir), Git registration, and branch before every destructive operation.
- `create()` fails closed when an existing worktree's branch mismatches the requested task configuration.
- `create()` rolls back a newly created worktree when marker creation fails, guarded by registration + common-dir checks.
- `remove()` / `reset()` / `sync_to_source()` validate ownership immediately before execution.
- `StaticReviewer` detects secrets, test weakening, and out-of-scope path changes in diffs.
- `SecurityGate` fails closed when deterministic blocking findings exist.

## 5. CI / Governance

| Item | Value | Evidence |
|---|---|---|
| Branch protection (main) | Required status checks: `repository-baseline`, `Analyze GitHub Actions`, `dependency-review`, `CodeQL`, `build-scan-sbom`, `windows-installer` | `gh api /repos/cvsz/zwslcore/branches/main/protection` |
| Required approving reviews | 1 | Branch protection API |
| Code-owner review required | Yes | Branch protection API |
| Force pushes blocked | Yes | Branch protection API |
| Deletions blocked | Yes | Branch protection API |
| Required signatures | No | Branch protection API |
| Repository rulesets | None (empty) | `gh api /repos/cvsz/zwslcore/rulesets` |
| Actions permissions | `contents: read` | CI workflow files |
| Third-party Actions pinned | Yes (immutable SHAs) | ci.yml, codeql.yml, provider-supply-chain.yml |
| Dockerfile status | Placeholder | Not a real runtime image |

## 6. Documentation Inventory

| Directory | Count | Notable files |
|---|---|---|
| `docs/` root | 15 markdown | `README.md`-adjacent: `PRODUCTION-READINESS.md`, `ENGINEERING-CONTROL-PLANE.md`, `BACKUP-RESTORE.md`, `MCP.md`, `MODELS-DEV.md`, `CLOUDSHELL-WEBUI.md`, `WINDOWS-WSL2-INSTALL.md` |
| `docs/adr/` | 1 | `0000-template.md` |
| `docs/ai/` | 16 | `guides/`, `playbooks/`, `prompts/` — AI integration playbooks and prompts |
| `docs/operations/` | 1 | `claude-code-setup.md` |
| `docs/security/` | 1 | `local-only-routing.md` |
| `docs/evidence/` | 1 | `production-readiness/P0-2-cold-start-2026-10-05.json` |

Missing documentation: No `docs/audit/` directory existed prior to this audit (created during this session). No `docs/architecture/` detailed component docs beyond `docs/architecture.md`.

## 7. Configuration

| File | Status | Notes |
|---|---|---|
| `.env` | Present (600 perms) | Secret — NOT touched, NOT read for content |
| `.env.ai` | Present (600 perms) | Secret — NOT touched |
| `.env.production` | Present (600 perms) | Secret — NOT touched |
| `.env.example` | Present | Safe example template |
| `.env.cloudflare.example` | Present | Safe example template |
| `config/agents.example.json` | Present | Example agent config |
| `config/litellm.yaml` | Present | LiteLLM config |
| `config/mcp.example.json` | Present | Example MCP config |
| `services/provider/requirements.lock` | Present | Hashed provider dependency lock |
| `services/provider/pyproject.toml` | Present | Provider package config |

## 8. Known Pre-Existing Conditions (at audit time)

- The `worktree.py` / `test_engineering_change_snapshot.py` security patch is staged but uncommitted (independently reviewed, APPROVED at patch SHA `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96`).
- 8 unstaged pre-existing tracked modifications exist across docs, mcp.py, provider files, and test_engineering_mcp.py — preserved, not touched.
- The provider subdirectory contains its own `.venv`, `.pytest_cache`, and `zwslcore_provider.egg-info` — untracked build artifacts.
- The root contains `.venv`, `.pytest_cache`, `.ruff_cache` — untracked build artifacts.
- `tmp_out/` directory owned by root — untracked.
- No `pyproject.toml` at repo root; no lock files except provider's `requirements.lock`.
- Dockerfile is a generic placeholder, not a production runtime image.

## 9. Evidence States (canonical, per ZEAZ-INTRODUCTION.md)

All claims in this baseline are `VERIFIED` where directly observed against the working tree, `VERIFIED` where confirmed via `gh api` read-only calls, and `UNVERIFIED` for any GitHub Actions/CI claim that cannot be confirmed locally (local CI-equivalent ≠ GitHub Actions required checks).

---

**Next phases:** Full codebase audit, security assessment, reliability assessment, testing assessment, CI/CD assessment, documentation inventory, prioritized remediation plan.
