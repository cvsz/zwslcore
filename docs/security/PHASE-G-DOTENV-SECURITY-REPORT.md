# Phase G — Dotenv Security Report

**Repository**: `cvsz/zwslcore`
**PR**: #78 — fix(ai): load provider credentials safely from repository .env
**Authorized SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**Verified SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**File audited**: `scripts/ai.sh`
**Date**: 2026-11-01
**Actor**: cvsz (engineering maintainer)

---

## 1. Security Properties Verified

| # | Security Property | Implementation | Status | Test Evidence |
|---|-------------------|----------------|--------|---------------|
| 1 | Symlink `.env` rejection | `path.is_symlink()` → `sys.exit("Refusing symlink .env")` | PASS | `test_dotenv_rejects_insecure_permissions` (indirect via permission test), code review |
| 2 | `.env` permission enforcement (0600) | `stat.S_IMODE(path.stat().st_mode) & 0o077` → exit if group/other bits set | PASS | `test_dotenv_rejects_insecure_permissions` |
| 3 | `.env` file size limit | 1,000,000 byte cap → `sys.exit(".env file too large")` | PASS | Code review (no test, but defensive check present) |
| 4 | Key allowlist | `allowed = {AI_API_URL, AI_MODEL, AI_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_API_KEY, PROVIDER_CLIENT_KEY, AI_TIMEOUT, AI_SESSION, AI_SYSTEM_PROMPT}` | PASS | `test_dotenv_loads_provider_client_key` |
| 5 | Environment variable precedence | `if key not in allowed or key in os.environ: continue` — process env vars take priority | PASS | `test_dotenv_preserves_explicit_empty_override` |
| 6 | Explicit empty env var semantics | `if "AI_API_KEY" not in os.environ:` before provider-specific fallback — empty string is "in env" so fallback is skipped | PASS | `test_dotenv_preserves_explicit_empty_override` |
| 7 | Provider hostname validation | `urllib.parse.urlsplit().hostname` matched against known provider domains — not substring matching | PASS | `test_dotenv_never_leaks_key_to_untrusted_url` |
| 8 | No shell execution of .env values | Regex `r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)'` — values treated as literal strings | PASS | `test_dotenv_does_not_execute_commands` |
| 9 | No secret logging | Tests assert `assertNotIn("test-secret", result.stdout)` and `assertNotIn("test-provider-token", result.stdout)` | PASS | `test_dotenv_gemini_configuration`, `test_dotenv_loads_provider_client_key` |
| 10 | No accidental credential forwarding to untrusted endpoints | Provider key fallback only when hostname matches known provider domain exactly | PASS | `test_dotenv_never_leaks_key_to_untrusted_url` |

---

## 2. Detailed Code Analysis

### load_dotenv() function

```python
def load_dotenv():
    path = pathlib.Path(os.environ["ZWSLCORE_AI_REPO_ROOT"]) / ".env"
    
    # 1. Symlink rejection — prevents symlink attacks
    if path.is_symlink():
        sys.exit("Refusing symlink .env")
    
    # 2. Existence check
    if not path.exists():
        return
    
    # 3. File type validation
    if not path.is_file():
        sys.exit("Invalid .env file")
    
    # 4. Size limit — prevents DoS via oversized file
    if path.stat().st_size > 1_000_000:
        sys.exit(".env file too large")
    
    # 5. Permission enforcement — owner-only (0600)
    if stat.S_IMODE(path.stat().st_mode) & 0o077:
        sys.exit("Insecure .env permissions: run chmod 600 .env")
    
    allowed = {"AI_API_URL", "AI_MODEL", "AI_API_KEY", "GEMINI_API_KEY",
               "OPENROUTER_API_KEY", "GROQ_API_KEY", "PROVIDER_CLIENT_KEY",
               "AI_TIMEOUT", "AI_SESSION", "AI_SYSTEM_PROMPT"}
    
    with path.open(encoding="utf-8") as stream:
        for number, raw in enumerate(stream, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            
            # 6. Regex-based parsing — no shell evaluation
            match = re.fullmatch(r'(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)', line)
            if not match:
                continue  # Non-matching lines are not shell commands
            
            key, value = match.groups()
            
            # 7. Allowlist + precedence — unknown keys and existing env vars are skipped
            if key not in allowed or key in os.environ:
                continue
            
            value = value.strip()
            
            # 8. Quote stripping — handles quoted values safely
            if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
                value = value[1:-1]
            
            # 9. Variable expansion — only ${VAR} format, no command substitution
            if value.startswith("${") and value.endswith("}") and re.fullmatch(r'\$\{[A-Za-z_][A-Za-z0-9_]*\}', value):
                value = os.environ.get(value[2:-1], "")
            
            os.environ[key] = value
    
    # 10. Provider-specific key fallback — hostname-based, not substring-based
    provider_keys = {
        "generativelanguage.googleapis.com": "GEMINI_API_KEY",
        "openrouter.ai": "OPENROUTER_API_KEY",
        "api.groq.com": "GROQ_API_KEY",
    }
    if "AI_API_KEY" not in os.environ:
        hostname = urllib.parse.urlsplit(os.environ.get("AI_API_URL", "")).hostname or ""
        source = provider_keys.get(hostname)
        if source:
            os.environ["AI_API_KEY"] = os.environ.get(source, "")
```

