# Provider Routing Review — cvsz/zwslcore

**Generated:** 2026-11-08  
**Scope:** Provider registry, routing decisions, cost policy, zero-cost enforcement  
**Status:** VERIFIED

---

## 1. Cost Policy Enforcement

| Policy | Behavior | Status |
|--------|----------|--------|
| `ZERO_COST_ONLY` (default) | Only `FREE_LOCAL` and `FREE_REMOTE` eligible; paid routes denied | VERIFIED |
| `PREFER_ZERO_COST` | Free routes ranked before paid; paid subject to explicit policy | VERIFIED |
| `PERMIT_PAID` | All cost classes permitted per configured authorization | VERIFIED |
| Cloud fallback | Disabled unless `FREE_CLOUD_FALLBACK_ENABLED=true` | VERIFIED |

---

## 2. Provider Configuration (`services/provider/config/providers.yaml`)

| Provider | Cost Class | Enabled By Default | Notes |
|----------|-----------|-------------------|-------|
| ollama | FREE_LOCAL | Yes | Local models; no API key |
| litellm | FREE_LOCAL | Yes | Local LiteLLM proxy; needs `LITELLM_MASTER_KEY` |
| openrouter | FREE_REMOTE | No | Requires `FREE_CLOUD_FALLBACK_ENABLED=true` + `OPENROUTER_API_KEY` |
| gemini | FREE_REMOTE | No | Requires `FREE_CLOUD_FALLBACK_ENABLED=true` + `GEMINI_API_KEY` |
| groq | FREE_REMOTE | No | Requires `FREE_CLOUD_FALLBACK_ENABLED=true` + `GROQ_API_KEY` |

---

## 3. Model Aliases

| Alias | Provider | Model | Fallbacks |
|-------|----------|-------|-----------|
| `zeaz-fast` | ollama | `qwen2.5-coder:3b` | — |
| `zeaz-coder` | ollama | `qwen2.5-coder:7b` | — |
| `zeaz-reasoning` | ollama | `qwen3:8b` | — |
| `zeaz-local` | ollama | `qwen3:8b` | — |
| `zeaz-free` | ollama | `qwen3:8b` | openrouter, gemini, groq (when cloud enabled) |
| `zeaz-auto` | litellm | `zeaz-coder` | ollama |
| `zeaz-cloud` | openrouter | `openrouter/free` | — (cloud only) |
| `zeaz-cloud-fast` | openrouter | `liquid/lfm-2.5-2.6b:free` | — (cloud only) |
| `zeaz-cloud-code` | openrouter | `cohere/north-mini-code:free` | — (cloud only) |

---

## 4. Zero-Cost Policy Verification

### ZERO_COST_ONLY Verified Behavior

| Test | Result |
|------|--------|
| `FREE_LOCAL` (ollama) allowed | PASS |
| `FREE_REMOTE` (openrouter with cloud enabled) allowed | PASS |
| Paid routes blocked | PASS |
| Cloud fallback disabled by default | PASS |
| External free-tier models not assumed permanently free | DOCUMENTED |
| Confidential prompts not sent remotely without explicit config | VERIFIED |

---

## 5. Provider Health and Fallback

| Feature | Implementation | Status |
|---------|---------------|--------|
| Provider health checks | Loopback HTTP health endpoints | VERIFIED |
| Fallback ladder | Primary → fallbacks on error | VERIFIED |
| Retry state | Bounded `max_attempts` per provider | VERIFIED |
| Circuit breaker | Open circuit on repeated failures | VERIFIED |
| Transport failure handling | `RateLimitBackendError` → 503 Service Unavailable | VERIFIED |
| Non-consuming attempts | Transport errors don't consume retry budget (PR #43) | VERIFIED |

---

## 6. PR Findings Affecting Routing

| PR | Impact | Status |
|----|--------|--------|
| #64 | Adds optional Cerebras, SambaNova, Cloudflare free-tier providers | DRAFT; review for zero-cost policy compliance |
| #70 | Secure dotenv loading for provider credentials | OPEN; merge ready |
| #90 | Changes default Ollama models to GGUF-imported aliases | OPEN; review default model changes |
| #79 | MCP session and provider client hardening | OPEN; security review needed |

---

## 7. Residual Risks

| Risk | Likelihood | Impact | Control |
|------|-----------|--------|---------|
| External free-tier models change pricing | Medium | Medium | Documented; not treated as permanently free |
| Remote fallback sends prompts outside local machine | Low | High | `FREE_CLOUD_FALLBACK_ENABLED=false` by default; explicit opt-in |
| Model identity drift | Low | Medium | `make models-manifest` with `--fail-on-drift` |
