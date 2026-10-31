# Audit Findings Register

**Repository:** `cvsz/zwslcore`  
**Base SHA:** `df7ef0eae393f44f39c5393533531fc4171c6156`  
**Audit date:** 2026-10-31  
**Evidence states:** VERIFIED / PARTIALLY VERIFIED / UNVERIFIED / BLOCKED / NOT APPLICABLE

---

## Finding Index

| ID | Title | Severity | Evidence state | Phase | Blocks approval |
|---|---|---|---|---|---|
| SEC-01 | Existing worktree branch mismatch | High | FIXED | 4 | No |
| SEC-02 | Marker write failure / orphan worktree | High | FIXED | 4 | No |
| SEC-03 | Partial marker cleanup | Medium | FIXED | 4 | No |
| SEC-04 | Cross-repository safety | High | FIXED | 4 | No |
| SEC-05 | Symlink / path escape | Medium | FIXED | 4 | No |
| SEC-06 | Legacy marker rejection | Medium | FIXED | 4 | No |
| SEC-07 | Task ID collision | Medium | FIXED | 4 | No |
| SEC-08 | TOCTOU residual risk | Medium | ACCEPTED RISK | 4 | No |
| SEC-09 | Same-user isolation limitation | Medium | ACCEPTED RISK | 4 | No |
| MAINT-01 | Dockerfile is a placeholder | Medium | VERIFIED | 1 | No |
| MAINT-02 | No root pyproject.toml | Medium | VERIFIED | 1 | No |
| MAINT-03 | Root `.venv` / `.pytest_cache` / `.ruff_cache` untracked | Low | VERIFIED | 1 | No |
| MAINT-04 | Provider `.venv` / `.pytest_cache` / `egg-info` untracked | Low | VERIFIED | 1 | No |
| OPS-01 | `tmp_out/` directory owned by root | Low | VERIFIED | 1 | No |

---

## SEC-01 — Existing worktree branch mismatch (FIXED)

**Severity:** High  
**File:** `services/engineering/worktree.py:230-236`  
**Status:** FIXED — independently reviewed and APPROVED  
**Evidence:** Patch SHA-256 `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96`  
**Test:** `test_create_rejects_existing_worktree_with_branch_mismatch` (9/9 security tests pass)

`create()` now compares `metadata["branch"]` against the branch computed from the requested `task_id`/`slug` when reusing an existing worktree. On mismatch it raises `RuntimeError` fail-closed, preserving the existing worktree, branch, and marker unchanged.

## SEC-02 — Marker write failure / orphan worktree (FIXED)

**Severity:** High  
**File:** `services/engineering/worktree.py:259-328`  
**Status:** FIXED — independently reviewed and APPROVED  
**Evidence:** Patch SHA-256 `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96`  
**Test:** `test_create_rolls_back_worktree_on_marker_write_failure`

When `git worktree add` succeeds but marker creation fails, `_rollback_new_worktree()` removes the newly created worktree only after verifying (a) target is registered in `git worktree list --porcelain` and (b) target common directory matches expected. Original exception is chained via `from exc`; rollback failures are reported together.

## SEC-03 — Partial marker cleanup (FIXED)

**Severity:** Medium  
**File:** `services/engineering/worktree.py:272-276`  
**Status:** FIXED  
**Evidence:** Patch SHA-256 `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96`

On marker-write failure, `marker.unlink(missing_ok=True)` best-effort removes any partially written marker file after rollback.

## SEC-04 — Cross-repository safety (FIXED)

**Severity:** High  
**File:** `services/engineering/worktree.py:149-161, 183-195` (pre-existing, re-verified)  
**Status:** FIXED (pre-existing, not weakened)  
**Evidence:** `test_forged_repository_marker_is_rejected`, `test_remove_refuses_wrong_repository`

`_read_ownership()` compares common-directory identity and checks `git worktree list` registration. `remove()` rejects foreign repositories with `RuntimeError`.

## SEC-05 — Symlink / path escape (FIXED)

**Severity:** Medium  
**File:** `services/engineering/worktree.py:62-73, 87, 230` (pre-existing, re-verified)  
**Status:** FIXED (pre-existing, not weakened)  
**Evidence:** `test_symlink_escape_is_rejected`

`_target_path()` resolves paths and enforces `relative_to(base_dir)`; `marker.is_symlink()` and `target.is_symlink()` are rejected; marker reads refuse symlinks.

## SEC-06 — Legacy marker rejection (FIXED)

**Severity:** Medium  
**File:** `services/engineering/worktree.py:100-133` (pre-existing, re-verified)  
**Status:** FIXED (pre-existing, not weakened)  
**Evidence:** `test_legacy_marker_is_rejected_without_reset`

