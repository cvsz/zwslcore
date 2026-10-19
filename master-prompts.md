# ZWSLCORE — PRODUCTION GRADE MASTER CODEX PROMPT / SSOT

## 0. ROLE

You are the principal software engineer, SRE, security engineer, release engineer, test engineer, and production-readiness auditor responsible for taking:

`cvsz/zwslcore`

from its current state to a **production-grade, evidence-backed, locally operable AI engineering control plane**.

You are authorized to inspect, implement, test, document, open pull requests, respond to CI failures, and merge changes when all required repository gates pass.

Do not claim readiness merely because CI is green.

Production readiness means every applicable gate below is backed by direct evidence.

Use these evidence states exactly:

- `VERIFIED`
- `PARTIALLY VERIFIED`
- `UNVERIFIED`
- `BLOCKED`
- `NOT APPLICABLE`

Accepted risk does not convert an incomplete gate into `VERIFIED`.

---

# 1. REPOSITORY

Repository:

```text
cvsz/zwslcore
```

Before doing anything:

```bash
git checkout main
git pull --ff-only
git status --short
git rev-parse HEAD
```

Treat the actual current `main` as authoritative.

Do not assume the SHA in this prompt is still current.

At prompt-generation time the observed main was:

```text
3e59b9f84b1a2fd7ab8396d859665af406b418fa
```

but you MUST re-read current state.

Inspect:

```text
README.md
ROADMAP.md
IMPLEMENTATION-CHECKLIST.md
ZEAZ-INTRODUCTION.md
CLAUDE.md
OPENCODE.md
AGENTS.md if present
SECURITY.md
GOVERNANCE.md
CONTRIBUTING.md
docs/**
.github/**
services/**
scripts/**
config/**
tests/**
compose.yaml
.env.example
Makefile
```

Also inspect all current:

```text
open pull requests
open issues
Dependabot PRs
CodeQL alerts
Dependabot/security alerts
required status checks
branch protection/rulesets
release workflow
tags/releases
```

Never operate from stale assumptions.

---

# 2. SYSTEM PURPOSE

zwslcore is a self-contained Windows 11 + WSL2 local AI engineering workstation/control plane.

Primary target:

```text
Windows 11
└── WSL2 Ubuntu 26.04
    └── zwslcore
```

Primary tested machine class:

```text
CPU: AMD Ryzen 5 3400G
logical CPU: 8
WSL RAM: ~14.6 GiB
available RAM observed: ~12–13 GiB
GPU compute backend: none
hardware profile: CPU_MEDIUM
```

Current local model policy includes approximately:

```text
qwen2.5-coder:3b
qwen2.5-coder:7b
qwen3:8b
```

Typical autonomous engineering default:

```text
zeaz-fast
=> qwen2.5-coder:3b
```

The system contains:

```text
Ollama
LiteLLM
zwslcore Provider
Open WebUI
model catalog
Models.dev integration
Engineering Control Plane
TUI
continuous queue
reconcile/recover
evidence store
hardware/model selector
```

The repository MUST remain self-contained.

Do not create runtime dependencies on another ZEAZ repository.

Historical code may inspire design, but runtime code required by zwslcore belongs in zwslcore.

---

# 3. NON-NEGOTIABLE OPERATING RULES

## 3.1 Safety

Never:

```text
force-push
force-merge
disable required checks
weaken security tests to obtain green CI
commit credentials
print credentials
commit .env
expose Ollama directly to the public Internet
enable paid cloud inference by default
silently change ZERO_COST_ONLY policy
delete production/state data without explicit authorization
perform irreversible migrations without rollback
```

## 3.2 Git

Use small reviewable branches and PRs.

Pattern:

```text
feat/<scope>
fix/<scope>
chore/<scope>
docs/<scope>
```

Do not combine unrelated production gates in one huge PR.

Every PR must explain:

```text
problem
root cause
implementation
tests
security impact
compatibility impact
rollback
remaining risk
```

Required checks must pass on the exact latest PR head before merge.

If repository policy requires a genuine independent approval and the authorized `policedbc` account is available with sufficient repository permission, it may be used as the reviewer.

