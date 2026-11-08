# Integration Test Report — cvsz/zwslcore

Audit date: 2026-11-09
Reviewer: cvsz
Repository branch: main (HEAD bc1eb1c)

## Scope

Integration points tested at the unit/contract level (no production systems, no third-party targets, no destructive operations):
- CLI to core engine (scripts/ai.sh offline self-test, dotenv loading)
- Python to system interfaces (Ollama loopback tags API, non-loopback rejection, redirect blocking)
- Shell to executables (bash -n syntax on install/doctor/smoke/wait-runtime/backup/restore/cloudflare-up/cloudshell/cloudshell-webui/chaos/create-local-models/provider-lock/zcloud-tunnel)
- Configuration loading (.env parsing, dotenv secure loading, invalid permissions rejected)
- Logging / error propagation (structured output, error redaction)
- Installation (bootstrap dry-run, idempotency, symlink refusal, invalid names)
- Backup / restore (online backup, isolated restore, content verification, recreate policy)
- Provider Docker image build (immutable digest base image, hash-pinned deps, non-root, read-only rootfs)
- Docker Compose config validation
- Supply-chain Dockerfile tests (base image digest, non-root user, no latest tag, no unpinned FROM, pip binary-only, require-hashes, PyYAML source exception documented, read-only rootfs)
- Model catalog (route building, paid/media filtering, audio rejection)
- Model inventory (loopback-only, digest validation, duplicate tag rejection)
- Model selector (zero-cost policy, paid remote blocking, hardware profile selection)
- Engineering control plane (state transitions, worktree isolation, snapshot scope, secrets excluded, attempt budget, concurrency, cancellation, reconciliation, resume)
- Transport retry (bounded retries, infrastructure failure budget, structured error handling)
- MCP (stdio-only, shell=False, env allowlist, bounded messages, invalid server name rejection)
- Queue lifecycle (dead letter, retry, cancel, quarantine, archive)

## Results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| Full unit test suite | `python3 -m unittest discover -s tests -v` | PASS | 192 tests OK |
| Python compilation | `py_compile` + `compileall` | PASS | EXIT: 0 |
| Bash syntax (all scripts) | `bash -n scripts/*.sh` | PASS | EXIT: 0 |
| Supply-chain Dockerfile tests | `python3 -m unittest tests.test_supply_chain_dockerfile` | NOT RUN | tests/test_supply_chain_dockerfile.py not present on main (present on audit/hardening branch only) |
| Adversarial security tests | `python3 -m unittest tests.test_adversarial_security` | PASS | 11 tests OK |
| MCP tests | `python3 -m unittest tests.test_engineering_mcp` | PASS | 7 tests OK, no ResourceWarning |
| Backup/restore tests | `python3 -m unittest tests.test_backup_restore` | PASS | OK |
| Adversarial/security overall | — | PASS | All path-traversal, escalation, concurrency, dotenv tests pass |

## Scenarios not run (environment-limited)

- Runtime end-to-end inference (requires Docker + Ollama + model pull; not available in this isolated environment).
- Docker Compose stack up / health checks (requires Docker daemon + host PostgreSQL; not run to avoid modifying the host).
- Provider container runtime health (image built successfully but not run).
- Windows / WSL2 compatibility (Linux-only environment available; not verified on Windows).

## Conclusion

All runnable integration/unit tests pass (192/192). Environment-limited scenarios (runtime inference, Compose stack, Windows) are documented as NOT RUN rather than reported as passed.
