from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Any

from .ledger import JsonContinuousLedger
from .loop import ContinuousEngineeringLoop, LoopPolicy, LoopResult, WorkItem
from .models import EngineeringTask, TaskRisk, TaskStatus
from .runtime import EngineeringRuntime, ProviderTransportError
from .store import SQLiteEngineeringStore


@dataclass
class ExecutionResult:
    passed: bool
    task: EngineeringTask
    error: str = ""
    consume_attempt: bool = True


class ContinuousEngineeringRunner:
    """Durable adapter from WorkItem queue to the bounded engineering runtime."""

    def __init__(
        self,
        store: SQLiteEngineeringStore,
        ledger: JsonContinuousLedger,
        runtime: EngineeringRuntime,
        *,
        progress: Callable[[str], None] | None = None,
    ) -> None:
        self.store = store
        self.ledger = ledger
        self.runtime = runtime
        self.progress = progress or (lambda message: None)

    def add(self, item: WorkItem) -> dict[str, Any]:
        return self.ledger.register(item)

    def run(
        self,
        *,
        max_iterations: int = 12,
        retry_blocked: bool = False,
    ) -> LoopResult:
        seed = self.ledger.pending(retry_blocked=retry_blocked)
        reset_once: set[str] = set()
        self.progress(f"[continuous] pending={len(seed)} max_iterations={max_iterations} retry_blocked={retry_blocked}")

        def implement(item: WorkItem) -> ExecutionResult:
            record = self.ledger.register(item)
            self.progress(
                f"[continuous] START kind={item.kind.value} priority={item.priority} "
                f"attempt={int(record.get('attempts', 0)) + 1}/{int(record.get('max_attempts', item.max_attempts))} "
                f"title={item.title}"
            )
            task_id = record.get("task_id") or f"work_{item.fingerprint[:20]}"
            task = self.store.get_task(task_id)
            payload = item.payload

            if retry_blocked and item.fingerprint not in reset_once and task is not None and (
                task.status in {TaskStatus.BLOCKED, TaskStatus.FAILED}
                or task.attempts >= task.max_attempts
            ):
                if task.worktree_path:
                    self.runtime.worktrees.reset(task.worktree_path)
                task.attempts = 0
                task.max_attempts = max(1, int(record.get("max_attempts", item.max_attempts)))
                task.status = TaskStatus.CREATED
                task.last_error = ""
                self.store.save_task(task)
                reset_once.add(item.fingerprint)
                self.progress(
                    f"[continuous] RESET task={task.id} attempts=0/{task.max_attempts} "
                    f"worktree={'reset' if task.worktree_path else 'none'}"
                )

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
                task_id=task.id,
            )
            before_attempts = task.attempts
            try:
                completed = self.runtime.run(
                    task,
                    validators=list(payload.get("validators") or ["git diff --check"]),
                    allowed_paths=set(payload.get("allowed_paths") or ()) or None,
                    commit=bool(payload.get("commit", False)),
                    resume=self.store.latest_checkpoint(task.id, "PLAN") is not None,
                    validation_mode=str(payload.get("validation_mode", "strict")),
                )
                consumed = completed.attempts > before_attempts
                if consumed:
                    self.ledger.update(
                        item.fingerprint,
                        attempts=int(record.get("attempts", 0)) + 1,
                    )
                self.progress(f"[continuous] task={completed.id} status={completed.status.value}")
                return ExecutionResult(
                    passed=completed.status == TaskStatus.SUCCEEDED,
                    task=completed,
                    error=completed.last_error,
                    consume_attempt=consumed,
                )
            except ProviderTransportError as exc:
                latest = self.store.get_task(task.id) or task
                self.progress(
                    f"[continuous] INFRA_RETRY task={task.id} error={str(exc)[:500]}"
                )
                self.ledger.update(
                    item.fingerprint,
                    state="PENDING",
                    last_error=str(exc)[:2000],
                )
                return ExecutionResult(
                    False,
                    latest,
                    str(exc),
                    consume_attempt=False,
                )
            except Exception as exc:
                latest = self.store.get_task(task.id) or task
                consumed = latest.attempts > before_attempts
                updates = {"last_error": str(exc)[:2000]}
                if consumed:
                    updates["attempts"] = int(record.get("attempts", 0)) + 1
                self.progress(f"[continuous] task={task.id} error={str(exc)[:500]}")
                self.ledger.update(item.fingerprint, **updates)
                return ExecutionResult(False, latest, str(exc), consume_attempt=consumed)

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
            self.progress(
                f"[continuous] CHECKPOINT state={durable_state} "
                f"attempt={value['attempt']} title={value['title']}"
            )
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