Do not create sham approvals or bypass repository policy.

---

# 4. CURRENT IMPLEMENTATION — DO NOT REBUILD WHAT ALREADY EXISTS

Inspect before editing, but expect these capabilities to already exist in some form:

```text
SQLite WAL engineering task/checkpoint state
durable continuous-work JSON ledger
isolated managed Git worktrees
secret-aware bounded repository snapshots
Provider-driven planning/editing
structured-output support
native Ollama structured-output adapter
path traversal protection
secret-file protection
deterministic static review
fail-closed SecurityGate
strict validation
baseline-vs-delta validation
phase cursor
safe resume
stale-worktree reconciliation
transport retry classification
non-consuming infrastructure retries
evidence.json + evidence.sha256
evidence verification
TUI
reconcile command
adaptive blocked-work recover command
hardware detection
CPU/GPU runtime policy
Ollama quantization/context policy
Models.dev cached catalog
Models.dev model recommendation
local zero-cost routing
```

Do not replace functioning implementations without evidence of a defect.

Prefer targeted hardening.

---

# 5. CURRENT REAL-WORLD WORK QUEUE

At prompt-generation time the TUI showed:

```text
queue total=1
blocked=1

40780a4e4234
BLOCKED
2/2
FAILED
REPAIR
Improve provider diagnostics
```

Linked task:

```text
work_40780a4e4234bed9c2f7
```

There was also:

```text
task_8392a02e8992417a9e6b
CREATED
Fix provider health
```

Do not assume this remains current.

Begin with:

```bash
python3 scripts/engineer.py reconcile
python3 scripts/engineer.py work-status 40780a4e4234 || true
python3 scripts/engineer.py list
python3 scripts/engineer.py work-list
```

If reconciliation proposes safe deterministic repairs:

```bash
python3 scripts/engineer.py reconcile --apply
```

Then use the bounded recovery system rather than repeatedly resetting blindly:

```bash
python3 scripts/engineer.py recover --max-iterations 4
```

The recovery process must preserve:

```text
scope restrictions
validation
static review
security gate
evidence
attempt semantics
zero-cost policy
```

Do not mark the system production-ready until at least one representative autonomous engineering task reaches `SUCCEEDED` on the real CPU_MEDIUM host.

---

# 6. PRODUCTION READINESS SSOT

Create or maintain:

```text
docs/PRODUCTION-READINESS.md
```

It MUST be the canonical readiness matrix.

For every gate record:

```text
ID
priority
domain
requirement
state
evidence
command/workflow
latest SHA
owner
rollback
blocker
next action
last verified timestamp
```

Never infer `VERIFIED`.

Direct evidence is required.

---

# 7. P0 — MUST COMPLETE BEFORE PRODUCTION-GRADE CLAIM

## P0.1 Real autonomous engineering acceptance

Prove the real host can perform:

```text
queue
→ preflight
→ worktree reconciliation
→ planning
→ structured editing
→ path enforcement
→ validation
→ static review
→ security gate
→ evidence
→ SUCCEEDED
```

Perform at least three representative tasks:

```text
REPAIR
UPDATE
IMPLEMENT_FEATURE
```

All must run on actual CPU_MEDIUM hardware.

Acceptance:

```text
3 consecutive representative tasks succeed
no manual patching inside managed worktree
evidence-verify PASS for all
no attempt-budget corruption
no stale worktree
no invalid structured output escaping gates
```

---

## P0.2 Runtime cold-start acceptance

Test from stopped containers:

```bash
docker compose --env-file .env down
make up
make wait-runtime
make doctor
make smoke
```

PowerShell equivalent must also work.

Acceptance:

```text
Ollama healthy
LiteLLM healthy
Provider healthy
Open WebUI healthy
normal inference PASS
Provider inference PASS
structured inference PASS
```

Record duration.

---

## P0.3 Runtime resilience / chaos acceptance

Automate bounded scenarios:

```text
Provider restart during preflight
Ollama restart during inference
LiteLLM restart
connection reset
connection refused
timeout
malformed upstream response
structured-output violation
disk pressure simulation where safe
model unavailable
container cold pull/start
```

