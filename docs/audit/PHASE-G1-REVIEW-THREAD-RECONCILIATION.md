# Phase G.1 — Review Thread Reconciliation

**Repository**: `cvsz/zwslcore`
**PR**: #78 — fix(ai): load provider credentials safely from repository .env
**Authorized Head SHA**: `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`
**Base Branch**: `main`
**Date**: 2026-11-01
**Actor**: cvsz (engineering operator), policedbc (independent reviewer)

---

## 1. Review Thread Inventory

All 9 PR comments retrieved via `gh pr view 78 --json comments`:

| # | Author | Type | Commit Scanned | Path | Line | Resolution Required |
|---|--------|------|----------------|------|------|---------------------|
| 1 | ecc-tools | Automated scan | `77f7205c` (old) | N/A | N/A | No — outdated commit |
| 2 | ecc-tools | Automated scan | `77f7205c` (old) | N/A | N/A | No — outdated commit |
| 3 | ecc-tools | Automated scan | `77f7205c` (old) | N/A | N/A | No — neutral, repository-level |
| 4 | ecc-tools | Automated scan | `77f7205c` (old) | N/A | N/A | No — outdated commit |
| 5 | chatgpt-codex-connector | Automated review | `77f7205c` (old) | N/A | N/A | No — informational |
| 6 | ecc-tools | Automated scan | `a72fc000` (current) | N/A | N/A | No |
| 7 | ecc-tools | Automated scan | `a72fc000` (current) | N/A | N/A | No |
| 8 | ecc-tools | Automated scan | `a72fc000` (current) | N/A | N/A | No — neutral, repository-level |
| 9 | ecc-tools | Automated scan | `a72fc000` (current) | N/A | N/A | No |

**Human review threads requiring resolution by policedbc**: 0

---

## 2. Historical Findings — Independent Verification

All 6 findings from Phase G were independently verified against the current PR diff at SHA `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e`.

### Finding 1: Hostname-based provider matching (P1)

**Original concern**: URL substring matching could leak provider keys to crafted URLs.

**Current implementation** (`scripts/ai.sh`):
```python
hostname = urllib.parse.urlsplit(os.environ.get("AI_API_URL", "")).hostname or ""
source = provider_keys.get(hostname)
```

**Verification**: Parsed hostname matched against exact provider domain keys. Not substring matching.

**Test**: `test_dotenv_never_leaks_key_to_untrusted_url` — `https://attacker.example/?next=generativelanguage.googleapis.com` → Credential configured: False

**Status**: RESOLVED ✓

### Finding 2: PROVIDER_CLIENT_KEY allowlist (P1)

**Original concern**: PROVIDER_CLIENT_KEY not in dotenv allowlist.

**Current implementation** (`scripts/ai.sh`):
```python
allowed = {"AI_API_URL", "AI_MODEL", "AI_API_KEY", "GEMINI_API_KEY",
           "OPENROUTER_API_KEY", "GROQ_API_KEY", "PROVIDER_CLIENT_KEY",
           "AI_TIMEOUT", "AI_SESSION", "AI_SYSTEM_PROMPT"}
```

**Test**: `test_dotenv_loads_provider_client_key` — loads PROVIDER_CLIENT_KEY without leaking secret

**Status**: RESOLVED ✓

### Finding 3: Cloud Shell dotenv documentation (P2)

**Original concern**: Documentation didn't reflect automatic dotenv loading behavior.

**Current implementation** (`docs/CLOUDSHELL-CLOUDFLARE-TUNNEL.md`):
Updated to state: "loads only an allowlisted set of AI settings from a repository .env when that file has 0600 permissions; it never sources the file into a shell"

**Status**: RESOLVED ✓

### Finding 4: .env permission documentation (P2)

**Original concern**: .env 0600 permission not documented in setup guides.

**Current implementation** (`docs/development.md`, `docs/startup.md`):
Both updated with `chmod 600 .env` instructions.

**Test**: `test_dotenv_rejects_insecure_permissions` — verifies 0644 permissions rejected

**Status**: RESOLVED ✓

### Finding 5: CLI test isolation (P2)

**Original concern**: Tests could be influenced by developer's repository .env.

**Current implementation** (`tests/test_ai_cli.py`):
Isolated checkout copy in `setUp`, drops all `AI_*` env vars, uses temp `XDG_STATE_HOME`.

**Status**: RESOLVED ✓ (all 11 tests pass)

### Finding 6: Explicit empty AI_API_KEY preservation (P2)

**Original concern**: Empty AI_API_KEY could be overwritten by provider fallback.

**Current implementation** (`scripts/ai.sh`):
```python
if key not in allowed or key in os.environ:
    continue
if "AI_API_KEY" not in os.environ:
    # provider-specific fallback
```

**Test**: `test_dotenv_preserves_explicit_empty_override` — `env["AI_API_KEY"] = ""` suppresses fallback

**Status**: RESOLVED ✓

---

## 3. Reviewer Resolution

**Reviewer**: policedbc

**Action**: All 6 findings independently verified as resolved. No threads require resolution action.

**Review state**: APPROVED on exact SHA `a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e` at `2026-10-31T22:21:36Z`

**Dismissed**: No

**Previous DISMISSED**: On old commit `77f7205c54a7f306d134ae27bd384758a474f641` — superseded by current APPROVED

---

## 4. Conclusion

0 unresolved human review threads. All 6 historical findings resolved with test evidence. policedbc APPROVED is current and valid on the exact authorized SHA.
