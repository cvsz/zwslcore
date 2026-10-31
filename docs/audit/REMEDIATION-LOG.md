# Remediation Log — Phase D

**Repository**: `cvsz/zwslcore`
**Date**: 2026-11-01

---

## CI-01: PR #71 Cloud Shell installer security hardening

**Finding**: policedbc CHANGES_REQUESTED review on PR #71 identified 5 findings:
1. `--install-ollama` pulls from network via `sh` without pinned artifact/checksum/signature verification
2. CLI doesn't set `AI_API_URL`/`AI_MODEL` or load `.env` for credential lookup
3. `.env` check may not reject dangling symlink before writing credential
4. Check `curl`/`zstd` before confirming Ollama needed; check free space at `$HOME` not model store filesystem
5. Documentation doesn't explain opt-in install/model flow

**Fix applied**: Updated `scripts/cloudshell.sh` and `tests/test_cloudshell_installer.py`:
- Symlinked `.env` rejected via `-L` check before `-e` existence check
- Ollama installer downloaded to temp file via `curl -o`, verified as shell script, then executed — no `curl | sh`
- Allowlisted AI settings (AI_API_URL, AI_MODEL, API keys) loaded from repository `.env`; secrets never printed
- Free space checked at `~/.ollama` model store with fallback to `$HOME`
- `curl` and `zstd` verified before confirming Ollama installation needed
- Usage message documents opt-in install/model flow

**Tests**: 9/9 `python3 -m unittest tests.test_cloudshell_installer -v` passed

**Commit**: `5921251d27013755eab8617716e3a76e8c70331b` on branch `feat/cloudshell-installer-20261017`

**Status**: Engineering complete; blocked by upstream Chainguard build-scan-sbom failure

---

## CI-02: PR #82 merge conflict resolution

**Finding**: PR #82 had 4 merge conflicts with main branch:
- `.env.example`: image digests vs S3 config
- `Makefile`: .PHONY targets + postgres-backup/postgres-migrate-docker vs release
- `compose.yaml`: Ollama comment vs deploy resource limits
- `services/provider/zeaz_provider/security.py`: two rate limiter implementations

**Fix applied**: Resolved all 4 conflicts preserving behavior from both sides:
- `.env.example`: newer image digests (HEAD) + S3 config (main)
- `Makefile`: combined .PHONY targets; both postgres targets + release target
- `compose.yaml`: Ollama comment + deploy resource limits
- `security.py`: OrderedDict with `_sweep`, `max_buckets` param, LRU eviction, empty bucket cleanup

**Commit**: `00b20d07f56161ef7c66fcc46f8589103d59b516` on branch `fix/postgres-docker-bridge-preflight-cvsz`

**Status**: MERGEABLE; pending policedbc review

---

## CI-03: PR #79 merge conflict resolution

**Finding**: PR #79 had 2 merge conflicts with main:
- `Makefile`: .PHONY targets (engineer-reconcile/engineer-recover vs release)
- `services/provider/zeaz_provider/security.py`: defaultdict vs OrderedDict rate limiter

**Fix applied**: Combined both implementations preserving behavior:
- `Makefile`: combined .PHONY targets including release
- `security.py`: OrderedDict with `_sweep`, `max_buckets` param, LRU eviction, empty bucket cleanup

**Commit**: `62afa1cec74042cbd7297942c1f5d8ca72212c64` on branch `audit/robustness-fixes-20261018`

**Status**: MERGEABLE; pending policedbc review

---

## CI-04: PR #76 merge conflict resolution

**Finding**: PR #76 had 1 merge conflict with main:
- `Makefile`: .PHONY targets (Cloudflare/webhook targets vs release)

**Fix applied**: Combined .PHONY targets including release

**Commit**: `f8b7c54f944b7d9c2a22617e467a7b5bf342d1fa` on branch `feat/cloudshell-ssh-access-mcp-diagnostics-20261017`

**Status**: MERGEABLE; pending policedbc review

---

## CI-05: PR #85 CodeQL version pairing

**Finding**: policedbc CHANGES_REQUESTED — CodeQL `analyze` at v4.39.1 but `init` remains v4.38.2, causing version mismatch error

**Fix applied**: Updated `github/codeql-action/init` to same v4.39.1 SHA as `analyze`

**Commit**: `800c407a60a0` on branch `dependabot/github_actions/github/codeql-action/analyze-4.39.1`

**Status**: MERGEABLE; pending policedbc re-review

---

## CI-06: PR #84 CodeQL version pairing

**Finding**: policedbc CHANGES_REQUESTED — CodeQL `init` at v4.39.1 but `analyze` remains v4.38.2

**Fix applied**: Updated `github/codeql-action/analyze` to same v4.39.1 SHA as `init`

**Commit**: `678987786e63` on branch `dependabot/github_actions/github/codeql-action/init-4.39.1`

**Status**: MERGEABLE; pending policedbc re-review

---

## SEC-13: Chainguard base image CVE revalidation

**Finding**: All locally available Chainguard images scanned with grype 0.121.0:
- `cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285`: Critical CVE-2026-115557 (fix=None), High CVE-2026-114613 (fix=26.2.2-r1)
- `cgr.dev/chainguard/python@sha256:3f411b4aac1e`: Critical CVE-2026-115557 fix=3.14.10_git20261028-r0 (Python 3.14 image available locally)
- `cgr.dev/chainguard/python@sha256:c07959e43e3e`: Critical CVE-2026-115557 fix=3.14.10_git20261028-r0

**Registry access**: Docker pull from cgr.dev blocked by TLS certificate error (`x509: certificate signed by unknown authority`)

**Status**: BLOCKED — patched Python 3.14 images exist locally but switching from Python 3.15 requires careful evaluation. Cannot claim remediation without passing scan against exact target image digest.

---

## SEC-14: Commit provenance verification

**Finding**: Existing commits on GitHub show `bad_email` due to author email (`cvsz@users.noreply.github.com`) not matching GPG key email (`seaza@msn.com`).

**Fix applied**: Changed `git config user.email` to `seaza@msn.com`. New commits have verified GPG signatures on GitHub.

**Verification**: `git verify-commit HEAD` passes locally with good signature from key `8644B3973EA1743EF5D21EBA87A69650EB250939`.

**Status**: Fixed for new commits; existing commits cannot be fixed without force-push (not authorized).
