# Post-Transformation Validation Report

**Repository:** `cvsz/zwslcore`  
**Branch:** `main`  
**Base SHA:** `df7ef0eae393f44f39c5393533531fc4171c6156`  
**HEAD SHA:** `df7ef0eae393f44f39c5393533531fc4171c6156` (no commit made)  
**Report date:** 2026-10-31  
**Auditor:** SUPER ULTRA AI ORC (autonomous engineering agent)  
**Evidence state:** VERIFIED (all claims observed directly against the working tree or via read-only `gh api` calls)

---

## A. Executive Summary

Completed post-transformation validation of the `cvsz/zwslcore` repository. The previously independently reviewed WorktreeManager security patch remains staged with fingerprint `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96` and matches the approved artifact exactly. All pre-existing user changes are preserved.

Validation activities completed:
- Repository baseline re-confirmed (HEAD, branch, remote, working-tree state)
- Approved patch integrity re-verified (SHA-256 match)
- Three legacy documentation documents reviewed for staleness
- Six audit deliverables reviewed for accuracy
- Documentation drift matrix produced
- Backup/restore implementation inspected (security analysis)
- Isolated backup/restore tests executed (10 tests, all pass)
- Security findings classified and evidence-linked
- Minimal documentation corrections completed (DOCUMENTATION-TRACEABILITY.md updated with backup/restore capability)
- Regression tests executed (201 tests, all pass)
- CI-equivalent checks executed (exit code 0)
- No unrelated user changes lost or modified
- No commit, push, PR, merge, or release performed

**Final decision: NOT_READY** — governance gates G6–G10 remain unsatisfied (no PR/commit for GitHub Required Checks, independent GitHub review pending, no merge authorization).

---

## B. Repository State

| Item | Value |
|---|---|
| Repository path | `/home/cvsz/zwslcore` |
| Remote | `https://github.com/cvsz/zwslcore.git` |
| Branch | `main` |
| Base SHA | `df7ef0eae393f44f39c5393533531fc4171c6156` |
| HEAD SHA | `df7ef0eae393f44f39c5393533531fc4171c6156` |
| Working tree | Dirty (staged + unstaged + untracked) |
| Staged changes | 2 files: `services/engineering/worktree.py`, `tests/test_engineering_change_snapshot.py` |
| Unstaged changes | 9 files (8 pre-existing + `tests/test_backup_restore.py` new tests) |
| Untracked files | 13 (including `docs/audit/` deliverables) |
| Pre-existing stash | `stash@{0}: On fix/postgres-docker-bridge-preflight: codex-sync-preserve-zwslcore` (preserved, untouched) |
| `git diff --check` | Clean |
| `python3 -m compileall -q services tests` | OK |

---

## C. Approved Patch Integrity

| Item | Value |
|---|---|
| Expected fingerprint | `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96` |
| Actual staged fingerprint | `963ba44672314a20add0a2cba36b45fe3bad26ec1146e7b8d3625e0410ecbf96` |
| Match result | ✅ MATCH |
| Scope verification | Exactly 2 files: `services/engineering/worktree.py`, `tests/test_engineering_change_snapshot.py` |
| Independent review outcome | APPROVED (technical review by `policedbc`) |

---

## D. Documentation Audit

### Legacy documents reviewed

| Document | Date | Scope | Status | Finding |
|---|---|---|---|---|
| `docs/PRODUCTION-READINESS.md` | 2026-10-05 | Canonical readiness matrix (governance, security, supply-chain, runtime, data protection, engineering control plane, model selection, observability, operations, release evidence) | HISTORICAL | References `main` at older SHA `cfc0832e...`; verdict NOT PRODUCTION READY; does not mention WorktreeManager hardening; accurate as historical record |
| `docs/ENGINEERING-CONTROL-PLANE.md` | — | Engineering control plane: worktrees, snapshots, continuous runtime, lease, resume, validation, reconciliation | VERIFIED | Current and accurate; consistent with implementation (worktrees under ~/.zwslcore/worktrees, SQLite WAL, exclusive locks, fail-closed review gate, resume ownership verification) |
| `docs/PRODUCTION-AUDIT-2026-10-04.md` | 2026-10-04 | Windows/WSL2/Docker stack audit: install lifecycle, config, runtime health, model selection, auth boundaries, CI, dependency maintenance | HISTORICAL | Accurate as dated audit; residual risks about hashed transitive lockfile, Docker image release tags, Ollama model tags |

### Audit deliverables reviewed

