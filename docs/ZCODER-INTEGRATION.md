# ZCoder Integration — ZWSLCore Provider Gateway

## Target client configuration

ZCoder (OpenCode) consumes ZWSLCore through the Provider Gateway on the ZWSLCore host:

```text
OPENAI_BASE_URL=http://192.168.1.100:8080/v1
OPENAI_API_KEY=<PROVIDER_CLIENT_KEY>
```

- `192.168.1.100` is the ZWSLCore host; `8080` is the Provider Gateway port (`PROVIDER_PORT`).
- `<PROVIDER_CLIENT_KEY>` is the value of `PROVIDER_CLIENT_KEY` from the private `.env` / `.env.production`. It is shared with the Provider via `ZEAZ_CLIENT_KEYS`.
- **Do not hardcode real credentials.** Supply `OPENAI_API_KEY` from the operator's private environment at runtime.
- The Provider Gateway accepts either `Authorization: Bearer <key>` or `X-API-Key: <key>` (constant-time comparison against stored SHA-256 digests).

## Supported client capabilities

| Capability | Provider Gateway support |
|------------|--------------------------|
| OpenAI-compatible API | `/v1/chat/completions`, `/v1/messages`, `/v1/responses` |
| Non-streaming responses | Yes (all chat/messages/responses endpoints) |
| Streaming responses | Yes (`stream: true`), SSE (`text/event-stream`) |
| Model discovery | `GET /v1/models` (authenticated) |
| Model alias selection | Configured aliases (e.g. `zeaz-fast`, `zeaz-coder`, `zeaz-reasoning`, `zeaz-local`, `zeaz-free`, `zeaz-auto`) |
| Structured output | Via Ollama native structured outputs and response-format mapping |
| Timeout handling | Per-provider `timeout_seconds` / `total_timeout_seconds`; gateway deadline 504 |
| Cancellation | HTTP request cancellation aborts the in-flight provider stream |
| Retry policy | Exponential backoff with jitter, `Retry-After` honoring, per-provider `max_attempts` |
| Circuit breaker | Per-provider circuit (open/half-open/closed) with observable state |
| Error reporting | Bounded error kinds (authentication, bad_request, not_found, rate_limit, timeout, network, protocol, circuit_open, configuration, upstream); no provider credentials or payloads in errors |

## Model aliases

Model aliases are declared in `services/provider/config/providers.yaml` and resolved dynamically through `GET /v1/models`. Clients **must not** assume a model name exists and **must not** silently substitute an unrelated model. Call `GET /v1/models` first and select from the returned `data[].id` values.

Default aliases (from `config/providers.yaml`):

- `zeaz-fast` → Ollama `qwen2.5-coder:3b`
- `zeaz-coder` → Ollama `qwen2.5-coder:7b`
- `zeaz-reasoning` → Ollama `qwen3:8b`
- `zeaz-local` → Ollama `qwen3:8b`
- `zeaz-free` → Ollama `qwen3:8b` (cloud fallbacks only when `FREE_CLOUD_FALLBACK_ENABLED=true`)
- `zeaz-auto` → LiteLLM `zeaz-coder`, fallback Ollama
- `zeaz-cloud`, `zeaz-cloud-fast`, `zeaz-cloud-code` → OpenRouter (only when cloud fallback enabled)

The actual model behind each alias is environment-variable driven (`ZEAZ_LOCAL_MODEL`, `ZEAZ_FAST_MODEL`, etc.) and may differ per deployment; discover it via `/v1/models`.

## Local-first model policy and cloud fallback

- Default provider order: Ollama, then explicitly configured local providers; remote free providers only when explicitly enabled.
- `FREE_CLOUD_FALLBACK_ENABLED=false` by default → cloud fallback OFF.
- `ZEAZ_COST_POLICY=ZERO_COST_ONLY` by default → only free cost classes permitted.
- No paid model fallback, no hidden external inference, no automatic remote routing, no silent fallback after local failure.
- A failed local provider with remote fallback disabled produces an explicit, actionable error (HTTP 410/502 with bounded error kind) rather than silently routing elsewhere.

## Environment variable reference and precedence

| Variable | Purpose | Default |
|----------|---------|---------|
| `OPENAI_BASE_URL` | Client base URL | (client-configured) `http://192.168.1.100:8080/v1` |
| `OPENAI_API_KEY` | Client bearer key | (client-configured) from `PROVIDER_CLIENT_KEY` |
| `PROVIDER_CLIENT_KEY` | Provider-configured client key | `REPLACE_ME_*` (must be replaced) |
| `PROVIDER_PORT` | Provider port | `8080` |
| `PROVIDER_BIND_ADDRESS` | Provider listener address | `127.0.0.1` (loopback only) |
| `FREE_CLOUD_FALLBACK_ENABLED` | Enable free cloud providers | `false` |
| `ZEAZ_COST_POLICY` | Cost policy | `ZERO_COST_ONLY` |
| `ZEAZ_HOST` / `ZEAZ_PORT` | Provider bind inside container | `0.0.0.0` / `8080` |

Precedence: Provider-side settings come from `ZEAZ_*` env vars and `config/providers.yaml`. Client-side settings come from `OPENAI_BASE_URL` / `OPENAI_API_KEY`. The client key must match a provider-configured key digest.

## Integration test matrix

Run against a running Provider Gateway. Tests requiring `PROVIDER_CLIENT_KEY` need the real key from the operator's private `.env`; they are not run with hardcoded credentials here.

| # | Test | Expected | Status notes |
|---|------|----------|--------------|
| 1 | Provider health `GET /health/live` | `200 {"status":"ok"}` | Runnable without credentials |
| 2 | Authenticated model listing `GET /v1/models` + key | `200`, model `data[]` | Requires `OPENAI_API_KEY` |
| 3 | Unauthenticated model listing | `401 Invalid API key` | Runnable without credentials |
| 4 | Authenticated chat completion | `200` completion | Requires key + local model |
| 5 | Streaming chat completion (`stream: true`) | SSE `text/event-stream` | Requires key + local model |
| 6 | Invalid model | `404` unknown model | Requires key |
| 7 | Request timeout handled | `504` timeout kind | Requires key + slow/unreachable target |
| 8 | Provider unavailable | `502` all providers failed | Requires key + down provider |
| 9 | Rate limit handled | `429` with `Retry-After` | Requires key |
| 10 | Unauthorized LAN client rejected | connection dropped / `401` | Firewall rule dependent |
| 11 | No cloud fallback when disabled | `410` for cloud-only aliases | Config dependent |
| 12 | No credential leakage in logs | no Bearer/API key in logs | Log inspection |

Use a mock provider for deterministic automated tests (unit/integration suite in `services/provider/tests/`). Use real Ollama only for explicitly authorized runtime smoke tests.

## Credential and logging guarantees

- Provider credentials are stored only as SHA-256 digests (`ZEAZ_CLIENT_KEY_HASHES`) or compared at runtime (`ZEAZ_CLIENT_KEYS`).
- Authorization headers are never logged.
- Bearer tokens and API keys are redacted from audit logs and error messages.
- Metrics expose provider/model names and error classes (infrastructure metadata) but no credentials, payloads, or internal addresses.

## Related

- `docs/NETWORK-TOPOLOGY.md` — LAN exposure and firewall policy.
- `docs/PRODUCTION-READINESS.md` — readiness gate states.
- `docs/BACKUP-RESTORE.md` — backup and restore procedures.
