# Architecture Audit — zwslcore

Audit date: 2026-11-08
Scope: Repository architecture, modularity, dependency boundaries, separation of concerns,
API consistency, backward compatibility.

## Overall assessment

The repository is a well-structured, security-conscious Python/TypeScript-agnostic template
implementing a WSL2-first local AI orchestration stack. The codebase demonstrates strong typing,
explicit input validation, fail-closed security gates, circuit breakers, rate limiting, and
immutable dependency pinning. Architecture is modular with clear separation between the Provider
gateway, engineering control plane, and model catalog.

## Subsystem inventory

### 1. Provider Gateway (`services/provider/zeaz_provider/`)
Multi-provider AI gateway (OpenAI/Anthropic/Responses-compatible) with routing, fallback,
resilience, and observability.

| Module | Responsibility |
|--------|---------------|
| main.py | FastAPI app, lifespan, auth middleware, request/response size bounds, SSE streaming, health/metrics |
| router.py | Model routing with cost policy, provider fallback, execution/stream with circuit breaker state recording |
| providers.py | ProviderClient: HTTP calls to Ollama/LiteLLM/OpenRouter/etc., retry via ResilienceExecutor, bounded reads |
| resilience.py | ResilienceExecutor + CircuitBreaker with retry/backoff, deadline enforcement, half-open probes |
| security.py | API key verification (constant-time), rate limiting (in-memory + Redis Lua), trusted proxy policy, secret redaction |
| config.py | YAML settings loading, env var expansion, provider/model/route validation, cost policy |
| errors.py | ProviderError classification, HTTP status mapping, fail-closed error kinds |
| normalize.py | OpenAI/Anthropic/Responses request/response payload conversion |
| streaming.py | SSE parsing, model rewriting, protocol stream translation (chat↔anthropic↔responses) |
| structured.py | Native structured output (Ollama) schema handling |
| capabilities.py | Model capability registry with TTL, lifecycle tracking, provider Models API refresh |
| audit.py | Redacted JSON request audit logging (no secrets, bounded paths) |
| observability.py | Prometheus metrics + optional OTLP metrics |

Security strengths:
- Authentication required on all inference/model routes (401 without valid key)
- Constant-time key comparison (`hmac.compare_digest`)
- Rate limiting with window retention (no reset-on-reject)
- Trusted proxy policy (only honors CF-Connecting-IP from trusted CIDRs)
- Request/response byte limits (4MB request, 16MB response)
- Security headers (X-Content-Type-Options, Referrer-Policy, Cache-Control no-store)
- Audit logging redacts secrets and bounds paths/methods
- Cost policy enforcement (ZERO_COST_ONLY default; paid/customer-key classes blocked)

### 2. Engineering Control Plane (`services/engineering/`)
Durable local engineering execution over isolated Git worktrees.

| Module | Responsibility |
|--------|---------------|
| runtime.py | EngineeringRuntime: plan/edit/validate/review/commit lifecycle with worktree snapshots |
| review.py | StaticReviewer (secret + test-weakening detection) + SecurityGate (fail-closed) |
| permissions.py | Agent permission rules (allow/ask/deny) with fnmatch matching |
| agents.py | AgentProfile + AgentRegistry (build/plan/review/explore/general built-ins) |
| models.py | Task statuses, risk levels, push policy, ReviewFinding |
| validation.py | Strict vs delta validation mode evaluation (regression gating) |
| store.py | SQLite WAL task/checkpoint persistence |
| evidence.py | Evidence export with SHA-256 integrity |
| worktree.py | Isolated Git worktree management |
| snapshot.py | Secret-aware bounded repository snapshotter |
| change_snapshot.py | Binary-capable Git patch change snapshots (undo/redo) |
| lease.py | SQLite runner lease for continuous execution |
| ledger.py | Durable continuous-work ledger |
| loop.py | Continuous engineering loop with priority scheduling |
| continuous.py | Continuous work queue processing |
| hardware.py | Hardware profiling (GPU/CPU) for model recommendations |
| mcp.py | Local stdio MCP client (shell=False, bounded limits) |
| observability.py | Engineering event emission |
| prometheus.py | Engineering Prometheus metrics |
| reconcile.py | Queue/task state reconciliation |
| tui.py | Read-only terminal dashboard |

Security strengths:
- Path traversal protection (`..` and absolute paths rejected)
- Secret-bearing path blocking (`.env`, `.pem`, `.key`, etc.)
- Allowed-path scope enforcement on edits
- Deterministic static diff review (secrets, test-weakening, scope)
- Fail-closed security gate
- No remote push capability (local commits only)
- Read-only profiles (plan/review/explore cannot edit or commit)

