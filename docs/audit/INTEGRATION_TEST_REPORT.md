# Integration Test Report — zwslcore

Audit date: 2026-11-09
Reviewer: cvsz

## Integration scope

Mapped real interfaces and tested applicable integrations using isolated/local methods (no production system modification, no destructive system operations).

## Integrations tested

| Interface | Method | Result | Evidence |
|-----------|--------|--------|----------|
| CLI to core engine | `bash -n` syntax validation of install/doctor/smoke/wait-runtime/backup/restore/chaos/bootstrap-wsl/cloudshell/cloudflare-up/ai scripts | PASS | EXIT: 0 (CI target) |
| Python to system interfaces | py_compile + compileall of provider/engineering/model_catalog/scripts | PASS | EXIT: 0 |
| Shell to executables | shellcheck -x on all shell scripts | PASS | EXIT: 0 |
| Configuration loading | `validate_repo.py` (structure + Markdown links); `docker compose config --quiet` | PASS | "Repository structure and local Markdown links are valid." |
| Import validation | Provider imports (zeaz_provider.main app) | PASS | CI target |
| Provider structured output | `tests/test_provider_structured_output.py` | PASS | part of 211/211 |
| Model catalog | `tests/test_model_catalog.py`, `test_models_dev_catalog.py`, `test_model_selector.py`, `test_model_inventory.py` | PASS | part of 211/211 |
| Engineering control plane | 14 engineering test modules | PASS | part of 211/211 |
| AI CLI / env loader | `test_ai_cli.py`, `tests/test_env_loader.sh` | PASS | part of 211/211 |
| Supply chain (Dockerfile) | `test_supply_chain_dockerfile.py` (immutable digests, non-root, read-only rootfs, hash-verified deps, binary-only) | PASS | part of 211/211 |

## Unsuccessful scenario coverage (unit-level)

The test suite validates failure handling: invalid JSON (400), missing auth (401), rate limiting (429), unknown model (404), cost-blocked provider (410), stream deadline (504/502), invalid request format, provider protocol errors, fallback behavior, circuit breaker state, test-weakening detection, secret detection in diffs, dotenv injection resistance.

## Not executed (requires live infrastructure)

The following require Docker/PostgreSQL/Ollama running and were not executed against a live system (per constraint: never modify user's real system configuration or perform destructive system operations):
- `make smoke` (authenticated end-to-end inference against live LiteLLM/Provider)
- `make doctor` (runtime health against live containers)
- `docker compose up` full stack
- Open WebUI / LiteLLM / Ollama cross-service E2E

These are CI-gated and documented as runtime requirements, not code defects.

## Test results

| Suite | Result |
|-------|--------|
| Full unit test suite | 211/211 PASS |
| Provider security tests | PASS |
| Provider observability tests | PASS |
| Supply-chain Dockerfile tests | PASS |
| Shell script syntax | PASS |

## Conclusion

All code-level integration points verified. Runtime E2E against live containers deferred to CI (repository-baseline job runs `docker compose config --quiet` and provider build/import test).
