# Dependency Upgrade Report — zwslcore

Audit date: 2026-11-09
Reviewer: cvsz

## Dependency inventory

Provider gateway (`services/provider/pyproject.toml`, `requirements.lock`):

| Dependency | Constraint | Locked version | Source |
|------------|-----------|----------------|--------|
| fastapi | >=0.142.2,<0.143 | 0.142.4 | pyproject.toml |
| httpx | >=0.28,<1 | 0.28.1 | pyproject.toml |
| pydantic | >=2.11,<3 | 2.14.1 | pyproject.toml |
| prometheus-client | >=0.22,<1 | 0.26.0 | pyproject.toml |
| PyYAML | >=6.0,<7 | 6.0.3 | pyproject.toml |
| redis | >=6.4,<9 | 8.1.0 | pyproject.toml |
| uvicorn[standard] | >=0.35,<1 | 0.54.0 | pyproject.toml |
| opentelemetry-api/sdk/exporter | >=1.36,<2 | 1.45.1 / 0.66b1 | pyproject.toml |

`requirements.lock` is generated with pip-compile using `--require-hashes --only-binary=:all: --generate-hashes` (binary-only, hash-verified).

Container images (`compose.yaml`, `.env.example`) all use immutable `@sha256:` digests:
- OLLAMA_IMAGE: ollama/ollama:0.40.2@sha256:b86366bb...
- LITELLM_IMAGE: ghcr.io/berriai/litellm:v1.104.2@sha256:3d88bd75...
- OPENWEBUI_IMAGE: ghcr.io/open-webui/open-webui:v0.11.4@sha256:9591b13f...
- Provider base: Chainguard python build sha256:898360ca..., runtime sha256:1a009647...

## Dependency upgrades considered

| PR | Type | Dependency | Status | Decision |
|----|------|-----------|--------|----------|
| #101 | Dependabot | fastapi <0.143 -> <0.163 | Rebased onto main, tests pass | REQUEST CHANGES (build-scan-sbom blocks merge) |
| #107 | Dependabot | trufflehog 3.99.7 -> 3.99.8 | Stale | REQUEST CHANGES |
| #85/#84 | Dependabot | codeql-action analyze/init 4.38.2 -> 4.39.1 | Stale | REQUEST CHANGES |

## Upgrade rationale

- No blind mass upgrades performed. Only PR #101 (fastapi) was rebased onto main and verified (tests pass).
- build-scan-sbom failure on current main blocks all dependency upgrades from merging — it is a pre-existing supply-chain blocker, not introduced by any PR.
- No unnecessary dependency additions. Lockfile uses hash verification.
