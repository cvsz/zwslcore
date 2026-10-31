# Docker and Supply Chain Security

**Repository**: `cvsz/zwslcore`  
**Dockerfile**: `services/provider/Dockerfile`  
**Compose file**: `compose.yaml`  
**Date**: 2026-11-01  
**Actor**: cvsz (engineering operator)

---

## 1. Current Docker Configuration

### Provider Dockerfile (`services/provider/Dockerfile`)

```dockerfile
FROM cgr.dev/chainguard/python:latest-dev@sha256:01280a9ffd0c9c427d3127540203af6707ebf35cdb0481182aef303c03db239c AS build
USER 0:0
WORKDIR /app
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="/opt/venv/bin:$PATH"
COPY pyproject.toml requirements.lock ./
COPY zeaz_provider ./zeaz_provider
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: --no-binary pyyaml -r requirements.lock \
    && pip install --no-cache-dir --no-deps --no-build-isolation .
COPY config ./config
FROM cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ZEAZ_CONFIG=/app/config/providers.yaml \
    ZEAZ_HOST=0.0.0.0 \
    ZEAZ_PORT=8080 \
    PATH=/opt/venv/bin:$PATH
WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/config ./config
USER 65532:65532
EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/opt/venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=3)"]
ENTRYPOINT ["zwslcore-provider"]
```

### Security Properties (Current)

| Property | Implementation | Status |
|----------|---------------|--------|
| Multi-stage build | Build stage + runtime stage | PASS |
| Non-root user | `USER 65532:65532` | PASS |
| Read-only root filesystem | `read_only: true` in compose | PASS |
| No new privileges | `security_opt: no-new-privileges:true` | PASS |
| Dropped capabilities | `cap_drop: [ALL]` | PASS |
| Immutable image digest | `sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285` | PASS |
| Hash-pinned dependencies | `--require-hashes` in pip install | PASS |
| No binary for pyyaml | `--no-binary pyyaml` | PASS |
| Health check | HTTP readiness probe | PASS |
| Resource limits | CPU and memory limits in deploy | PASS |
| Network isolation | Dedicated bridge network | PASS |
| No secrets in image | Config copied from build context | PASS |

---

## 2. Identified Issues

### Issue 1: Critical CVE in Base Image

| CVE | Severity | Package | Fix Available |
|-----|----------|---------|---------------|
| CVE-2026-115557 | Critical | python-3.15 | No |
| CVE-2026-114613 | High | py3-pip-wheel | 26.2.2-r1+ |

**Impact**: `build-scan-sbom` CI check fails due to `severity-cutoff: high`.

**Remediation**: No technically available fix. See `CVE-2026-115557-ROOT-CAUSE.md` and `BASE-IMAGE-REMEDIATION-DECISION.md`.

### Issue 2: Build Stage Runs as Root

| Finding | Severity | Remediation |
|---------|----------|-------------|
| Build stage uses `USER 0:0` | Medium | Consider using non-root build user, but Chainguard distroless may not support this |

---

## 3. Compose Security Properties

| Service | Read-only Root | Non-root User | No New Privs | Dropped Caps | Health Check | Resource Limits |
|---------|---------------|---------------|--------------|--------------|--------------|-----------------|
| provider | Yes | Yes (65532) | Yes | ALL | Yes | Yes |
| open-webui | No | Default | Default | Default | Yes | Yes |
| litellm | No | Default | Default | Default | Yes | Yes |
| ollama | No | Default | Default | Default | Yes | Yes |

---

## 4. Supply Chain Integrity

| Control | Implementation | Status |
|---------|---------------|--------|
| Digest-pinned base image | `sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285` | PASS |
| Hash-pinned Python dependencies | `--require-hashes` in pip | PASS |
| SBOM generation | `anchore/sbom-action` in CI | PASS |
| Image signing/attestation | `actions/attest` in CI (main branch only) | PASS |
| Vulnerability scanning | `anchore/scan-action` in CI | PASS (blocked by CVE) |

---

## 5. Remediation Plan

| Priority | Action | Owner | Status |
|----------|--------|-------|--------|
| Critical | Resolve CVE-2026-115557 in base image | policedbc (risk acceptance) | BLOCKED_EXTERNAL |
| High | Add non-root user to open-webui, litellm, ollama services | cvsz | PENDING |
| High | Add `security_opt` and `cap_drop` to all services | cvsz | PENDING |
| Medium | Add `.dockerignore` to prevent context leakage | cvsz | PENDING |
| Medium | Pin all images in compose by digest | cvsz | PARTIAL (some pinned, some use variables) |

---
