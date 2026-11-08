# Security Audit — zwslcore

Audit date: 2026-11-08
Scope: Source code, CI workflows, container image, dependency lock, configuration.

## Methodology

Static review of the Provider gateway, engineering control plane, model catalog, shell scripts,
CI workflows, Compose file, Dockerfile, and dependency lockfile. Penetration testing scope is
limited to local test instances and repository code (no third-party systems, no production).

## Findings

### S0-01 (P0) — zeaz.md contains GitHub HTML instead of markdown policy

**Finding:** `zeaz.md` (the canonical ZeaZDev policy referenced by AGENTS.md) contained saved
GitHub HTML markup rather than markdown policy text. Introduced in commit ff93b37.

**Root cause:** The file was populated with a rendered GitHub page instead of the policy source.

**Affected files:** `zeaz.md`

**Remediation:** Replaced `zeaz.md` with the canonical ZeaZDev AI & Engineering Operating Policy
in markdown form (reading order, canonical source of truth, engineering principles, change safety,
AI agent operating rules, security defaults, validation standard, scope and precedence).

**Test evidence:** `grep -c '<!DOCTYPE\|<html\|</html>' zeaz.md` returns 0; file is valid markdown.

**Verification result:** Fixed.

**Remaining risk:** None.

---

### S1-01 (P1) — None confirmed

No P1 security defects were identified in the reviewed source code.

---

### S2-01 (P2) — Provider container runtime binds to 0.0.0.0 internally

**Finding:** `services/provider/Dockerfile` sets `ZEAZ_HOST=0.0.0.0` inside the container.
Compose publishes only loopback (`127.0.0.1:8080`) by default, so external exposure requires the
operator to additionally set `PROVIDER_BIND_ADDRESS=0.0.0.0`. The compose comment documents the
required host firewall rule (restrict ingress to 192.168.1.85/32).

**Root cause:** Default image env binds to all interfaces; network isolation is enforced at the
Compose publish layer, not the container layer.

**Affected files:** `services/provider/Dockerfile`, `compose.yaml`, `.env.example`

**Remediation:** Defense-in-depth is acceptable but the container should ideally bind loopback by
default as well. Documented the operator requirement to never expose `0.0.0.0:8080` without the
firewall rule.

**Test evidence:** Compose port mapping `${PROVIDER_BIND_ADDRESS:-127.0.0.1}:${PROVIDER_PORT:-8080}:8080` defaults to loopback.

**Verification result:** Documented risk accepted with compensating controls (loopback publish,
read-only rootfs, non-root user, dropped capabilities, no-new-privileges).

**Remaining risk:** P2 — operator error could expose the Provider to the LAN.

---

### S2-02 (P2) — Host-managed PostgreSQL outside backup scope

**Finding:** LiteLLM uses a host PostgreSQL database (`litellm` role/database) that is outside
Docker Compose and outside the `scripts/backup.py` bundle. Operator must create it manually and
back it up separately (documented in README).

**Root cause:** Architecture delegates PostgreSQL to the host operator.

**Affected files:** README.md (Host PostgreSQL setup), compose.yaml (litellm uses host.docker.internal)

**Remediation:** Documented backup requirement in README and BACKUP-RESTORE.md.

**Test evidence:** README documents `sudo -u postgres psql` role/database creation and separate
dump requirement.

**Verification result:** Documented risk accepted.

**Remaining risk:** P2 — database loss if not backed up separately.

---

### S3-01 (P3) — Shell script SC2034/SC2329 warnings resolved

**Finding:** ShellCheck initially flagged unused variables (doctor.sh LITELLM_MASTER_KEY,
smoke.sh OLLAMA_PORT/OPENWEBUI_PORT), unused functions (doctor.sh container_running/
container_healthy), and a non-constant source (cloudflare-up.sh).

**Root cause:** Variables read for environment documentation/completeness; helpers invoked
indirectly through a wrapper; profile sourcing is intentional.

**Affected files:** scripts/doctor.sh, scripts/smoke.sh, scripts/cloudflare-up.sh, scripts/ai.sh,
tests/test_env_loader.sh

**Remediation:** Fixed ai.sh SC2155 (separate declare/assign); added ShellCheck disable comments
with justification for intentional patterns; test_env_loader.sh SC2016 confirmed as a correct
security test (single-quoted `$(touch ...)` must NOT be executed — verified by line 27).

**Test evidence:** `shellcheck -x <all shell scripts>` exits 0.

**Verification result:** Fixed.

**Remaining risk:** None.

---

### Security baseline verification

Per SECURITY.md repository security baseline:

| Control | Status | Evidence |
|---------|--------|----------|
| Protected default branch | Governed by CODEOWNERS + branch policy | .github/CODEOWNERS |
| PR review before merge | Required reviews configured | GitHub branch protection |
| Required status checks | CI, CodeQL, Dependency Review, Supply Chain | .github/workflows/ |
| Dependabot alerts/updates | Enabled | .github/dependabot.yml |
| Secret scanning/push protection | TruffleHog in CI (`fail: true`) | .github/workflows/ci.yml |
| Least-privilege Actions | `contents: read` on all workflows | .github/workflows/*.yml |
| Pinned Actions | Immutable SHAs (checkout v7, codeql v4, etc.) | .github/workflows/*.yml |
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

## Penetration testing scope

Authorized scope: repository code and local test instances only. No third-party systems,
no production, no credential submission. Input validation, command injection, path traversal,
authentication bypass, unsafe file operations, and secrets exposure were reviewed statically.
No exploitable vulnerabilities were identified in the reviewed scope.

## Conclusion

Security posture is strong: authentication, authorization, rate limiting, circuit breakers,
input validation, output bounding, secret redaction, immutable supply chain, and container
hardening are all implemented. The two P2 items are documented operator-responsibility risks
with compensating controls.
