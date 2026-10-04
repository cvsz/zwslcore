from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.evidence import EvidenceExporter
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.runtime import EngineeringRuntime
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.worktree import WorktreeManager


class ResumeProvider:
    model = "zeaz-fast"

    def __init__(self) -> None:
        self.plan_calls = 0
        self.edit_calls = 0
        self.fail_edits = True

    def preflight(self) -> None:
        return None

    def chat(self, prompt, system, **kwargs):
        if "Produce a concise implementation plan" in prompt:
            self.plan_calls += 1
            return f"plan-{self.plan_calls}"
        self.edit_calls += 1
        if self.fail_edits:
            return '{"changes":[]}'
        return '{"changes":[{"path":"services/example.py","content":"x = 1"}]}'


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "services").mkdir(parents=True)
    (repo / "services" / "__init__.py").write_text("", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "README.md").write_text("base\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
    return repo


class EngineeringResumeTests(unittest.TestCase):
    def test_resume_reuses_plan_when_head_matches(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            provider = ResumeProvider()
            runtime = EngineeringRuntime(
                store,
                provider,
                worktrees=WorktreeManager(root / "worktrees"),
                evidence=EvidenceExporter(store, root / "evidence"),
            )
            task = EngineeringTask(title="resume", repository=str(repo), max_attempts=3)

            with self.assertRaises(ValueError):
                runtime.run(
                    task,
                    validators=["git diff --check"],
                    allowed_paths={"services"},
                )

            self.assertEqual(provider.plan_calls, 1)
            plan_cp = store.latest_checkpoint(task.id, "PLAN")
            self.assertIsNotNone(plan_cp)
            self.assertTrue(plan_cp.payload["baseline_head"])

            provider.fail_edits = False
            result = runtime.run(
                task,
                validators=["git diff --check"],
                allowed_paths={"services"},
                resume=True,
            )

            self.assertEqual(result.status, TaskStatus.SUCCEEDED)
            self.assertEqual(provider.plan_calls, 1)
            self.assertEqual(result.attempts, 2)
            self.assertEqual(result.metadata["phase_cursor"], "REVIEW")
            self.assertIn("run_config", result.metadata)

    def test_resume_replans_when_head_changed(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            provider = ResumeProvider()
            manager = WorktreeManager(root / "worktrees")
            runtime = EngineeringRuntime(
                store,
                provider,
                worktrees=manager,
                evidence=EvidenceExporter(store, root / "evidence"),
            )
            task = EngineeringTask(title="resume changed head", repository=str(repo), max_attempts=3)

            with self.assertRaises(ValueError):
                runtime.run(
                    task,
                    validators=["git diff --check"],
                    allowed_paths={"services"},
                )
            self.assertEqual(provider.plan_calls, 1)

            worktree = Path(task.worktree_path)
            (worktree / "services" / "baseline.py").write_text("baseline = 1\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(worktree), "commit", "-m", "advance head"],
                check=True,
                capture_output=True,
            )

            provider.fail_edits = False
            result = runtime.run(
                task,
                validators=["git diff --check"],
                allowed_paths={"services"},
                resume=True,
            )

            self.assertEqual(result.status, TaskStatus.SUCCEEDED)
            self.assertEqual(provider.plan_calls, 2)


if __name__ == "__main__":
    unittest.main()