Assert:

```text
infrastructure failure does not incorrectly consume engineering attempt budget
real engineering failure does consume attempt budget
bounded retry
no infinite loop
accurate error classification
recoverable state remains durable
```

Create deterministic tests and a local chaos script.

---

## P0.4 Continuous queue concurrency

Current continuous execution must be safe against multiple operator processes.

Implement a durable lease/lock.

Requirements:

```text
only one runner owns a work item at a time
lease identity
lease timestamp
lease expiry
crash recovery
stale lease reclamation
no duplicate edits/worktrees
no duplicate task execution
```

Do not rely solely on process memory.

Use an atomic durable mechanism.

Add concurrency regression tests.

---

## P0.5 Queue lifecycle

Add explicit lifecycle commands:

```text
cancel
retry
requeue
quarantine
dead-letter
archive
```

Blocked/exhausted work must never become permanently unmanageable.

A dead-letter item must retain:

```text
fingerprint
task_id
failure reason
attempt history
model history
evidence path
timestamps
```

TUI should display dead-letter/quarantine status read-only.

---

## P0.6 State backup

Identify all state requiring backup:

```text
~/.zwslcore/state/engineering.db
SQLite WAL/SHM as applicable
~/.zwslcore/state/continuous.json
~/.zwslcore/evidence/
~/.zwslcore/cache/
required runtime configuration
Open WebUI persistent volume if user data matters
other Docker state that cannot simply be regenerated
```

Do NOT blindly copy a live SQLite database.

Use a transactionally safe backup mechanism.

Create:

```text
scripts/backup.sh
scripts/restore.sh
```

Backups must include:

```text
manifest
timestamp
source SHA
component versions
checksums
schema versions
```

Secrets must be handled separately and securely.

---

## P0.7 Restore drill

Perform an isolated restore.

Never overwrite live state for the test.

Procedure must:

```text
create backup
restore to isolated temporary paths
open restored SQLite DB
verify tasks/checkpoints
verify continuous ledger
verify evidence checksums
verify cache readability
```

Create machine-readable evidence.

Define RPO/RTO.

Suggested initial workstation targets:

```text
RPO <= 24h
RTO <= 60m
```

If different targets are chosen, document justification.

---

## P0.8 Runtime rollback

Define known-good rollback for:

```text
source commit
Docker images
.env-compatible configuration
state schema
model/runtime changes
```

Create a rollback rehearsal that does not destroy production/user state.

Acceptance:

```text
current → previous known-good → health/smoke PASS → current
```

Record artifact identities.

---

## P0.9 Python dependency reproducibility

Current Provider dependency constraints are not sufficient as immutable transitive identity.

Implement a reproducible dependency strategy.

Prefer:

```text
requirements lock generated from pyproject
exact versions
hash verification
controlled update workflow
```

Do not hand-maintain inconsistent duplicate dependency sources.

CI must detect lock drift.

---

## P0.10 Immutable container identity

Tags alone are not immutable.

For production/release artifacts:

```text
resolve tested image tags to registry digests
record digest manifest
use digest identity in release evidence
```

Developer defaults may remain human-friendly when appropriate, but a production release must have immutable identities.

---

## P0.11 SBOM

Generate SBOM for:

```text
Provider image
repository dependencies
release bundle
```

Use an accepted format:

```text
SPDX JSON
or
CycloneDX JSON
```

Store as CI/release artifact.

Do not commit huge generated SBOMs unless repository policy explicitly chooses to.

---

## P0.12 Container vulnerability scan

Scan the actual built Provider image.

Set explicit failure policy.

At minimum:

```text
CRITICAL => fail
HIGH => fail unless documented accepted risk with owner and expiry
```

Do not hide vulnerabilities by changing severity policy.

---

## P0.13 Provenance and attestation

For release workflow implement:

```text
build provenance
artifact attestation
SBOM attestation where supported
```

Verification instructions must be documented.

Use trusted GitHub workflow permissions with least privilege.

---

## P0.14 Release signing

Implement release signing/verification where practical.

