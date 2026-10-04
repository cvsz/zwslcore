from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.agents import AgentConfigError, AgentRegistry
from services.engineering.delegation import make_child_task
from services.engineering.evidence import EvidenceExporter
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.runtime import EngineeringRuntime
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.worktree import WorktreeManager


class CapturingProvider:
    model = "zeaz-fast"

    def __init__(self) -> None:
        self.systems: list[str] = []

    def preflight(self) -> None:
        return None

    def chat(self, prompt, system, **kwargs):
        self.systems.append(system)
        if "Produce a concise implementation plan" in prompt:
            return "Plan safely."
        return json.dumps({
            "changes": [{"path": "services/example.py", "content": "value = 2\n"}]
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


class AgentRegistryTests(unittest.TestCase):
    def write_config(self, root: Path, payload: dict) -> Path:
        path = root / "agents.json"
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def test_missing_config_keeps_builtins(self):
        with tempfile.TemporaryDirectory() as td:
            registry = AgentRegistry(Path(td) / "missing.json")
            self.assertEqual(
                {item.name for item in registry.list()},
                {"build", "explore", "general", "plan", "review"},
            )

    def test_custom_agent_inherits_and_last_rule_wins(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_config(root, {
                "agents": {
                    "safe-implementer": {
                        "extends": "general",
                        "mode": "subagent",
                        "description": "Scoped implementation agent.",
                        "permissions": [
                            {"permission": "edit", "pattern": "*", "action": "deny"},
                            {"permission": "edit", "pattern": "services/safe/*", "action": "allow"},
                        ],
                    }
                }
            })
            agent = AgentRegistry(path).get("safe-implementer")
            self.assertEqual(agent.mode, "subagent")
            self.assertEqual(agent.decide("edit", "services/unsafe/a.py"), "deny")
            self.assertEqual(agent.decide("edit", "services/safe/a.py"), "allow")
            self.assertEqual(agent.decide("commit", "*"), "deny")
            self.assertEqual(agent.source, str(path))

    def test_default_custom_base_is_read_only_plan(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_config(root, {
                "agents": {
                    "architect": {
                        "description": "Architecture only",
                        "prompt": "Focus on dependency boundaries.",
                    }
                }
            })
            agent = AgentRegistry(path).get("architect")
            self.assertEqual(agent.mode, "primary")
            self.assertEqual(agent.decide("plan", "*"), "allow")
            self.assertEqual(agent.decide("edit", "*"), "deny")
            self.assertEqual(agent.prompt, "Focus on dependency boundaries.")

    def test_builtin_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_config(root, {
                "agents": {"build": {"extends": "plan"}}
            })
            with self.assertRaisesRegex(AgentConfigError, "collides"):
                AgentRegistry(path)

    def test_invalid_base_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_config(root, {
                "agents": {"custom": {"extends": "other-custom"}}
            })
            with self.assertRaisesRegex(AgentConfigError, "built-in"):
                AgentRegistry(path)

    def test_disabled_custom_agent_is_not_registered(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_config(root, {
                "agents": {"disabled": {"enabled": False}}
            })
            registry = AgentRegistry(path)
            with self.assertRaisesRegex(ValueError, "unknown agent"):
                registry.get("disabled")

    def test_custom_subagent_can_be_delegated(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            path = self.write_config(root, {
                "agents": {
                    "inspector": {
                        "extends": "review",
                        "mode": "subagent",
                    }
                }
            })
            registry = AgentRegistry(path)
            parent = EngineeringTask(title="parent")
            child = make_child_task(
                parent,
                title="inspect",
                description="review provider",
                agent_name="inspector",
                agent_registry=registry,
            )
            self.assertEqual(child.metadata["delegated_agent"], "inspector")


class RuntimeCustomAgentTests(unittest.TestCase):
    def test_custom_prompt_is_applied_but_read_only_policy_still_wins(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            config = root / "agents.json"
            config.write_text(json.dumps({
                "agents": {
                    "architect": {
                        "extends": "plan",
                        "prompt": "Focus on interfaces and failure boundaries.",
                    }
                }
            }), encoding="utf-8")
            repo = make_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            provider = CapturingProvider()
            runtime = EngineeringRuntime(
                store,
                provider,
                worktrees=WorktreeManager(root / "worktrees"),
                evidence=EvidenceExporter(store, root / "evidence"),
                agent_registry=AgentRegistry(config),
            )
            task = EngineeringTask(title="architecture", repository=str(repo))
            result = runtime.run(
                task,
                allowed_paths={"services"},
                agent_name="architect",
            )
            self.assertEqual(result.status, TaskStatus.SUCCEEDED)
            self.assertTrue(result.metadata["read_only_result"])
            self.assertEqual(result.metadata["agent"], "architect")
            self.assertTrue(result.metadata["agent_custom_prompt"])
            self.assertTrue(
                any(
                    "Focus on interfaces and failure boundaries." in system
                    for system in provider.systems
                )
            )
            self.assertEqual(
                (Path(result.worktree_path) / "services" / "example.py").read_text(encoding="utf-8"),
                "value = 1\n",
            )


if __name__ == "__main__":
    unittest.main()
