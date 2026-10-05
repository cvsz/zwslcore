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

By default `ZEAZ_ENGINEERING_MODEL=auto`. Before constructing the Provider client, the control plane ranks the configured local aliases by hardware fit, zero-cost class, context capacity and structured-output support. On CPU-constrained hosts this normally selects `zeaz-fast`; higher-memory/GPU hosts may prefer a larger local alias. Set `ZEAZ_ENGINEERING_MODEL` to an explicit Provider alias to override automatic selection.


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

Only one task executor may use the same engineering database or queue ledger at a time, including direct `run`, `resume`, continuous, and recovery commands. The executor takes non-blocking OS locks for both state paths and stores its owner ID, fencing generation, acquisition time, heartbeat, expiry, and release/reclaim state in SQLite. A second process exits with the current lease owner details. If a process crashes, the OS releases its locks; the next process can reclaim the persisted lease and advances the fencing generation. Lock files are coordination files; do not delete them to cancel a running job.

Continuous retries reset only zwslcore-managed worktrees before the next attempt. Remote push is never performed by the engineering runtime.

### Queue lifecycle

The queue lifecycle commands operate on a full fingerprint or an unambiguous fingerprint prefix:

    python3 scripts/engineer.py work-cancel FINGERPRINT --reason "no longer needed"
    python3 scripts/engineer.py work-retry FINGERPRINT --reason "corrected the reported failure"
    python3 scripts/engineer.py work-quarantine FINGERPRINT --reason "needs manual review"
    python3 scripts/engineer.py work-dead-letter FINGERPRINT --reason "automatic recovery is exhausted"
    python3 scripts/engineer.py work-requeue FINGERPRINT --reason "approved another bounded attempt round"
    python3 scripts/engineer.py work-archive FINGERPRINT

`work-retry` accepts only blocked or exhausted work. It starts a new attempt round, preserves earlier attempt history and resets a linked failed task immediately before execution. `work-requeue` accepts quarantined or dead-letter work and also preserves the previous failure record. A dead-letter record retains the fingerprint, task ID, failure reason, attempts, model history, evidence path and timestamps. It cannot be archived until that record is complete. `work-list --include-archived` and `work-status FINGERPRINT` can inspect archived records. The read-only TUI displays active `QUARANTINED` and `DEAD_LETTER` entries without scheduling them.

Queue lifecycle mutations, reconciliation apply, and task cancellation use the same exclusive runner locks as continuous execution. They fail closed while a queue runner owns either the engineering database or the queue ledger. Use `work-add` to append work while a run is active; the new item will be picked up by the next bounded run.

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


## Resumable phase cursor

Each checkpoint updates task metadata with:

- phase_cursor
- phase_checkpoint_id
- baseline_head
- run_config

Resume a blocked or failed task:

    python3 scripts/engineer.py resume TASK_ID

The resume path is deliberately conservative:

1. provider preflight still runs;
2. the managed worktree is reset to clean HEAD;
3. the current HEAD is compared with the HEAD stored in the PLAN checkpoint;
4. the prior plan is reused only when those HEAD values match;
5. EDITING, VALIDATING and REVIEWING always run again;
6. if HEAD changed, the runtime performs a fresh planning call.

Resume history is retained in task metadata before the attempt budget is reset. A succeeded task cannot be resumed through this command.


## Validation profiles

The default validation mode is strict:

    python3 scripts/engineer.py run TASK_ID --validation-mode strict --validate "python3 -m unittest discover -s tests -v"

Strict mode blocks when any final validator returns non-zero.

For repositories with known pre-existing failures, delta mode is explicit opt-in:

    python3 scripts/engineer.py run TASK_ID --validation-mode delta --validate "python3 -m unittest discover -s tests -v"

Delta mode:

1. runs the same validator list on the clean managed worktree before planning/editing;
2. stores a BASELINE_VALIDATION checkpoint;
3. runs the validators again after model edits;
4. blocks any command that changed from exit code 0 to non-zero;
5. records pre-existing failures that remain failing as residual_failures;
6. records pre-existing failures that become green as improvements.

Delta mode never changes path validation, static review, secret checks or the security gate. Resume and continuous-work records persist the selected validation mode in run_config.


## Stale worktree reconciliation

A resumed/continuous task never assumes that its managed worktree still matches the current source checkout.

Before resume, the runtime:

1. verifies the managed-worktree ownership marker;
2. records the previous task worktree HEAD;
3. reads the current source repository HEAD;
4. hard-resets and cleans the managed worktree to that source HEAD;
5. records both revisions in task metadata;
6. reuses a PLAN checkpoint only when its baseline HEAD matches the reconciled HEAD.