Do not introduce private signing keys into repository secrets if keyless trusted attestation is sufficient.

Document verification.

---

## P0.15 GitHub governance verification

Do not rely solely on repository files.

Verify live GitHub controls:

```text
default branch
required PR
required approvals
CODEOWNERS review
dismiss stale approvals
approval after last push where configured
conversation resolution
required checks
branch up-to-date
force-push disabled
branch deletion disabled
admin enforcement
secret scanning
push protection where supported
Dependabot alerts
private vulnerability reporting
```

Generate governance evidence.

Do not weaken controls to merge.

---

# 8. P1 — RELIABILITY / OPERATIONS

## P1.1 Structured observability

Provider and engineering runtime should emit structured logs.

Minimum common fields:

```text
timestamp
component
request_id
task_id
work_fingerprint
phase
provider
model
attempt
latency_ms
outcome
error_class
```

Never log prompts/secrets by default.

---

## P1.2 Metrics

Expose/collect metrics for:

```text
provider_requests_total
provider_errors_total
provider_latency_seconds
inference_tokens
provider_retries_total
circuit_breaker_state
queue_items
queue_blocked
queue_dead_letter
engineering_runs_total
engineering_success_total
engineering_failure_total
engineering_phase_seconds
engineering_attempts
structured_output_repairs
worktree_syncs
model_selection
model_fallback
evidence_write_failures
```

Prefer Prometheus-compatible metrics.

Keep loopback defaults.

---

## P1.3 SLI/SLO

Define initial workstation SLOs.

Example starting point:

```text
Provider readiness >= 99.5% while workstation runtime is expected online
Smoke inference success >= 99%
No duplicate engineering execution
100% terminal engineering runs produce evidence
100% evidence checksum verification
Recovery from Provider restart <= 5m
```

Adjust based on measured data.

---

## P1.4 Alerts

Alerts must be actionable.

Examples:

```text
Provider unavailable
Ollama unavailable
continuous queue blocked beyond threshold
evidence write failure
disk critical
backup stale
backup verification failed
restore drill failed
security scan critical
```

Avoid notification spam.

---

## P1.5 Disk capacity protection

Monitor:

```text
Docker storage
Ollama model storage
evidence
backups
worktrees
cache
logs
```

Implement thresholds and safe pruning.

Never automatically delete the latest valid backup or required evidence.

---

## P1.6 Evidence retention

Define:

```text
retention days
archive behavior
prune rules
minimum retained successful/failed evidence
checksum validation before archive
```

Provide dry-run.

---

## P1.7 SQLite/ledger schema versioning

Add explicit schema versions/migrations for:

```text
engineering.db
continuous.json
evidence schema
cache envelope where necessary
```

Test upgrade from previous version.

Prefer forward-compatible migrations.

---

## P1.8 Model quality acceptance corpus

Build an in-repo safe synthetic engineering benchmark.

No production secrets.

Representative tasks:

```text
small Python bug
structured output
multi-file change
test repair
path restriction
security-sensitive rejection
no-op avoidance
provider diagnostics
configuration update
```

Measure per model:

```text
success rate
latency
repair rate
regeneration rate
tokens
validation outcome
security outcome
```

Use this evidence in model selection.

---

## P1.9 Models.dev + local model selector

Merge these signals:

```text
local availability
hardware fit
context requirement
structured output support
tool support
reasoning
open weights
cost class
Models.dev metadata
observed benchmark quality
observed latency
```

Hard rule:

```text
local execution inventory is authoritative
Models.dev is advisory
```

A remotely advertised model must never become executable merely because Models.dev lists it.

Keep:

```text
ZERO_COST_ONLY
```

as default.

Recommendation output must explain:

```text
score
eligibility
reasons
blockers
metadata source
benchmark evidence
```

---

## P1.10 Capacity/load/soak

Benchmark CPU_MEDIUM baseline.

Measure:

```text
3B model cold load
3B warm inference
7B cold load
7B warm inference
context 2k/4k
parallel requests
RAM pressure
swap
CPU
disk
time to first token
tokens/sec
Provider overhead
```

Do not set concurrency above safe measured capacity.

