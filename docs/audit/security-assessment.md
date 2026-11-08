# Security Assessment — cvsz/zwslcore

**Generated:** 2026-11-08  
**Scope:** Complete repository security surface  
**Status:** PARTIALLY_VERIFIED

---

## 1. Authentication and Authorization

| Control | Implementation | Status |
|---------|---------------|--------|
| Provider API key authentication | `PROVIDER_CLIENT_KEY` required via Bearer or `x-api-key` header; missing/invalid → HTTP 401 | VERIFIED |
| Unauthenticated mode | `ZEAZ_ALLOW_UNAUTHENTICATED=false` by default; opt-in only | VERIFIED |
| Open WebUI authentication | Required; signup disabled by default (`ENABLE_SIGNUP=false`) | VERIFIED |
| LiteLLM admin | Password-based proxy-admin account; credentials stored in `~/.local/share/zwslcore/litellm-admin-credentials` (mode 0600) | VERIFIED |
| Path-scoped agent permissions | Last-match-wins; default deny; read-only profiles for `plan`/`review`/`explore` | VERIFIED |
| MCP authorization | Local stdio only; no remote HTTP/SSE/OAuth; autonomous agents do not receive MCP tool execution | VERIFIED |

---

## 2. Input Validation

| Control | Implementation | Status |
|---------|---------------|--------|
| Request body size limits | `max_request_bytes` enforced; HTTP 413 on overflow | VERIFIED |
| JSON schema validation | Model name validation (1-256 chars, no control characters); stream flag must be boolean; token limits validated | VERIFIED |
| Sampling parameter ranges | temperature (0-2), top_p (0-1), penalties (-2 to 2) | VERIFIED |
| JSON constant rejection | `_reject_json_constant` prevents NaN/Infinity | VERIFIED |
| Dotenv parsing | Symlink rejection, file size limit (1MB), permission check (0o077), allowlisted keys only, no command substitution | VERIFIED (PR #70) |

---

## 3. Secret Handling

| Control | Implementation | Status |
|---------|---------------|--------|
| `.env` gitignored | `.env`, `.env.production` not tracked | VERIFIED |
| `.env` mode 0600 | Owner-only permissions enforced at load time | VERIFIED |
| Symlink rejection | `.env` symlinks rejected before any existence check | VERIFIED |
| Allowlisted keys only | Dotenv loader only accepts known AI configuration keys | VERIFIED |
| No secrets in logs | Secrets redacted in evidence bundles; no secret logging | VERIFIED |
| Secret scanning | TruffleHog CI with `fail: true`; no tracked secret-bearing files | VERIFIED |
| No committed secrets | Verified via `git ls-files` grep for `.env`, `id_rsa`, `*.pem`, `*.key` | VERIFIED |
| Untracked local secrets | `services/provider/config/s3.local.yaml` is untracked (operator-local) | WARNING — keep untracked |

---

## 4. Network Exposure

| Control | Implementation | Status |
|---------|---------------|--------|
| Loopback-only binding | Provider (8080), LiteLLM (4000), Ollama (11434) bind to `127.0.0.1` by default | VERIFIED |
| Open WebUI LAN opt-in | `OPENWEBUI_BIND_ADDRESS=0.0.0.0` is explicit operator override | VERIFIED |
| No redirects | HTTP client `follow_redirects=False`, `trust_env=False` | VERIFIED |
| SSRF protection | Trusted proxy policy only resolves `cf-connecting-ip` from trusted CIDRs | VERIFIED |
| Ollama not exposed publicly | `ENABLE_OLLAMA_API=false` in Open WebUI config | VERIFIED |
| Cloud fallback opt-in | `FREE_CLOUD_FALLBACK_ENABLED=false` by default | VERIFIED |

---

## 5. Container Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Non-root user | `USER 65532:65532` | VERIFIED |
| Read-only rootfs | `read_only: true` in Compose | VERIFIED |
| Dropped capabilities | `cap_drop: ALL` | VERIFIED |
| No new privileges | `no-new-privileges: true` | VERIFIED |
| Resource limits | CPU and memory limits on all services | VERIFIED |
| Health checks | All services have HTTP-based health checks | VERIFIED |
| Log rotation | `max-size: 10m`, `max-file: 3` | VERIFIED |
| Tmpfs | `/tmp:size=64m,noexec,nosuid` on provider | VERIFIED |

---

## 6. Supply Chain Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Immutable image digests | All `FROM` and `image:` references use `@sha256:` digests | VERIFIED (updated for issue #108) |
| Hash-pinned Python deps | `--require-hashes` in Dockerfile; `requirements.lock` with hashes | VERIFIED |
| Binary-only policy | `--only-binary=:all:` with `--no-binary pyyaml` exception (no musl wheel) | VERIFIED |
| CodeQL | v4 (outdated); PRs #84/#85 to v4.39.1 open | PARTIAL |
| Dependency review | Enabled on PRs | VERIFIED |
| Dependabot | Configured for GitHub Actions, Docker, PyPI | VERIFIED |
| SBOM generation | SPDX JSON in provider-supply-chain workflow | VERIFIED |
| Attestation | `actions/attest` v4.2.2 for image and manifest | VERIFIED |
| Grype scan | `fail-build: true`, `severity-cutoff: high` | VERIFIED |

---

## 7. Filesystem Security

| Control | Implementation | Status |
|---------|---------------|--------|
| Worktree isolation | Git worktrees under `~/.zwslcore/worktrees` | VERIFIED |
| Path allowlists | `--allow-path` restricts engineering operations | VERIFIED |
| Snapshot integrity | SHA-256 metadata on change snapshots | VERIFIED |
| Backup integrity | SHA-256 manifest checksums; restore target outside backup directory | VERIFIED (PR #79 hardening) |
| Temp file safety | `mkdtemp` with mode 0o700; restore staging outside backup | VERIFIED (PR #79) |

---

## 8. Vulnerability Status

### Fixed by Issue #108 Remediation (Dockerfile digest update)

| CVE | Package | Severity | Was | Now |
|-----|---------|----------|-----|-----|
| CVE-2026-115557 | python-3.15 | Critical | 3.15.1 (vulnerable) | 3.15.2 (fixed) |
| CVE-2026-114613 | py3-pip-wheel | High | 26.2.2-r0 | 26.2.2-r1 (fixed) |
| CVE-2026-113351 | libexpat1 | High | 2.9.0-r0 | 2.10.0-r0 (fixed) |
| CVE-2026-115506 | libexpat1 | High | 2.9.0-r0 | 2.10.0-r0 (fixed) |

### Remaining (No Fix Available)

| CVE | Package | Severity | Disposition |
|-----|---------|----------|-------------|
| CVE-2026-119586 | sqlite-libs | High | Risk accepted — no fix available; compensating controls |
| CVE-2026-84243 | glibc-2.44 | High | Risk accepted — no fix available; compensating controls |

See `docs/security/CVE-2026-119586-DISPOSITION.md` and `docs/security/CVE-2026-84243-DISPOSITION.md`.

---

## 9. Residual Risks

| Risk | Likelihood | Impact | Control |
|------|-----------|--------|---------|
| CVE-2026-119586 (sqlite) | Low | High | Container hardening; no SQL `.recover` exposure |
| CVE-2026-84243 (glibc) | Low | High | Container hardening; Python abstraction layer |
| `.env` contains dev secrets | Low | High | Gitignored; rotate before production |
| GPG signing blocked | Medium | Blocker | Passphrase required for signed commits |
| Untracked `s3.local.yaml` | Low | Low | Keep untracked; do not commit real values |
