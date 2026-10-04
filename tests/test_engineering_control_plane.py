from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.continuous import ContinuousEngineeringRunner
from services.engineering.hardware import HardwareProfile
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.loop import ContinuousEngineeringLoop, LoopPolicy, WorkItem, WorkKind
from services.provider.zeaz_provider.cost import CostClass, CostPolicy, cost_allowed, cost_rank
from services.engineering.models import Checkpoint, EngineeringTask, TaskStatus
from services.engineering.review import SecurityGate, StaticReviewer
from services.engineering.runtime import EngineeringRuntime
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
            self.assertTrue(manager._marker(target).exists())
            self.assertFalse((target / ".zwslcore-managed").exists())
            status = subprocess.run(
                ["git", "-C", str(target), "status", "--porcelain"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout
            self.assertEqual(status, "")
            self.assertTrue(branch.startswith("agent/"))
            manager.remove(repo, target)
            self.assertFalse(manager._marker(target).exists())


class NewFileReviewRegressionTests(unittest.TestCase):
    def test_intent_to_add_exposes_new_file_in_diff(self):
        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
            (repo / "new.py").write_text('api_key = "sk-abcdefghijklmnopqrstuvwxyz"\n', encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "-N", "--", "."], check=True)
            diff = subprocess.run(
                ["git", "-C", str(repo), "diff", "--no-ext-diff", "--binary"],
                check=True,
                text=True,
                capture_output=True,
            ).stdout
            findings = StaticReviewer().review(diff)
            self.assertTrue(any(f.category == "secret" for f in findings))


class HardwareProfileTests(unittest.TestCase):
    def test_cpu_medium_model_selection(self):
        profile = HardwareProfile(
            os="linux",
            architecture="x86_64",
            cpu="cpu",
            logical_cpus=8,
            ram_total_gb=18,
            ram_available_gb=13,
            gpu="none-detected",
            profile="CPU_MEDIUM",
        )
        models = profile.recommended_models()
        self.assertEqual(models["fast"], "qwen2.5-coder:3b")
        self.assertEqual(models["coder"], "qwen2.5-coder:7b")
        self.assertEqual(models["reasoning"], "qwen2.5-coder:7b")
        self.assertEqual(models["default"], "qwen2.5-coder:7b")


class CostPolicyTests(unittest.TestCase):
    def test_zero_cost_rejects_paid_and_unknown(self):
        self.assertTrue(cost_allowed(CostClass.FREE_LOCAL, CostPolicy.ZERO_COST_ONLY))
        self.assertTrue(cost_allowed(CostClass.FREE_REMOTE, CostPolicy.ZERO_COST_ONLY))
        self.assertFalse(cost_allowed(CostClass.PAID_PLATFORM, CostPolicy.ZERO_COST_ONLY))
        self.assertFalse(cost_allowed(CostClass.UNKNOWN, CostPolicy.ZERO_COST_ONLY))

    def test_prefer_zero_cost_rank(self):
        self.assertLess(cost_rank(CostClass.FREE_LOCAL), cost_rank(CostClass.FREE_REMOTE))
        self.assertLess(cost_rank(CostClass.FREE_REMOTE), cost_rank(CostClass.CUSTOMER_KEY))


class ContinuousLedgerTests(unittest.TestCase):
    def test_attempt_budget_survives_restart(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = JsonContinuousLedger(Path(td) / "continuous.json")
            item = WorkItem("repair", WorkKind.REPAIR, max_attempts=2)
            ledger.register(item)
            ledger.update(item.fingerprint, attempts=1, state="PENDING")
            pending = ledger.pending()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0].max_attempts, 1)
            ledger.update(item.fingerprint, attempts=2, state="BLOCKED")
            self.assertEqual(ledger.pending(), [])
            retried = ledger.pending(retry_blocked=True)
            self.assertEqual(len(retried), 1)
            self.assertEqual(retried[0].max_attempts, 2)

    def test_atomic_record_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            ledger = JsonContinuousLedger(Path(td) / "continuous.json")
            item = WorkItem("feature", WorkKind.IMPLEMENT_FEATURE, priority=80)
            ledger.register(item)
            records = ledger.records()
            self.assertEqual(records[0]["title"], "feature")
            self.assertEqual(records[0]["state"], "PENDING")


class LoopCheckpointTests(unittest.TestCase):
    def test_attempt_exhaustion_checkpoint_is_blocked(self):
        checkpoints = []
        item = WorkItem("repair", WorkKind.REPAIR, max_attempts=1)
        result = ContinuousEngineeringLoop(
            lambda work: object(),
            lambda work, result: (False, ()),
            checkpoint=checkpoints.append,
        ).run([item])
        self.assertEqual(len(result.blocked), 1)
        self.assertEqual(checkpoints[-1]["state"], "BLOCKED_ATTEMPTS")


class SnapshotScopeTests(unittest.TestCase):
    def test_scope_limits_context(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "services").mkdir()
            (root / "docs").mkdir()
            (root / "services" / "app.py").write_text("service-content\n", encoding="utf-8")
            (root / "docs" / "large.md").write_text("docs-content\n" * 1000, encoding="utf-8")
            text = RepositorySnapshotter(root, include_paths={"services"}).snapshot()
            self.assertIn("service-content", text)
            self.assertNotIn("docs-content", text)

    def test_default_snapshot_budget_is_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            for index in range(20):
                (root / f"file-{index}.txt").write_text("x" * 20000, encoding="utf-8")
            text = RepositorySnapshotter(root).snapshot()
            self.assertLessEqual(len(text.encode("utf-8")), 96 * 1024)


class ProviderPreflightTests(unittest.TestCase):
    def test_preflight_failure_does_not_consume_attempt_or_create_worktree(self):
        class FailingProvider:
            model = "zeaz-local"

            def preflight(self):
                raise RuntimeError("provider HTTP 502 for /health/ready: upstream unavailable")

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            repo.mkdir()
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
            (repo / "README.md").write_text("base\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
            subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)

            store = SQLiteEngineeringStore(Path(td) / "state.db")
            manager = WorktreeManager(Path(td) / "worktrees")
            task = EngineeringTask(title="preflight", repository=str(repo))
            runtime = EngineeringRuntime(
                store,
                FailingProvider(),
                worktrees=manager,
            )

            with self.assertRaisesRegex(RuntimeError, "provider HTTP 502"):
                runtime.run(task)

            loaded = store.get_task(task.id)
            self.assertEqual(loaded.attempts, 0)
            self.assertEqual(loaded.worktree_path, "")
            self.assertEqual(list(manager.base_dir.glob("*")), [])


class ContinuousRetryResetTests(unittest.TestCase):
    def test_retry_blocked_resets_task_attempt_budget_and_state(self):
        class NoopProvider:
            model = "zeaz-local"

            def preflight(self):
                return None

            def chat(self, prompt, system):
                if "Produce a concise implementation plan" in prompt:
                    return "plan"
                return '{"changes":[{"path":"services/example.py","content":"print(\"ok\")\n"}]}'

        with tempfile.TemporaryDirectory() as td:
            repo = Path(td) / "repo"
            (repo / "services").mkdir(parents=True)
            subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
            subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
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
            record = ledger.register(item)
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
            result = runner.run(max_iterations=1, retry_blocked=True)

            loaded = store.get_task(task_id)
            self.assertEqual(result.blocked, ())
            self.assertEqual(loaded.status, TaskStatus.SUCCEEDED)
            self.assertEqual(loaded.attempts, 1)
            self.assertEqual(loaded.max_attempts, 2)
            self.assertEqual(loaded.last_error, "")


if __name__ == "__main__":
    unittest.main()