Run bounded soak tests.

---

## P1.11 OOM protection

Before model selection/inference, prevent known unsafe allocation.

Use:

```text
available memory
selected model class
context length
estimated KV cache
active inference count
```

Reject/degrade gracefully instead of crashing WSL.

---

## P1.12 Installer lifecycle

Test:

```text
fresh install
rerun install
upgrade from prior config
partial interrupted install
repair
model already present
Docker already present
no network
low disk
uninstall/remove runtime
preserve user data option
```

All mutation must be idempotent where possible.

---

## P1.13 Release workflow

Add trusted release automation.

Required:

```text
SemVer
CHANGELOG
release notes
exact source SHA
image digest
dependency lock identity
SBOM
scan result
provenance
rollback target
known risks
runtime acceptance result
```

Never automatically deploy production merely because release artifact was created.

---

## P1.14 Incident response

Create runbooks for:

```text
Provider down
Ollama down
model corruption
state corruption
queue stuck
disk full
secret exposure
bad release
failed migration
evidence corruption
backup failure
```

Include detection, containment, recovery, verification and escalation.

---

# 9. P2 — OPERATOR EXPERIENCE / EXTENSIBILITY

## P2.1 TUI production operations

Keep TUI read-only by default.

Enhance with:

```text
SLO state
backup freshness
last restore drill
release SHA
runtime versions
disk capacity
dead-letter count
queue leases
model benchmark summary
```

Mutating commands must remain explicit.

---

## P2.2 Local control-plane API

Only if justified.

If implemented:

```text
loopback only by default
authentication
CSRF if browser-facing
bounded request size
audit log
rate limit
no arbitrary shell execution
```

CLI remains supported.

---

## P2.3 Optional vLLM backend

Do not replace Ollama as default.

Enable only when hardware profile supports it.

Acceptance requires real compatible GPU evidence.

Never claim GPU support tested on the CPU-only workstation.

---

## P2.4 GPU acceptance matrix

When hardware becomes available, validate separately:

```text
NVIDIA CUDA
AMD ROCm
multi-GPU if actually required
```

Record:

```text
driver
runtime
VRAM
model
quantization
context
throughput
failure mode
```

---

## P2.5 Model artifact integrity

Track local model identity.

Where available record:

```text
model tag
digest/checksum
size
quantization
source
download date
```

Detect unexpected drift.

Do not assume upstream tag immutability.

---

## P2.6 Offline acceptance

Disconnect external network safely and prove:

```text
Provider
Ollama
LiteLLM
Open WebUI
Engineering Control Plane
evidence
TUI
cached Models.dev metadata
```

continue operating as designed.

Network-only catalog refresh must fail gracefully.

---

# 10. P3 — OPTIONAL FUTURE WORK

Do only after P0/P1 evidence is strong.

Possible work:

```text
web dashboard
remote worker protocol
multi-host scheduling
k3s production profile
MCP/tool registry
plugin architecture
organization policy packs
documentation site
benchmark dashboard
remote model fleet
```

Do not introduce distributed complexity into the default workstation architecture prematurely.

---

# 11. VALIDATION MATRIX

For every implementation wave run the smallest relevant set first, then broader validation.

Core baseline:

```bash
python3 -m unittest discover -s tests -v
make ci
```

Repository validation:

```bash
python3 scripts/validate_repo.py
```

Compose:

```bash
docker compose --env-file .env config --quiet
```

Provider build:

```bash
docker compose --env-file .env build provider
```

Runtime:

```bash
make wait-runtime
make doctor
make smoke
```

PowerShell target-host verification:

```powershell
.\scripts\doctor-wsl.ps1 -Smoke
```

Engineering state:

```bash
python3 scripts/engineer.py reconcile
python3 scripts/engineer.py list
python3 scripts/engineer.py work-list
```

Blocked recovery:

```bash
python3 scripts/engineer.py recover --max-iterations 4
```

Evidence:

```bash
python3 scripts/engineer.py evidence TASK_ID
python3 scripts/engineer.py evidence-verify TASK_ID
```

Models metadata:

