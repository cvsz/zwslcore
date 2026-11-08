# Build and Lint Report — cvsz/zwslcore

Audit date: 2026-11-09
Reviewer: cvsz
Repository branch: main (HEAD bc1eb1c)
Implementation branch: fix/zwslcore-shellcheck-hardening-20261109

## Tooling discovered (shell-verified)

| Tool | Version | Source | Used |
|------|---------|--------|------|
| python3 | 3.14.4 | system | Yes |
| ruff | 0.17.4 | pip | Yes (local check only; not a CI gate at repository root) |
| shellcheck | 0.11.0 | system | Yes |
| unittest | stdlib | Yes | Yes |
| docker | 29.9.3 | system | Yes (image build test) |
| grype | 0.121.0 | user install | Yes (container scan) |

## Ruff configuration

No root `pyproject.toml` exists on this repository (verified via shell and `git ls-files`). Therefore ruff applies its default rule set with no project exclusions or ignores. `services/provider/pyproject.toml` exists for the provider package only.

## Build results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| Provider Docker image build | `docker build --pull --tag local/zwslcore-provider:ci services/provider` | PASS | EXIT: 0; image sha256:6207d02d73ef3f14e41b0a58ef533b0c94f4d573b0244ddd5ed0d73130ea012f |
| py_compile scripts | `python3 -m py_compile scripts/sync-free-models.py scripts/models-dev.py services/model_catalog/catalog.py services/model_catalog/models_dev.py services/model_catalog/selector.py` | PASS | EXIT: 0 |
| compileall services | `python3 -m compileall -q services/provider/zeaz_provider services/engineering scripts/engineer.py` | PASS | EXIT: 0 |
| Docker compose config validation | `docker compose --env-file .env.example config --quiet` | PASS | EXIT: 0 (env file copied then removed; no secrets committed) |

## Lint results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| ruff check (root) | `ruff check .` | 161 pre-existing findings | No root pyproject.toml → default rules; findings are pre-existing style/lint across the codebase (TRY004, BLE001, RUF022, I001, PLW1510, SIM117, F841, F401, FLY002); none introduced by this work; ruff is not a CI gate at root |
| ruff format --check | `ruff format --check .` | format drift present | Pre-existing; not introduced by this work |
| shellcheck (edited files) | `shellcheck scripts/cloudshell-webui.sh scripts/zcloud-tunnel.sh` | PASS | EXIT: 0 (two P3 warnings resolved) |
| shellcheck (other scripts) | `shellcheck scripts/*.sh` | INFO-level only | Pre-existing SC1091 (dynamic source), SC2034 (unused var), SC2329 (unused function); not introduced by this work |

## Test results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| Unit tests (main) | `python3 -m unittest discover -s tests -v` | PASS | 192 tests OK |

## Container scan

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| grype --fail-on critical | `grype local/zwslcore-provider:ci --fail-on critical` | PASS | EXIT: 0; Critical CVE-2026-115557 resolved |
| grype --fail-on high | `grype local/zwslcore-provider:ci --fail-on high` | BLOCKED | EXIT: 2; two High vendor CVEs with no fix (risk accepted) |

## Notes

- The two shellcheck P3 warnings on edited files were resolved; all other shellcheck findings are pre-existing info-level and were not mass-changed to avoid scope creep and regressions.
- No root-level ruff config exists; adding one would be a separate, intentional change (not part of this minimal fix).
