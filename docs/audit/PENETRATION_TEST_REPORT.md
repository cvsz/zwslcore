# Penetration Test Report — zwslcore

Audit date: 2026-11-09
Reviewer: cvsz
Scope: Repository code and local test instances only. Authorized scope — no third-party systems, no production, no credential submission.

## Penetration testing performed

Static security review across Provider gateway, engineering control plane, model catalog, shell scripts, CI workflows, Compose, Dockerfile, dependency lockfile.

## Test categories and results

| Category | Result | Evidence |
|----------|--------|----------|
| Input validation | PASS | Provider `body()` validates JSON, model name, stream flag, token limits, sampling ranges; rejects non-dict bodies, oversized requests (4MB) |
| Command injection | PASS | No shell=True usage in provider; httpx used for outbound; dotenv reader (`dotenv_get`) reads KEY=VALUE literally without eval/source |
| Path traversal | PASS | Engineering `_apply_changes` rejects absolute paths, `..` parts, secret-bearing paths (.env, .pem, .key); enforces allowed-path scope |
| Privilege escalation | PASS | Container runs non-root (65532), cap_drop ALL, no-new-privileges, read-only rootfs |
| Authentication bypass | PASS | API key required on all /v1/* routes; constant-time `hmac.compare_digest`; fail-closed when no keys configured |
| Authorization bypass | PASS | Engineering agent permission model (allow/ask/deny); read-only profiles cannot edit/commit |
| Unsafe file operations | PASS | Change snapshot store is binary-capable but path-scoped; no symlink following on arbitrary paths |
| Symlink handling | PASS | `load_dotenv()` refuses symlink .env; `_apply_changes` resolves and bounds target within worktree root |
| Secrets exposure | PASS | Security redaction regex strips sk-/AIza/AKIA/Bearer patterns; audit logging redacts client_id and bounds fields; no secrets committed |
| Dependency vulnerabilities | BLOCKED | build-scan-sbom FAILURE on current main (high-severity image scan) — see SECURITY_AUDIT.md S1-02 |
| Insecure defaults | PASS | Loopback-only binding by default, signup disabled, ZERO_COST_ONLY cost policy, cloud fallback opt-in |
| Race conditions | PASS | InMemoryRateLimiter uses ordered dict + monotonic clock with window retention (no reset-on-reject); circuit breaker uses asyncio.Lock |
| Resource exhaustion | PASS | Request concurrency limiter (semaphore), response byte limits, rate limiting max 10k buckets |

## Confirmed vulnerabilities

None identified in the reviewed scope beyond the pre-existing build-scan-sbom supply-chain blocker (S1-02).

## Regression tests

Existing tests cover: client key verification (fail-closed), cost policy (zero-cost-only), router route resolution (404 unknown model, 410 cost-blocked), endpoint authentication (401 without credentials), rate limiter window enforcement, stream total deadline, audit redaction, observability metrics.

## Scope limitations

- Anchore image scan not run locally (requires network/anchore service); build-scan-sbom failure observed via CI on PR #101 rebase.
- No active exploitation performed (passive/static review only), per authorized scope.

## Conclusion

No exploitable vulnerabilities identified in authorized scope. The single blocker is the build-scan-sbom supply-chain scan failure on current main, which blocks all PR merges until remediated.