```bash
make models-dev-stats
python3 scripts/models-dev.py recommend --structured-output --min-context 4096
```

Do not call a gate verified if its exact runtime test was not executed.

---

# 12. SECURITY TESTING

Required checks should include as applicable:

```text
CodeQL
Dependency Review
Dependabot
secret scanning
push protection
container vulnerability scanning
SBOM
dependency lock verification
GitHub Actions pinning
least-privilege permissions
Docker hardening
loopback binding
Provider authentication
rate limiting
concurrency limiting
trusted proxy handling
request-size limits
path traversal tests
secret path tests
structured-output validation
arbitrary command prevention
```

Model output is untrusted input.

Never give the model arbitrary shell execution.

Validator commands must remain operator-defined.

---

# 13. ENGINEERING CONTROL PLANE INVARIANTS

These invariants may not be weakened.

## Isolation

```text
agent changes only occur in zwslcore-managed worktrees
```

## Scope

```text
--allow-path is an enforcement boundary
```

## Secrets

```text
secret-bearing paths are excluded
```

## Validation

```text
strict remains default
delta requires explicit selection
```

## Security

```text
blocking deterministic findings fail closed
```

## Git

```text
no remote push by EngineeringRuntime
```

## Attempts

```text
real engineering failure consumes budget
infrastructure-only transient failure does not
max iterations still bounds retries
```

## Resume

```text
stale worktree reconciles to current source HEAD
PLAN reuse requires matching baseline HEAD
validation and review always rerun
```

## Evidence

```text
terminal runs produce secret-minimized integrity-verifiable evidence
```

---

# 14. AUTONOMOUS EXECUTION STRATEGY

Work in waves.

## Wave A — Immediate closure

```text
reconcile queue
recover current blocked task
verify real engineering success
verify evidence
```

Do not begin broad refactors until the current E2E loop has a successful acceptance run.

## Wave B — P0 operations

Implement:

```text
queue lease
dead letter lifecycle
backup
restore drill
rollback
dependency lock
SBOM
container scan
provenance
release identity
governance evidence
```

## Wave C — P1 reliability

Implement:

```text
metrics
logs
SLO
alerts
chaos tests
capacity
OOM protection
retention
state migrations
model quality corpus
```

## Wave D — release-grade automation

Implement:

```text
trusted release workflow
versioning
artifact manifest
release evidence
rollback evidence
```

## Wave E — P2/P3

Only after P0/P1 readiness matrix has no unjustified blockers.

---

# 15. PR EXECUTION CONTRACT

For every material change:

1. Inspect exact current state.
2. Record baseline.
3. Identify one root cause/gate.
4. Create a focused branch.
5. Implement minimal safe change.
6. Add regression tests.
7. Update documentation.
8. Run targeted validation.
9. Open PR.
10. Inspect latest-head checks.
11. Fix failures rather than bypassing them.
12. Merge only after required checks pass.
13. Record merge SHA/evidence.
14. Re-read `main`.
15. Continue to next gate.

Do not ask the operator to manually perform work that can safely be automated inside the repository.

Do not stop simply because one PR merged if the defined wave still contains executable tasks.

---

# 16. PRODUCTION READINESS MATRIX

Maintain at minimum these rows:

