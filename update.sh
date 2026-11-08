
#!/usr/bin/env bash
set -Eeuo pipefail

cd ~/zwslcore

echo "=================================================="
echo " ZWSLCore — PRE-WORK CHECKPOINT & FULL AUDIT"
echo "=================================================="

# --------------------------------------------------
# PHASE 0: GOVERNANCE AND REPOSITORY VALIDATION
# --------------------------------------------------

if [[ ! -f zeaz.md ]]; then
  echo "FATAL: zeaz.md not found. Aborting."
  exit 1
fi

git rev-parse --show-toplevel >/dev/null
git fetch --prune origin

if [[ -n "$(git status --porcelain)" ]]; then
  echo "FATAL: Working tree contains uncommitted changes."
  git status --short
  echo "Review and commit intended changes manually. No files were staged."
  exit 1
fi

if [[ -n "$(git ls-files -u)" ]]; then
  echo "FATAL: Merge conflicts detected."
  exit 1
fi

# --------------------------------------------------
# PHASE 1: CREATE AND PUSH PRE-WORK CHECKPOINT
# --------------------------------------------------

BASE_SHA="$(git rev-parse HEAD)"
TIMESTAMP="$(date -u +%Y%m%dT%H%M%SZ)"
CHECKPOINT_BRANCH="checkpoint/zwslcore-pre-audit-${TIMESTAMP}"
WORK_BRANCH="audit/zwslcore-full-hardening-${TIMESTAMP}"

echo "Baseline HEAD: ${BASE_SHA}"

git switch -c "$CHECKPOINT_BRANCH"
git push -u origin "$CHECKPOINT_BRANCH"

echo "Checkpoint pushed: ${CHECKPOINT_BRANCH}"

# --------------------------------------------------
# PHASE 2: CREATE IMPLEMENTATION BRANCH
# --------------------------------------------------

git switch -c "$WORK_BRANCH" "$BASE_SHA"

echo "Implementation branch: ${WORK_BRANCH}"

# --------------------------------------------------
# PHASE 3: RUN OPENCODE
# --------------------------------------------------

opencode run --auto \
  -m nvidia/nvidia/nemotron-3.5-super-vl-120b-a12b \
  --agent build \
  --title "ZWSLCore — Full Independent Audit, Fix, Upgrade & Security Hardening" \
  "$(cat <<'ZEAZ_ZWSLCORE_MASTER_PROMPT'
Read zeaz.md and all applicable AGENTS.md files before making changes.

OBJECTIVE
Perform a complete, evidence-driven independent audit and implementation of ZWSLCore. Find and fix verified bugs, incomplete implementations, security weaknesses, configuration errors, test gaps, documentation drift, and operational risks.

GOVERNANCE
1. Treat zeaz.md as the mandatory source of truth.
2. Inspect the current Git branch, HEAD, working tree, and remotes first.
3. Preserve all existing user changes. Never overwrite unrelated work.
4. Never expose secrets, credentials, tokens, private keys, or environment values.
5. Never run destructive commands, delete persistent data, reset volumes, or perform unsafe migrations.
6. Never force-push, bypass branch protection, self-approve, or impersonate an independent reviewer.
7. Do not merge, release, publish, or deploy to production.
8. If zeaz.md is missing or governance cannot be established, stop implementation and report the blocker.

PHASE 1 — BASELINE
- Inventory repository structure, services, dependencies, Docker images, Compose configuration, workflows, scripts, tests, and documentation.
- Record branch, HEAD SHA, dirty state, tool versions, and runtime state.
- Identify stale reports and distinguish historical claims from current evidence.

PHASE 2 — ARCHITECTURE
Audit Provider Gateway, Ollama, LiteLLM, Open WebUI, PostgreSQL, networking, configuration, and service dependencies.
Validate API contracts, model routing, streaming, timeout behavior, retries, error handling, concurrency, and resource limits.
Identify unnecessary complexity and reduce code where safe.

PHASE 3 — NETWORK SECURITY
Target topology:
- ZWSLCore host: 192.168.1.100
- ZCoder client: 192.168.1.85
- Provider endpoint target: http://192.168.1.100:8080/v1

Requirements:
- Preserve loopback access.
- If LAN access is required, expose only the Provider Gateway on the required host interface.
- Restrict inbound access to 192.168.1.85/32.
- Do not expose Ollama, LiteLLM, PostgreSQL, or internal administration ports.
- Never flush firewall rules or replace existing firewall policy.
- Inspect existing firewall and routing before proposing changes.
- Plain HTTP does not encrypt Bearer tokens. Prefer TLS or an established encrypted private network. Never weaken authentication to make connectivity work.
- Do not apply host firewall or production network changes without explicit authorization.

PHASE 4 — PROVIDER SECURITY
Inspect authentication, authorization, fail-closed behavior, key validation, constant-time comparisons, rate limits, concurrency limits, request/response size limits, CORS, Host validation, SSRF, redirects, proxy trust, metrics, health endpoints, and sensitive logging.
Fix verified vulnerabilities with regression tests.
Ensure unauthenticated health and metrics endpoints expose no sensitive information.

