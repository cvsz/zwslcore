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
| SEC-10 | `.env.production` contains real secrets | File exists on disk but NOT tracked by git; `.env.production` in `.gitignore` | VERIFIED | `git ls-files` returns nothing; `git check-ignore` confirms ignored |
| SEC-11 | `.env.production.backup.*` contains real secrets | Added explicit `.env.production.backup*` to `.gitignore` for defense-in-depth | VERIFIED | `git check-ignore` confirms ignored via `.env.*` + explicit rule |
| SEC-12 | `.env.cloudflare` contains Cloudflare token | File exists on disk but NOT tracked by git; `.env.cloudflare` matches `.env.*` in `.gitignore` | VERIFIED | `git check-ignore` confirms ignored |

## CI/CD remediation (PR #102)

| ID | Finding | Action | Evidence state | Verification |
|---|---|---|---|---|
| CI-01 | `repository-baseline` Fail — `python` not found in distroless runtime | Restored `cgr.dev/chainguard/python` multi-stage Dockerfile (build + runtime) with pinned digests | VERIFIED | Local docker build + `--entrypoint python` succeeds |
| CI-02 | `repository-baseline` Fail — `python-dateutil` conflict with botocore | Fixed `requirements.lock`: `python-dateutil==2.9.0.post0`, added `six==1.17.0`, corrected pip-compile `via` comments | VERIFIED | Local `pip-compile --check` equivalent passes |
| CI-03 | `build-scan-sbom` Fail — Chainguard base image CVEs | **BLOCKED** — CVE-2026-115557 Critical (no fix available), CVE-2026-114613 High (fix exists but cannot apply in distroless image without `apk`) | BLOCKED | Upstream Chainguard base image issue; requires new base image digest |
| CI-04 | S3 config support | Added `boto3` dependency, S3 config loader in `config.py`, `s3.local.yaml` template | VERIFIED | Local S3 download + `load_settings()` from S3 bucket succeeds |

## New features (PR #102)

| ID | Feature | Action | Evidence state | Verification |
|---|---|---|---|---|
| FEAT-01 | S3/SeaweedFS config loading | Provider config can be loaded from S3 bucket via `ZEAZ_S3_CONFIG_*` env vars | VERIFIED | `load_settings()` downloads and parses config from local SeaweedFS |
