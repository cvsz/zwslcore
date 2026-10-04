from __future__ import annotations

import dataclasses
from typing import Any

from .ledger import JsonContinuousLedger
from .models import EngineeringTask, TaskStatus
from .store import SQLiteEngineeringStore


TERMINAL_BLOCKED = {TaskStatus.BLOCKED, TaskStatus.FAILED}
TERMINAL_DONE = {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}


@dataclasses.dataclass(frozen=True)
class ReconcileFinding:
    kind: str
    fingerprint: str = ""
    task_id: str = ""
    detail: str = ""
    safe_fix: bool = False
    remediation: str = ""


@dataclasses.dataclass(frozen=True)
class ReconcileReport:
    findings: tuple[ReconcileFinding, ...]
    applied: tuple[ReconcileFinding, ...]
    orphan_tasks: tuple[str, ...]


class QueueReconciler:
    """Reconcile durable work ledger state with SQLite engineering tasks."""

    def __init__(
        self,
        store: SQLiteEngineeringStore,
        ledger: JsonContinuousLedger,
    ) -> None:
        self.store = store
        self.ledger = ledger

    def inspect(self) -> ReconcileReport:
        records = self.ledger.records()
        tasks = {task.id: task for task in self.store.list_tasks()}
        findings: list[ReconcileFinding] = []
        linked_ids: set[str] = set()

        for record in records:
            fp = str(record.get("fingerprint", ""))
            task_id = str(record.get("task_id") or "")
            if task_id:
                linked_ids.add(task_id)
            task = tasks.get(task_id) if task_id else None
            state = str(record.get("state", "PENDING"))
            attempts = int(record.get("attempts", 0))

            if task_id and task is None:
                findings.append(
                    ReconcileFinding(
                        "missing_task",
                        fingerprint=fp,
                        task_id=task_id,
                        detail="ledger references a task that does not exist",
                        safe_fix=True,
                    )
                )
                continue

            if task is None:
                continue

            if task.status == TaskStatus.SUCCEEDED and state != "SUCCEEDED":
                findings.append(
                    ReconcileFinding(
                        "succeeded_task_ledger_drift",
                        fingerprint=fp,
                        task_id=task.id,
                        detail=f"task=SUCCEEDED ledger={state}",
                        safe_fix=True,
                    )
                )
            elif task.status == TaskStatus.CANCELLED and state != "CANCELLED":
                findings.append(
                    ReconcileFinding(
                        "cancelled_task_ledger_drift",
                        fingerprint=fp,
                        task_id=task.id,
                        detail=f"task=CANCELLED ledger={state}",
                        safe_fix=True,
                    )
                )
            elif task.status in TERMINAL_BLOCKED and state == "RUNNING":
                findings.append(
                    ReconcileFinding(
                        "terminal_task_running_ledger",
                        fingerprint=fp,
                        task_id=task.id,
                        detail=f"task={task.status.value} ledger=RUNNING",
                        safe_fix=True,
                    )
                )
            elif task.status == TaskStatus.CREATED and state == "RUNNING":
                findings.append(
                    ReconcileFinding(
                        "created_task_running_ledger",
                        fingerprint=fp,
                        task_id=task.id,
                        detail="task=CREATED ledger=RUNNING",
                        safe_fix=True,
                    )
                )

            if attempts != task.attempts and task.status in TERMINAL_DONE | TERMINAL_BLOCKED:
                findings.append(
                    ReconcileFinding(
                        "attempt_drift",
                        fingerprint=fp,
                        task_id=task.id,
                        detail=f"task_attempts={task.attempts} ledger_attempts={attempts}",
                        safe_fix=True,
                    )
                )

        orphan_tasks = tuple(
            sorted(
                task.id
                for task in tasks.values()
                if task.id not in linked_ids
                and task.status not in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}
            )
        )
        for task_id in orphan_tasks:
            task = tasks[task_id]
            findings.append(
                ReconcileFinding(
                    "orphan_task",
                    task_id=task_id,
                    detail=f"status={task.status.value} title={task.title}",
                    safe_fix=False,
                    remediation=(
                        f"enqueue-task {task_id} --kind REPAIR "
                        f"or cancel {task_id} --reason <reason>"
                    ),
                )
            )

        return ReconcileReport(tuple(findings), (), orphan_tasks)

    def apply_safe(self) -> ReconcileReport:
        initial = self.inspect()
        applied: list[ReconcileFinding] = []

        for finding in initial.findings:
            if not finding.safe_fix or not finding.fingerprint:
                continue

            record = next(
                (
                    item
                    for item in self.ledger.records()
                    if item.get("fingerprint") == finding.fingerprint
                ),
                None,
            )
            if record is None:
                continue

            task = self.store.get_task(finding.task_id) if finding.task_id else None

            if finding.kind == "missing_task":
                self.ledger.update(
                    finding.fingerprint,
                    task_id="",
                    state="PENDING",
                    attempts=0,
                    last_error="",
                )
            elif finding.kind == "succeeded_task_ledger_drift" and task is not None:
                self.ledger.update(
                    finding.fingerprint,
                    state="SUCCEEDED",
                    attempts=task.attempts,
                    last_error="",
                )
            elif finding.kind == "cancelled_task_ledger_drift" and task is not None:
                self.ledger.update(
                    finding.fingerprint,
                    state="CANCELLED",
                    attempts=task.attempts,
                    last_error=task.last_error,
                )
            elif finding.kind == "terminal_task_running_ledger" and task is not None:
                self.ledger.update(
                    finding.fingerprint,
                    state="BLOCKED",
                    attempts=task.attempts,
                    last_error=task.last_error,
                )
            elif finding.kind == "created_task_running_ledger" and task is not None:
                self.ledger.update(
                    finding.fingerprint,
                    state="PENDING",
                    attempts=task.attempts,
                    last_error=task.last_error,
                )
            elif finding.kind == "attempt_drift" and task is not None:
                self.ledger.update(
                    finding.fingerprint,
                    attempts=task.attempts,
                )
            else:
                continue
            applied.append(finding)

        final = self.inspect()
        return ReconcileReport(final.findings, tuple(applied), final.orphan_tasks)