PHASE 5 — ZCODER COMPATIBILITY
Validate OpenAI-compatible API behavior:
- GET /v1/models
- POST /v1/chat/completions
- POST /v1/responses
- Streaming and non-streaming behavior
- Authentication and error contracts
- Model discovery and model identifiers
- Timeouts and cancellation

Do not invent model names. Discover actual models from the running service or configuration.
Document the exact client configuration and safe connectivity test.

PHASE 6 — LOCAL-FIRST MODEL POLICY
- Keep cloud fallback disabled by default.
- Never silently route private prompts or code to external providers.
- Make provider selection and fallback behavior observable.
- Validate that local-only mode remains local under provider failures.
- Do not introduce external API keys or paid services.

PHASE 7 — LITELLM, OLLAMA AND DATABASE
- Audit configuration, health checks, readiness, persistence, resource limits, and restart behavior.
- Keep internal services on private networks.
- Preserve PostgreSQL databases, roles, permissions, and volumes.
- No DROP, TRUNCATE, volume deletion, or unreviewed migrations.
- Verify backup and recovery procedures without overwriting existing backups.

PHASE 8 — SUPPLY CHAIN
- Review image digest pinning, base image vulnerabilities, non-root execution, capabilities, filesystem permissions, read-only filesystem compatibility, SBOM, dependency pinning, and provenance.
- Verify current CVE status against authoritative sources when network research is available.
- Do not claim a vulnerability is fixed without evidence.
- Do not upgrade pinned images blindly.

PHASE 9 — BUG HUNT AND IMPLEMENTATION
Inspect all relevant Python, YAML, Docker, Bash, PowerShell, TypeScript, and workflow code.
Look for:
- Runtime errors and unhandled exceptions
- Race conditions and resource leaks
- Incorrect configuration defaults
- Missing validation
- Authentication and authorization bypasses
- Unsafe subprocess and shell handling
- Path traversal and injection risks
- Retry storms and timeout gaps
- Incomplete tests and misleading success states
- Documentation and implementation drift

Implement verified fixes in small, reviewable changes. Add regression tests for each security or correctness fix.

PHASE 10 — QUALITY GATES
Run all applicable:
- Syntax and formatting checks
- Lint and type checks
- Unit and integration tests
- Security scans and secret scans
- Docker build
- Docker Compose config validation
- Service health checks
- API contract tests
- Network access tests where safe

Report each result as PASS, FAIL, SKIPPED, BLOCKED, or NOT RUN. Never represent skipped tests as passed.

PHASE 11 — DOCUMENTATION
Update architecture documentation, configuration reference, deployment guidance, security model, troubleshooting, API examples, and operational runbooks.
Document LAN access and TLS requirements accurately.
Do not include secrets or credentials in examples.

PHASE 12 — GIT AND DELIVERY
- Work on the dedicated implementation branch created before this run.
- Keep changes scoped and reviewable.
- Run quality gates against the exact final HEAD.
- Inspect the final diff for accidental changes and secrets.
- Commit implementation changes with clear messages.
- Push only this feature branch, after verifying the diff and secret scan.
- Create a draft PR only if repository governance and permissions allow it safely.
- Do not merge or deploy.

PHASE 13 — FINITE REVIEW LOOP
Repeat:
1. Audit the changed implementation.
2. Run relevant regression tests.
3. Inspect failures.
4. Fix verified issues.
5. Re-run affected quality gates.
Stop when all feasible gates pass or remaining blockers require external access, authorization, or infrastructure changes.

DEFINITION OF DONE
- zeaz.md and applicable agent policies followed.
- No unrelated user changes lost.
- Verified bugs fixed with regression tests.
- Security findings remediated or explicitly documented.
- Local-first policy preserved.
- No unauthorized external exposure or production changes.
- Quality gate results accurately reported.
- Documentation reflects actual implementation.
- Final branch and HEAD SHA recorded.

FINAL REPORT
Provide:
1. Executive summary.
2. Initial repository state and exact HEAD.
3. Findings by severity with file and line references.
4. Changes implemented and rationale.
5. Tests and exact results.
6. Remaining risks and blockers.
7. Network/TLS recommendations.
8. Changed-file inventory.
9. Final branch, commit SHA, and PR URL if created.
10. Explicit list of actions not performed.

Do not fabricate test results, reviews, approvals, commits, or deployment status.
ZEAZ_ZWSLCORE_MASTER_PROMPT
)"

echo
echo "=================================================="
echo " OPENCODE SESSION FINISHED"
echo "=================================================="
echo "Checkpoint: ${CHECKPOINT_BRANCH}"
echo "Work branch: ${WORK_BRANCH}"
echo "Initial HEAD: ${BASE_SHA}"
git status --short
git log -1 --oneline
