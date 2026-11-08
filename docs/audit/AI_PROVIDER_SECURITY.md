# AI Provider Security Review — cvsz/zwslcore

**Date:** 2026-11-09  
**Repository:** cvsz/zwslcore  
**Status:** VERIFIED

## 1. Scope

This document reviews the security of the zwslcore Provider Gateway — an OpenAI/Anthropic-compatible multi-provider AI gateway running on loopback (`127.0.0.1:8080`).

## 2. Authentication

| Control | Implementation | Status |
|---------|---------------|--------|
| Client key required | `PROVIDER_CLIENT_KEY` validated via `verify_client_key()` | VERIFIED |
| Bearer token support | `Authorization: Bearer <key>` header accepted | VERIFIED |
| x-api-key support | `x-api-key` header accepted | VERIFIED |
| Missing key → 401 | `authenticate()` raises HTTP 401 on invalid/missing key | VERIFIED |
| Hash comparison | `hmac.compare_digest()` for constant-time comparison | VERIFIED |
| Hash storage | Client keys stored as SHA-256 hashes (`ZEAZ_CLIENT_KEY_HASHES`) | VERIFIED |
| Unauthenticated opt-in | `ZEAZ_ALLOW_UNAUTHENTICATED=true` (default `false`) | VERIFIED |

## 3. Input Validation

| Control | Implementation | Status |
|---------|---------------|--------|
| Request body size limit | `max_request_bytes` (default 4 MiB) enforced in `body()` | VERIFIED |
| JSON validation | `json.loads()` with `_reject_json_constant` (rejects NaN/Infinity) | VERIFIED |
| Model name validation | 1-256 chars, no `\r\n\x00` | VERIFIED |
| Stream flag validation | Must be `bool` type | VERIFIED |
| Token limit validation | `max_tokens` 1 to `max_output_tokens`; no duplicates | VERIFIED |
| Sampling range validation | temperature [0,2], top_p [0,1], penalties [-2,2] | VERIFIED |
| Messages/tools must be arrays | Type-checked in `body()` | VERIFIED |
| Input must be string or array | Type-checked in `body()` | VERIFIED |

## 4. Network Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Loopback binding | Provider binds to `127.0.0.1` by default | VERIFIED |
| No redirects | `follow_redirects=False` on httpx client | VERIFIED |
| No trust env | `trust_env=False` on httpx client | VERIFIED |
| URL validation | `base_url` must be HTTP(S), no credentials/query/fragment | VERIFIED |
| Content-Type validation | JSON responses must have `application/json` content type | VERIFIED |
| Response size limit | `max_response_bytes` (default 16 MiB) enforced | VERIFIED |
| Stream bounding | `bounded_stream()` enforces byte limit on SSE | VERIFIED |

## 5. Provider Isolation

| Control | Implementation | Status |
|---------|---------------|--------|
| Per-provider config | Separate `ProviderConfig` per provider | VERIFIED |
| API key isolation | Keys stored per-provider; not shared across routes | VERIFIED |
| Circuit breaker | Per-provider circuit breaker with failure threshold | VERIFIED |
| Retry with backoff | Exponential backoff with jitter; `Retry-After` respected | VERIFIED |
| Fallback ordering | Primary → fallbacks; fallback allowed per error kind | VERIFIED |
| Cost policy | `ZERO_COST_ONLY` default; paid routes blocked | VERIFIED |
| Retired model filtering | `ModelLifecycle.RETIRED` targets excluded | VERIFIED |

## 6. Logging & Audit

| Control | Implementation | Status |
|---------|---------------|--------|
| No secret logging | Secrets redacted; not logged | VERIFIED |
| Audit events | JSON audit events with hashed request IDs | VERIFIED |
| Path allowlisting | Only known paths logged; others as `unmatched` | VERIFIED |
| Method normalization | Unknown methods as `OTHER` | VERIFIED |

## 7. Container Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Non-root user | `65532:65532` | VERIFIED |
| Read-only rootfs | `read_only: true` | VERIFIED |
| Dropped capabilities | `cap_drop: [ALL]` | VERIFIED |
| No new privileges | `no-new-privileges: true` | VERIFIED |
| tmpfs /tmp | `noexec,nosuid,size=64m` | VERIFIED |
| Resource limits | CPU and memory limits set | VERIFIED |

## 8. Residual Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| No GPU detected | CPU-only inference | Q4_K_M quantization; 4096-context profile |
| Provider keys in `.env` | Local dev keys gitignored | Rotate before production |
| Redis rate-limit optional | Memory backend default; Redis opt-in | Documented |

## 9. Conclusion

AI Provider security is VERIFIED with defense-in-depth: authentication, input validation, network isolation, provider isolation, circuit breaking, and container hardening. No critical findings.
