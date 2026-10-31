# Remediation Log

**Repository:** `cvsz/zwslcore`  
**Base SHA:** `df7ef0eae393f44f39c5393533531fc4171c6156`  
**Log date:** 2026-10-31  

---

## Completed remediation

| ID | Finding | Action | Evidence state | Verification |
|---|---|---|---|---|
| SEC-01 through SEC-07 | Worktree security defects | Patch applied to `services/engineering/worktree.py` + regression tests in `tests/test_engineering_change_snapshot.py` | VERIFIED (independently reviewed APPROVED) | 9/9 security tests, 13/13 change snapshot, 49/49 engineering regression, 197/197 full discovery, CI-equivalent exit 0 |
| SEC-08 | TOCTOU residual risk | Documented as accepted risk; no same-user isolation claimed | DOCUMENTED | N/A (architectural limitation) |
| SEC-09 | Same-user isolation limitation | Documented as not claimed | DOCUMENTED | N/A (by design) |

## Proposed remediation (requires owner authorization)

| ID | Finding | Proposed action | Status | Authorization needed |
|---|---|---|---|---|
| MAINT-01 | Dockerfile placeholder | Replace with production multi-stage Dockerfile | PROPOSED | Stack runtime decision |
| MAINT-02 | No root pyproject.toml | Add root `pyproject.toml` with package metadata + tool config | PROPOSED | Packaging/dependency decision |
| MAINT-03 | Root cache dirs untracked | Verify `.gitignore` coverage | INVESTIGATE | None (read-only) |
| MAINT-04 | Provider build artifacts untracked | Verify `.gitignore` coverage | INVESTIGATE | None (read-only) |
| OPS-01 | `tmp_out/` owned by root | Investigate ownership | REPORT | File-system access |

## Verification gates remaining

| Gate | Status | Required to close |
|---|---|---|
| GitHub Required Checks (6 contexts) | NOT VERIFIED | PR must exist; GitHub Actions must report all checks passing for PR head commit |
| Independent GitHub review by `policedbc` | PENDING | `policedbc` must authenticate and submit real GitHub PR review |
| Explicit merge authorization | NOT AUTHORIZED | Repository owner must authorize merge |

## Items intentionally NOT changed

- Pre-existing unstaged modifications (8 tracked files): preserved per governance rule 1.3
- Pre-existing untracked files (13): preserved per governance rule 1.3
- Pre-existing stash `stash@{0}`: preserved, not touched
- Secret files (`.env`, `.env.ai`, `.env.production`): not read, not touched, not committed
- Provider build artifacts: not deleted (governance rule 1.3)
