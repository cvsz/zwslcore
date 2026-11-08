# Security Audit — cvsz/zwslcore

Audit date: 2026-11-09
Reviewer: cvsz
Repository branch: main (HEAD bc1eb1c)
Implementation branch: fix/zwslcore-shellcheck-hardening-20261109

## zeaz.md governance blocker (P0)

The canonical governance file `zeaz.md` is absent from this repository (not on disk, not tracked in git, not in any branch). Per ZEAZ §0, this blocker is recorded and conservative security defaults are applied. No governance requirements were invented. Existing security controls remain intact and were not weakened.

## Supply-chain / container vulnerability state (shell-verified via grype)

The Provider Docker image was built locally (`docker build --pull --tag local/zwslcore-provider:ci services/provider`, EXIT: 0) and scanned with grype 0.121.0.

| CVE | Package | Version | Severity | Fix state | Disposition |
|-----|---------|---------|----------|-----------|-------------|
| CVE-2026-119586 | sqlite-libs | 3.54.1-r0 | High | none available | RISK ACCEPTED — compensating controls |
| CVE-2026-84243 | glibc-2.44 | 2.44-r14 | High | unknown | RISK ACCEPTED — compensating controls |
| CVE-2026-116566 | python-3.15 | 3.15.2_git20261106-r0 | Medium | unknown | Monitor |
| CVE-2026-103995 | python-3.15 | 3.15.2_git20261106-r0 | Low | unknown | Monitor |

- `grype --fail-on critical` → PASS (EXIT: 0). Critical CVE-2026-115557 (python-3.15) is RESOLVED via the image update to Python 3.15.2.
- `grype --fail-on high` → BLOCKED (EXIT: 2) on the two High vendor CVEs. No fixed version is published by Chainguard/Wolfi. This blocks the `build-scan-sbom` required CI check.

## Risk acceptance (documented)

- CVE-2026-119586: docs/security/CVE-2026-119586-DISPOSITION.md
- CVE-2026-84243: docs/security/CVE-2026-84243-DISPOSITION.md

Both dispositions document: no vendor fix available, compensating controls (non-root user 65532:65532, read-only rootfs, dropped capabilities, no-new-privileges, loopback-only binding, secret scanning, dependency hash verification, immutable image digests), reassessment every 90 days, remediation trigger when Chainguard publishes a fix.

## Code-level security verification (tests)

| Area | File | Result |
|------|------|--------|
| Path traversal (symlink/dotdot/absolute/secret files) | tests.test_adversarial_security.PathTraversalApplyChangesTests | PASS — all vectors rejected at edit gate |
| Permission escalation (delegated agent scope) | tests.test_adversarial_security.PermissionEscalationTests | PASS — child agents cannot expand parent scope |
| Worktree concurrency | tests.test_adversarial_security.WorktreeConcurrencyTests | PASS — concurrent task creation does not corrupt store |
| Dotenv security (no command execution, no key leakage) | tests.test_ai_cli.CliTests | PASS |
| Structured output / injection | tests.test_provider_structured_output | PASS |

## Container hardening (verified in compose.yaml / Dockerfile)

- Provider: non-root user 65532:65532, read_only rootfs, cap_drop ALL, no-new-privileges, tmpfs /tmp noexec/nosuid, loopback-only bind (127.0.0.1).
- Ollama/LiteLLM/Open WebUI: loopback-only binds by default.
- Immutable image digests (@sha256:) for all Compose images and Dockerfile stages.
- `--require-hashes --only-binary=:all:` pip install with `--no-binary pyyaml` exception documented.
- No committed secrets (.env gitignored; secret placeholders only in .env.example).

## Unresolved security findings

- CVE-2026-119586 (High) — risk accepted, no fix available.
- CVE-2026-84243 (High) — risk accepted, no fix available.
- zeaz.md missing (P0) — governance blocker; canonical policy reference absent.
