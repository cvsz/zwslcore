# Dependency Upgrade Report — cvsz/zwslcore

Audit date: 2026-11-09
Reviewer: cvsz
Repository branch: main (HEAD bc1eb1c)

## Dependency inventory

| Component | Location | Pinning | Status |
|-----------|----------|---------|--------|
| Ollama image | compose.yaml | `ollama/ollama:0.40.2@sha256:b86366bb...` | Immutable digest |
| LiteLLM image | compose.yaml | `ghcr.io/berriai/litellm:v1.104.2@sha256:3d88bd75...` | Immutable digest |
| Open WebUI image | compose.yaml | `ghcr.io/open-webui/open-webui:v0.11.4@sha256:9591b13f...` | Immutable digest |
| Provider base image | services/provider/Dockerfile | `cgr.dev/chainguard/python:latest@sha256:1a009647...` | Immutable digest (Python 3.15.2) |
| Provider build image | services/provider/Dockerfile | `cgr.dev/chainguard/python:latest-dev@sha256:898360ca...` | Immutable digest |
| Provider Python deps | services/provider/requirements.lock | `--require-hashes --only-binary=:all:` | Hash-pinned |
| Provider build deps | services/provider/pyproject.toml | `setuptools>=75,<85`, `fastapi>=0.142.2,<0.143`, etc. | Version-bounded |
| GitHub Actions | .github/workflows/* | Immutable SHAs (e.g. actions/checkout@3d3c42e...) | SHA-pinned |

## Outdated / vulnerable dependency detection

- No root `pyproject.toml` or lockfile exists at repository root (verified via shell and `git ls-files`), so no root-level dependency audit was performed.
- `services/provider/requirements.lock` is hash-pinned; supply-chain verified via `pip install --require-hashes --only-binary=:all:`.
- Dependabot is configured (`.github/dependabot.yml`); several Dependabot PRs are open (fastapi, codeql-action analyze/init, trufflehog).
- Provider image grype scan: two High-severity vendor CVEs (CVE-2026-119586 sqlite-libs, CVE-2026-84243 glibc-2.44) have NO available fix from Chainguard/Wolfi. Risk accepted with compensating controls. Critical CVE-2026-115557 resolved via image update to Python 3.15.2.

## Upgrade decisions

- **No blind mass upgrades performed**, per ZEAZ §5 ("Upgrade only when justified").
- No dependency versions were changed in this work. All image pins and dependency constraints are preserved.
- The two High CVEs cannot be upgraded (no vendor fix); risk acceptance documented instead of a blind upgrade.
- Open Dependabot PRs (fastapi, codeql-action, trufflehog) were inspected but NOT merged: each would require re-verification and the build-scan-sbom gate already fails on unfixable vendor CVEs, so merging dependency updates would not unblock the gate.

## Conclusion

Dependencies are pinned and reviewed. No justified upgrade was available or performed. Remaining risk: two unfixable High-severity base-image packages (risk accepted, reassess every 90 days).