### 3. Model Catalog (`services/model_catalog/`)
Provider-agnostic model metadata with models.dev sync, Ollama inventory, and model selection.

| Module | Responsibility |
|--------|---------------|
| catalog.py | Catalog sync, stats, lookup, recommendation |
| inventory.py | Ollama inventory capture, manifest comparison, drift detection |
| models_dev.py | Models.dev catalog fetch, cache with stale guard |
| selector.py | Engineering model selection by hardware profile and cost policy |

Security strengths:
- Ollama inventory uses loopback-only endpoint, rejects redirects and non-loopback
- Immutable model identity (digest-based), fail-closed on drift
- Zero-cost model filtering under ZERO_COST_ONLY policy

### 4. CI / Supply Chain
| Workflow | Purpose |
|----------|---------|
| ci.yml | Repository validation, unit tests, script syntax checks, py_compile, docker compose config, provider build + test, secret scan (TruffleHog) |
| codeql.yml | CodeQL Python analysis on push/PR/schedule |
| dependency-review.yml | Dependency review action on PRs |
| provider-supply-chain.yml | Docker build, image scan (anchore), SPDX SBOM, release manifest, attestation |
| auto-fix-open-prs.yml | Scheduled read-only PR issue detection |
| automated-audit-review-approve.yml | Read-only audit + review comment (policedbc) |

### 5. Scripts (`scripts/`)
install.sh, doctor.sh, smoke.sh, backup.sh, restore.sh, chaos.sh, bootstrap-wsl.sh,
engineer.py, models-dev.py, sync-free-models.py, model_manifest.py, validate_repo.py,
github_admin.py, and PowerShell wrappers (install-wsl2.ps1, doctor-wsl.ps1, engineer-wsl.ps1).

## Architecture observations (strengths)

1. **Secure defaults**: loopback-only binding, signup disabled, auth required, cost policy zero-cost-only, cloud fallback opt-in.
2. **Defense in depth**: circuit breakers + retries + timeouts + rate limiting + size bounds + read-only rootfs + non-root container + dropped capabilities.
3. **Fail-closed**: security gate blocks on findings; validation blocks regressions; missing config fails fast.
4. **Immutable supply chain**: container images pinned to `@sha256:` digests, Python deps pinned with `--require-hashes --only-binary=:all:`, GitHub Actions pinned to immutable SHAs.
5. **Separation of concerns**: Provider (routing/inference) vs Engineering (task execution) vs Model Catalog (metadata) are cleanly separated.
6. **Observable**: Prometheus metrics, structured audit logging, OTLP option, evidence bundles with SHA-256.

## Architecture observations (areas for attention)

| Area | Observation | Severity |
|------|-------------|----------|
| Provider Dockerfile `ZEAZ_HOST=0.0.0.0` | Container runtime binds to 0.0.0.0 internally, but Compose publishes only loopback by default. Operator must not set PROVIDER_BIND_ADDRESS=0.0.0.0 without the documented firewall rule. | P2 (documented, mitigated) |
| LiteLLM PostgreSQL | Host-managed PostgreSQL (outside Compose/backup scope). Operator must create role/database and back up separately. Documented in README. | P2 (documented) |
| `pyproject.toml` | New root pyproject.toml added for ruff configuration; provider retains its own services/provider/pyproject.toml (build config only, no ruff section). Consistent config recommended. | P3 |
| Shell script variable usage | Some dotenv-read variables unused in doctor.sh/smoke.sh (documented with shellcheck disable comments). | P3 |

## Dependency boundaries

- Provider depends on: fastapi, httpx, pydantic, prometheus-client, PyYAML, redis, uvicorn, opentelemetry (*). All hashed in requirements.lock.
- Engineering depends on Python standard library only (no third-party deps).
- Tests use unittest (stdlib) only.

## Backward compatibility

- Provider API is OpenAI/Anthropic/Responses-compatible; version 0.1.0.
- Model aliases (zeaz-fast, zeaz-coder, zeaz-reasoning, zeaz-local, zeaz-free, zeaz-auto, zeaz-cloud, zeaz-cloud-fast, zeaz-cloud-code) are stable routing aliases.
- Cost policy defaults to ZERO_COST_ONLY; opt-in required for paid routes.

## Conclusion

Architecture is sound, modular, and security-focused. No P0/P1 architectural defects identified. The remaining items are P2/P3 documentation and configuration hygiene items tracked in the remediation report.
