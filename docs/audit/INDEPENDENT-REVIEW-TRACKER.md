# Independent Review Tracker — Phase D

**Repository**: `cvsz/zwslcore`
**Reviewer**: `policedbc` (independent reviewer / security auditor)
**Engineer**: `cvsz` (repository owner / engineering maintainer)
**Date**: 2026-11-01

---

## Review Requests Submitted

| PR | SHA | Date Requested | Reviewer | Review State | Review Date | Reviewed SHA | Notes |
|-----|-----|----------------|----------|--------------|-------------|--------------|-------|
| #78 | `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` | 2026-11-01 | policedbc | APPROVED | 2026-11-01 | `a72fc000` | Previous APPROVED was DISMISSED; this is a fresh re-review |
| #73 | `44fdf4e72638b51d3e7a4a4ce0a70140700c880a` | 2026-11-01 | policedbc | APPROVED | 2026-11-01 | `44fdf4e7` | First review |
| #72 | `15e5de2026afb902fcc729b2e62b80b1e58576fd` | 2026-11-01 | policedbc | APPROVED | 2026-11-01 | `15e5de20` | First review; draft removed |
| #71 | `5921251d27013755eab8617716e3a76e8c70331b` | 2026-11-01 | policedbc | COMMENTED | 2026-11-01 | `5921251` | Engineering fixes complete; blocked by upstream Chainguard build-scan-sbom |

---

## Review Decisions Detail

### PR #78 — APPROVED

**Reviewed SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`

**Scope**: 5 files changed (docs updates + scripts/ai.sh + tests/test_ai_cli.py)

**Security verified**:
1. Symlink `.env` rejection via `path.is_symlink()`
2. `.env` permission check (must be 0600)
3. 1MB file size cap
4. Allowlisted keys only
5. Environment variable precedence over `.env`
6. Hostname-based provider mapping (prevents key leakage via crafted URLs)
7. Empty key disables fallback
8. No command execution from `.env` values
9. Secrets never logged in output

**CI**: All 7 checks pass including build-scan-sbom

**Status**: READY FOR MERGE

---

### PR #73 — APPROVED

**Reviewed SHA**: `44fdf4e72638b51d3e7a4a4ce0a70140700c880a`

**Scope**: 3 new files (docs/CHAT-UI-READINESS.md, scripts/chat_ui_contract.py, tests/test_chat_ui_contract.py)

**Security verified**: 13 static contract checks all PASS including:
- Direct Ollama disabled
- Public signup disabled by default
- Provider authentication enabled
- UI loopback by default
- All services loopback-bound

**CI**: All 7 checks pass including build-scan-sbom

**Scope note**: Static configuration assertions only; not a runtime E2E or authorization audit

**Status**: READY FOR MERGE

---

### PR #72 — APPROVED

**Reviewed SHA**: `15e5de2026afb902fcc729b2e62b80b1e58576fd`

**Scope**: 3 new files (docs/cloudshell-hybrid-cluster.md, scripts/cloudshell_cluster.py, tests/test_cloudshell_cluster.py)

**Security verified**:
1. Loopback-only default endpoint
2. Remote HTTPS required (plain HTTP rejected for non-loopback)
3. No credentials in URL
4. No redirects
5. URL must match requested URL
6. Concurrency bounded (1-10 jobs, 1-600s timeout)
7. Health checks via `/api/tags`
8. Failure tracking per job
9. No automatic tunnel creation

**Limitations documented**: no durable job queue, no tunnel provisioning, no auto-recovery, no model sharding, no live multi-node integration evidence

**CI**: All 4 checks pass including build-scan-sbom

**Status**: READY FOR MERGE (stacked on #71 branch; retarget to main after #71 merges)

---

### PR #71 — COMMENTED (not APPROVED)

**Reviewed SHA**: `5921251d27013755eab8617716e3a76e8c70331b`

**Engineering fixes verified**: All 5 policedbc CHANGES_REQUESTED findings addressed:
1. Ollama installer downloaded to temp file + verified before execute (no `curl | sh`)
2. Allowlisted `.env` AI settings loaded; secrets not leaked
3. Dangling symlink `.env` rejected before existence check
4. Free space checked at model store `~/.ollama`
5. `curl`/`zstd` verified before install; documentation explains opt-in flow

**Tests**: 9/9 `python3 -m unittest tests.test_cloudshell_installer -v` passed

**CI blocker**: build-scan-sbom FAILURE due to upstream Chainguard base image CVE (CVE-2026-115557 Critical, no fix on Python 3.15 image). Not caused by PR #71 changes.

**Status**: BLOCKED — awaiting Chainguard base image remediation upstream

---

## Review Protocol Compliance

| Requirement | Status |
|-------------|--------|
| Never self-approve | COMPLIANT |
| Never approve using cvsz on its own PR | COMPLIANT |
| Never bypass branch protection | COMPLIANT |
| Never bypass required checks | COMPLIANT |
| Never disable CodeQL | COMPLIANT |
| Never reduce vulnerability severity thresholds | COMPLIANT |
| Never force-push | COMPLIANT |
| Never rewrite published history | COMPLIANT |
| Never merge during Phase D | COMPLIANT |
| Review decisions reference exact SHA | COMPLIANT |
| Wait for actual GitHub review response | COMPLIANT |

---

## Pending Reviews

| PR | SHA | Blocker | Next Action |
|-----|-----|---------|-------------|
| #82 | `00b20d07f56161ef7c66fcc46f8589103d59b516` | policedbc review pending | Request policedbc review |
| #79 | `62afa1cec74042cbd7297942c1f5d8ca72212c64` | policedbc review pending | Request policedbc review |
| #76 | `f8b7c54f944b7d9c2a22617e467a7b5bf342d1fa` | policedbc review pending | Request policedbc review |
| #85 | `800c407a60a0` | policedbc re-review pending | Request policedbc re-review |
| #84 | `678987786e63` | policedbc re-review pending | Request policedbc re-review |
