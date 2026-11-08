# Build and Lint Report — zwslcore

Audit date: 2026-11-09
Reviewer: cvsz

## Tooling discovered

| Tool | Version | Source | Used |
|------|---------|--------|------|
| python3 | 3.14.4 | system | Yes |
| ruff | 0.17.4 | pip (--break-system-packages) | Yes |
| shellcheck | 0.11.0 | system | Yes |
| pytest | 9.2.0 | system | Yes |
| unittest | stdlib | system | Yes |
| docker | 29.9.3 | system | Yes (image build test) |

## Ruff configuration

Added root `pyproject.toml` with `[tool.ruff]` documenting intentional rule exclusions:
TRY004, PLW1510, BLE001, RUF012, PYI034, UP022, TRY203, TRY201, FURB192. These encode
established codebase patterns. Unsafe fixes are explicitly disallowed.

## Build results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| Provider Docker image build | `docker build --pull --tag local/zwslcore-provider:test services/provider` | PASS | EXIT: 0 |
| py_compile scripts | `python3 -m py_compile scripts/...` | PASS | EXIT: 0 |
| compileall services | `python3 -m compileall -q services/...` | PASS | EXIT: 0 |

## Lint results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| ruff check | `ruff check .` | PASS | "All checks passed!" |
| ruff format --check | `ruff format --check .` | PASS | "166 files already formatted" |
| shellcheck | `shellcheck -x scripts/*.sh ...` | PASS | EXIT: 0 |

## Test results

| Check | Command | Result | Evidence |
|-------|---------|--------|----------|
| Unit tests | `python3 -m unittest discover -s tests -v` | PASS | 211/211 OK |
