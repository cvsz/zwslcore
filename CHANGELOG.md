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

### Changed

- **Provider Gateway**: Enhanced type annotations, improved error handling, async patterns throughout
- **Engineering Control Plane**: Full type safety, worktree isolation, evidence bundles, validation modes
- **Model Catalog**: Hardware-aware selection, Models.dev integration with atomic caching
- **Documentation**: All docs synchronized with latest implementation state
- **CI Pipeline**: mypy strict mode, ruff linting, shellcheck, bandit, compile checks all passing

### Fixed

- **Type Safety**: Resolved all mypy errors (65+ fixed) including generic types, union handling, Optional narrowing
- **Variable Shadowing**: Renamed conflicting variables in engineer.py (task_cancel, task_show, task_evidence, etc.)
- **Import Order**: Fixed E402 violations in scripts with per-file ruff exceptions
- **Test Stability**: Fixed UnboundLocalError in cancel command (task_cancel.id reference)
- **Streaming Functions**: Added proper AsyncIterator type annotations for all streaming operations

### Security

- **Supply Chain**: Immutable SHA pins in Dockerfile/Compose, --require-hashes, --only-binary policy
- **Runtime**: Non-root containers, read-only rootfs, dropped capabilities, loopback-only binding
- **Authentication**: Bearer token required, rate limiting (memory/Redis), trusted proxy support
- **Engineering Runtime**: Path traversal protection, secret detection, scope enforcement, evidence verification
- **Bandit Scan**: Only low-severity findings (expected subprocess usage in admin scripts)

### Performance

- **Connection Pooling**: httpx limits (200 connections, 50 keepalive) with configurable timeouts
- **Async Patterns**: Full async/await throughout provider and engineering runtime
- **Bounded Resources**: Request/response size limits, concurrency limits, snapshot budgets
- **Caching**: Models.dev catalog with atomic writes, stale-guard fallback, hardware-aware selection
- **Engineering Snapshots**: Dynamic budget scaling with Ollama context length (32KB @ 4096 ctx)
