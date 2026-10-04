from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.evidence import EvidenceExporter
from services.engineering.models import Checkpoint, EngineeringTask, TaskStatus
from services.engineering.store import SQLiteEngineeringStore


class EvidenceExporterTests(unittest.TestCase):
    def test_bundle_is_secret_minimized_and_verifiable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = root / "repo"
            repo.mkdir()
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "app.py").write_text("value = 1\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "app.py"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
            (repo / "app.py").write_text("value = 2\n", encoding="utf-8")

            store = SQLiteEngineeringStore(root / "state.db")
            task = EngineeringTask(
                title="evidence",
                description="change app",
                repository=str(repo),
                worktree_path=str(repo),
                status=TaskStatus.FAILED,
                attempts=1,
                last_error="api_key=sk-abcdefghijklmnopqrstuvwxyz provider failed",
            )
            store.save_task(task)
            store.save_checkpoint(
                Checkpoint(
                    task_id=task.id,
                    phase="VALIDATION",
                    payload={
                        "passed": False,
                        "failures": ["python -m unittest"],
                        "results": [{
                            "command": "python -m unittest",
                            "returncode": 1,
                            "stdout": "token=super-secret-value",
                            "stderr": "failure",
                        }],
                    },
                )
            )
            store.save_checkpoint(
                Checkpoint(
                    task_id=task.id,
                    phase="REVIEW",
                    payload={
                        "findings": [{
                            "severity": "high",
                            "category": "scope",
                            "path": "app.py",
                            "message": "detail",
                            "blocking": True,
                        }]
                    },
                )
            )

            exporter = EvidenceExporter(store, root / "evidence")
            path, digest = exporter.export(task)
            self.assertTrue(path.exists())
            self.assertEqual(len(digest), 64)
            self.assertTrue(exporter.verify(task.id))

            raw = path.read_text(encoding="utf-8")
            self.assertNotIn("super-secret-value", raw)
            self.assertNotIn("sk-abcdefghijklmnopqrstuvwxyz", raw)
            data = json.loads(raw)
            self.assertEqual(data["task"]["status"], "FAILED")
            self.assertIn("[REDACTED]", data["task"]["last_error"])
            self.assertEqual(data["git"]["changed_paths"], ["app.py"])
            validation = next(cp for cp in data["checkpoints"] if cp["phase"] == "VALIDATION")
            self.assertEqual(validation["results"][0]["returncode"], 1)
            self.assertIn("stdout_sha256", validation["results"][0])

            path.write_text(raw + "tamper\n", encoding="utf-8")
            self.assertFalse(exporter.verify(task.id))

    def test_checkpoint_order_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            store = SQLiteEngineeringStore(Path(td) / "state.db")
            task = EngineeringTask(title="order")
            store.save_task(task)
            first = Checkpoint(task_id=task.id, phase="PLAN", created_at=10.0)
            second = Checkpoint(task_id=task.id, phase="VALIDATION", created_at=20.0)
            store.save_checkpoint(second)
            store.save_checkpoint(first)
            self.assertEqual(
                [cp.phase for cp in store.list_checkpoints(task.id)],
                ["PLAN", "VALIDATION"],
            )


if __name__ == "__main__":
    unittest.main()