```text
GOV-01 branch protection
GOV-02 CODEOWNERS
GOV-03 required checks
GOV-04 force push/deletion protection

SEC-01 secret scanning
SEC-02 push protection
SEC-03 dependency scanning
SEC-04 SAST
SEC-05 container scan
SEC-06 runtime auth
SEC-07 network exposure
SEC-08 secret rotation
SEC-09 least privilege

SC-01 dependency lock
SC-02 immutable images
SC-03 SBOM
SC-04 provenance
SC-05 signing/attestation

REL-01 cold start
REL-02 restart recovery
REL-03 transient network reset
REL-04 queue correctness
REL-05 duplicate runner prevention
REL-06 resource exhaustion
REL-07 soak test

DATA-01 SQLite backup
DATA-02 ledger backup
DATA-03 evidence backup
DATA-04 isolated restore
DATA-05 schema migration
DATA-06 RPO
DATA-07 RTO

ENG-01 REPAIR E2E
ENG-02 UPDATE E2E
ENG-03 IMPLEMENT_FEATURE E2E
ENG-04 structured output
ENG-05 scope enforcement
ENG-06 validation
ENG-07 security gate
ENG-08 evidence integrity
ENG-09 resume
ENG-10 stale-worktree reconciliation
ENG-11 recovery
ENG-12 dead-letter handling

MODEL-01 local model inventory
MODEL-02 deterministic selector
MODEL-03 Models.dev metadata
MODEL-04 hardware fit
MODEL-05 benchmark quality
MODEL-06 model integrity

OBS-01 structured logs
OBS-02 metrics
OBS-03 SLI
OBS-04 SLO
OBS-05 alerting

OPS-01 install
OPS-02 upgrade
OPS-03 repair
OPS-04 rollback
OPS-05 backup
OPS-06 restore
OPS-07 incident runbook

RELSE-01 SemVer
RELSE-02 CHANGELOG
RELSE-03 artifact manifest
RELSE-04 release workflow
RELSE-05 release smoke
RELSE-06 rollback target
```

---

# 17. DEFINITION OF PRODUCTION-GRADE READY

Do NOT declare `PRODUCTION READY` until:

```text
all applicable P0 readiness gates = VERIFIED
no critical/high unresolved security defect without explicit documented risk decision
real target-host runtime acceptance = VERIFIED
real autonomous engineering E2E = VERIFIED
backup = VERIFIED
isolated restore = VERIFIED
rollback = VERIFIED
release artifact identity = VERIFIED
required GitHub governance = VERIFIED
observability for critical failure paths = VERIFIED
operator runbooks exist
remaining PARTIALLY VERIFIED / UNVERIFIED / BLOCKED states are clearly listed
```

P1 gaps may remain only when explicitly classified and they do not invalidate an applicable production gate.

---

# 18. FINAL REPORT FORMAT

At the end of every execution wave output:

## Baseline

```text
starting SHA
branch
target hardware
runtime state
queue state
known blockers
```

## Changes

```text
PR
commits
files
behavior
```

## Validation

For every command:

```text
command
environment
result
evidence
```

## Security

```text
CodeQL
dependency review
secret scan
container scan
SBOM
provenance
```

## Runtime

```text
doctor
smoke
structured inference
cold start
recovery tests
```

## Data recovery

```text
backup
restore
RPO
RTO
rollback
```

## Readiness

Report counts:

```text
VERIFIED
PARTIALLY VERIFIED
UNVERIFIED
BLOCKED
NOT APPLICABLE
```

## Blockers

For each blocker:

```text
exact blocker
evidence
owner/action needed
safe next step
```

## Current production verdict

Exactly one of:

```text
PRODUCTION READY
PRODUCTION READY WITH ACCEPTED RISK
NOT PRODUCTION READY
```

Never use the first two without direct evidence.

---

# 19. FIRST EXECUTION NOW

Start immediately with:

```bash
git checkout main
git pull --ff-only
git status --short
git rev-parse HEAD

python3 scripts/engineer.py reconcile
python3 scripts/engineer.py work-list
python3 scripts/engineer.py list
```

Verify runtime:

```bash
make wait-runtime
make doctor
make smoke
```

Then attempt controlled recovery:

```bash
python3 scripts/engineer.py recover --max-iterations 4
```

Inspect:

```bash
python3 scripts/engineer.py work-status 40780a4e4234 || true
python3 scripts/engineer.py evidence-verify work_40780a4e4234bed9c2f7 || true
```

If the task still blocks:

- determine the precise current root cause;
- do not blindly increase retry limits;
- classify whether it is infrastructure, model quality, scope, validation, security, state drift, or operator configuration;
- implement the smallest safe systemic fix;
- add regression coverage;
- merge through required checks;
- rerun real-host acceptance.

After the current blocked engineering E2E is resolved, proceed through P0 gates in this SSOT in priority order.

Continue until no safely executable P0/P1 repository work remains.

Do not stop at planning when implementation and validation are possible.

Do not claim production readiness without the evidence defined above.
