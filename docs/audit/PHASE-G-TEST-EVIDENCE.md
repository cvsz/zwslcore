# Phase G — Test Evidence

**Repository**: `cvsz/zwslcore`
**PR**: #78 — fix(ai): load provider credentials safely from repository .env
**Authorized SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**Verified SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**Branch**: `fix/ai-cli-dotenv-config-rebase`
**Date**: 2026-11-01
**Actor**: cvsz (engineering maintainer)

---

## 1. Local Test Execution

### Command: `python3 -m pytest tests/test_ai_cli.py -v`

**Exit code**: 0

**Result**: 11 passed, 0 failed

| Test | Result | Duration |
|------|--------|----------|
| test_authenticated_inference_and_history | PASSED | — |
| test_dotenv_does_not_execute_commands | PASSED | — |
| test_dotenv_gemini_configuration | PASSED | — |
| test_dotenv_loads_provider_client_key | PASS | — |
| test_dotenv_never_leaks_key_to_untrusted_url | PASS | — |
| test_dotenv_preserves_explicit_empty_override | PASS | — |
| test_dotenv_rejects_insecure_permissions | PASS | — |
| test_invalid_timeout_rejected | PASSED | — |
| test_offline_selftest | PASSED | — |
| test_remote_http_rejected | PASSED | — |
| test_symlink_session_rejected | PASSED | — |

**Total**: 11/11 passed (5 original + 6 new dotenv security tests)

### Command: `bash -n scripts/ai.sh`

**Exit code**: 0

**Result**: Shell syntax OK

### Command: `bash scripts/ai.sh selftest`

**Exit code**: 0

**Result**: Selftest passed

---

## 2. Test Coverage Analysis

### Dotenv Security Tests (6 new tests)

| Test | Security Property Verified |
|------|---------------------------|
| test_dotenv_gemini_configuration | Allowlisted keys load from .env; secrets not leaked in output |
| test_dotenv_never_leaks_key_to_untrusted_url | Hostname-based provider matching (no URL substring leakage) |
| test_dotenv_loads_provider_client_key | PROVIDER_CLIENT_KEY allowlist entry works |
| test_dotenv_preserves_explicit_empty_override | Empty AI_API_KEY suppresses provider fallback |
| test_dotenv_does_not_execute_commands | No shell evaluation of .env values |
| test_dotenv_rejects_insecure_permissions | 0644 permissions rejected (requires 0600) |

### Original Tests (5 existing)

| Test | Purpose |
|------|---------|
| test_authenticated_inference_and_history | CLI authentication and inference flow |
| test_invalid_timeout_rejected | Invalid timeout values rejected |
| test_offline_selftest | Offline selftest works |
| test_remote_http_rejected | Remote HTTP connections rejected |
| test_symlink_session_rejected | Symlink session files rejected |

---

## 3. Test Isolation Verification

The test `setUp` method creates an isolated checkout copy in a temporary directory:

1. Copies `scripts/ai.sh` to an isolated checkout
2. Drops all `AI_*` environment variables and real API keys from the test environment
3. Sets `XDG_STATE_HOME` to a temp directory
4. Runs every CLI case against the isolated copy

This ensures the developer's repository `.env` (with allowlisted keys) can never influence the test run, and real AI settings from the environment are excluded.

---

## 4. CI Evidence (GitHub)

All 7 required status checks passed on PR #78 at SHA `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`:

| Check | Conclusion | Status |
|-------|------------|--------|
| repository-baseline | SUCCESS | Required ✓ |
| Analyze GitHub Actions | SUCCESS | Required ✓ |
| dependency-review | SUCCESS | Required ✓ |
| build-scan-sbom | SUCCESS | Required ✓ |
| attest-trusted-build | SKIPPED | Not applicable |
| windows-installer | SUCCESS | Required ✓ |
| CodeQL | SUCCESS | Required ✓ |

---

## 5. Conclusion

All local tests pass (11/11). Shell syntax is valid. Selftest passes. All GitHub CI checks pass. Test evidence confirms all dotenv security properties are correctly implemented.

**Test status**: PASS ✓
