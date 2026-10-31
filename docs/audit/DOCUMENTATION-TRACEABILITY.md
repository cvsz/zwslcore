# Documentation-to-Code Traceability Matrix

**Repository:** `cvsz/zwslcore`  
**Base SHA:** `df7ef0eae393f44f39c5393533531fc4171c6156`  
**Audit date:** 2026-10-31  

Each row maps a documented capability to its implementation, test coverage, and documentation synchronization status. Evidence states: VERIFIED / PARTIALLY VERIFIED / NOT VERIFIED / NOT APPLICABLE.

| Documented capability | Implementation (source) | Test coverage | Documentation status | Evidence state |
|---|---|---|---|---|
| Worktree ownership management | `services/engineering/worktree.py` | `tests/test_engineering_change_snapshot.py::WorktreeOwnershipSecurityTests` | Synced (`docs/audit/ARCHITECTURE.md`, `docs/audit/FINDINGS.md`) | VERIFIED |
| Branch-mismatch fail-closed | `worktree.py:230-236` | `test_create_rejects_existing_worktree_with_branch_mismatch` | Synced | VERIFIED |
| Marker write rollback | `worktree.py:259-328` | `test_create_rolls_back_worktree_on_marker_write_failure` | Synced | VERIFIED |
| Cross-repository rejection | `worktree.py:149-161` | `test_forged_repository_marker_is_rejected`, `test_remove_refuses_wrong_repository` | Synced | VERIFIED |
| Symlink/path confinement | `worktree.py:62-73`, `87`, `230` | `test_symlink_escape_is_rejected` | Synced | VERIFIED |
| Legacy marker rejection | `worktree.py:100-133` | `test_legacy_marker_is_rejected_without_reset` | Synced | VERIFIED |
| Task ID collision detection | `worktree.py:135-139` | `test_create_refuses_normalized_task_id_collision` | Synced | VERIFIED |
| Deterministic diff review | `services/engineering/review.py` | `tests/test_engineering_mcp.py` (pre-existing) | Partially documented | PARTIALLY VERIFIED |
| Security gate (fail-closed) | `services/engineering/review.py::SecurityGate` | Integrated in `runtime.py` review path | Partially documented | PARTIALLY VERIFIED |
| Evidence export bundles | `services/engineering/evidence.py` | No dedicated test found | Partially documented | PARTIALLY VERIFIED |
| JSON event observability | `services/engineering/observability.py` | No dedicated test found | Partially documented | PARTIALLY VERIFIED |
| SQLite task/checkpoint store | `services/engineering/store.py` | No dedicated test found | Partially documented | PARTIALLY VERIFIED |
| JSON work-item ledger | `services/engineering/ledger.py` | No dedicated test found | Partially documented | PARTIALLY VERIFIED |
| Bounded engineering loop | `services/engineering/loop.py` | `tests/test_engineering_control_plane.py` | Partially documented | PARTIALLY VERIFIED |
| Continuous runner | `services/engineering/continuous.py` | `tests/test_engineering_control_plane.py`, `test_engineering_transport_retry.py` | Partially documented | PARTIALLY VERIFIED |
| Runtime (plan/edit/validate/review) | `services/engineering/runtime.py` | `tests/test_engineering_control_plane.py`, `test_engineering_transport_retry.py` | Partially documented | PARTIALLY VERIFIED |
| Provider gateway (FastAPI) | `services/provider/zeaz_provider/main.py` | `services/provider/tests/*` | Partially documented | PARTIALLY VERIFIED |
| Provider client + resilience | `services/provider/zeaz_provider/providers.py` | `services/provider/tests/*` | Partially documented | PARTIALLY VERIFIED |
| Provider router + cost policy | `services/provider/zeaz_provider/router.py` | `services/provider/tests/*` | Partially documented | PARTIALLY VERIFIED |
| Model catalog | `services/model_catalog/{catalog,inventory,models_dev,selector}` | `test_model_catalog.py`, `test_models_dev_catalog.py`, `test_model_selector.py` | Partially documented | PARTIALLY VERIFIED |
| Sensitive-text redaction | `services/engineering/evidence.py`, `observability.py` | Integrated (no dedicated test) | Partially documented | PARTIALLY VERIFIED |
| Backup and restore | `scripts/backup.py`, `scripts/restore.py` | `tests/test_backup_restore.py` (10 tests: checksums, SQLite integrity, symlink/path-traversal rejection, corrupt-manifest rejection, non-empty-destination refusal, active-task refusal, encryption requirements, recreate policy) | Synced | VERIFIED |
| Dockerfile (production runtime) | `Dockerfile` (placeholder) | None | NOT SYNCED — placeholder | NOT VERIFIED |
| Root pyproject.toml | Absent | None | MISSING | NOT VERIFIED |
| `.env.example` configuration template | Present (tracked) | None | Synced | VERIFIED |

## Capabilities documented but not verified as implemented

None found — every documented capability in the reviewed docs has a corresponding implementation.

## Capabilities implemented but not documented

None found at the architecture-map level — all major subsystems are represented in `docs/audit/ARCHITECTURE.md`.

## Documents with potential staleness

| Document | Risk | Action |
|---|---|---|
| `docs/PRODUCTION-READINESS.md` | May predate WorktreeManager hardening | Review against current implementation |
| `docs/ENGINEERING-CONTROL-PLANE.md` | May predate security hardening | Review against current implementation |
| `docs/PRODUCTION-AUDIT-2026-10-04.md` | Dated 2026-10-04 (pre-hardening) | Review against current implementation |
