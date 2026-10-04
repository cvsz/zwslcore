# Engineering Control Plane

zwslcore includes a self-contained local engineering runtime refactored from proven patterns in cvsz/zcoder. It does not import or clone zcoder at runtime.

## Safety defaults

- SQLite WAL durable task/checkpoint state
- isolated Git worktrees under ~/.zwslcore/worktrees
- bounded secret-aware repository snapshots
- provider-driven planning/editing through local zwslcore Provider
- path traversal and secret-bearing path rejection
- operator-supplied validation commands only
- deterministic static review and fail-closed security gate
- local-only by default; no remote push is performed
- bounded continuous UPGRADE / UPDATE / IMPLEMENT_FEATURE / REPAIR loop

## CLI

Create a task:

    python3 scripts/engineer.py create "Fix health check" --description "Repair readiness behavior" --repository .

List tasks:

    python3 scripts/engineer.py list

Inspect durable state:

    python3 scripts/engineer.py show TASK_ID

Run in an isolated worktree:

    python3 scripts/engineer.py run TASK_ID --allow-path services --validate "python3 -m unittest discover -s tests -v"

Create a local commit only after validation and security review:

    python3 scripts/engineer.py run TASK_ID --allow-path services --validate "python3 -m unittest discover -s tests -v" --commit

The runtime never pushes a remote branch. Push/PR orchestration remains a separate explicit operator step.

## State

Default durable state:

    ~/.zwslcore/state/engineering.db

Managed worktrees:

    ~/.zwslcore/worktrees/

## Model

By default the control plane uses the CPU-friendly local provider alias zeaz-fast. Override by setting ZEAZ_ENGINEERING_MODEL in .env. The larger zeaz-coder and zeaz-local aliases remain available when quality is preferred over latency.


## Hardware profile

Inspect the current WSL hardware and model recommendations:

    python3 scripts/engineer.py profile

The profile records OS/architecture, logical CPU count, total/available RAM, detected GPU text and a deterministic CPU/GPU profile. Model recommendations follow the same RAM thresholds used by the installer.

## Durable continuous work

Queue a work item:

    python3 scripts/engineer.py work-add "Repair provider" --kind REPAIR --description "Repair provider behavior" --repository . --priority 80 --allow-path services --validate "python3 -m unittest discover -s tests -v"

Inspect the queue:

    python3 scripts/engineer.py work-list

Run bounded work:

    python3 scripts/engineer.py continuous --max-iterations 4

The durable JSON ledger lives at ~/.zwslcore/state/continuous.json. Completed fingerprints are not repeated. Consumed attempts survive process restarts. Blocked work requires explicit --retry-blocked to reset its budget.

Continuous retries reset only zwslcore-managed worktrees before the next attempt. Remote push is never performed by the engineering runtime.

## Provider cost policy

Every provider has a cost class:

- FREE_LOCAL
- FREE_REMOTE
- CUSTOMER_KEY
- PAID_PLATFORM
- UNKNOWN

ZEAZ_COST_POLICY controls routing:

- ZERO_COST_ONLY is the default and blocks paid/unknown routes.
- PREFER_ZERO_COST ranks free routes first.
- PERMIT_PAID permits configured routes regardless of class.

A provider being configured is therefore not sufficient to make it eligible for routing; it must also satisfy the active cost policy.


## Live progress and status

Engineering runs emit progress immediately to the operator console, including task ID, worktree, attempt, planning model, snapshot byte size, validation, security gate and completion/failure state.

Inspect a durable work item while another terminal is running it:

    python3 scripts/engineer.py work-status FINGERPRINT_PREFIX

The status output includes the continuous ledger record, linked EngineeringTask and latest task checkpoint.

## Local model context budget

The local engineering snapshot defaults to:

- 120 files maximum
- 64 KiB per file
- 32 KiB total text context

When --allow-path is supplied, the snapshot is restricted to those declared paths. This keeps local CPU inference bounded and prevents unrelated repository content from dominating the prompt.


## Durable evidence bundles

Every EngineeringRuntime completion path attempts to write a secret-minimized evidence bundle:

    ~/.zwslcore/evidence/TASK_ID/evidence.json
    ~/.zwslcore/evidence/TASK_ID/evidence.sha256

Commands:

    python3 scripts/engineer.py evidence TASK_ID
    python3 scripts/engineer.py evidence-show TASK_ID
    python3 scripts/engineer.py evidence-verify TASK_ID

The bundle contains:

- task ID, risk, final status, attempts and branch/worktree metadata
- ordered checkpoint chronology
- validation commands, return codes and SHA-256 hashes of stdout/stderr
- deterministic review findings without raw diff content
- Git HEAD, branch, changed paths, diff byte count and diff SHA-256
- a sidecar SHA-256 checksum for tamper detection

Raw validator stdout/stderr and raw Git diff are intentionally excluded by default to reduce accidental secret retention. Common API-key/token patterns in final error summaries are redacted.
