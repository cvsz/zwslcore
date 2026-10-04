from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from services.engineering.ledger import JsonContinuousLedger
from services.engineering.loop import WorkItem, WorkKind
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.reconcile import QueueReconciler
from services.engineering.store import SQLiteEngineeringStore


class QueueReconcileTests(unittest.TestCase):
    def test_succeeded_task_repairs_blocked_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "state.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("done", WorkKind.REPAIR, max_attempts=2)
            ledger.register(item)
            task = EngineeringTask(
                id=f"work_{item.fingerprint[:20]}",
                title=item.title,
                status=TaskStatus.SUCCEEDED,
                attempts=1,
            )
            store.save_task(task)
            ledger.update(
                item.fingerprint,
                task_id=task.id,
                state="BLOCKED",
                attempts=2,
                last_error="stale",
            )

            report = QueueReconciler(store, ledger).apply_safe()
            record = ledger.records()[0]
            self.assertEqual(record["state"], "SUCCEEDED")
            self.assertEqual(record["attempts"], 1)
            self.assertEqual(record["last_error"], "")
            self.assertTrue(any(item.kind == "succeeded_task_ledger_drift" for item in report.applied))

    def test_missing_task_reference_is_reset_to_pending(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "state.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("missing", WorkKind.REPAIR)
            ledger.register(item)
            ledger.update(
                item.fingerprint,
                task_id="work_missing",
                state="RUNNING",
                attempts=1,
            )

            QueueReconciler(store, ledger).apply_safe()
            record = ledger.records()[0]
            self.assertEqual(record["state"], "PENDING")
            self.assertEqual(record["task_id"], "")
            self.assertEqual(record["attempts"], 0)

    def test_unlinked_nonterminal_task_is_reported_as_orphan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "state.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            task = EngineeringTask(title="Fix provider health", status=TaskStatus.CREATED)
            store.save_task(task)

            report = QueueReconciler(store, ledger).inspect()
            self.assertEqual(report.orphan_tasks, (task.id,))
            finding = next(item for item in report.findings if item.kind == "orphan_task")
            self.assertFalse(finding.safe_fix)
            self.assertIn("Fix provider health", finding.detail)
            self.assertIn("enqueue-task", finding.remediation)
            self.assertIn("cancel", finding.remediation)

    def test_cancel_cli_closes_orphan_and_writes_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "state.db"
            ledger_path = root / "continuous.json"
            store = SQLiteEngineeringStore(db)
            task = EngineeringTask(
                title="Fix provider health",
                repository=str(root),
                status=TaskStatus.CREATED,
            )
            store.save_task(task)

            proc = subprocess.run(
                [
                    sys.executable,
                    "scripts/engineer.py",
                    "--db",
                    str(db),
                    "--ledger",
                    str(ledger_path),
                    "cancel",
                    task.id,
                    "--reason",
                    "provider health is already verified",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertEqual(payload["status"], "CANCELLED")
            self.assertTrue(Path(payload["evidence_path"]).exists())

            loaded = store.get_task(task.id)
            self.assertEqual(loaded.status, TaskStatus.CANCELLED)
            self.assertIn("provider health is already verified", loaded.last_error)
            checkpoint = store.latest_checkpoint(task.id)
            self.assertEqual(checkpoint.phase, "CANCELLED")

            report = QueueReconciler(store, JsonContinuousLedger(ledger_path)).inspect()
            self.assertNotIn(task.id, report.orphan_tasks)

            second = subprocess.run(
                [
                    sys.executable,
                    "scripts/engineer.py",
                    "--db",
                    str(db),
                    "--ledger",
                    str(ledger_path),
                    "cancel",
                    task.id,
                    "--reason",
                    "duplicate request",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertTrue(json.loads(second.stdout)["idempotent"])

    def test_cancelled_task_repairs_linked_ledger_state(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "state.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem("cancelled", WorkKind.REPAIR)
            ledger.register(item)
            task = EngineeringTask(
                id=f"work_{item.fingerprint[:20]}",
                title=item.title,
                status=TaskStatus.CANCELLED,
            )
            store.save_task(task)
            ledger.update(
                item.fingerprint,
                task_id=task.id,
                state="PENDING",
            )

            report = QueueReconciler(store, ledger).apply_safe()
            record = ledger.records()[0]
            self.assertEqual(record["state"], "CANCELLED")
            self.assertTrue(
                any(item.kind == "cancelled_task_ledger_drift" for item in report.applied)
            )

    def test_enqueue_task_cli_links_existing_task(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "state.db"
            ledger_path = root / "continuous.json"
            store = SQLiteEngineeringStore(db)
            task = EngineeringTask(
                title="Fix provider health",
                description="repair health diagnostics",
                repository=str(root),
                status=TaskStatus.CREATED,
            )
            store.save_task(task)

            proc = subprocess.run(
                [
                    sys.executable,
                    "scripts/engineer.py",
                    "--db",
                    str(db),
                    "--ledger",
                    str(ledger_path),
                    "enqueue-task",
                    task.id,
                    "--kind",
                    "REPAIR",
                    "--priority",
                    "90",
                    "--allow-path",
                    "services",
                ],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)
            record = json.loads(proc.stdout)
            self.assertEqual(record["task_id"], task.id)
            self.assertEqual(record["state"], "PENDING")
            self.assertEqual(record["priority"], 90)
            self.assertEqual(record["payload"]["allowed_paths"], ["services"])


if __name__ == "__main__":
    unittest.main()
