# Local-Only Routing — Security Documentation

## Overview

The ZEAZ Gateway enforces local-only inference routing through the `LOCAL_ONLY` cost policy. This ensures that AI requests never silently fall back to remote inference providers.

## Cost Policy: LOCAL_ONLY

| Cost Class | LOCAL_ONLY |
|------------|------------|
| `FREE_LOCAL` | ALLOW |
| `FREE_REMOTE` | DENY |
| `CUSTOMER_KEY` | DENY |
| `PAID_PLATFORM` | DENY |
| `UNKNOWN` | DENY |

## Route Configuration: zeaz-claude

```yaml
zeaz-claude:
  provider: ollama
  model: ${ZEAZ_CODER_MODEL:-qwen2.5-coder:3b}
  cost_policy: LOCAL_ONLY
  fallbacks: []
```

## Enforcement Points

### Route Selection (`ProviderRouter.route()`)

- Resolves route-level `cost_policy` or falls back to global policy
- Filters candidate targets by cost class
- Removes remote fallbacks under `LOCAL_ONLY`
- Returns HTTP 410 if no local target is available

### Request Execution (`ProviderRouter.execute()`)

- Uses `_route_candidates()` which enforces cost policy at runtime
- Never falls back to remote providers under `LOCAL_ONLY`
- Local provider failure does not trigger remote fallback

### Streaming (`ProviderRouter.stream()`)

- Uses `_route_candidates()` with same policy enforcement
- Streaming failures do not fall back to remote

## Fail-Closed Behavior

When Ollama is unavailable under `LOCAL_ONLY`:

1. `_route_candidates()` finds no available targets
2. Raises `ProviderError` with status 410, `fallback_allowed=False`
3. Gateway returns HTTP 410 to the client
4. No remote provider is contacted

## Security Boundaries

- Ollama binds to `127.0.0.1` only (not exposed to LAN or Internet)
- Gateway authenticates all `/v1/messages` requests
- No hardcoded API keys in source code
- TLS verification enabled for HTTPS connections
- `PROVIDER_CLIENT_KEY` sourced from environment only

## Verification

Unit tests confirm:
- `cost_allowed(FREE_LOCAL, LOCAL_ONLY)` → `True`
- `cost_allowed(ALL_OTHER_CLASSES, LOCAL_ONLY)` → `False`
- Router excludes remote fallbacks under `LOCAL_ONLY`
- `execute()` never calls remote providers under `LOCAL_ONLY`
- `stream()` never calls remote providers under `LOCAL_ONLY`
- Route without local target returns HTTP 410
