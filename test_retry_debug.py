#!/usr/bin/env python3
"""Exact copy of the failing test with debug output."""

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, '/home/cvsz/zwslcore')

from services.engineering.continuous import ContinuousEngineeringRunner
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.loop import WorkItem, WorkKind
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.runtime import EngineeringRuntime, ProviderClient
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.worktree import WorktreeManager


class NoopProvider:
    model = "zeaz-local"

    def preflight(self, *, request_id=None):
        return None

    def __init__(self):
        self.edit_calls = 0

    MAX_EDIT_RETRIES = 2

    def chat(self, prompt, system, **kwargs):
        if "Produce a concise implementation plan" in prompt:
            return "plan"
        self.edit_calls += 1
        if self.edit_calls <= self.MAX_EDIT_RETRIES:
            return '{"changes":[]}'
        return '{"changes":[{"path":"services/example.py","content":"x = 1"}]}'


class ContinuousRetryResetTests(unittest.TestCase):
    def test_retry_blocked_resets_task_attempt_budget_and_state(self):
        class NoopProvider:
            model = "zeaz-local"

            def preflight(self, *, request_id=None):
                return None

            def __init__(self):
                self.edit_calls = 0

            MAX_EDIT_RETRIES = 2

            def chat(self, prompt, system, **kwargs):
                if "Produce a concise implementation plan" in prompt:
                    return "plan"
                self.edit_calls += 1
                if self.edit_calls <= self.MAX_EDIT_RETRIES:
                    return '{"changes":[]}'
                return '{"changes":[{"path":"services/example.py","content":"x = 1"}]}'

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            (repo / "services").mkdir(parents=True)
            (repo / "services" / "__init__.py").write_text("", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"], check=True)
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)

            store = SQLiteEngineeringStore(Path(td) / "state.db")
            ledger = JsonContinuousLedger(Path(td) / "continuous.json")
            manager = WorktreeManager(Path(td) / "worktrees")
            item = WorkItem(
                "retry",
                WorkKind.REPAIR,
                payload={
                    "repository": str(repo),
                    "risk": "medium",
                    "validators": ["git diff --check"],
                    "allowed_paths": ["services"],
                    "commit": False,
                },
                max_attempts=2,
            )
            ledger.register(item)
            task_id = f"work_{item.fingerprint[:20]}"
            task = EngineeringTask(
                id=task_id,
                title=item.title,
                repository=str(repo),
                status=TaskStatus.FAILED,
                attempts=2,
                max_attempts=2,
                last_error="old failure",
            )
            store.save_task(task)
            ledger.update(
                item.fingerprint,
                state="BLOCKED",
                attempts=2,
                task_id=task_id,
                last_error="old failure",
            )

            runtime = EngineeringRuntime(store, NoopProvider(), worktrees=manager)
            runner = ContinuousEngineeringRunner(store, ledger, runtime)
            result = runner.run(max_iterations=2, retry_blocked=True)

            print(f"DEBUG: result.completed = {result.completed}")
            print(f"DEBUG: result.blocked = {result.blocked}")
            print(f"DEBUG: result.iterations = {result.iterations}")
            print(f"DEBUG: result.halt_reason = {result.halt_reason}")
            print(f"DEBUG: item.fingerprint = {item.fingerprint}")
            print(f"DEBUG: match = {result.completed == (item.fingerprint,)}")

            self.assertEqual(result.completed, (item.fingerprint,))
            loaded = store.get_task(task_id)
            self.assertEqual(loaded.status, TaskStatus.SUCCEEDED, loaded.last_error)
            self.assertEqual(loaded.attempts, 2)
            self.assertEqual(loaded.max_attempts, 2)
            self.assertEqual(loaded.last_error, "")


if __name__ == "__main__":
    unittest.main()