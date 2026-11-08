"""Adversarial security tests for worktree path isolation and permission boundaries.

These tests verify that untrusted task input cannot escape the permitted
repository path, bypass symlink checks, or escalate permissions through
child task delegation.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
import threading
import unittest
from pathlib import Path

from services.engineering.runtime import EngineeringRuntime
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.worktree import WorktreeManager
from services.engineering.models import EngineeringTask, TaskStatus, TaskRisk
from services.engineering.agents import AgentRegistry
from services.engineering.change_snapshot import ChangeSnapshotStore
from services.engineering.evidence import EvidenceExporter
from services.engineering.delegation import delegated_allowed_paths


class _FakeProvider:
    """Minimal provider stub with just the attributes EngineeringRuntime needs."""

    model = "zeaz-fast"


class PathTraversalApplyChangesTests(unittest.TestCase):
    """EngineeringRuntime._apply_changes must reject path escape attempts."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="zwslcore-adversarial-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "--allow-empty", "-m", "init"],
            check=True, capture_output=True,
        )
        self.store = SQLiteEngineeringStore(self.tmp / "state.db")
        self.worktrees = WorktreeManager(self.tmp / "worktrees")
        self.evidence = EvidenceExporter(self.store)
        self.agent_registry = AgentRegistry(path=None)
        self.runtime = EngineeringRuntime(
            self.store,
            _FakeProvider(),
            worktrees=self.worktrees,
            evidence=self.evidence,
            agent_registry=self.agent_registry,
        )

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _task(self) -> EngineeringTask:
        return EngineeringTask(
            id="task_adv",
            title="Adversarial path test",
            description="",
            risk=TaskRisk.LOW,
            status=TaskStatus.EDITING,
            attempts=0,
            max_attempts=3,
            repository=str(self.repo),
            branch_name="agent/task_adv",
            worktree_path=str(self.tmp / "worktrees" / "task_adv"),
            metadata={},
            last_error="",
        )

    def test_absolute_path_rejected(self):
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            with self.assertRaises(ValueError) as ctx:
                self.runtime._apply_changes(
                    worktree,
                    [{"path": "/etc/passwd", "content": "x"}],
                    allowed_paths=None,
                )
            self.assertIn("unsafe path", str(ctx.exception))
        finally:
            self.worktrees.remove(self.repo, worktree)

    def test_dotdot_path_rejected(self):
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            with self.assertRaises(ValueError) as ctx:
                self.runtime._apply_changes(
                    worktree,
                    [{"path": "../../etc/passwd", "content": "x"}],
                    allowed_paths=None,
                )
            self.assertIn("unsafe path", str(ctx.exception))
        finally:
            self.worktrees.remove(self.repo, worktree)

    def test_dotdot_mid_path_rejected(self):
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            with self.assertRaises(ValueError) as ctx:
                self.runtime._apply_changes(
                    worktree,
                    [{"path": "services/../../../etc/passwd", "content": "x"}],
                    allowed_paths=None,
                )
            self.assertIn("unsafe path", str(ctx.exception))
        finally:
            self.worktrees.remove(self.repo, worktree)

    def test_secret_env_file_rejected(self):
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            with self.assertRaises(ValueError) as ctx:
                self.runtime._apply_changes(
                    worktree,
                    [{"path": ".env", "content": "SECRET=1"}],
                    allowed_paths=None,
                )
            self.assertIn("secret-bearing path", str(ctx.exception))
        finally:
            self.worktrees.remove(self.repo, worktree)

    def test_secret_pem_file_rejected(self):
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            with self.assertRaises(ValueError) as ctx:
                self.runtime._apply_changes(
                    worktree,
                    [{"path": "config/server.pem", "content": "-----BEGIN-----"}],
                    allowed_paths=None,
                )
            self.assertIn("secret-bearing path", str(ctx.exception))
        finally:
            self.worktrees.remove(self.repo, worktree)

    def test_outside_allowed_scope_rejected(self):
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            with self.assertRaises(ValueError) as ctx:
                self.runtime._apply_changes(
                    worktree,
                    [{"path": "README.md", "content": "x"}],
                    allowed_paths={"services"},
                )
            self.assertIn("path outside declared scope", str(ctx.exception))
        finally:
            self.worktrees.remove(self.repo, worktree)

    def test_symlink_escape_rejected(self):
        """A symlink inside the worktree pointing outside must not be written through."""
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            outside = self.tmp / "outside-secret.txt"
            outside.write_text("pwned\n", encoding="utf-8")
            link = worktree / "escape-link"
            link.symlink_to(outside)

            with self.assertRaises((ValueError, OSError)):
                self.runtime._apply_changes(
                    worktree,
                    [{"path": "escape-link", "content": "pwned"}],
                    allowed_paths=None,
                )
        finally:
            self.worktrees.remove(self.repo, worktree)

    def test_valid_in_scope_change_accepted(self):
        task = self._task()
        worktree, _ = self.worktrees.create(self.repo, task.id, "adv")
        try:
            (worktree / "services").mkdir()
            self.runtime._apply_changes(
                worktree,
                [{"path": "services/test.txt", "content": "hello"}],
                allowed_paths={"services"},
            )
            self.assertEqual(
                (worktree / "services" / "test.txt").read_text(encoding="utf-8"),
                "hello",
            )
        finally:
            self.worktrees.remove(self.repo, worktree)