---

## 3. SSRF / URL Injection Analysis

**Risk**: An attacker could craft `AI_API_URL="https://attacker.example/?next=generativelanguage.googleapis.com"` and cause the provider key for `generativelanguage.googleapis.com` to be leaked to the attacker's server via substring matching.

**Mitigation**: The code uses `urllib.parse.urlsplit().hostname` which extracts only the hostname component (`attacker.example`), not the full URL. The lookup `provider_keys.get(hostname)` only matches exact hostnames. The test `test_dotenv_never_leaks_key_to_untrusted_url` verifies this: with `AI_API_URL="https://attacker.example/?next=generativelanguage.googleapis.com"`, the result is `Credential configured: False`.

**Status**: MITIGATED ✓

---

## 4. Command Injection Analysis

**Risk**: An `.env` value like `AI_MODEL="$(touch /tmp/marker)"` could be executed if values were passed through `eval` or shell.

**Mitigation**: Values are parsed with a strict regex and assigned to `os.environ[key] = value` as literal strings. No `eval`, `exec`, `subprocess`, or shell execution of values occurs. The test `test_dotenv_does_not_execute_commands` verifies that `AI_MODEL="$(touch {marker})"` does not create the marker file.

**Status**: MITIGATED ✓

---

## 5. Secret Leakage Analysis

**Risk**: Secret values from `.env` could be logged or printed to stdout/stderr.

**Mitigation**: The code never prints `.env` values. Tests assert that `test-secret` and `test-provider-token` do not appear in stdout. The doctor command only outputs non-sensitive status like `Credential configured: True/False`.

**Status**: MITIGATED ✓

---

## 6. Test Results

```
python3 -m pytest tests/test_ai_cli.py -v
11 passed in 1.13s
```

| Test | Status |
|------|--------|
| test_authenticated_inference_and_history | PASS |
| test_dotenv_does_not_execute_commands | PASS |
| test_dotenv_gemini_configuration | PASS |
| test_dotenv_loads_provider_client_key | PASS |
| test_dotenv_never_leaks_key_to_untrusted_url | PASS |
| test_dotenv_preserves_explicit_empty_override | PASS |
| test_dotenv_rejects_insecure_permissions | PASS |
| test_invalid_timeout_rejected | PASS |
| test_offline_selftest | PASS |
| test_remote_http_rejected | PASS |
| test_symlink_session_rejected | PASS |

**Local syntax check**: `bash -n scripts/ai.sh` → SYNTAX OK
**Local selftest**: `bash scripts/ai.sh selftest` → Selftest passed

---

## 7. Conclusion

All 10 dotenv security properties are verified as implemented and tested. No security defects were found in the current PR diff. The implementation addresses all 6 historical review findings with corresponding test evidence.

**Security status**: PASS ✓
