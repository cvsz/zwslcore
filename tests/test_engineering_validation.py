from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.evidence import EvidenceExporter
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.runtime import EngineeringRuntime
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.validation import evaluate_validation, validate_mode
from services.engineering.worktree import WorktreeManager


def result(command: str, code: int) -> dict:
    return {
        "passed": code == 0,
        "failures": [] if code == 0 else [command],
        "results": [{
            "command": command,
            "returncode": code,
            "stdout": "",
            "stderr": "",
        }],
    }


class ValidationPolicyTests(unittest.TestCase):
    def test_strict_blocks_any_final_failure(self):
        value = evaluate_validation(None, result("test", 1), mode="strict")
        self.assertFalse(value["passed"])
        self.assertEqual(value["regressions"], ["test"])

    def test_delta_allows_existing_failure(self):
        value = evaluate_validation(
            result("test", 1),
            result("test", 1),
            mode="delta",
        )
        self.assertTrue(value["passed"])
        self.assertEqual(value["residual_failures"], ["test"])
        self.assertEqual(value["regressions"], [])

    def test_delta_blocks_new_regression(self):
        value = evaluate_validation(
            result("test", 0),
            result("test", 1),
            mode="delta",
        )
        self.assertFalse(value["passed"])
        self.assertEqual(value["regressions"], ["test"])

    def test_delta_records_improvement(self):
        value = evaluate_validation(
            result("test", 1),
            result("test", 0),
            mode="delta",
        )
        self.assertTrue(value["passed"])
        self.assertEqual(value["improvements"], ["test"])

    def test_invalid_mode_rejected(self):
        with self.assertRaisesRegex(ValueError, "unsupported validation mode"):
            validate_mode("permissive")


class Provider:
    model = "zeaz-fast"

    def preflight(self):
        return None

    def chat(self, prompt, system, **kwargs):
        if "Produce a concise implementation plan" in prompt:
            return "plan"
        return '{"changes":[{"path":"services/example.py","content":"x = 2"}]}'


def make_repo(root: Path, name: str) -> Path:
    repo = root / name
    (repo / "services").mkdir(parents=True)
    (repo / "services" / "example.py").write_text("x = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
    return repo


class RuntimeValidationModeTests(unittest.TestCase):
    def test_delta_allows_unchanged_baseline_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root, "delta")
            store = SQLiteEngineeringStore(root / "delta.db")
            runtime = EngineeringRuntime(
                store,
                Provider(),
                worktrees=WorktreeManager(root / "delta-worktrees"),
                evidence=EvidenceExporter(store, root / "delta-evidence"),
            )
            task = EngineeringTask(title="delta", repository=str(repo))
            result_task = runtime.run(
                task,
                validators=['python3 -c "import sys; sys.exit(1)"'],
                allowed_paths={"services"},
                validation_mode="delta",
            )
            self.assertEqual(result_task.status, TaskStatus.SUCCEEDED)
            validation = store.latest_checkpoint(task.id, "VALIDATION")
            self.assertTrue(validation.payload["passed"])
            self.assertEqual(
                validation.payload["residual_failures"],
                ['python3 -c "import sys; sys.exit(1)"'],
            )

    def test_strict_blocks_same_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root, "strict")
            store = SQLiteEngineeringStore(root / "strict.db")
            runtime = EngineeringRuntime(
                store,
                Provider(),
                worktrees=WorktreeManager(root / "strict-worktrees"),
                evidence=EvidenceExporter(store, root / "strict-evidence"),
            )
            task = EngineeringTask(title="strict", repository=str(repo))
            with self.assertRaisesRegex(RuntimeError, "validation strict failed"):
                runtime.run(
                    task,
                    validators=['python3 -c "import sys; sys.exit(1)"'],
                    allowed_paths={"services"},
                    validation_mode="strict",
                )
            self.assertIn(task.status, {TaskStatus.BLOCKED, TaskStatus.FAILED})


if __name__ == "__main__":
    unittest.main()
