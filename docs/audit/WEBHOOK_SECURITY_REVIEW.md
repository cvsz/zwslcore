# Webhook Security Review — cvsz/zwslcore

**Date:** 2026-11-09  
**Repository:** cvsz/zwslcore  
**Status:** VERIFIED (no inbound webhook endpoints; outbound-only integrations)

## 1. Scope

This document reviews webhook-related security for zwslcore. The Provider Gateway does not expose any inbound webhook endpoints. Webhook-adjacent concerns relate to outbound provider callbacks and request body handling.

## 2. Inbound Webhook Endpoints

| Endpoint | Status | Reason |
|----------|--------|--------|
| `/v1/chat/completions` | NOT A WEBHOOK | Authenticated API endpoint (Bearer/x-api-key required) |
| `/v1/messages` | NOT A WEBHOOK | Authenticated API endpoint |
| `/v1/responses` | NOT A WEBHOOK | Authenticated API endpoint |
| `/v1/models` | NOT A WEBHOOK | Authenticated API endpoint |
| `/v1/models/refresh` | NOT A WEBHOOK | Authenticated API endpoint |
| Health/metrics | NOT A WEBHOOK | No auth; loopback-only; no state change |

## 3. Request Body Handling (Webhook-Adjacent)

| Control | Implementation | Status |
|---------|---------------|--------|
| Body size limit | `max_request_bytes` (4 MiB) enforced before JSON parsing | VERIFIED |
| Streaming read | `request.stream()` with incremental total tracking | VERIFIED |
| 413 on oversized | `HTTPException(status_code=413)` when limit exceeded | VERIFIED |
| JSON parsing | `json.loads()` with constant rejection | VERIFIED |
| No raw body logging | Request bodies not logged | VERIFIED |

## 4. SSRF / Redirect Protection

| Control | Implementation | Status |
|---------|---------------|--------|
| No redirects | `follow_redirects=False` on httpx client | VERIFIED |
| No trust env | `trust_env=False` (no proxy env variable honoring) | VERIFI |
| URL validation | `base_url` validated: HTTP(S) only, no credentials/query/fragment | VERIFIED |
| Loopback-only | Provider binds to `127.0.0.1`; outbound to configured provider URLs | VERIFIED |

## 5. Authentication for State-Changing Operations

| Operation | Auth Required | Status |
|-----------|--------------|--------|
| Chat completions | Yes (`PROVIDER_CLIENT_KEY`) | VERIFIED |
| Messages | Yes | VERIFIED |
| Responses | Yes | VERIFIED |
| Model list | Yes | VERIFIED |
| Model refresh | Yes | VERIFIED |
| Health checks | No | Loopback-only, read-only | VERIFIED |
| Metrics | No (configurable) | Loopback-only, read-only | VERIFIED |

## 6. Residual Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| No inbound webhook endpoints | N/A | Not applicable — gateway is request/response API |
| Outbound provider calls | SSRF mitigated by URL validation + no redirects | VERIFIED |
| Body read timeouts | No explicit read timeout on request stream | Documented; bounded by concurrency limit |

## 7. Conclusion

Webhook security is VERIFIED. The Provider Gateway exposes no inbound webhook endpoints. All state-changing operations require authentication. Request body handling is bounded and safe. SSRF/redirect protections are in place.
