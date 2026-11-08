# Security Audit — zwslcore

Audit date: 2026-11-08
Scope: Source code, CI workflows, container image, dependency lock, configuration.
Reviewer: cvsz (developer phase); independent review pending as policedbc.

## Methodology

Static review of the Provider gateway, engineering control plane, model catalog, shell scripts,
CI workflows, Compose file, Dockerfile, and dependency lockfile. Penetration testing scope is
limited to local test instances and repository code (no third-party systems, no production).

## Findings

### S0-01 (P0) — zeaz.md contains GitHub HTML instead of markdown policy — FIXED

**Finding:** `zeaz.md` (the canonical ZeaZDev policy referenced by AGENTS.md) contained saved
GitHub HTML markup rather than markdown policy text. Introduced in commit ff93b37.

**Root cause:** The file was populated with a rendered GitHub page instead of the policy source.

**Affected files:** `zeaz.md`

**Remediation:** Replaced `zeaz.md` with the canonical ZeaZDev AI & Engineering Operating Policy
in markdown form (reading order, canonical source of truth, engineering principles, change safety,
AI agent operating rules, security defaults, validation standard, scope and precedence).

**Test evidence:** `grep -c '<!DOCTYPE\|<html\|</html>' zeaz.md` returns 0; file is valid markdown.

**Verification result:** Fixed (commit d2b8708, GPG-signed).

**Remaining risk:** None.

---

### S1-01 (P1) — None confirmed in source code

No P1 security defects were identified in the reviewed source code (Provider gateway,
engineering control plane, model catalog, shell scripts).

---

### S1-02 (P1) — Provider image supply-chain scan fails (build-scan-sbom) — ACTIVE BLOCKER

**Finding:** The `provider-supply-chain` CI workflow's `build-scan-sbom` job fails on current
main with `severity-cutoff: high`. The anchore image scan detects high-severity
vulnerability(ies) in the built Provider image. This blocks all PRs from merging (it is a
required check on every PR).

**Root cause:** New vulnerability(ies) published in the Chainguard base image or a
transitive dependency since the last digest update (Oct 2026). The last remediation
(CHANGELOG) addressed CVE-2026-115557, CVE-2026-114613, CVE-2026-113351/115506; new CVEs
have since emerged.

**Affected files:** `services/provider/Dockerfile`, `services/provider/requirements.lock`,
`.github/workflows/provider-supply-chain.yml`

**Remediation:**
1. Re-run `anchore/scan-action` (via CI) to identify the specific CVE.
2. Update the Chainguard base image digest in `services/provider/Dockerfile` and `.env.example`.
3. Update any affected dependency in `pyproject.toml` and regenerate `requirements.lock`
   with `--require-hashes --generate-hashes`.
4. Re-run `build-scan-sbom` until SUCCESS at severity-cutoff: high.

**Test evidence:** Local `docker build` succeeds; `pip list` shows fastapi 0.142.4,
httpx 0.28.1, pydantic 2.14.1, protobuf 7.36.2, PyYAML 6.0.3, urllib3 2.8.0.
Anchore scan not run locally (requires anchore service / network).
CI evidence: PR #101 rebase CI run — build-scan-sbom FAILURE on current main.

**Verification result:** BLOCKED — build-scan-sbom FAILURE on current main.

**Remaining risk:** P1 — all PRs blocked from merging until supply-chain scan passes.
No PR can be merged without remediating this.

---

### S2-01 (P2) — Provider container runtime binds to 0.0.0.0 internally

**Finding:** `services/provider/Dockerfile` sets `ZEAZ_HOST=0.0.0.0` inside the container.
Compose publishes only loopback (`127.0.0.1:8080`) by default, so external exposure requires
the operator to additionally set `PROVIDER_BIND_ADDRESS=0.0.0.0`.

**Root cause:** Default image env binds to all interfaces; network isolation is enforced at
the Compose publish layer.

**Affected files:** `services/provider/Dockerfile`, `compose.yaml`, `.env.example`

**Remediation:** Documented the operator requirement to never expose `0.0.0.0:8080` without
the host firewall rule (restrict ingress to 192.168.1.85/32, per docs/NETWORK-TOPOLOGY.md).

**Test evidence:** Compose port mapping `${PROVIDER_BIND_ADDRESS:-127.0.0.1}:${PROVIDER_PORT:-8080}:8080`
defaults to loopback.

**Verification result:** Documented risk accepted with compensating controls (loopback publish,
read-only rootfs, non-root user, dropped capabilities, no-new-privileges).

