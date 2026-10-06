from __future__ import annotations

import contextlib
import hashlib
import io
import json
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from services.engineering.models import Checkpoint, EngineeringTask, TaskStatus
from services.engineering.prometheus import EngineeringMetrics, serve
from services.engineering.store import SQLiteEngineeringStore


class EngineeringMetricsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db_path = self.root / "state" / "engineering.db"
        self.ledger_path = self.root / "state" / "continuous.json"
        self.evidence_root = self.root / "evidence"
        self.store = SQLiteEngineeringStore(self.db_path)
        self.metrics = EngineeringMetrics(
            self.db_path,
            self.ledger_path,
            self.evidence_root,
        )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_render_exports_bounded_aggregate_counts_without_task_identity(self) -> None:
        completed = EngineeringTask(
            title="private task title",
            status=TaskStatus.SUCCEEDED,
            attempts=2,
            metadata={"evidence_error": "private error"},
        )
        active = EngineeringTask(
            title="another private title",
            status=TaskStatus.PLANNING,
            attempts=1,
        )
        self.store.save_task(completed)
        self.store.save_task(active)
        self.store.save_checkpoint(
            Checkpoint(
                task_id=completed.id,
                phase="EDIT_RESPONSE_REPAIRED",
            )
        )
        self.evidence_root.joinpath(completed.id).mkdir(parents=True)
        content = b'{"schema":1}\n'
        evidence = self.evidence_root / completed.id / "evidence.json"
        evidence.write_bytes(content)
        digest = hashlib.sha256(content).hexdigest()
        (evidence.parent / "evidence.sha256").write_text(
            f"{digest}  evidence.json\n",
            encoding="utf-8",
        )
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.ledger_path.write_text(
            json.dumps(
                {
                    "schema": 1,
                    "records": {
                        "fingerprint": {"state": "PENDING"},
                        "other": {"state": "RUNNING"},
                        "unknown": {"state": "PRIVATE_STATE"},
                    },
                }
            ),
            encoding="utf-8",
        )

        rendered = self.metrics.render()

        self.assertIn('zeaz_engineering_store_up 1', rendered)
        self.assertIn('zeaz_engineering_ledger_up 1', rendered)
        self.assertIn('zeaz_engineering_tasks{status="SUCCEEDED"} 1', rendered)
        self.assertIn('zeaz_engineering_task_attempts{status="PLANNING"} 1', rendered)
        self.assertIn('zeaz_engineering_checkpoints{phase="EDIT_RESPONSE_REPAIRED"} 1', rendered)
        self.assertIn('zeaz_engineering_structured_output_repairs 1', rendered)
        self.assertIn('zeaz_engineering_queue_items{state="PENDING"} 1', rendered)
        self.assertIn('zeaz_engineering_queue_items{state="RUNNING"} 1', rendered)
        self.assertIn('zeaz_engineering_queue_items{state="OTHER"} 1', rendered)
        self.assertIn('zeaz_engineering_evidence_bundles{state="available"} 1', rendered)
        self.assertIn('zeaz_engineering_tasks_with_evidence_write_error 1', rendered)
        self.assertNotIn(completed.id, rendered)
        self.assertNotIn(completed.title, rendered)
        self.assertNotIn("private error", rendered)
        self.assertNotIn("fingerprint", rendered)

    def test_render_fails_closed_on_missing_state_and_exposes_zeroed_metrics(self) -> None:
        rendered = EngineeringMetrics(
            self.root / "missing.db",
            self.root / "missing.json",
            self.evidence_root,
        ).render()
        self.assertIn("zeaz_engineering_store_up 0", rendered)
        self.assertIn("zeaz_engineering_ledger_up 1", rendered)
        self.assertIn('zeaz_engineering_tasks{status="SUCCEEDED"} 0', rendered)

    def test_render_does_not_modify_the_database(self) -> None:
        self.store.save_task(EngineeringTask(title="read-only exporter"))
        before = hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        self.metrics.render()
        after = hashlib.sha256(self.db_path.read_bytes()).hexdigest()
        self.assertEqual(before, after)

    def test_http_endpoint_serves_metrics_and_only_on_metrics_path(self) -> None:
        import http.server

        holder: dict[str, http.server.ThreadingHTTPServer] = {}

        class EphemeralServer(http.server.ThreadingHTTPServer):
            def __init__(self, address, handler):
                super().__init__(address, handler)
                holder["server"] = self

            def serve_forever(self) -> None:
                holder["ready"].set()
                super().serve_forever()

        ready = threading.Event()
        holder["ready"] = ready
        with contextlib.redirect_stdout(io.StringIO()):
            thread = threading.Thread(
                target=serve,
                args=(self.metrics, 0, EphemeralServer),
                daemon=True,
            )
            thread.start()
            self.assertTrue(ready.wait(2))
            server = holder["server"]
            self.assertEqual(server.server_address[0], "127.0.0.1")
            port = server.server_address[1]
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{port}/metrics") as response:
                    body = response.read().decode("utf-8")
                    self.assertEqual(response.status, 200)
                    self.assertIn("zeaz_engineering_store_up", body)
                with self.assertRaises(urllib.error.HTTPError) as raised:
                    urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=2)
                raised.exception.close()
            finally:
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
