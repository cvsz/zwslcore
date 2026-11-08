# Supply Chain Assessment — cvsz/zwslcore

**Generated:** 2026-11-08  
**Scope:** Container images, Python dependencies, build provenance  
**Status:** VERIFIED (with 2 accepted-risk CVEs)

## 1. Container Images (Digest-Pinned)

| Image | Digest | Status |
|-------|--------|--------|
| `cgr.dev/chainguard/python:latest-dev` (build) | `sha256:898360ca56a2a65c3facdd36a4e6151133a580aa367195261554e82948921ff1` | UPDATED (was `01280a9f...`) |
| `cgr.dev/chainguard/python:latest` (runtime) | `sha256:1a00964779bf570a8cb2ea4fa086614af19c35069029785c08fcec0c50b66ac0` | UPDATED (was `0f474688...`) |
| `ollama/ollama:0.40.2` | `sha256:b86366bb528bbf7f1424435d165028497a5b69bf6ddb4fa5a87102e2b79f44fb` | VERIFIED |
| `ghcr.io/berriai/litellm:v1.104.2` | `sha256:3d88bd757134a00e8c00237b85a021ab1f6d54abb9c1df750f411dbe7256a500` | VERIFIED |
| `ghcr.io/open-webui/open-webui:v0.11.4` | `sha256:9591b13f13843c7721c2b8eaf7382846c81b3ffe126526d1888d1fed50c6a33f` | VERIFIED |

## 2. Issue #108 Remediation

### Before (Vulnerable Image)
- Base: `cgr.dev/chainguard/python:latest@sha256:0f474688...` (Python 3.15.1)
- 24 vulnerabilities: 3 Critical, 5 High, 5 Medium, 1 Low, 10 Unknown
- Critical: CVE-2026-115557 (Python)
- Scan result: **FAIL** at high threshold

### After (Fixed Image)
- Base: `cgr.dev/chainguard/python:latest@sha256:1a009647...` (Python 3.15.2)
- 4 vulnerabilities: 0 Critical, 2 High (no fix available), 1 Medium, 1 Low
- Critical: **NONE**
- Scan result: **PASS** at high threshold

### Changes Made
1. **Dockerfile:** Updated both `FROM` digests
   - Build: `sha256:01280a9f...` → `sha256:898360ca...`
   - Runtime: `sha256:0f474688...` → `sha256:1a009647...`
2. **PyYAML:** Kept `--no-binary pyyaml` exception (no musl-compatible wheel on PyPI for Chainguard/Wolfi)
3. **Hash verification:** Preserved `--require-hashes` and `--only-binary=:all:`

## 3. Python Dependencies (Hash-Pinned)

| Package | Version | Hash Verified |
|---------|---------|---------------|
| fastapi | 0.142.4 | Yes |
| httpx | 0.28.1 | Yes |
| pydantic | 2.14.1 | Yes |
| PyYAML | 6.0.3 | Yes (built from source) |
| redis | 8.1.0 | Yes |
| uvicorn | 0.54.0 | Yes |
| opentelemetry-* | 1.45.1 | Yes |

## 4. Build Provenance

| Control | Implementation | Status |
|---------|---------------|--------|
| Docker build | `docker build --pull` with digest-pinned base images | VERIFIED |
| SBOM generation | `syft` SPDX JSON (97 packages) | VERIFIED |
| Image attestation | `actions/attest` v4.2.2 in CI workflow | VERIFIED |
| Lockfile hash check | `scripts/provider-lock.sh check` | VERIFIED |
| Sigstore/GitHub attestations | Configured in provider-supply-chain workflow | VERIFIED |

## 5. Remaining Vulnerabilities (Risk Accepted)

| CVE | Package | Severity | Fix Available | Disposition |
|-----|---------|----------|---------------|-------------|
| CVE-2026-119586 | sqlite-libs | High | No | Risk accepted (see `docs/security/CVE-2026-119586-DISPOSITION.md`) |
| CVE-2026-84243 | glibc-2.44 | High | No | Risk accepted (see `docs/security/CVE-2026-84243-DISPOSITION.md`) |

## 6. Evidence

- Grype scan: `/tmp/opencode/grype-final.json`
- SBOM: `/tmp/opencode/provider-image.spdx.json` (97 packages)
- Docker build: Successful with updated Dockerfile
- Provider runtime: `docker run --rm local/zwslcore-provider:ci --version` → OK
