from __future__ import annotations

import subprocess
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path

from services.engineering.continuous import ContinuousEngineeringRunner
from services.engineering.lease import RunnerLeaseHeldError, SQLiteRunnerLease
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.models import EngineeringTask
from services.engineering.store import SQLiteEngineeringStore


class RunnerLeaseTests(unittest.TestCase):
    def test_only_one_runner_can_read_and_execute_queue_at_a_time(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "engineering.db")
            entered_pending = threading.Event()
            allow_pending_to_finish = threading.Event()

            class BlockingLedger:
                path = root / "continuous.json"

                def pending(self, *, retry_blocked=False):
                    entered_pending.set()
                    if not allow_pending_to_finish.wait(timeout=5):
                        raise TimeoutError("test did not release pending scan")
                    return []

            class CountingLedger:
                pending_calls = 0
                path = root / "continuous.json"

                def pending(self, *, retry_blocked=False):
                    self.pending_calls += 1
                    return []

            first = ContinuousEngineeringRunner(
                store,
                BlockingLedger(),
                runtime=object(),
            )
            second_ledger = CountingLedger()
            second = ContinuousEngineeringRunner(
                SQLiteEngineeringStore(root / "engineering.db"),
                second_ledger,
                runtime=object(),
            )
            outcome: list[object] = []

            def run_first():
                try:
                    outcome.append(first.run())
                except Exception as exc:  # surfaced to the main test thread
                    outcome.append(exc)

            worker = threading.Thread(target=run_first)
            worker.start()
            self.assertTrue(entered_pending.wait(timeout=5))
            try:
                with self.assertRaises(RunnerLeaseHeldError):
                    second.run()
                self.assertEqual(second_ledger.pending_calls, 0)
            finally:
                allow_pending_to_finish.set()
                worker.join(timeout=5)

            self.assertFalse(worker.is_alive())
            self.assertEqual(len(outcome), 1)
            self.assertNotIsInstance(outcome[0], Exception)
            current = store.get_runner_lease(SQLiteRunnerLease.DEFAULT_NAME)
            self.assertEqual(current["status"], "RELEASED")
            self.assertTrue(current["owner_id"])
            self.assertGreater(current["heartbeat_at"], 0)
            self.assertGreater(current["expires_at"], 0)

    def test_heartbeat_renews_expiry_and_owner_checked_release(self):
        with tempfile.TemporaryDirectory() as td:
            store = SQLiteEngineeringStore(Path(td) / "engineering.db")
            lease = SQLiteRunnerLease(
                store,
                ttl_seconds=60,
                heartbeat_interval=20,
                owner_id="test-owner",
            ).acquire()
            try:
                before = store.get_runner_lease(lease.name)
                time.sleep(0.002)
                self.assertTrue(lease.heartbeat_once())
                after = store.get_runner_lease(lease.name)
                self.assertGreaterEqual(after["heartbeat_at"], before["heartbeat_at"])
                self.assertGreater(after["expires_at"], before["expires_at"])
                lease.assert_owned()

                self.assertFalse(
                    store.release_runner_lease(
                        lease.name,
                        "different-owner",
                        lease.fencing_token,
                        now=time.time(),
                    )
                )
            finally:
                lease.release()

            released = store.get_runner_lease(lease.name)
            self.assertEqual(released["status"], "RELEASED")
            self.assertIsNotNone(released["released_at"])

    def test_process_crash_releases_lock_and_next_runner_reclaims_durable_lease(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "engineering.db"
            child_code = "\n".join(
                [
                    "import os, sys",
                    "from services.engineering.lease import SQLiteRunnerLease",
                    "from services.engineering.store import SQLiteEngineeringStore",
                    "store = SQLiteEngineeringStore(sys.argv[1])",
                    "lease = SQLiteRunnerLease(store, ttl_seconds=3600, heartbeat_interval=120, owner_id='crashed-owner').acquire()",
                    "os._exit(0)",
                ]
            )
            proc = subprocess.run(
                [sys.executable, "-c", child_code, str(db)],
                cwd=Path(__file__).resolve().parents[1],
                text=True,
                capture_output=True,
                timeout=10,
            )
            self.assertEqual(proc.returncode, 0, proc.stderr)

            store = SQLiteEngineeringStore(db)
            stale = store.get_runner_lease(SQLiteRunnerLease.DEFAULT_NAME)
            self.assertEqual(stale["owner_id"], "crashed-owner")
            self.assertEqual(stale["status"], "HELD")
            self.assertGreater(stale["expires_at"], time.time())

            with SQLiteRunnerLease(
                store,
                ttl_seconds=60,
                heartbeat_interval=20,
                owner_id="replacement-owner",
            ) as replacement:
                reclaimed = store.get_runner_lease(replacement.name)
                self.assertEqual(reclaimed["owner_id"], "replacement-owner")
                self.assertEqual(reclaimed["previous_owner_id"], "crashed-owner")
                self.assertIsNotNone(reclaimed["reclaimed_at"])
                self.assertEqual(reclaimed["fencing_token"], stale["fencing_token"] + 1)
                replacement.assert_owned()

    def test_release_failure_does_not_mask_runner_error(self):
        class BrokenReleaseLease(SQLiteRunnerLease):
            def release(self):
                raise OSError("lease store unavailable")

        with tempfile.TemporaryDirectory() as td:
            store = SQLiteEngineeringStore(Path(td) / "engineering.db")
            original = RuntimeError("runner work failed")
            try:
                with BrokenReleaseLease(store):
                    raise original
            except RuntimeError as exc:
                self.assertIs(exc, original)
                self.assertTrue(any("lease store unavailable" in note for note in exc.__notes__))
            else:
                self.fail("runner error was swallowed")

    def test_direct_run_refuses_to_start_while_queue_runner_owns_state(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "engineering.db"
            ledger_path = root / "continuous.json"
            store = SQLiteEngineeringStore(db)
            task = EngineeringTask(title="must not start")
            store.save_task(task)
            ledger = JsonContinuousLedger(ledger_path)
            lease = SQLiteRunnerLease(
                store,
                lock_paths=SQLiteRunnerLease.queue_lock_paths(store, ledger.path),
                owner_id="test-queue-owner",
            ).acquire()
            try:
                proc = subprocess.run(
                    [
                        sys.executable,
                        "scripts/engineer.py",
                        "--db", str(db),
                        "--ledger", str(ledger_path),
                        "run", task.id,
                    ],
                    cwd=Path(__file__).resolve().parents[1],
                    text=True,
                    capture_output=True,
                    timeout=10,
                )
            finally:
                lease.release()
            self.assertEqual(proc.returncode, 1)
            self.assertIn("is held", proc.stderr)


if __name__ == "__main__":
    unittest.main()