This prevents long-lived blocked tasks from repeatedly planning against obsolete repository snapshots after main has advanced.


## Terminal UI

The engineering CLI includes a zero-dependency, read-only terminal dashboard:

    python3 scripts/engineer.py tui

From Windows PowerShell:

    .\scripts\engineer-wsl.ps1 tui

Options:

    --interval SECONDS
    --limit N
    --once
    --no-color

The dashboard auto-refreshes and displays:

- current hardware profile and accelerator backend;
- configured/automatically selected engineering model alias;
- queue counts and per-item state;
- attempt budget progress;
- current phase cursor;
- recent task status and evidence availability;
- current runtime quantization/context/Flash Attention policy.

The TUI never executes or mutates tasks. Ctrl+C exits cleanly. Use `--once --no-color` for logs, CI captures or non-interactive terminals.


## Adaptive recovery

Blocked queue items can be recovered with:

    python3 scripts/engineer.py recover --max-iterations 4

The recovery command is equivalent to a bounded continuous run with blocked-item retry enabled, plus the runtime's adaptive inference policy.

For auto-selected local engineering models:

- context 4096 -> snapshot budget 8192 bytes
- context 8192 -> snapshot budget 16384 bytes
- context 16384+ -> snapshot budget capped at 32768 bytes

Repository snapshot ordering uses meaningful words from the task title and description as path-priority hints. For example, a task named "Improve provider diagnostics" prioritizes paths containing provider or diagnostics before unrelated files.

On CPU_MEDIUM with at least 10 GiB available RAM, the model ladder normally starts:

    zeaz-fast -> zeaz-coder

The first model remains the low-latency path. A consumed attempt promotes to the next model only for model-quality errors such as malformed structured edits, empty/no-op edits or out-of-scope edit generation. Transport, validation and security failures do not trigger promotion.

CPU_SMALL filters out local aliases with a negative hardware-fit score, so recovery does not force a model that is too large for the detected machine.

The active model, model ladder, snapshot budget and any model escalation are persisted in task metadata and therefore appear in durable evidence.


## Queue reconciliation

The continuous ledger and SQLite task store are reconciled before recovery.

Inspect drift:

    python3 scripts/engineer.py reconcile

Apply only deterministic safe fixes:

    python3 scripts/engineer.py reconcile --apply

Safe fixes include:

- ledger references to missing tasks -> clear link and return work to PENDING;
- SUCCEEDED task with stale non-succeeded ledger state -> mark ledger SUCCEEDED;
- terminal failed/blocked task left as RUNNING -> mark ledger BLOCKED;
- CREATED task left as RUNNING -> return ledger to PENDING;
- terminal task/ledger attempt-count drift -> synchronize ledger attempts.

Non-terminal tasks that are not linked from any work item are reported as orphan tasks and are not auto-enqueued because their validator/scope intent cannot be inferred safely.

Explicitly enqueue an existing task:

    python3 scripts/engineer.py enqueue-task TASK_ID --kind REPAIR --priority 90 --allow-path services

The command reuses persisted run_config when available and otherwise defaults to git diff --check, strict validation and no commit.

The `recover` command applies safe reconciliation before processing blocked work. The TUI surfaces drift and orphan tasks with actionable commands.


## Persistent recovery model cursor

Adaptive model escalation is task-scoped and durable.

When a model-quality failure promotes a task from one local alias to the next alias in the configured model ladder, the runtime records:

- `model_escalated_to`;
- `model_current`;
- bounded `model_escalation_history`;
- the model-selection source for the next run.

A later process invocation restores that task to its persisted recovery alias when the alias is still present in the current hardware-safe ladder. Fresh tasks always start from the current default selector result and never inherit another task's promoted model.

When a task succeeds, the runtime records `model_working` and `model_last_success_at`. The TUI displays the task-specific recovery/working model so the queue view distinguishes the global default model from the model actually being used to recover a blocked task.


## Orphan task lifecycle

Reconciliation treats a nonterminal SQLite task without a linked continuous-work record as an orphan. Orphans are reported but are not modified automatically because intent cannot be inferred safely.

Resolve an orphan explicitly by either enqueueing it:

    python3 scripts/engineer.py enqueue-task TASK_ID --kind REPAIR

or cancelling it:

    python3 scripts/engineer.py cancel TASK_ID --reason "no longer required"

Cancellation is idempotent for already-cancelled tasks, refuses succeeded tasks, writes a CANCELLED checkpoint, updates linked ledger records to CANCELLED, records cancellation history, and writes a fresh evidence bundle.