**Remaining risk:** P2 — operator error could expose the Provider to the LAN.

---

### S2-02 (P2) — Host-managed PostgreSQL outside backup scope

**Finding:** LiteLLM uses a host PostgreSQL database (`litellm` role/database) that is outside
Docker Compose and outside the `scripts/backup.py` bundle. Operator must create it manually
and back it up separately.

**Root cause:** Architecture delegates PostgreSQL to the host operator.

**Affected files:** README.md (Host PostgreSQL setup), compose.yaml (litellm uses host.docker.internal)

**Remediation:** Documented backup requirement in README and BACKUP-RESTORE.md.

**Test evidence:** README documents `sudo -u postgres psql` role/database creation and separate
dump requirement.

**Verification result:** Documented risk accepted.

**Remaining risk:** P2 — database loss if not backed up separately.

---

### S3-01 (P3) — Shell script lint warnings resolved

**Finding:** ShellCheck initially flagged unused variables (doctor.sh LITELLM_MASTER_KEY,
smoke.sh OLLAMA_PORT/OPENWEBUI_PORT), unused functions (doctor.sh container_running/
container_healthy), non-constant source (cloudflare-up.sh), and declare/assign masking
(ai.sh SC2155).

**Root cause:** Variables read for environment documentation/completeness; helpers invoked
indirectly through a wrapper; profile sourcing is intentional; return value masked by export.

**Affected files:** scripts/doctor.sh, scripts/smoke.sh, scripts/cloudflare-up.sh, scripts/ai.sh,
tests/test_env_loader.sh

**Remediation:** Fixed ai.sh SC2155 (separate declare/assign); added ShellCheck disable comments
with justification for intentional patterns; test_env_loader.sh SC2016 confirmed as a correct
security test (single-quoted `$(touch ...)` must NOT be executed — verified by line 27).

**Test evidence:** `shellcheck -x <all shell scripts>` exits 0 (commit d5743d6, GPG-signed).

**Verification result:** Fixed.

**Remaining risk:** None.

---

### Security baseline verification

Per SECURITY.md repository security baseline:

| Control | Status | Evidence |
|---------|--------|----------|
| Protected default branch | Governed | .github/CODEOWNERS + branch policy |
| PR review before merge | Required | GitHub branch protection |
| Required status checks | CI, CodeQL, Dependency Review, Supply Chain | .github/workflows/ |
| Dependabot alerts/updates | Enabled | .github/dependabot.yml |
| Secret scanning/push protection | TruffleHog in CI (`fail: true`) | .github/workflows/ci.yml |
| Least-privilege Actions | `contents: read` on all workflows | .github/workflows/*.yml |
| Pinned Actions | Immutable SHAs | .github/workflows/*.yml |
| No committed secrets | validate_repo.py + TruffleHog | CI passed locally |
| CodeQL enabled | Python language | .github/workflows/codeql.yml |

### Provider runtime security controls

| Control | Implementation |
|---------|---------------|
| Authentication | API key required on /v1/* routes; /health and /metrics unauthenticated but non-sensitive |
| Key verification | SHA-256 hashes, `hmac.compare_digest`, fail-closed when no keys configured |
| Rate limiting | In-memory (10k buckets, window retention) or Redis Lua; 120/min default |
| Circuit breaker | Failure threshold 5, 30s reset, half-open probe |
| Retries | Max 3 attempts, exponential backoff, Retry-After honoring |
| Timeouts | Per-request timeout + total deadline (135s) |
| Size limits | 4MB request, 16MB response |
| Container | Non-root (65532), read-only rootfs, cap_drop ALL, no-new-privileges, tmpfs /tmp noexec |
| Image | Chainguard base, `@sha256:` digest, `--require-hashes --only-binary=:all:` |

### Penetration testing scope

Authorized scope: repository code and local test instances only. No third-party systems,
no production, no credential submission. Input validation, command injection, path traversal,
authentication bypass, unsafe file operations, and secrets exposure were reviewed statically.
No exploitable vulnerabilities were identified in the reviewed scope.

## Conclusion

Security posture is strong: authentication, authorization, rate limiting, circuit breakers,
input validation, output bounding, secret redaction, immutable supply chain intent, and container
hardening are implemented. The two P2 items (S2-01, S2-02) are documented operator-responsibility
risks with compensating controls. S1-02 (build-scan-sbom failure) is an active P1 blocker
preventing any PR merge until remediated.
