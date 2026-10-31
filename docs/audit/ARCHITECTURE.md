# System Architecture Map

**Repository:** `cvsz/zwslcore`  
**Branch:** `main`  
**Base SHA:** `df7ef0eae393f44f39c5393533531fc4171c6156`  
**Audit date:** 2026-10-31  
**Evidence state:** VERIFIED (observed directly against source)

---

## 1. Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                         zwslcore Platform                       │
├─────────────────┬─────────────────┬─────────────────────────────┤
│  Engineering    │  Provider       │  Model Catalog              │
│  Control Plane  │  Gateway        │                             │
│  (Python)       │  (FastAPI)      │                             │
│                 │                 │                             │
│ ┌─────────────┐ │ ┌─────────────┐ │ ┌───────────────────────┐ │
│ │ Runtime     │ │ │ main.py     │ │ │ catalog.py            │ │
│ │ WorktreeMgr │ │ │ providers.py│ │ │ inventory.py          │ │
│ │ Snapshots   │ │ │ router.py   │ │ │ models_dev.py         │ │
│ │ Continuous  │ │ │ normalize.py│ │ │ selector.py           │ │
│ │ Store/Ledger│ │ │ resilience  │ │ │                       │ │
│ │ Review/Gate │ │ │ security    │ │ │                       │ │
│ │ Evidence    │ │ │ resilience  │ │ │                       │ │
│ │ Observability││ │ streaming   │ │ │                       │ │
│ └─────────────┘ │ └─────────────┘ │ └───────────────────────┘ │
└─────────────────┴─────────────────┴─────────────────────────────┘
```

## 2. Service Boundaries

| Boundary | Responsibility | Entry points | Key modules |
|---|---|---|---|
| **Engineering Control Plane** | Task lifecycle, isolated Git worktrees, snapshots, continuous work queue, evidence, observability | `services/engineering/__init__.py`, `runtime.py` | `worktree.py`, `change_snapshot.py`, `continuous.py`, `loop.py`, `store.py`, `ledger.py`, `review.py`, `validation.py`, `evidence.py`, `observability.py`, `agents.py`, `permissions.py`, `delegation.py`, `reconcile.py`, `snapshot.py`, `tui.py`, `prometheus.py`, `hardware.py`, `lease.py`, `models.py`, `tools.py` |
| **Provider Gateway** | OpenAI-compatible model routing, normalization, resilience, rate limiting, security, streaming | `services/provider/zeaz_provider/main.py` (`app`) | `providers.py`, `router.py`, `normalize.py`, `resilience.py`, `security.py`, `capabilities.py`, `observability.py`, `streaming.py`, `structured.py`, `config.py`, `cost.py`, `limits.py`, `errors.py`, `audit.py` |
| **Model Catalog** | Provider/model metadata, inventory, selection, dev-cache | `services/model_catalog/` | `catalog.py`, `inventory.py`, `models_dev.py`, `selector.py` |

## 3. Engineering Control Plane — Core Components

| Class | File | Responsibility | Security properties |
|---|---|---|---|
| `WorktreeManager` | `worktree.py` | Ownership-aware Git worktree creation/removal/reset/sync | Branch-mismatch fail-closed; marker rollback with registration+common-dir guards; symlink/path confinement; cross-repo rejection |
| `EngineeringRuntime` | `runtime.py` | Bounded local engineering execution over isolated worktrees | Validates ownership via `_read_ownership()` before all destructive ops; `commit=False` by default; snapshot capture after edits |
| `ChangeSnapshotStore` | `change_snapshot.py` | Snapshot capture/undo/redo over managed worktrees | `_assert_managed()` confines to base_dir; `_assert_head()` prevents drift; `reset()` validates ownership |
| `ContinuousEngineeringRunner` | `continuous.py` | Durable work-item queue → runtime adapter | SQLiteRunnerLease for cross-process exclusion; retry/rollback via ownership-verified `reset()` |
| `ContinuousEngineeringLoop` | `loop.py` | Bounded orchestration with dedupe, regression halt, no-progress halt | Dedupe by SHA-256 fingerprint; `stop_on_regression`; `max_no_progress_iterations` |
| `SQLiteEngineeringStore` | `store.py` | Crash-consistent task/checkpoint store | SQLite WAL; `BEGIN IMMEDIATE` for leases; fencing-token increments; foreign-key ON DELETE CASCADE |
| `JsonContinuousLedger` | `ledger.py` | JSON work-item lifecycle ledger | `fcntl.flock` exclusive write lock; atomic temp-file + `os.replace`; sensitive-text redaction; state-transition validation |
| `StaticReviewer` / `SecurityGate` | `review.py` | Deterministic diff review | Secret pattern detection; test-weakening detection; out-of-scope path rejection; fail-closed gate |
| `EvidenceExporter` | `evidence.py` | Secret-minimized evidence bundles | SHA-256 checksums; atomic writes; `redact_sensitive_text()` for API keys/tokens/passwords |
| `Observability` | `observability.py` | JSON engineering phase events | Bounded correlation IDs only; allow-listed phases/outcomes/error classes; sensitive-label redaction |

## 4. Provider Gateway — Core Components

| Class | File | Responsibility |
|---|---|---|
| `app` (FastAPI) | `main.py` | OpenAI-compatible provider gateway with lifespan-managed settings/client/router/rate-limiter |
| `ProviderClient` | `providers.py` | httpx-based provider client with `ResilienceExecutor` (circuit breaker + retries); bounded response bytes; stream size limits |
| `ProviderRouter` | `router.py` | Model routing with cost policy, primary+fallback targets, capability/retired filtering |
| `ResilienceExecutor`/`ResiliencePolicy` | `resilience.py` | Circuit breaker with failure threshold, reset timeout, total timeout |
| `InMemoryRateLimiter`/`RedisRateLimiter` | `security.py` | Per-client rate limiting (in-memory or Redis backend) |
| `TrustedProxyPolicy` | `security.py` | Client IP extraction honoring `cf-connecting-ip` for trusted proxies |

## 5. Data Flow — Task Execution

1. `ContinuousEngineeringRunner.run()` pulls pending `WorkItem`s from `JsonContinuousLedger`
2. `EngineeringRuntime.run(task)` creates/syncs a worktree via `WorktreeManager.create()`/`sync_to_source()`
3. Provider generates a plan → edits → validation → `StaticReviewer.review()` → `SecurityGate.evaluate()`
4. On success: `commit=False` (working-tree edits only), then `ChangeSnapshotStore.capture()` writes evidence bundle
5. `EvidenceExporter.export()` writes `evidence.json` + `evidence.sha256` with redacted sensitive text
6. On failure: task marked BLOCKED/FAILED; `ContinuousEngineeringRunner.rollback()` calls ownership-verified `reset()`

## 6. Security Boundaries

| Boundary | Enforcement | Residual risk (documented) |
|---|---|---|
| Worktree path confinement | `_target_path()`: `relative_to(base_dir)`, symlink rejection | TOCTOU between validation and destructive Git op |
| Repository isolation | Common-directory identity comparison; `git worktree list` registration | Same-user hostile process can mutate Git metadata |
| Ownership evidence | JSON marker with version, task_id, repository, common_dir, branch | Marker is not an authentication boundary |
| Secret detection | `StaticReviewer.SECRET_PATTERNS` + `evidence._SECRET_PATTERNS` + `observability._SENSITIVE_LABEL` | Pattern-based, not exhaustive |
| Diff scope enforcement | `StaticReviewer.review()` allowed_paths check | Depends on caller supplying correct `allowed_paths` |
| Process exclusion | `SQLiteRunnerLease` + `JsonContinuousLedger.fcntl.flock` | Cross-node exclusion not provided (single-host) |
| Sensitive logging | `observability.emit_engineering_event()` bounded fields only | Correlation hashes, not raw task text |

## 7. Configuration & Secrets

| File | Sensitivity | Status |
|---|---|---|
| `.env` | Secret (600 perms) | Present, NOT tracked, NOT read |
| `.env.ai` | Secret (600 perms) | Present, NOT tracked, NOT read |
| `.env.production` | Secret (600 perms) | Present, NOT tracked, NOT read |
| `.env.example` | Safe template | Present, tracked |
| `.env.cloudflare.example` | Safe template | Present, tracked |
| `config/agents.example.json` | Safe example | Present, tracked |
| `config/litellm.yaml` | Config | Present, tracked |
| `config/mcp.example.json` | Safe example | Present, tracked |
| `services/provider/requirements.lock` | Hashed lock | Present, tracked |

## 8. CI / Governance

| Workflow | Purpose | Required checks (main) |
|---|---|---|
| `ci.yml` | Repository baseline + stack validation | `repository-baseline`, `Analyze GitHub Actions`, `dependency-review`, `CodeQL`, `build-scan-sbom`, `windows-installer` |
| `codeql.yml` | CodeQL security analysis | `CodeQL` |
| `dependency-review.yml` | Dependency review | `dependency-review` |
| `provider-supply-chain.yml` | Provider image build + scan + SBOM + attestation | `build-scan-sbom` |

Branch protection on `main`: strict required status checks (6 contexts), 1 required approving review, code-owner review, enforce_admins, no force push, no deletions, required conversation resolution. No repository rulesets.

## 9. Known Pre-Existing Conditions

- `worktree.py` / `test_engineering_change_snapshot.py` security patch staged but uncommitted (patch SHA `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96`, independently reviewed APPROVED)
- 8 unstaged pre-existing tracked modifications (preserved)
- `Dockerfile` is a generic placeholder, not a production runtime image
- No `pyproject.toml` at repo root
- Provider subdirectory contains untracked `.venv`, `.pytest_cache`, `egg-info`
- Root contains untracked `.venv`, `.pytest_cache`, `.ruff_cache`
- `tmp_out/` directory owned by root (untracked)
