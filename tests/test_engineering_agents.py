from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.agents import get_agent, list_agents
from services.engineering.evidence import EvidenceExporter
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.permissions import PermissionRule, evaluate_permission
from services.engineering.runtime import EngineeringRuntime
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.tools import get_tool, list_tools
from services.engineering.worktree import WorktreeManager


class Provider:
    model = "zeaz-fast"

    def __init__(self):
        self.calls = []

    def preflight(self) -> None:
        return None

    def chat(self, prompt, system, **kwargs):
        self.calls.append({"prompt": prompt, **kwargs})
        if "Produce a concise implementation plan" in prompt:
            return "Inspect the scoped code and describe the minimal safe change."
        return json.dumps({
            "changes": [{"path": "services/example.py", "content": "value = 2" + chr(10)}]
        })


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "services").mkdir(parents=True)
    (repo / "services" / "example.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
    return repo


class PermissionTests(unittest.TestCase):
    def test_last_matching_rule_wins(self):
        rules = (
            PermissionRule("*", "*", "deny"),
            PermissionRule("edit", "*", "allow"),
            PermissionRule("edit", "secrets/*", "deny"),
        )
        self.assertEqual(evaluate_permission("edit", "services/a.py", rules).action, "allow")
        self.assertEqual(evaluate_permission("edit", "secrets/a.txt", rules).action, "deny")

    def test_builtin_profiles_are_fail_closed(self):
        names = {item.name for item in list_agents()}
        self.assertEqual(names, {"build", "explore", "general", "plan", "review"})
        self.assertEqual(get_agent("build").decide("edit", "services/a.py"), "allow")
        self.assertEqual(get_agent("plan").decide("edit", "services/a.py"), "deny")
        self.assertEqual(get_agent("review").decide("commit", "*"), "deny")
        self.assertEqual(get_agent("general").decide("commit", "*"), "deny")

    def test_tool_registry_is_declarative(self):
        names = {item.name for item in list_tools()}
        self.assertEqual(
            names,
            {"snapshot", "plan", "edit", "validate", "review", "commit", "delegate"},
        )
        self.assertTrue(get_tool("edit").mutates_repository)
        self.assertFalse(get_tool("review").mutates_repository)


class RuntimeAgentTests(unittest.TestCase):
    def test_plan_call_uses_bounded_output_budget(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            provider = Provider()
            runtime = EngineeringRuntime(
                store,
                provider,
                worktrees=WorktreeManager(root / "worktrees"),
                evidence=EvidenceExporter(store, root / "evidence"),
            )
            task = EngineeringTask(title="bounded plan", repository=str(repo))

            result = runtime.run(
                task,
                allowed_paths={"services"},
                agent_name="plan",
            )

            self.assertEqual(result.status, TaskStatus.SUCCEEDED)
            self.assertEqual(provider.calls[0]["max_tokens"], EngineeringRuntime.PLAN_MAX_TOKENS)
            self.assertIn("five short bullet points", provider.calls[0]["prompt"])

    def test_plan_agent_stops_before_editing(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            runtime = EngineeringRuntime(
                store,
                Provider(),
                worktrees=WorktreeManager(root / "worktrees"),
                evidence=EvidenceExporter(store, root / "evidence"),
            )
            task = EngineeringTask(title="plan only", repository=str(repo))
            result = runtime.run(
                task,
                allowed_paths={"services"},
                agent_name="plan",
            )
            self.assertEqual(result.status, TaskStatus.SUCCEEDED)
            self.assertTrue(result.metadata["read_only_result"])
            self.assertEqual(result.metadata["agent"], "plan")
            worktree = Path(result.worktree_path)
            self.assertEqual(
                (worktree / "services" / "example.py").read_text(encoding="utf-8"),
                "value = 1\n",
            )
            checkpoint = store.latest_checkpoint(task.id)
            self.assertEqual(checkpoint.phase, "READ_ONLY_COMPLETE")

    def test_build_agent_edits_and_validates(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            runtime = EngineeringRuntime(
                store,
                Provider(),
                worktrees=WorktreeManager(root / "worktrees"),
                evidence=EvidenceExporter(store, root / "evidence"),
            )
            task = EngineeringTask(title="build", repository=str(repo))
            result = runtime.run(
                task,
                allowed_paths={"services"},
                validators=["git diff --check"],
                agent_name="build",
            )
            self.assertEqual(result.status, TaskStatus.SUCCEEDED)
            self.assertEqual(result.metadata["agent"], "build")
            self.assertEqual(
                (Path(result.worktree_path) / "services" / "example.py").read_text(encoding="utf-8"),
                "value = 2\n",
            )

    def test_general_agent_cannot_commit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            runtime = EngineeringRuntime(
                store,
                Provider(),
                worktrees=WorktreeManager(root / "worktrees"),
                evidence=EvidenceExporter(store, root / "evidence"),
            )
            task = EngineeringTask(title="general", repository=str(repo))
            with self.assertRaisesRegex(PermissionError, "commit"):
                runtime.run(
                    task,
                    allowed_paths={"services"},
                    validators=["git diff --check"],
                    agent_name="general",
                    commit=True,
                )


if __name__ == "__main__":
    unittest.main()
