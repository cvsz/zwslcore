from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .ledger import JsonContinuousLedger
from .loop import ContinuousEngineeringLoop, LoopPolicy, LoopResult, WorkItem
from .models import EngineeringTask, TaskRisk, TaskStatus
from .runtime import EngineeringRuntime
from .store import SQLiteEngineeringStore


@dataclass
class ExecutionResult:
    passed: bool
    task: EngineeringTask
    error: str = ""


class ContinuousEngineeringRunner:
    """Durable adapter from WorkItem queue to the bounded engineering runtime."""

    def __init__(
        self,
        store: SQLiteEngineeringStore,
        ledger: JsonContinuousLedger,
        runtime: EngineeringRuntime,
    ) -> None:
        self.store = store
        self.ledger = ledger
        self.runtime = runtime

    def add(self, item: WorkItem) -> dict[str, Any]:
        return self.ledger.register(item)

    def run(
        self,
        *,
        max_iterations: int = 12,
        retry_blocked: bool = False,
    ) -> LoopResult:
        seed = self.ledger.pending(retry_blocked=retry_blocked)

        def implement(item: WorkItem) -> ExecutionResult:
            record = self.ledger.register(item)
            task_id = record.get("task_id") or f"work_{item.fingerprint[:20]}"
            task = self.store.get_task(task_id)
            payload = item.payload
            if task is None:
                task = EngineeringTask(
                    id=task_id,
                    title=item.title,
                    description=str(payload.get("description", "")),
                    repository=str(Path(payload.get("repository", ".")).resolve()),
                    risk=TaskRisk(str(payload.get("risk", "medium")).lower()),
                    max_attempts=max(1, item.max_attempts),
                )
                self.store.save_task(task)
            self.ledger.update(
                item.fingerprint,
                state="RUNNING",
                attempts=int(record.get("attempts", 0)) + 1,
                task_id=task.id,
            )
            try:
                completed = self.runtime.run(
                    task,
                    validators=list(payload.get("validators") or ["git diff --check"]),
                    allowed_paths=set(payload.get("allowed_paths") or ()) or None,
                    commit=bool(payload.get("commit", False)),
                )
                return ExecutionResult(
                    passed=completed.status == TaskStatus.SUCCEEDED,
                    task=completed,
                    error=completed.last_error,
                )
            except Exception as exc:
                latest = self.store.get_task(task.id) or task
                self.ledger.update(item.fingerprint, last_error=str(exc)[:2000])
                return ExecutionResult(False, latest, str(exc))

        def validate(item: WorkItem, result: ExecutionResult) -> tuple[bool, tuple[str, ...]]:
            return result.passed, ()

        def rollback(item: WorkItem, result: ExecutionResult) -> None:
            if result.task.worktree_path:
                self.runtime.worktrees.reset(result.task.worktree_path)

        def checkpoint(value: dict[str, Any]) -> None:
            state = value["state"]
            if state == "SUCCEEDED":
                durable_state = "SUCCEEDED"
            elif state.startswith("BLOCKED"):
                durable_state = "BLOCKED"
            else:
                durable_state = "PENDING"
            self.ledger.update(
                value["item_id"],
                state=durable_state,
                last_checkpoint=value,
            )

        loop = ContinuousEngineeringLoop(
            implement,
            validate,
            rollback=rollback,
            checkpoint=checkpoint,
            policy=LoopPolicy(max_iterations=max_iterations),
        )
        return loop.run(seed)


def stable_work_id(title: str, kind: str, payload: dict[str, Any]) -> str:
    raw = f"{kind}\n{title}\n{payload}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()
