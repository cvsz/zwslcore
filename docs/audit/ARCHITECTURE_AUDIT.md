# Architecture Audit — zwslcore

Audit date: 2026-11-09
Scope: Repository architecture, modularity, dependency boundaries, separation of concerns,
API consistency, backward compatibility.

## Overall assessment

The repository is a well-structured, security-conscious Python template implementing a
WSL2-first local AI orchestration stack. Strong typing, explicit input validation,
fail-closed security gates, circuit breakers, rate limiting, and immutable dependency
pinning are implemented. Architecture is modular with clear separation between the
Provider gateway, engineering control plane, and model catalog.

## Subsystem inventory

### 1. Provider Gateway (`services/provider/zeaz_provider/`)
Multi-provider AI gateway (OpenAI/Anthropic/Responses-compatible) with routing, fallback,
resilience, and observability.

| Module | Responsibility |
|--------|---------------|
| main.py | FastAPI app, auth middleware, request/response size bounds, SSE streaming, health/metrics |
| router.py | Model routing with cost policy, provider fallback, execution/stream with circuit breaker |
| providers.py | ProviderClient: HTTP calls, retry via ResilienceExecutor, bounded reads |
| resilience.py | ResilienceExecutor + CircuitBreaker with retry/backoff, deadline enforcement |
| security.py | API key verification (constant-time), rate limiting, trusted proxy policy, secret redaction |
| config.py | YAML settings loading, env var expansion, provider/model/route validation |
| errors.py | ProviderError classification, HTTP status mapping, fail-closed error kinds |
| normalize.py | OpenAI/Anthropic/Responses request/response conversion |
| streaming.py | SSE parsing, model rewriting, protocol stream translation |
| structured.py | Native structured output (Ollama) schema handling |
| capabilities.py | Model capability registry with TTL, lifecycle tracking |
| audit.py | Redacted JSON request audit logging |
| observability.py | Prometheus metrics + optional OTLP metrics |

Security strengths: authentication required on inference routes; constant-time key comparison;
rate limiting with window retention; trusted proxy policy; request/response byte limits;
security headers; audit redaction; cost policy enforcement (ZERO_COST_ONLY default).

### 2. Engineering Control Plane (`services/engineering/`)
Durable local engineering execution over isolated Git worktrees.

Security strengths: path traversal protection, secret-bearing path blocking, allowed-path scope
enforcement, deterministic static diff review (secrets/test-weakening/scope), fail-closed
security gate, no remote push (local commits only), read-only profiles.

### 3. Model Catalog (`services/model_catalog/`)
Provider-agnostic model metadata with models.dev sync, Ollama inventory, model selection.

Security strengths: loopback-only Ollama endpoint, redirect rejection, immutable model identity,
zero-cost model filtering.

### 4. CI / Supply Chain
ci.yml, codeql.yml, dependency-review.yml, provider-supply-chain.yml (anchore scan, SPDX SBOM,
attestation), auto-fix-open-prs.yml, automated-audit-review-approve.yml.

### 5. Scripts (`scripts/`)
install.sh, doctor.sh, smoke.sh, backup.sh, restore.sh, engineer.py, models-dev.py,
validate_repo.py, github_admin.py, PowerShell wrappers.

## Architecture observations (strengths)

1. Secure defaults: loopback-only binding, signup disabled, auth required, zero-cost-only,
   cloud fallback opt-in.
2. Defense in depth: circuit breakers + retries + timeouts + rate limiting + size bounds +
   read-only rootfs + non-root container + dropped capabilities.
3. Fail-closed: security gate blocks findings; validation blocks regressions; missing config
   fails fast.
4. Immutable supply chain: `@sha256:` image digests, hashed Python deps, pinned GitHub Actions.
5. Separation of concerns: Provider vs Engineering vs Model Catalog are cleanly separated.
6. Observable: Prometheus metrics, structured audit logging, evidence bundles with SHA-256.

## Areas for attention

| Area | Observation | Severity |
|------|-------------|----------|
| Provider Dockerfile ZEAZ_HOST=0.0.0.0 | Container binds 0.0.0.0 internally; Compose publishes loopback by default. Operator must not set PROVIDER_BIND_ADDRESS=0.0.0.0 without firewall rule. | P2 (documented, mitigated) |
| LiteLLM PostgreSQL | Host-managed, outside Compose/backup scope. Documented in README. | P2 (documented) |
| pyproject.toml | New root ruff config; provider retains its own pyproject.toml (build config only). | P3 |

## Conclusion

Architecture is sound, modular, and security-focused. No P0/P1 architectural defects identified.