class WorktreeConcurrencyTests(unittest.TestCase):
    """Concurrent worktree operations must not corrupt shared SQLite state."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="zwslcore-concurrent-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "--allow-empty", "-m", "init"],
            check=True, capture_output=True,
        )
        self.store = SQLiteEngineeringStore(self.tmp / "state.db")
        self.worktrees = WorktreeManager(self.tmp / "worktrees")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_concurrent_task_creation(self):
        """Creating multiple tasks concurrently must not corrupt the store."""
        errors = []

        def create_task(idx):
            try:
                task = EngineeringTask(
                    id=f"task_concurrent_{idx}",
                    title=f"Concurrent task {idx}",
                    description="",
                    risk=TaskRisk.LOW,
                    status=TaskStatus.BASELINING,
                    attempts=0,
                    max_attempts=3,
                    repository=str(self.repo),
                    branch_name=f"agent/task_concurrent_{idx}",
                    worktree_path=str(
                        self.tmp / "worktrees" / f"task_concurrent_{idx}"
                    ),
                    metadata={},
                    last_error="",
                )
                self.store.save_task(task)
                worktree, branch = self.worktrees.create(self.repo, task.id, f"task{idx}")
                task.worktree_path = str(worktree)
                task.branch_name = branch
                task.status = TaskStatus.PLANNING
                self.store.save_task(task)
            except Exception as exc:  # noqa: BLE001
                errors.append(str(exc))

        threads = [threading.Thread(target=create_task, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        self.assertEqual(len(errors), 0, f"Concurrent errors: {errors}")
        # Verify all tasks are retrievable
        for i in range(10):
            task = self.store.get_task(f"task_concurrent_{i}")
            self.assertIsNotNone(task)
            self.assertEqual(task.status, TaskStatus.PLANNING)


class PermissionEscalationTests(unittest.TestCase):
    """Child tasks must not inherit broader permissions than intended."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="zwslcore-perm-"))
        self.repo = self.tmp / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init"], cwd=self.repo, check=True, capture_output=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "test@test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Test"],
            check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "commit", "--allow-empty", "-m", "init"],
            check=True, capture_output=True,
        )
        self.store = SQLiteEngineeringStore(self.tmp / "state.db")
        self.worktrees = WorktreeManager(self.tmp / "worktrees")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_delegated_paths_exceed_parent_raise(self):
        """delegated_allowed_paths must reject child paths outside parent scope."""
        parent = EngineeringTask(
            id="parent_task",
            title="Parent task",
            description="",
            risk=TaskRisk.LOW,
            status=TaskStatus.PLANNING,
            attempts=0,
            max_attempts=3,
            repository=str(self.repo),
            branch_name="agent/parent_task",
            worktree_path=str(self.tmp / "worktrees" / "parent_task"),
            metadata={"run_config": {"allowed_paths": {"services", "tests", "docs"}}},
            last_error="",
        )
        with self.assertRaises(ValueError) as ctx:
            delegated_allowed_paths(parent, {"services", "config"})
        self.assertIn("exceed parent scope", str(ctx.exception))

    def test_delegated_paths_within_parent_allowed(self):
        """delegated_allowed_paths must allow child paths within parent scope."""
        parent = EngineeringTask(
            id="parent_task",
            title="Parent task",
            description="",
            risk=TaskRisk.LOW,
            status=TaskStatus.PLANNING,
            attempts=0,
            max_attempts=3,
            repository=str(self.repo),
            branch_name="agent/parent_task",
            worktree_path=str(self.tmp / "worktrees" / "parent_task"),
            metadata={"run_config": {"allowed_paths": {"services", "tests", "docs"}}},
            last_error="",
        )
        result = delegated_allowed_paths(parent, {"services"})
        self.assertEqual(set(result), {"services"})


if __name__ == "__main__":
    unittest.main()
