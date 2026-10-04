from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.loop import ContinuousEngineeringLoop, LoopPolicy, WorkItem, WorkKind
from services.engineering.models import Checkpoint, EngineeringTask, TaskStatus
from services.engineering.review import SecurityGate, StaticReviewer
from services.engineering.snapshot import RepositorySnapshotter
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.worktree import WorktreeManager


class StoreTests(unittest.TestCase):
    def test_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            store = SQLiteEngineeringStore(Path(td) / "state.db")
            task = EngineeringTask(title="fix")
            store.save_task(task)
            task.status = TaskStatus.PLANNING
            store.save_task(task)
            store.save_checkpoint(Checkpoint(task_id=task.id, phase="PLAN", payload={"ok": True}))
            self.assertEqual(store.get_task(task.id).status, TaskStatus.PLANNING)
            self.assertEqual(store.latest_checkpoint(task.id).payload, {"ok": True})


class SnapshotTests(unittest.TestCase):
    def test_secret_excluded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "app.py").write_text("print('ok')", encoding="utf-8")
            (root / ".env").write_text("TOKEN=secret", encoding="utf-8")
            text = RepositorySnapshotter(root).snapshot()
            self.assertIn("app.py", text)
            self.assertNotIn("TOKEN=secret", text)


class ReviewTests(unittest.TestCase):
    def test_secret_and_scope_block(self):
        diff = '+++ b/other.py\n+api_key = "sk-abcdefghijklmnopqrstuvwxyz"\n'
        findings = StaticReviewer().review(diff, allowed_paths={"src"})
        passed, blocking = SecurityGate().evaluate(findings)
        self.assertFalse(passed)
        self.assertTrue(blocking)


class LoopTests(unittest.TestCase):
    def test_bounded_retry(self):
        calls = []
        def implement(item):
            calls.append(item.fingerprint)
            return object()
        def validate(item, result):
            return False, ()
        item = WorkItem("repair", WorkKind.REPAIR, max_attempts=2)
        result = ContinuousEngineeringLoop(
            implement, validate,
            policy=LoopPolicy(max_iterations=5, max_no_progress_iterations=2),
        ).run([item])
        self.assertEqual(len(calls), 2)
        self.assertEqual(len(result.blocked), 1)


class WorktreeTests(unittest.TestCase):
    def test_isolated_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            wt = Path(td) / "worktrees"
            repo.mkdir()
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
            manager = WorktreeManager(wt)
            target, branch = manager.create(repo, "task-1", "fix test")
            self.assertTrue((target / ".zwslcore-managed").exists())
            self.assertTrue(branch.startswith("agent/"))
            manager.remove(repo, target)


if __name__ == "__main__":
    unittest.main()
