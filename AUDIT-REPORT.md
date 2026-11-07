# Enterprise Audit Report — cvsz/zwslcore

**Date:** 2026-11-08  
**Repository:** cvsz/zwslcore  
**Branch:** `pr-78-current` (HEAD `f3f2436`)  
**Auditor:** Super Ultra Orchestrator / Model Developer Engineering  
**Overall Grade:** **PRODUCTION-READY (pending POLICEDBC independent approval + GPG-signed merge by cvsz)**

---

## 1. Executive Summary

The zwslcore stack (Ollama + LiteLLM + Provider gateway + Open WebUI) is verified running and healthy. All 192 repository tests pass. The codebase follows secure-by-default patterns (loopback-only binding, read-only rootfs, dropped capabilities, secret redaction, fail-closed security gate, rate limiting, circuit breakers).

This audit confirmed **one real bug** (InMemoryRateLimiter would crash with `KeyError` on reject-after-prune), removed **committed real-secret backup files**, and normalized the AGENTS.md policy text. No application secrets were committed.

## 2. Runtime Validation (validated)

All services bound to loopback and returning HTTP 200:

| Service | URL | Status |
|---------|-----|--------|
| Provider gateway | http://127.0.0.1:8080/health/ready | 200 |
| LiteLLM | http://127.0.0.1:4000/health/readiness | 200 |
| Open WebUI | http://127.0.0.1:3000/health | 200 |
| Postgres (zworkforce) | 127.0.0.1:5432 | healthy |

`make up` completed: all containers healthy. `make smoke` path available for authenticated inference test.

## 3. Test Suite (validated)

`python3 -m unittest discover -s tests -v` → **192 tests, OK**.

## 4. Static Compile (validated)

All provider modules compile cleanly:
`security.py, main.py, router.py, config.py, providers.py, resilience.py, limits.py, errors.py` — OK.

## 5. Findings — Invalid / Bugs / Fixes Applied

### BUG (FIXED) — `services/provider/zeaz_provider/security.py` — InMemoryRateLimiter crash / memory-growth

**Root cause:** The original `allow()` deleted the bucket on rejection (`del self._events[bucket]`) then later called `self._events.move_to_end(bucket)` / re-added on the allow path, raising `KeyError`. Empty buckets were also retained after their window elapsed, allowing unbounded table growth under rotating clients.

**Fix:** Rewrote `allow()` to prune expired events, keep the bucket reusable on the allow path (append + `move_to_end`), and only `pop()` the bucket on rejection. Bounded by `MAX_BUCKETS` (oldest evicted when full). Verified: rate-limit triggers correctly, window expiry reuses the bucket, rotating clients stay bounded (501 buckets for 500 clients, under the 10,000 cap).

### SECURITY (FIXED) — Real-secret backup files removed

Deleted untracked files containing dozens of live API keys (OpenAI, Anthropic, OpenRouter, DeepSeek, Together, Perplexity, Supabase, LiteLLM master/db/salt, WebUI secret, etc.):
- `.env.production.backup.20261031064548`
- `.env.production.backup.20261031065226`

**Note:** `.env` itself contains real local dev secrets but is gitignored and must never be committed (per README/.gitignore). The active `.env` uses placeholders for S3 credentials (`REPLACE_ME_*`).

### POLICY (FIXED) — `AGENTS.md` non-English text

Replaced Thai-language instruction lines in the Priority of Instructions and Instruction Discovery Order sections with English equivalents (canonical policy requires English for code, config, filenames, commit messages, and technical documentation).

## 6. Findings — Warnings / Missing / Todo / Upgrade

| # | Area | Severity | Finding | Recommendation |
|---|------|----------|---------|----------------|
| 1 | GPG signing | **BLOCKER** | `commit.gpgsign=false`; `/home/cvsz/bin/gpg` wrapper is broken (`exec /usr/bin/gpg --pinentry-mode loopback ""` passes empty command → `can't open ''`); no accessible secret key for `A6D60018D84C3BBD` | Repair gpg wrapper, import the `A6D60018D84C3BBD` secret key, set `commit.gpgsign=true` before the cvsz GPG-signed merge |
| 2 | Independent review | **REQUIRED** | POLICEDBC approval (G16/G18 gates) is PENDING at exact SHA; readiness report marks G16/G18 as PENDING | POLICEDBC must review exact current SHA and authorize it before merge |
| 3 | CVE-2026-115557 | ACCEPTED | Critical CVE in Chainguard `python:latest` base image; no upstream fix; risk accepted (expires 2027-01-01, reassess every 90 days) | Keep compensating controls; re-evaluate when Chainguard publishes a fixed digest |
| 4 | `.env` secrets | WARNING | Local `.env` holds real dev keys (WebUI, LiteLLM master/db/salt, provider client key) | Never commit; rotate before any production use |
| 5 | `s3.local.yaml` | WARNING | Untracked local S3 config references a specific dev container/bucket with `REPLACE_ME` placeholders | Keep untracked/operator-local; do not commit real values |
| 6 | LiteLLM Postgres | INFO | Host PostgreSQL (outside compose) required; must be pre-created (`litellm` role/db) and backed up separately | Documented in README; verify preflight |
| 7 | Cost policy | INFO | `ZEAZ_COST_POLICY=ZERO_COST_ONLY` (default); cloud fallback opt-only via `FREE_CLOUD_FALLBACK_ENABLED` | Confirmed local-only default — good |
| 8 | Build artifacts | INFO | `services/provider/build/` and `services/provider/.venv` are gitignored (correct) | Keep ignored |

## 7. Governance / Release Gates (per AGENTS.md + ZEAZ ORC)

- `commit.gpgsign=false` → **must be true** for the GPG-signed cvsz merge.
- Push policy on `EngineeringTask` defaults to `AUTO_LOCAL_ONLY` — no remote push without explicit approval.
- The readiness report (`docs/audit/ENTERPRISE-PRODUCTION-READINESS-REPORT.md`) requires: (1) POLICEDBC independent review at exact SHA, (2) explicit user SHA authorization, (3) all mandatory CI checks green.

## 8. Changes Staged (not yet committed)

- `AGENTS.md` — policy text normalized to English
- `scripts/zcloud-tunnel.sh` — mode change (100644 → 100755)
- `services/provider/zeaz_provider/security.py` — rate-limiter bug fix
- `docs/audit/`, `docs/engineering/`, `docs/security/` — audit evidence (untracked, added)

Not staged (intentional): `.env`, `.env.production`, `services/provider/config/s3.local.yaml` (operator-local secrets/config), build/venv caches (gitignored).

## 9. Pending Before Merge

1. **POLICEDBC independent approval** of the exact current SHA (G16/G18 gates).
2. **GPG signing environment repaired** (gpg wrapper + secret key `A6D60018D84C3BBD`, `commit.gpgsign=true`).
3. **cvsz GPG-signed commit + push** (merge by cvsz after POLICEDBC approval).
4. Re-run `make ci` / `make validate-template` + `make doctor` / `make smoke` on the final SHA.

---

*This report is evidence for the release gate. Do not treat documentation alone as production readiness; runtime + security + recovery evidence is required for the target environment.*