Plain-text (legacy) markers are refused with "legacy or incomplete ownership marker"; JSON markers require version + required fields.

## SEC-07 — Task ID collision (FIXED)

**Severity:** Medium  
**File:** `services/engineering/worktree.py:135-139` (pre-existing, re-verified)  
**Status:** FIXED (pre-existing, not weakened)  
**Evidence:** `test_create_refuses_normalized_task_id_collision`

`_read_ownership()` rejects when `metadata["task_id"] != task_id`; normalized task IDs that collide are detected.

## SEC-08 — TOCTOU residual risk (ACCEPTED RISK)

**Severity:** Medium  
**File:** `services/engineering/worktree.py` (architectural)  
**Status:** ACCEPTED RISK — documented, not mitigated in this scope  
**Reason:** A same-user hostile process could mutate Git metadata between ownership validation and the destructive Git command. No cross-process file locking added; Git itself serializes worktree creation via `-b` branch creation; marker `open("x")` is O_EXCL atomic. Explicitly documented as not providing same-user isolation.

## SEC-09 — Same-user isolation limitation (ACCEPTED RISK)

**Severity:** Medium  
**File:** `services/engineering/worktree.py` (architectural)  
**Status:** ACCEPTED RISK — documented, not claimed  
**Reason:** The ownership marker protects against accidental misuse and confused-deputy reuse, not against a hostile process running with the same OS user privileges. Not claimed as a security boundary.

## MAINT-01 — Dockerfile is a placeholder

**Severity:** Medium  
**File:** `Dockerfile`  
**Evidence state:** VERIFIED  
**Phase:** 1  
**Description:** The root `Dockerfile` is a generic `FROM alpine:3.24` placeholder with `CMD ["sh", "-c", "echo 'Replace Dockerfile...']`. It is not a production runtime image and cannot build or run the zwslcore stack.  
**Impact:** `docker build` and container deployment cannot work without replacing this file.  
**Remediation:** Replace with a real multi-stage Dockerfile that installs the Python runtime, copies source, installs dependencies, and sets the entrypoint.  
**Authorization:** Requires stack-specific runtime decisions — PROPOSED, not implemented without owner input.

## MAINT-02 — No root pyproject.toml

**Severity:** Medium  
**File:** (absent)  
**Evidence state:** VERIFIED  
**Phase:** 1  
**Description:** No `pyproject.toml` exists at the repository root. The provider subdirectory has its own `pyproject.toml`, but the root engineering package has no packaging metadata.  
**Impact:** `pip install` of the root package, reproducible dependency installation, and tool configuration (ruff, pytest, mypy) lack a central manifest.  
**Remediation:** Add a root `pyproject.toml` describing the package, Python version requirement, and tool configuration.  
**Authorization:** Requires dependency decisions — PROPOSED, not implemented without owner input.

## MAINT-03 — Root cache directories untracked

**Severity:** Low  
**Files:** `.venv/`, `.pytest_cache/`, `.ruff_cache/`  
**Evidence state:** VERIFIED  
**Phase:** 1  
**Description:** These directories exist at the repository root and are untracked. `.gitignore` may or may not cover them.  
**Impact:** Minor repository hygiene; no functional impact.  
**Remediation:** Verify `.gitignore` covers Python cache/venv patterns; no code change required if ignored.

## MAINT-04 — Provider build artifacts untracked

**Severity:** Low  
**Files:** `services/provider/.venv/`, `services/provider/.pytest_cache/`, `services/provider/zwslcore_provider.egg-info/`  
**Evidence state:** VERIFIED  
**Phase:** 1  
**Description:** Untracked build artifacts in the provider subdirectory.  
**Impact:** Minor repository hygiene; no functional impact.  
**Remediation:** Verify `.gitignore` covers these; no code change required if ignored.

## OPS-01 — tmp_out directory owned by root

**Severity:** Low  
**File:** `tmp_out/`  
**Evidence state:** VERIFIED  
**Phase:** 1  
**Description:** The `tmp_out/` directory is owned by `root` and untracked.  
**Impact:** May cause permission issues for the `cvsz` user when writing temporary output.  
**Remediation:** Investigate ownership; no code change required.  
**Authorization:** File-system operation outside repository scope — report only.

---

## Accepted risks (not blocking)

- SEC-08 (TOCTOU): Documented; requires same-user hostile access; not mitigated in this scope.
- SEC-09 (Same-user isolation): Not claimed; marker is accidental-misuse protection only.

## Findings requiring owner authorization (not implemented)

- MAINT-01 (Dockerfile): Stack-specific runtime decision required.
- MAINT-02 (pyproject.toml): Dependency/packaging decision required.
