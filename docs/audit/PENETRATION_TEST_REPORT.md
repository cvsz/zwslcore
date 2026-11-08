# Penetration Test Report — cvsz/zwslcore

Audit date: 2026-11-09
Reviewer: cvsz
Scope: Non-destructive, code-level security testing on repository code and local test instances only.
Authorization: Authorized scope limited to cvsz/zwslcore repository code and local test instances. No third-party systems, no production, no unrelated machines, no destructive tests, no credential submission, no active control-plane confirmation.

## Scope and method

Static and code-level review of:
- Input validation
- Command injection
- Path traversal
- Privilege escalation
- Authentication bypass
- Authorization bypass
- Unsafe file operations
- Symlink handling
- Secrets exposure
- Dependency vulnerabilities
- Insecure defaults
- Race conditions
- Resource exhaustion
- Information disclosure

No network exploitation, no credential submission, no active control-plane confirmation, no third-party targets.

## Findings

| Finding | Severity | File(s) | Evidence | Result |
|---------|----------|---------|----------|--------|
| Path traversal (symlink / dotdot / absolute path / secret files) | P2 (mitigated) | services/engineering/worktree.py, services/engineering/permissions.py, scripts/ai.sh | tests.test_adversarial_security.PathTraversalApplyChangesTests — absolute path rejected, dotdot path rejected, dotdot mid-path rejected, outside-allowed-scope rejected, symlink escape rejected, secret env file rejected, secret PEM file rejected | PASS — all vectors rejected at edit gate |
| Permission escalation (delegated agent scope) | P2 (mitigated) | services/engineering/delegation.py, services/engineering/permissions.py | tests.test_adversarial_security.PermissionEscalationTests — delegated paths within parent allowed; delegated paths exceeding parent raise | PASS — child agents cannot expand parent scope |
| Worktree concurrency | P2 (mitigated) | services/engineering/worktree.py, services/engineering/store.py | tests.test_adversarial_security.WorktreeConcurrencyTests — concurrent task creation does not corrupt the store | PASS |
| Dotenv security (no command execution, no key leakage to untrusted URL) | P2 (mitigated) | scripts/ai.sh | tests.test_ai_cli.CliTests — dotenv does not execute commands, never leaks key to untrusted URL, rejects insecure permissions | PASS |
| Structured output / injection hardening | P3 | services/provider/zeaz_provider/* | tests.test_provider_structured_output — JSON schema extraction, native Ollama format, response normalization | PASS |
| Dependency vulnerabilities (container) | P1 (risk accepted) | services/provider/Dockerfile | grype scan — CVE-2026-119586 (High, sqlite-libs), CVE-2026-84243 (High, glibc) no fix available | RISK ACCEPTED — compensating controls |
| Secrets exposure | P3 | — | `git ls-files` grep for .env/id_rsa/*.pem/*.key; no tracked secret-bearing files; `.env` gitignored | PASS |

## Conclusion

No exploitable vulnerabilities were identified within the authorized scope. The two High-severity container vulnerabilities have no vendor fix and are risk-accepted with documented compensating controls. All code-level security controls (path traversal, permission escalation, concurrency, dotenv safety, structured output) are covered by passing regression tests.

No third-party systems were attacked. No production or unrelated machines were accessed. No secrets were exposed in this report.
