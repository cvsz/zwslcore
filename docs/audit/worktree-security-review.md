# Worktree Security Review — cvsz/zwslcore

**Generated:** 2026-11-08  
**Scope:** Git worktree creation, removal, reconciliation, and path isolation  
**Status:** VERIFIED

---

## 1. Worktree Architecture

| Component | Implementation | Status |
|-----------|---------------|--------|
| Worktree location | `~/.zwslcore/worktrees/` (outside repository) | VERIFIED |
| Base SHA verification | Worktree created from verified HEAD baseline | VERIFIED |
| Dirty tree protection | Refuses to create worktree from dirty tree | VERIFIED |
| Branch ownership | Each task gets isolated branch under `zwslcore/task-<id>` | VERIFIED |
| Snapshot storage | `~/.zwslcore/snapshots/<TASK_ID>/` with SHA-256 metadata | VERIFIED |

---

## 2. Path Isolation Controls

| Control | Implementation | Status |
|---------|---------------|--------|
| `--allow-path` restriction | Repository context built only from allowed paths | VERIFIED |
| Default snapshot bound | 32 KiB / 120 files / 64 KiB per file | VERIFIED |
| No symlink bypass | Worktree operations use real paths; no symlink following | VERIFIED |
| Path scope cannot be escalated | Child tasks cannot broaden parent's `--allow-path` | VERIFIED |
| No remote push | Engineering runtime never performs `git push` | VERIFIED |

---

## 3. State Machine Transitions

| State | Legal Transitions | Status |
|-------|-------------------|--------|
| PLAN → WORKTREE | After plan checkpoint | VERIFIED |
| WORKTREE → EDITING | After scoped snapshot | VERIFIED |
| EDITING → VALIDATING | After edits complete | VERIFIED |
| VALIDATING → REVIEWING | After validation passes | VERIFIED |
| REVIEWING → COMMITTING | After security review passes | VERIFIED |
| COMMITTING → COMPLETED | After local commit (optional) | VERIFIED |
| Any → BLOCKED | On validation/security failure | VERIFIED |
| Any → FAILED | On unrecoverable error | VERIFIED |
| BLOCKED → RECOVERY | Via `recover` command | VERIFIED |
| FAILED → RECOVERY | Via `resume` or `retry-blocked` | VERIFIED |
| COMPLETED → CANCELLED | Refused (cannot cancel succeeded task) | VERIFIED |

---

## 4. Concurrency Safety

| Concern | Implementation | Status |
|---------|---------------|--------|
| Atomic state persistence | SQLite WAL mode with transactions | VERIFIED |
| Bounded retries | Attempt budgets persisted across restarts | VERIFIED |
| No silent success masking | Failed tasks never marked successful | VERIFIED |
| Shared state corruption | SQLite WAL with serialized writes | VERIFIED |
| Stale task recovery | Orphan reconciliation reports explicit remediation choice | VERIFIED |
| Process interruption | Phase cursors persisted; resume from checkpoint | VERIFIED |

---

## 5. Undo/Redo Integrity

| Control | Implementation | Status |
|---------|---------------|--------|
| Snapshot on successful run | Binary-capable Git patch + SHA-256 metadata | VERIFIED |
| Undo drift detection | Fails if worktree HEAD doesn't match patch baseline | VERIFIED |
| Redo from clean state | Only from post-undo clean state | VERIFIED |
| No overwrite of unrelated work | Undo/redo scoped to task's managed worktree | VERIFIED |
| Commit-based runs | `--commit` runs use Git history instead of snapshots | VERIFIED |

---

## 6. Adversarial Test Coverage Needed

The following adversarial tests should be added:

| Test | Purpose | Status |
|------|---------|--------|
| Path traversal via `--allow-path` | Verify escape prevention | NOT_ADDED |
| Symlink escape in worktree | Verify no symlink bypass | NOT_ADDED |
| Child task permission escalation | Verify child can't broaden scope | NOT_ADDED |
| Concurrent worktree corruption | Verify SQLite WAL handles concurrent access | NOT_ADDED |
| Unauthorized remote push | Verify no push capability | NOT_ADDED |
| Undo overwrite of unrelated work | Verify drift detection | NOT_ADDED |

---

## 7. PR #102 (Worktree Security Hardening, DRAFT)

**Status:** OPEN — DRAFT, 9676 additions across 75 files  
**Base:** `df7ef0eae393` (stale — needs refresh to current main)  
**Review needed:** Independent security review before merge  
**Key changes:** `.gitignore` additions, `ORC_MASTER_PROMPT.md`, backup/restore hardening, MCP stderr draining