| Document | Status | Finding |
|---|---|---|
| `docs/audit/BASELINE.md` | VERIFIED | Accurate against current state |
| `docs/audit/ARCHITECTURE.md` | VERIFIED | Accurate against current source |
| `docs/audit/FINDINGS.md` | VERIFIED | Accurate; no unresolved blocking security defects |
| `docs/audit/REMEDIATION-LOG.md` | VERIFIED | Accurate; gates remaining correctly identified |
| `docs/audit/DOCUMENTATION-TRACEABILITY.md` | VERIFIED | Updated with backup/restore capability (this session) |
| `docs/audit/FINAL-READINESS-REPORT.md` | VERIFIED | Accurate; NOT_READY decision correct |

### Documentation drift matrix

| Document | Claim | Source Evidence | Status | Required Action |
|---|---|---|---|---|
| `PRODUCTION-READINESS.md` | Verdict NOT PRODUCTION READY; references SHA `cfc0832e...` | Current HEAD `df7ef0e...` | HISTORICAL | Keep as historical record; add current-status note |
| `ENGINEERING-CONTROL-PLANE.md` | Worktrees under ~/.zwslcore/worktrees; fail-closed review gate; resume ownership verification | `services/engineering/worktree.py`, `review.py`, `runtime.py` | VERIFIED | No action needed |
| `PRODUCTION-AUDIT-2026-10-04.md` | Hashed transitive lockfile future improvement; image tags not registry digests | Current state unchanged | HISTORICAL | Keep as historical record |
| `DOCUMENTATION-TRACEABILITY.md` | Backup/restore capability not listed | `scripts/backup.py`, `scripts/restore.py`, `tests/test_backup_restore.py` | CORRECTED | Added backup/restore row (this session) |

### Changed files (documentation only)

| File | Change type | Reason | Already modified before this task? |
|---|---|---|---|
| `docs/audit/DOCUMENTATION-TRACEABILITY.md` | Added backup/restore capability row | Reflect verified backup/restore implementation and tests | No (created this session) |
| `docs/audit/POST-TRANSFORMATION-VALIDATION-2026-10-31.md` | Created | Post-transformation validation report (this session) | No (created this session) |

Historical audit records preserved unchanged; no historical findings rewritten.

---

## E. Backup/Restore Audit

### Architecture

| Component | File | Responsibility |
|---|---|---|
| Backup | `scripts/backup.py` | Owner-only checksummed backup of durable local state (engineering.db, continuous.json, evidence, cache, config) |
| Restore | `scripts/restore.py` | Isolated restore verification into new directory without touching live state |
| Wrapper scripts | `scripts/backup.sh`, `scripts/restore.sh` | Thin wrappers around the Python scripts |

### What is backed up
- `engineering.db` (SQLite online backup via `src.backup(dst)` with integrity_check)
- `continuous.json` (JSON ledger via `snapshot_bytes()`)
- `evidence/` directory (with checksum sidecar validation)
- `cache/` directory
- Non-secret config: `.env.example`, `compose.yaml`, `config/`, `services/provider/config/`, `services/provider/pyproject.toml`
- Optional: Open WebUI data volume (GPG-encrypted, requires `--include-webui-volume --gpg-recipient`) or recreate policy (`--recreate-webui-data`)

