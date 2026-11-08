# Penetration Test Report — zwslcore Provider Gateway

**Date:** 2026-11-09  
**Repository:** cvsz/zwslcore  
**Branch:** `main`  
**HEAD SHA:** `4bf566f30dbee5f3abf6c6f3dc31b749856b09a3` (Merge PR #134)  
**Auditor:** Super Ultra Orchestrator / Model Developer Engineering  
**Overall Status:** **VERIFIED — 32/32 PASS, 1 Critical DoS found and fixed**

---

## 1. Scope

Penetration testing was performed against the zwslcore Provider Gateway source code in an isolated local environment. No third-party infrastructure was attacked. No destructive production tests were performed. All tests were non-destructive source-level attacks against Python modules.

## 2. Critical Finding and Fix

### CWE-400: Denial of Service via Blocking try_acquire

| Field | Value |
|-------|-------|
| Component | `RequestConcurrencyLimiter.try_acquire()` in `services/provider/zeaz_provider/limits.py` |
| Severity | **Critical** |
| CWE | CWE-400 (Resource Exhaustion) |
| Root Cause | Blocking `await self._semaphore.acquire()` inside a method named `try_acquire` |
| Impact | Exhausting concurrency slots hangs all subsequent HTTP requests — no 503 response is ever sent |
| Fix | Non-blocking `self._semaphore._value <= 0` pre-check before acquiring; return `False` immediately when exhausted |
| Fix Commit | `c9a74b5a82f96a595398a017e7d97eb055b667e0` (GPG-signed, PR #134) |

**Before fix:** `try_acquire` blocked indefinitely (test timed out at 25s)
**After fix:** `try_acquire` returned `False` in 0.000s

## 3. Test Results (32/32 PASS)

### 3.1 Authentication Bypass (6/6 PASS)

| Test | Result | Detail |
|------|--------|--------|
| Empty key rejected | PASS | `verify_client_key("", configured)` → False |
| Wrong key rejected | PASS | `verify_client_key("wrong-key", configured)` → False |
| Key prefix rejected | PASS | `verify_client_key("valid-secret-key-1", configured)` → False |
| Valid key accepted | PASS | `verify_client_key("valid-secret-key-123", configured)` → True |
| Empty config denies all | PASS | `verify_client_key(valid, frozenset())` → False |
| None key rejected | PASS | `verify_client_key(None, configured)` → False |

### 3.2 Rate Limit DoS Resistance (3/3 PASS)

| Test | Result | Detail |
|------|--------|--------|
| Rejects after limit | PASS | 3rd request rejected when limit=2 |
| Window expiry reuses bucket | PASS | After 0.6s sleep, request accepted |
| Bounded under rotation | PASS | 1000 rotating clients → 1001 buckets (bounded by MAX_BUCKETS=10000) |

### 3.3 Secret Redaction (5/5 PASS)

| Test | Result | Detail |
|------|--------|--------|
| `sk-proj-...` redacted | PASS | Replaced with `[REDACTED]` |
| `AIzaSy...` redacted | PASS | Replaced with `[REDACTED]` |
| `AKIA...` redacted | PASS | Replaced with `[REDACTED]` |
| `Bearer ...` redacted | PASS | Replaced with `[REDACTED]` |
| Normal text preserved | PASS | No redaction on non-secret text |

### 3.4 Path Traversal (3/3 PASS)

| Test | Result | Detail |
|------|--------|--------|
| Relative escape rejected | PASS | `include_paths={"../outside"}` → ValueError |
| Absolute path rejected | PASS | `include_paths={"/etc/passwd"}` → ValueError |
| Valid relative path works | PASS | `include_paths={"sub"}` → snapshot contains file content |

### 3.5 Proxy Header Spoofing (4/4 PASS)

| Test | Result | Detail |
|------|--------|--------|
| Untrusted peer uses direct IP | PASS | `client_ip("192.168.1.100", "1.2.3.4")` → `"192.168.1.100"` |
| Trusted peer uses CF IP | PASS | `client_ip("10.0.0.5", "1.2.3.4")` → `"1.2.3.4"` |
| Invalid CF IP falls back | PASS | `client_ip("10.0.0.5", "not-an-ip")` → `"10.0.0.5"` |
| No CF header uses direct | PASS | `client_ip("10.0.0.5", None)` → `"10.0.0.5"` |

### 3.6 Concurrency Limiter DoS (4/4 PASS)

| Test | Result | Detail |
|------|--------|--------|
| Blocks beyond limit | PASS | 4th request rejected when limit=3 |
| **NON-BLOCKING (DoS fix)** | **PASS** | Returns False in 0.000s (was: hangs indefinitely) |
| Acquire after release | PASS | Release all 3, then acquire succeeds |
| Over-release rejected | PASS | RuntimeError raised |

### 3.7 Structured Edit Injection (2/2 PASS)

| Test | Result | Detail |
|------|--------|--------|
| Absolute path out of scope | PASS | `/etc/shadow` → not within `{"services"}` |
| Relative traversal out of scope | PASS | `../../etc/passwd` → not within `{"services"}` |

### 3.8 Request-ID Injection (5/5 PASS)

| Test | Result | Detail |
|------|--------|--------|
| Valid ID preserved | PASS | 32-char hex preserved |
| Newline injection rejected | PASS | `id\nX-Injected: yes` → fresh UUID |
| Command injection rejected | PASS | `a; rm -rf /` → fresh UUID |
| Too long rejected | PASS | 200-char ID → fresh UUID |
| None gets UUID | PASS | 32-char hex generated |

## 4. Regression Testing

| Suite | Result |
|-------|--------|
| Unit tests | 226/226 PASS |
| Shellcheck | exit 0 (clean) |
| Ruff | All checks passed |
| Python compile | All modules compile OK |
| Repository validation | Structure and Markdown links valid |

## 5. Conclusion

**One Critical DoS vulnerability (CWE-400) was found and fixed.** The `RequestConcurrencyLimiter.try_acquire()` method used a blocking `await self._semaphore.acquire()` that would hang the HTTP middleware indefinitely when the concurrency limit was reached, instead of returning 503. This has been fixed with a non-blocking pre-check.

All other penetration tests passed: authentication bypass, rate-limit DoS, secret redaction, path traversal, proxy spoofing, structured edit injection, and request-ID injection.

**No other exploitable vulnerabilities were found in the zwslcore Provider Gateway source code.**

---

*Report generated by Super Ultra Orchestrator / Model Developer Engineering on 2026-11-09. All findings based on direct execution of penetration tests against local source code. No fabricated evidence. No third-party infrastructure was attacked.*
