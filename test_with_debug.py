#!/usr/bin/env python3
"""Run the test with debug output."""

import sys
import os
import tempfile
from pathlib import Path
import subprocess

# Add project root to path
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
        print(f"[DEBUG] chat call {self.edit_calls}: plan={('plan' in prompt)}, kwargs keys={list(kwargs.keys())}")
        if self.edit_calls <= self.MAX_EDIT_RETRIES:
            return '{"changes":[]}'
        return '{"changes":[{"path":"services/example.py","content":"x = 1"}]}'


def run_test():
    with tempfile.TemporaryDirectory() as td:
        print(f"[DEBUG] Temp dir: {td}")
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

        from services.engineering.continuous import ContinuousEngineeringRunner
        from services.engineering.ledger import JsonContinuousLedger
        from services.engineering.loop import WorkItem, WorkKind
        from services.engineering.models import EngineeringTask, TaskStatus
        from services.engineering.runtime import EngineeringRuntime, ProviderClient
        from services.engineering.store import SQLiteEngineeringStore
        from services.engineering.worktree import WorktreeManager

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
        print(f"[DEBUG] Item fingerprint: {item.fingerprint}")
        ledger.register(item)
        task_id = f"work_{item.fingerprint[:20]}"
        print(f"[DEBUG] Task ID: {task_id}")
        task = EngineeringTask(
            id=task_id,
            title=item.title,
            repository=str(repo),
            status=TaskStatus.FAILED,
            attempts=2,
            max_attempts=2,
            last_error="old failure",
        )
        from services.engineering.models import TaskStatus
        from services.engineering.store import SQLiteEngineeringStore
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

        print(f"[DEBUG] result.completed = {result.completed}")
        print(f"[DEBUG] result.blocked = {result.blocked}")
        print(f"[DEBUG] result.iterations = {result.iterations}")
        print(f"[DEBUG] result.halt_reason = {result.halt_reason}")
        print(f"[DEBUG] item.fingerprint = {item.fingerprint}")
        print(f"[DEBUG] match = {result.completed == (item.fingerprint,)}")

        # Check if task was completed
        loaded = None
        from services.engineering.store import SQLiteEngineeringStore
        from services.engineering.models import TaskStatus
        store = SQLiteEngineeringStore(Path(td) / "state.db")
        loaded = store.get_task(task_id)
        print(f"[DEBUG] loaded.status = {loaded.status if loaded else 'None'}")
        print(f"[DEBUG] loaded.attempts = {loaded.attempts if loaded else 'None'}")
        print(f"[DEBUG] loaded.last_error = {loaded.last_error if loaded else 'None'}")

        # Assert
        assert result.completed == (item.fingerprint,), f"Expected {(item.fingerprint,)}, got {result.completed}"
        assert loaded.status == TaskStatus.SUCCEEDED, f"Expected SUCCEEDED, got {loaded.status}"
        assert loaded.attempts == 2, f"Expected 2, got {loaded.attempts}"
        assert loaded.max_attempts == 2, f"Expected 2, got {loaded.max_attempts}"
        assert loaded.last_error == "", f"Expected empty, got {loaded.last_error}"
        print("[SUCCESS] Test passed!")

if __name__ == "__main__":
    run_test()