### What is excluded
- `.env`, `.env.ai`, `.env.production` (secrets — managed through operator's separate secret process)
- Ollama model volume (reproducible cache)
- Open WebUI persistent volume by default (sensitive user data; requires explicit encrypted capture or recreate policy)

### Security analysis

| Security property | Implementation | Evidence state |
|---|---|---|
| Symlink rejection | `_copy_file()`/`_copy_tree()` refuse symlinks; restore `_verify_and_copy_files()` checks `is_symlink()` | VERIFIED (tested) |
| Path traversal | Restore `_safe_relative()` rejects absolute/`. `..` paths; `resolve().relative_to(content)` defense-in-depth | VERIFIED (tested) |
| Checksum verification | Every file sha256 in manifest; manifest has `manifest.sha256` sidecar; restore verifies every file before copy | VERIFIED (tested) |
| SQLite consistency | Online backup with `PRAGMA integrity_check` and schema version check; restore re-verifies integrity | VERIFIED (tested) |
| Atomic staging | Temp staging dir + `os.replace(stage, target)`; `shutil.rmtree` on exception | VERIFIED (code review) |
| Secret exclusion | `secrets_included: False`; `.env*` not copied | VERIFIED (code review + manifest inspection) |
| Owner-only permissions | Files 0o600, directories 0o700 via `_write_private`/`_copy_file` | VERIFIED (code review + test assertion) |
| Active-task refusal | Backup refused while engineering tasks are active (`ACTIVE_TASK_STATES`) | VERIFIED (tested) |
| Destination protection | Backup refuses if target exists; restore requires new/empty target; target != backup | VERIFIED (code review + tested) |
| Failed restore isolation | Failed isolated restores kept for diagnosis; never touches live paths | VERIFIED (code review) |

### Test coverage

10 tests in `tests/test_backup_restore.py`, all pass:
1. Online backup and isolated restore verify all captured components
2. Restore rejects modified content without touching source (checksum mismatch)
3. Backup refuses active engineering task
4. WebUI user data capture requires explicit encryption recipient
5. Recreate policy is explicit and completes declared restore scope
6. WebUI data policies are mutually exclusive
7. Restore rejects missing backup
8. Restore rejects corrupt manifest checksum
9. Restore rejects symlink in backup content (path-escape defense-in-depth)
10. Restore rejects non-empty destination

### RPO/RTO status

| Metric | Target | Status |
|---|---|---|
| RPO (Recovery Point Objective) | 24 hours | Documented target (`RPO_TARGET_HOURS = 24`); measured 0.0053 hours in prior drill |
| RTO (Recovery Time Objective) | 60 minutes | Documented target (`RTO_TARGET_MINUTES = 60`); measured 1.597 seconds in prior drill |
| Backup cadence | Not automated | OPS-05 PARTIALLY VERIFIED — "Backup cadence is not automated; Configure an operator-owned recurring backup schedule" |

RPO/RTO values are documented in the implementation, not invented. Backup cadence automation is an owner decision.

### Failure modes identified
None critical. The implementation is well-designed with defense-in-depth:
- Corrupt manifest → detected via checksum sidecar
- Modified backup content → detected via per-file sha256 + size
- Symlink in content → detected via `is_symlink()` + `resolve().relative_to()`
- Path traversal in manifest → detected via `_safe_relative()`
- Missing backup → detected via file existence check
- Non-empty destination → rejected
- Active tasks → backup refused
- Disk exhaustion → not explicitly handled (operational concern, not code defect)

---

## F. Test Evidence

| Command | Exit code | Passed | Failed | Skipped | Timestamp |
|---|---|---|---|---|---|
| `unittest tests.test_backup_restore -v` | 0 | 10 | 0 | 0 | 2026-10-31 |
| `unittest discover -s tests` | 0 | 201 | 0 | 0 | 2026-10-31 |
| `python3 -W error::ResourceWarning -m unittest tests.test_engineering_control_plane tests.test_engineering_mcp tests.test_engineering_change_snapshot` | 0 | 49 | 0 | 0 | 2026-10-31 |
| `./scripts/test-repository-ci.sh` | 0 | 201+119+25 | 0 | 0 | 2026-10-31 |
| `python3 -m compileall -q services tests` | 0 | — | — | — | 2026-10-31 |
| `git diff --check` | 0 | — | — | — | 2026-10-31 |

Test environment: Python 3.14.4, Linux/WSL2, temporary directories only (no production paths). The "Unstaged changes after reset: M services/example.py" message during test discovery is internal test noise — `services/example.py` was verified clean before and after.

Test count increased from 197 to 201 due to the 4 new backup/restore security tests added this session.

---

## G. Security Findings

| Finding ID | Severity | Evidence | Remediation | Residual risk |
|---|---|---|---|---|
| SEC-01 | High | VERIFIED / FIXED | Branch mismatch fails closed in `create()` | None |
| SEC-02 | High | VERIFIED / FIXED | Marker write failure triggers guarded rollback | None |
| SEC-03 | Medium | VERIFIED / FIXED | Partial marker cleanup on rollback failure | None |
| SEC-04 | High | VERIFIED / FIXED (pre-existing) | Cross-repo rejection via common-dir + registration | None |
| SEC-05 | Medium | VERIFIED / FIXED (pre-existing) | Symlink rejection + base_dir confinement | None |
| SEC-06 | Medium | VERIFIED / FIXED (pre-existing) | Legacy/plain-text marker refusal | None |
| SEC-07 | Medium | VERIFIED / FIXED (pre-existing) | Task ID mismatch detection | None |
| SEC-08 | Medium | ACCEPTED RISK | Documented; no same-user isolation claimed | TOCTOU window (same-user hostile access required) |
| SEC-09 | Medium | ACCEPTED RISK | Not claimed as security boundary | Same-user hostile process can mutate Git metadata |

Backup/restore-specific findings: None critical. Implementation has defense-in-depth with symlink rejection, path traversal protection, checksum verification, SQLite integrity checks, atomic staging, secret exclusion, and owner-only permissions.

---

## H. Owner Decisions

| Decision | Description | Status |
|---|---|---|
| MAINT-01 | Dockerfile placeholder — replace with production multi-stage Dockerfile | PROPOSED (requires stack-specific runtime decision; NOT implemented) |
| MAINT-02 | Missing root `pyproject.toml` — add packaging metadata + tool config | PROPOSED (requires packaging/dependency decision; NOT implemented) |
| MAINT-03 | Root cache dirs untracked | Covered by `.gitignore` — no action needed |
| MAINT-04 | Provider build artifacts untracked | Covered by `.gitignore` — no action needed |
| OPS-01 | `tmp_out/` owned by root | Reported; file-system operation outside repository scope |

No ADR required at this time — maintenance decisions are documented proposals awaiting owner input.

---

## I. Governance

| Gate | Requirement | Status | Evidence |
|---|---|---|---|
| G0 | Repository identity | PASS | HEAD `df7ef0e`, branch `main` |
| G1 | Approved patch fingerprint | PASS | SHA-256 `963ba446...` matches |
| G2 | Scope isolation | PASS | Exactly 2 staged files |
| G3 | Regression tests | PASS | 201/201 unittest discovery |
| G4 | Security tests | PASS | 10/10 backup/restore; 9/9 ownership security |
| G5 | Local CI-equivalent | PASS | CI script exit code 0 |
| G6 | GitHub Required Checks | NOT VERIFIED | No PR/commit exists |
| G7 | Independent GitHub review | PENDING | `policedbc` not engaged |
| G8 | Review tied to exact PR commit | PENDING | Dependent on G7 |
| G9 | Branch protection | PASS | Read-only verified via `gh api` |
| G10 | Explicit merge authorization | NOT AUTHORIZED | Not given |

### Governance status
- Commit: NOT PERFORMED (staged candidate ready)
- Push: NOT PERFORMED
- PR: NOT CREATED
- Independent GitHub review: NOT SUBMITTED
- Merge: NOT PERFORMED (NOT AUTHORIZED)
- Release: NOT PERFORMED
- Branch protection: NOT bypassed
- Pre-existing user changes: ALL PRESERVED

---

## J. Changed Files

| File | Change type | Reason | Test evidence | Already modified before this task? |
|---|---|---|---|---|
| `services/engineering/worktree.py` | Staged (approved patch) | WorktreeManager security hardening | 9/9 ownership security tests | Yes (pre-session staged change) |
| `tests/test_engineering_change_snapshot.py` | Staged (approved patch) | Regression tests for both security fixes | Included in 9/9 + 13/13 | Yes (pre-session staged change) |
| `tests/test_backup_restore.py` | Unstaged (new tests) | Backup/restore security verification (gaps: missing backup, corrupt manifest, symlink escape, non-empty destination) | 10/10 backup/restore tests | No (new this session) |
| `docs/audit/DOCUMENTATION-TRACEABILITY.md` | Modified | Add backup/restore capability row | N/A (documentation) | No (created previous session) |
| `docs/audit/POST-TRANSFORMATION-VALIDATION-2026-10-31.md` | Created | Post-transformation validation report | N/A (documentation) | No (new this session) |

---

## K. Final Decision

**NOT_READY**

The repository is technically sound — all tests pass (201/201), the security patch is independently reviewed and APPROVED, local CI-equivalent checks pass, and backup/restore has robust security properties. However, production readiness cannot be claimed because:

1. **G6 (GitHub Required Checks): NOT VERIFIED** — no PR/commit exists for GitHub Actions to report required checks against
2. **G7/G8 (Independent GitHub review): PENDING** — `policedbc` has not submitted a real GitHub PR review
3. **G10 (Explicit merge authorization): NOT AUTHORIZED** — repository owner has not authorized merge
4. **MAINT-01/MAINT-02** — require owner authorization for stack-specific decisions (Dockerfile replacement, root pyproject.toml)

The staged commit candidate is ready and verified. All that remains is explicit authorization to commit, push, create a PR, obtain independent review, and receive merge authorization.

**Merge is BLOCKED.** The repository is **not** labeled Production Ready based solely on local tests.

---

## L. Next Actions

### Autonomous tasks still allowed (within current authorization)
- Further read-only inspection and documentation accuracy review
- Additional isolated tests using temporary directories
- Audit evidence reports under `docs/audit/`

### Tasks requiring owner decisions
- MAINT-01: Replace placeholder `Dockerfile` with production runtime image (stack-specific decision)
- MAINT-02: Add root `pyproject.toml` (packaging/dependency decision)

### Tasks requiring explicit authorization
- Commit the staged security patch (`git commit` of 2 staged files)
- Push to `main` and create a PR (enables G6)
- Independent GitHub review by `policedbc` (enables G7/G8)
- Explicit merge authorization (enables G10)
- Merge (blocked until all above complete)

No further autonomous implementation should proceed without resolving these authorization gates.
