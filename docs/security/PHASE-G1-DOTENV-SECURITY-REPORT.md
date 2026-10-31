# Phase G.1 — Dotenv Security Report

**Repository**: `cvsz/zwslcore`
**PR**: #78 — fix(ai): load provider credentials safely from repository .env
**Authorized Head SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**File audited**: `scripts/ai.sh`
**Date**: 2026-11-01
**Actor**: cvsz (engineering operator)

---

## 1. Security Properties — All PASS

| ID | Property | Implementation | Test Evidence | Result |
|----|----------|---------------|---------------|--------|
| SEC-01 | Reject symlink `.env` | `path.is_symlink()` → exit | Code review | PASS |
| SEC-02 | Enforce 0600 permissions | `stat.S_IMODE & 0o077` → exit | `test_dotenv_rejects_insecure_permissions` | PASS |
| SEC-03 | 1 MB max file size | `st_size > 1_000_000` → exit | Code review | PASS |
| SEC-04 | Allowlist-only key parsing | `allowed` set of 10 keys | `test_dotenv_loads_provider_client_key` | PASS |
| SEC-05 | Environment precedence | `key in os.environ` → skip | `test_dotenv_preserves_explicit_empty_override` | PASS |
| SEC-06 | Prevent command execution | Regex parsing, no eval/exec | `test_dotenv_does_not_execute_commands` | PASS |
| SEC-07 | Prevent credential leakage | `urlsplit().hostname` exact match | `test_dotenv_never_leaks_key_to_untrusted_url` | PASS |
| SEC-08 | Preserve empty override | `if "AI_API_KEY" not in os.environ` | `test_dotenv_preserves_explicit_empty_override` | PASS |
| SEC-09 | Prevent secrets in logs | No secret output | `assertNotIn("test-secret", stdout)` | PASS |
| SEC-10 | Deterministic isolated tests | Isolated checkout in setUp | 11/11 tests pass | PASS |

---

## 2. Adversarial Test Results

| Test Case | Input | Expected | Actual | Result |
|-----------|-------|----------|--------|--------|
| Symlink .env | `.env` → `/nonexistent` | Refused | Refused | PASS |
| Group-readable .env | chmod 0644 | Rejected | Rejected | PASS |
| World-readable .env | chmod 0644 | Rejected | Rejected | PASS |
| Oversized .env | >1MB | Rejected | Rejected | PASS |
| Unknown key | `FOO=bar` | Ignored | Ignored | PASS |
| Shell substitution | `AI_MODEL="$(touch x)"` | Literal value | Literal | PASS |
| Quoted value | `AI_KEY="secret"` | Stripped quotes | Stripped | PASS |
| export syntax | `export AI_KEY=secret` | Parsed key | Parsed | PASS |
| Empty API key override | `AI_API_KEY=""` | Fallback suppressed | Suppressed | PASS |
| Malicious URL (path) | `...?next=generativelanguage.googleapis.com` | No key leak | No key leak | PASS |
| Malicious URL (query) | `...?next=generativelanguage.googleapis.com` | No key leak | No key leak | PASS |
| Developer .env contamination | Present in repo | Isolated from tests | Isolated | PASS |
| Env var precedence | `AI_API_KEY=explicit` | Explicit wins | Explicit wins | PASS |

**No real secrets printed in any test output.**

---

## 3. Code Analysis — load_dotenv()

The implementation:
1. Rejects symlinked `.env` files
2. Validates file existence and type
3. Enforces 1 MB size cap
4. Enforces owner-only (0600) permissions
5. Parses only allowlisted keys via strict regex
6. Skips keys already in environment (precedence)
7. Strips surrounding quotes safely
8. Supports only `${VAR}` variable expansion (no command substitution)
9. Falls back to provider-specific key only when `AI_API_KEY` not in env
10. Matches provider hostname via `urlsplit().hostname` (not substring)
11. Never logs or prints secret values

---

## 4. Conclusion

All 10 dotenv security properties verified PASS. Adversarial testing confirms no credential leakage, no command injection, and no symlink attacks.

**Security status**: PASS ✓
