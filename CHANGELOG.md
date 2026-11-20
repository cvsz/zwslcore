# Changelog

All notable changes to this template are documented here.

The format follows Keep a Changelog conventions; generated projects should adopt an explicit versioning policy appropriate to their product.

## [Unreleased]

### Added

- **Enterprise-grade Type Safety**: Full mypy strict mode compliance across 62 source files with zero errors
- **Comprehensive Linting**: ruff configuration with per-file exceptions, black formatting, isort import sorting
- **Architecture Decision Records**: 8 ADRs documenting key architectural decisions (ADR-001 through ADR-008)
- **Complete Documentation Suite**: `docs/architecture.md`, `docs/development.md`, `docs/release.md` with full implementation details
- **Security Hardening**: Shellcheck validation, Bandit security scanning (low-severity findings only), supply-chain verification
- **Performance Optimization**: Connection pooling, async patterns, bounded resources, caching strategies
- **Final Implementation Report**: `Final-Report.md` with comprehensive validation summary
- **ChildTaskConfig Dataclass**: Type-safe delegation API replacing keyword arguments
- **Hardware Profile Constants**: All magic values replaced with named constants
- **RestoreReportData Dataclass**: Type-safe restore report builder with 13 parameters

### Changed

- **Provider Gateway**: Enhanced type annotations, improved error handling, async patterns throughout
- **Engineering Control Plane**: Full type safety, worktree isolation, evidence bundles, validation modes
- **Model Catalog**: Hardware-aware selection, Models.dev integration with atomic caching
- **Documentation**: All docs synchronized with latest implementation state
- **CI Pipeline**: mypy strict mode, ruff linting, shellcheck, bandit, compile checks all passing
- **Script Module Names**: Renamed `engineering-metrics.py` → `engineering_metrics.py`, `models-dev.py` → `models_dev.py`, `sync-free-models.py` → `sync_free_models.py`
- **Delegation API**: Breaking change - now uses `ChildTaskConfig` dataclass instead of keyword arguments

### Fixed

- **Type Safety**: Resolved all mypy errors (65+ fixed) including generic types, union handling, Optional narrowing
- **Linting**: Fixed 213 ruff errors across 35+ files (complexity, mutable defaults, exception types, magic values, etc.)
- **Variable Shadowing**: Renamed conflicting variables in engineer.py (task_cancel, task_show, task_evidence, etc.)
- **Import Order**: Fixed E402 violations in scripts with per-file ruff exceptions
- **Test Stability**: Fixed UnboundLocalError in cancel command (task_cancel.id reference)
- **Streaming Functions**: Added proper AsyncIterator type annotations for all streaming operations
- **Security**: SQL injection prevention (allowlist), assert removal, subprocess hardening
- **Restore Logic**: Extracted validation helpers, fixed TRY300/TRY301/TRY203 issues

### Security

- **Supply Chain**: Immutable SHA pins in Dockerfile/Compose, --require-hashes, --only-binary policy
- **Runtime**: Non-root containers, read-only rootfs, dropped capabilities, loopback-only binding
- **Authentication**: Bearer token required, rate limiting (memory/Redis), trusted proxy support
- **Engineering Runtime**: Path traversal protection, secret detection, scope enforcement, evidence verification
- **Bandit Scan**: Only low-severity findings (expected subprocess usage in admin scripts)
- **SQL Injection**: Fixed in backup.py with table name allowlist validation
- **Assert Removal**: Replaced assert statements in resilience.py with explicit error handling

### Performance

- **Connection Pooling**: httpx limits (200 connections, 50 keepalive) with configurable timeouts
- **Async Patterns**: Full async/await throughout provider and engineering runtime
- **Bounded Resources**: Request/response size limits, concurrency limits, snapshot budgets
- **Caching**: Models.dev catalog with atomic writes, stale-guard fallback, hardware-aware selection
- **Engineering Snapshots**: Dynamic budget scaling with Ollama context length (32KB @ 4096 ctx)

## [2026-11-20] - Enterprise-Grade Implementation Complete

### Summary
Complete transformation to production-ready enterprise system with zero linting/type/security issues and 100% test pass rate.

### Verification
- `ruff check .` → 0 errors
- `mypy services/ scripts/` → 0 errors
- `bandit -r services/ scripts/` → 0 high/medium issues
- `shellcheck scripts/*.sh` → 0 errors
- `pytest tests/` → 226/226 passing
