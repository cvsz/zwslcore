# Engineering undo and redo

zwslcore captures a reversible local patch after a non-commit engineering task passes validation and the security gate.

## Storage

Snapshots live outside the repository:

    ~/.zwslcore/snapshots/TASK_ID/
      change.patch
      snapshot.json

The metadata records:

- task ID;
- worktree HEAD;
- SHA-256 of the patch;
- patch byte size;
- capture timestamp;
- state: applied or undone.

Patch size is bounded to 8 MiB.

## Commands

    python3 scripts/engineer.py snapshot-status TASK_ID
    python3 scripts/engineer.py undo TASK_ID
    python3 scripts/engineer.py redo TASK_ID

## Safety rules

Undo and redo are intentionally fail-closed.

Undo requires:

1. the task path to be a zwslcore-managed worktree;
2. current HEAD to equal the snapshot HEAD;
3. the current working patch hash to equal the stored patch hash.

Undo then resets/cleans only that managed worktree.

Redo requires:

1. the same managed worktree and HEAD;
2. snapshot state to be `undone`;
3. a clean working tree.

The stored binary patch is then applied and the resulting patch hash is verified. If verification fails, the worktree is reset to clean HEAD.

Tracked and ordinary untracked files are included. Ignored files remain outside the snapshot.

## Commit-mode runs

When `--commit` is requested, zwslcore does not create a working-tree undo snapshot. The local Git commit is already the durable revision boundary and can be handled with normal Git history operations.

## Relation to OpenCode

This capability is inspired by OpenCode's snapshot/revert architecture, but uses zwslcore's existing managed Git worktrees and an independent Python implementation. No OpenCode snapshot storage or runtime dependency is used.
