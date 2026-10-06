from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from services.engineering.continuous import ContinuousEngineeringRunner
from services.engineering.ledger import ContinuousLedgerError, JsonContinuousLedger
from services.engineering.loop import WorkItem, WorkKind
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.store import SQLiteEngineeringStore


class QueueLifecycleTests(unittest.TestCase):
    def _run_cli(self, root: Path, ledger_path: Path, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [
                sys.executable,
                "scripts/engineer.py",
                "--db",
                str(root / "engineering.db"),
                "--ledger",
                str(ledger_path),
                *args,
            ],
            cwd=Path(__file__).resolve().parents[1],
            text=True,
            capture_output=True,
            timeout=10,
        )

    def test_quarantine_dead_letter_and_requeue_preserve_failure_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("failed work", WorkKind.REPAIR, max_attempts=2)
            ledger.register(item)
            ledger.record_attempt(
                item.fingerprint,
                attempts=2,
                status="BLOCKED",
                error="validator failed",
                task_id="task-123",
                model="qwen2.5-coder:3b",
                evidence_path=str(root / "evidence.json"),
            )
            ledger.update(item.fingerprint, state="BLOCKED")

            quarantine = self._run_cli(
                root,
                ledger.path,
                "work-quarantine",
                item.fingerprint[:12],
                "--reason",
                "needs operator review",
            )
            self.assertEqual(quarantine.returncode, 0, quarantine.stderr)
            self.assertEqual(json.loads(quarantine.stdout)["state"], "QUARANTINED")
            self.assertEqual(ledger.pending(), [])

            dead = self._run_cli(
                root,
                ledger.path,
                "work-dead-letter",
                item.fingerprint[:12],
                "--reason",
                "validator failure is not recoverable automatically",
            )
            self.assertEqual(dead.returncode, 0, dead.stderr)
            record = json.loads(dead.stdout)
            self.assertEqual(record["state"], "DEAD_LETTER")
            payload = record["dead_letter"]
            self.assertEqual(payload["fingerprint"], item.fingerprint)
            self.assertEqual(payload["task_id"], "task-123")
            self.assertEqual(payload["failure_reason"], "validator failure is not recoverable automatically")
            self.assertEqual(payload["attempt_history"][0]["attempt"], 2)
            self.assertEqual(payload["model_history"][0]["model"], "qwen2.5-coder:3b")
            self.assertEqual(payload["evidence_path"], str(root / "evidence.json"))
            self.assertTrue(payload["created_at"])
            self.assertTrue(payload["dead_lettered_at"])

            requeued = self._run_cli(
                root,
                ledger.path,
                "work-requeue",
                item.fingerprint[:12],
                "--reason",
                "operator approved another bounded attempt round",
            )
            self.assertEqual(requeued.returncode, 0, requeued.stderr)
            record = json.loads(requeued.stdout)
            self.assertEqual(record["state"], "PENDING")
            self.assertEqual(record["attempts"], 0)
            self.assertTrue(record["retry_requested"])
            self.assertEqual(len(record["attempt_history"]), 1)
            self.assertIn("dead_letter", record)
            self.assertEqual(len(ledger.pending()), 1)

    def test_archive_retains_dead_letter_and_explicit_requeue_restores_it(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("archive candidate", WorkKind.REPAIR)
            ledger.register(item)
            ledger.dead_letter(item.fingerprint, "terminal failure")

            archived = self._run_cli(
                root,
                ledger.path,
                "work-archive",
                item.fingerprint[:12],
                "--reason",
                "retain terminal evidence outside active queue",
            )
            self.assertEqual(archived.returncode, 0, archived.stderr)
            self.assertEqual(ledger.records(), [])
            self.assertEqual(ledger.archived_records()[0]["state"], "DEAD_LETTER")

            listed = self._run_cli(root, ledger.path, "work-list", "--include-archived")
            self.assertEqual(listed.returncode, 0, listed.stderr)
            self.assertIn("DEAD_LETTER", listed.stdout)

            status = self._run_cli(root, ledger.path, "work-status", item.fingerprint[:12])
            self.assertEqual(status.returncode, 0, status.stderr)
            self.assertTrue(json.loads(status.stdout)["archived"])

            restored = self._run_cli(
                root,
                ledger.path,
                "work-requeue",
                item.fingerprint[:12],
                "--reason",
                "reopen after manual review",
            )
            self.assertEqual(restored.returncode, 0, restored.stderr)
            self.assertEqual(ledger.records()[0]["state"], "PENDING")
            self.assertEqual(ledger.archived_records(), [])

    def test_retry_resets_only_blocked_or_exhausted_work(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("retry candidate", WorkKind.REPAIR, max_attempts=1)
            ledger.register(item)
            ledger.record_attempt(
                item.fingerprint,
                attempts=1,
                status="BLOCKED",
                error="old failure",
                task_id="task-456",
            )
            ledger.update(item.fingerprint, state="BLOCKED")

            retried = self._run_cli(
                root,
                ledger.path,
                "work-retry",
                item.fingerprint[:12],
                "--reason",
                "failure corrected",
            )
            self.assertEqual(retried.returncode, 0, retried.stderr)
            result = json.loads(retried.stdout)
            self.assertEqual(result["state"], "PENDING")
            self.assertEqual(result["attempts"], 0)
            self.assertTrue(result["retry_requested"])
            self.assertEqual(result["retry_history"][0]["previous_attempts"], 1)

    def test_cancel_command_handles_unlinked_pending_work(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("cancel unlinked work", WorkKind.REPAIR)
            ledger.register(item)

            cancelled = self._run_cli(
                root,
                ledger.path,
                "work-cancel",
                item.fingerprint[:12],
                "--reason",
                "request withdrawn",
            )
            self.assertEqual(cancelled.returncode, 0, cancelled.stderr)
            record = json.loads(cancelled.stdout)
            self.assertEqual(record["state"], "CANCELLED")
            self.assertEqual(record["cancel_reason"], "request withdrawn")
            self.assertEqual(ledger.pending(), [])

    def test_cancel_redacts_sensitive_operator_reason_from_task_and_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "engineering.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("cancel with redaction", WorkKind.REPAIR)
            task = EngineeringTask(
                id=f"work_{item.fingerprint[:20]}",
                title=item.title,
                description="",
                repository=str(root),
            )
            store.save_task(task)
            ledger.register(item, initial_fields={"task_id": task.id})

            cancelled = self._run_cli(
                root,
                ledger.path,
                "work-cancel",
                item.fingerprint[:12],
                "--reason",
                "operator requested cancellation token=private-sample-value",
            )

            self.assertEqual(cancelled.returncode, 0, cancelled.stderr)
            self.assertNotIn("private-sample-value", (root / "continuous.json").read_text())
            saved_task = store.get_task(task.id)
            self.assertIn("[REDACTED]", saved_task.last_error)
            self.assertNotIn("private-sample-value", json.dumps(saved_task.metadata))

    def test_operator_retry_resets_linked_task_before_the_new_attempt(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "engineering.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("retry linked task", WorkKind.REPAIR, max_attempts=1)
            task_id = f"work_{item.fingerprint[:20]}"
            task = EngineeringTask(
                id=task_id,
                title=item.title,
                repository=str(root),
                status=TaskStatus.FAILED,
                attempts=1,
                max_attempts=1,
                last_error="previous validation failure",
            )
            store.save_task(task)
            ledger.register(item)
            ledger.update(
                item.fingerprint,
                state="BLOCKED",
                attempts=1,
                task_id=task_id,
                last_error=task.last_error,
            )
            ledger.retry(item.fingerprint, "the validator was fixed")

            class SuccessfulRuntime:
                class Worktrees:
                    def reset(self, path):
                        raise AssertionError("task has no worktree to reset")

                worktrees = Worktrees()

                def run(self, task, **kwargs):
                    self.seen_status = task.status
                    self.seen_attempts = task.attempts
                    task.status = TaskStatus.SUCCEEDED
                    task.attempts += 1
                    store.save_task(task)
                    return task

            runtime = SuccessfulRuntime()
            result = ContinuousEngineeringRunner(store, ledger, runtime).run(max_iterations=1)

            self.assertEqual(result.completed, (item.fingerprint,))
            self.assertEqual(runtime.seen_status, TaskStatus.CREATED)
            self.assertEqual(runtime.seen_attempts, 0)
            record = ledger.records()[0]
            self.assertEqual(record["state"], "SUCCEEDED")
            self.assertEqual(record["attempts"], 1)
            self.assertFalse(record["retry_requested"])

    def test_cannot_transition_running_or_archive_nonterminal_work(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = JsonContinuousLedger(Path(td) / "continuous.json")
            item = WorkItem("live", WorkKind.REPAIR)
            ledger.register(item)
            ledger.update(item.fingerprint, state="RUNNING")

            with self.assertRaises(ContinuousLedgerError):
                ledger.cancel(item.fingerprint, "stop")
            with self.assertRaises(ContinuousLedgerError):
                ledger.quarantine(item.fingerprint, "inspect")
            with self.assertRaises(ContinuousLedgerError):
                ledger.dead_letter(item.fingerprint, "terminal failure")
            with self.assertRaises(ContinuousLedgerError):
                ledger.archive(item.fingerprint)

    def test_concurrent_registers_do_not_lose_ledger_updates(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "continuous.json"
            ledgers = [JsonContinuousLedger(path), JsonContinuousLedger(path)]
            errors: list[Exception] = []

            def add_items(offset: int, ledger: JsonContinuousLedger) -> None:
                try:
                    for index in range(25):
                        ledger.register(WorkItem(f"item {offset + index}", WorkKind.REPAIR))
                except Exception as exc:
                    errors.append(exc)

            workers = [
                threading.Thread(target=add_items, args=(0, ledgers[0])),
                threading.Thread(target=add_items, args=(25, ledgers[1])),
            ]
            for worker in workers:
                worker.start()
            for worker in workers:
                worker.join(timeout=10)

            self.assertFalse(any(worker.is_alive() for worker in workers))
            self.assertEqual(errors, [])
            records = ledgers[0].records()
            self.assertEqual(len(records), 50)
            self.assertEqual(len({record["fingerprint"] for record in records}), 50)

    def test_dead_letter_and_attempt_history_redact_credentials(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("redact evidence", WorkKind.REPAIR)
            ledger.register(item)
            ledger.record_attempt(
                item.fingerprint,
                attempts=1,
                status="FAILED",
                error="provider returned api_key=sample-secret-value",
            )
            record = ledger.dead_letter(
                item.fingerprint,
                "retry failed with token=another-secret-value",
            )
            serialized = (root / "continuous.json").read_text(encoding="utf-8")
            self.assertNotIn("sample-secret-value", serialized)
            self.assertNotIn("another-secret-value", serialized)
            self.assertIn("[REDACTED]", record["dead_letter"]["failure_reason"])
            self.assertIn("[REDACTED]", record["dead_letter"]["attempt_history"][0]["error"])


if __name__ == "__main__":
    unittest.main()
