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

By default the control plane uses the local provider alias zeaz-local. Override by setting ZEAZ_ENGINEERING_MODEL in .env.
