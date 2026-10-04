from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from services.engineering.hardware import HardwareProfile
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.loop import WorkItem, WorkKind
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.tui import build_dashboard


class EngineeringTuiTests(unittest.TestCase):
    def test_dashboard_renders_queue_task_model_and_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "engineering.db")
            ledger = JsonContinuousLedger(root / "continuous.json")

            item = WorkItem(
                "Improve provider diagnostics",
                WorkKind.REPAIR,
                priority=80,
                max_attempts=2,
            )
            ledger.register(item)

            task_id = f"work_{item.fingerprint[:20]}"
            task = EngineeringTask(
                id=task_id,
                title=item.title,
                status=TaskStatus.EDITING,
                attempts=1,
                max_attempts=2,
                metadata={
                    "phase_cursor": "EDITING",
                    "evidence_sha256": "abc123",
                },
            )
            store.save_task(task)
            ledger.update(
                item.fingerprint,
                state="RUNNING",
                attempts=1,
                task_id=task_id,
            )

            profile = HardwareProfile(
                os="linux",
                architecture="x86_64",
                cpu="cpu",
                logical_cpus=8,
                ram_total_gb=14.6,
                ram_available_gb=13.0,
                gpu="none-detected",
                profile="CPU_MEDIUM",
                accelerator_backend="cpu",
                gpu_memory_gb=0.0,
            )
            env = {
                "ZEAZ_ENGINEERING_MODEL": "auto",
                "ZEAZ_FAST_MODEL": "qwen2.5-coder:3b",
                "ZEAZ_CODER_MODEL": "qwen2.5-coder:7b",
                "ZEAZ_REASONING_MODEL": "qwen3:8b",
                "ZEAZ_LOCAL_MODEL": "qwen2.5-coder:7b",
                "ZEAZ_OLLAMA_CONTEXT_LENGTH": "4096",
            }

            with patch("services.engineering.tui.detect_hardware", return_value=profile):
                text = build_dashboard(
                    store,
                    ledger,
                    env=env,
                    color=False,
                    width=120,
                    now=task.updated_at + 3,
                )

            self.assertIn("zwslcore engineering control plane", text)
            self.assertIn("CPU_MEDIUM", text)
            self.assertIn("selected=zeaz-fast", text)
            self.assertIn("Improve provider diagnostics", text)
            self.assertIn("EDITING", text)
            self.assertIn("evidence=yes", text)
            self.assertNotIn("RECOVERY", text)
            self.assertNotIn("\x1b[", text)

    def test_empty_dashboard_is_stable(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "engineering.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            profile = HardwareProfile(
                os="linux",
                architecture="x86_64",
                cpu="cpu",
                logical_cpus=4,
                ram_total_gb=8,
                ram_available_gb=7,
                gpu="none-detected",
                profile="CPU_SMALL",
            )
            with patch("services.engineering.tui.detect_hardware", return_value=profile):
                text = build_dashboard(
                    store,
                    ledger,
                    env={"ZEAZ_ENGINEERING_MODEL": "zeaz-fast"},
                    color=False,
                    width=90,
                )
            self.assertIn("no queued work", text)
            self.assertIn("no engineering tasks", text)



    def test_blocked_dashboard_shows_recover_command_and_ladder(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "engineering.db")
            ledger = JsonContinuousLedger(root / "continuous.json")
            item = WorkItem(
                "Improve provider diagnostics",
                WorkKind.REPAIR,
                priority=80,
                max_attempts=2,
            )
            ledger.register(item)
            task_id = f"work_{item.fingerprint[:20]}"
            task = EngineeringTask(
                id=task_id,
                title=item.title,
                status=TaskStatus.FAILED,
                attempts=2,
                max_attempts=2,
                metadata={
                    "phase_cursor": "FAILED",
                    "evidence_sha256": "abc123",
                    "model_escalated_to": "zeaz-coder",
                },
            )
            store.save_task(task)
            ledger.update(
                item.fingerprint,
                state="BLOCKED",
                attempts=2,
                task_id=task_id,
            )
            profile = HardwareProfile(
                os="linux",
                architecture="x86_64",
                cpu="cpu",
                logical_cpus=8,
                ram_total_gb=14.6,
                ram_available_gb=12.8,
                gpu="none-detected",
                profile="CPU_MEDIUM",
                accelerator_backend="cpu",
                gpu_memory_gb=0.0,
            )
            env = {
                "ZEAZ_ENGINEERING_MODEL": "auto",
                "ZEAZ_FAST_MODEL": "qwen2.5-coder:3b",
                "ZEAZ_CODER_MODEL": "qwen2.5-coder:7b",
                "ZEAZ_REASONING_MODEL": "qwen3:8b",
                "ZEAZ_LOCAL_MODEL": "qwen2.5-coder:7b",
                "ZEAZ_OLLAMA_CONTEXT_LENGTH": "4096",
            }
            with patch("services.engineering.tui.detect_hardware", return_value=profile):
                text = build_dashboard(
                    store,
                    ledger,
                    env=env,
                    color=False,
                    width=140,
                )
            self.assertIn("RECOVERY", text)
            self.assertIn("recover --max-iterations 4", text)
            self.assertIn("ladder=zeaz-fast→zeaz-coder", text)
            self.assertIn("snapshot_budget=8192", text)
            self.assertIn("zeaz-coder", text)


if __name__ == "__main__":
    unittest.main()
