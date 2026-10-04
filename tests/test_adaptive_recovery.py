from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.engineering.models import EngineeringTask
from services.engineering.runtime import EngineeringRuntime, ProviderClient
from services.engineering.snapshot import RepositorySnapshotter
from services.engineering.store import SQLiteEngineeringStore


class AdaptiveRecoveryTests(unittest.TestCase):
    def test_quality_failure_promotes_model_once(self):
        with tempfile.TemporaryDirectory() as td:
            store = SQLiteEngineeringStore(Path(td) / "state.db")
            provider = ProviderClient(model="zeaz-fast")
            runtime = EngineeringRuntime(
                store,
                provider,
                model_ladder=("zeaz-fast", "zeaz-coder"),
            )
            self.assertEqual(
                runtime.promote_model("model proposed no file changes"),
                "zeaz-coder",
            )
            self.assertEqual(provider.model, "zeaz-coder")
            self.assertIsNone(runtime.promote_model("model proposed no file changes"))

    def test_validation_failure_does_not_promote_model(self):
        with tempfile.TemporaryDirectory() as td:
            store = SQLiteEngineeringStore(Path(td) / "state.db")
            provider = ProviderClient(model="zeaz-fast")
            runtime = EngineeringRuntime(
                store,
                provider,
                model_ladder=("zeaz-fast", "zeaz-coder"),
            )
            self.assertIsNone(runtime.promote_model("validation strict failed: tests"))
            self.assertEqual(provider.model, "zeaz-fast")

    def test_snapshot_prioritizes_task_relevant_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "services" / "engineering").mkdir(parents=True)
            (root / "services" / "provider").mkdir(parents=True)
            (root / "services" / "engineering" / "aaa.py").write_text(
                "engineering = 1\n" * 100,
                encoding="utf-8",
            )
            (root / "services" / "provider" / "diagnostics.py").write_text(
                "provider_diagnostics = 1\n",
                encoding="utf-8",
            )
            snapshot = RepositorySnapshotter(
                root,
                include_paths={"services"},
                max_total_bytes=256,
                priority_terms={"provider", "diagnostics"},
            ).snapshot()
            self.assertIn("services/provider/diagnostics.py", snapshot)
            self.assertIn("provider_diagnostics", snapshot)


if __name__ == "__main__":
    unittest.main()
