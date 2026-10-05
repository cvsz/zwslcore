from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.backup import BackupError, create_backup
from scripts.restore import RestoreError, restore_backup
from services.engineering.evidence import EvidenceExporter
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.loop import WorkItem, WorkKind
from services.engineering.models import Checkpoint, EngineeringTask, TaskStatus
from services.engineering.store import SQLiteEngineeringStore


REPOSITORY = Path(__file__).resolve().parents[1]


class BackupRestoreTests(unittest.TestCase):
    def _source(self, root: Path) -> tuple[Path, SQLiteEngineeringStore, JsonContinuousLedger, str]:
        source = root / "source"
        state = source / "state"
        state.mkdir(parents=True)
        store = SQLiteEngineeringStore(state / "engineering.db")
        task = EngineeringTask(title="backup fixture", status=TaskStatus.SUCCEEDED)
        store.save_task(task)
        store.save_checkpoint(Checkpoint(task_id=task.id, phase="DONE", payload={"ok": True}))
        ledger = JsonContinuousLedger(state / "continuous.json")
        item = WorkItem("backup queue fixture", WorkKind.REPAIR)
        ledger.register(item)
        EvidenceExporter(store, source / "evidence").export(task)
        cache = source / "cache"
        cache.mkdir()
        (cache / "catalog.json").write_text('{"schema":1,"items":[]}', encoding="utf-8")
        return source, store, ledger, task.id

    def test_online_backup_and_isolated_restore_verify_all_captured_components(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, live_store, live_ledger, task_id = self._source(root)
            backup_path = root / "backup"
            restored = root / "isolated-restore"

            with patch("scripts.backup._runtime_metadata", return_value={"python": "test", "containers": {}}):
                result = create_backup(
                    source_root=source,
                    repository_root=REPOSITORY,
                    output=backup_path,
                )
            self.assertEqual(result, backup_path)
            self.assertEqual(backup_path.stat().st_mode & 0o777, 0o700)
            self.assertEqual((backup_path / "content/state/engineering.db").stat().st_mode & 0o777, 0o600)

            manifest = json.loads((backup_path / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["sqlite"]["integrity_check"], "ok")
            self.assertEqual(manifest["sqlite"]["row_counts"]["tasks"], 1)
            self.assertEqual(manifest["ledger"]["active_records"], 1)
            self.assertTrue(any("Open WebUI persistent volume" in item for item in manifest["excluded"]))

            restore_path = restore_backup(backup_path, restored)
            report = json.loads((restore_path / "restore-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PARTIAL")
            self.assertEqual(report["checks"]["engineering_sqlite"]["tasks"], 1)
            self.assertEqual(report["checks"]["engineering_sqlite"]["checkpoints"], 1)
            self.assertEqual(report["checks"]["continuous_ledger"]["active_records"], 1)
            self.assertEqual(report["checks"]["evidence"]["checksums_passed"], 1)
            self.assertEqual(report["checks"]["cache"]["json_files_readable"], 1)
            self.assertTrue(EvidenceExporter(live_store, source / "evidence").verify(task_id))
            self.assertEqual(len(live_ledger.records()), 1)
            self.assertTrue((source / "state/engineering.db").exists())

    def test_restore_rejects_modified_content_without_touching_source(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, _, _, _ = self._source(root)
            backup_path = root / "backup"
            with patch("scripts.backup._runtime_metadata", return_value={"python": "test", "containers": {}}):
                create_backup(source_root=source, repository_root=REPOSITORY, output=backup_path)
            (backup_path / "content/cache/catalog.json").write_text("{}", encoding="utf-8")

            with self.assertRaisesRegex(RestoreError, "checksum or size mismatch"):
                restore_backup(backup_path, root / "bad-restore")
            self.assertTrue((source / "state/engineering.db").exists())

    def test_backup_refuses_active_engineering_task(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, store, _, _ = self._source(root)
            active = EngineeringTask(title="active", status=TaskStatus.EDITING)
            store.save_task(active)
            with patch("scripts.backup._runtime_metadata", return_value={"python": "test", "containers": {}}):
                with self.assertRaisesRegex(BackupError, "while engineering tasks are active"):
                    create_backup(
                        source_root=source,
                        repository_root=REPOSITORY,
                        output=root / "must-not-exist",
                    )
            self.assertFalse((root / "must-not-exist").exists())

    def test_webui_user_data_capture_requires_explicit_encryption_recipient(self):
        with tempfile.TemporaryDirectory() as td:
            source, _, _, _ = self._source(Path(td))
            with patch("scripts.backup._runtime_metadata", return_value={"python": "test", "containers": {}}):
                with self.assertRaisesRegex(BackupError, "requires --gpg-recipient"):
                    create_backup(
                        source_root=source,
                        repository_root=REPOSITORY,
                        output=Path(td) / "must-not-exist",
                        include_webui_volume=True,
                    )

    def test_recreate_policy_is_explicit_and_completes_declared_restore_scope(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, _, _, _ = self._source(root)
            backup_path = root / "backup"
            restored = root / "isolated-restore"
            with patch("scripts.backup._runtime_metadata", return_value={"python": "test", "containers": {}}):
                create_backup(
                    source_root=source,
                    repository_root=REPOSITORY,
                    output=backup_path,
                    recreate_webui_data=True,
                )

            manifest = json.loads((backup_path / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["policy"]["open_webui_user_data"], "recreate")
            self.assertIsNone(manifest["docker_user_data"])
            self.assertTrue(any("user-authorized recreate policy" in item for item in manifest["excluded"]))

            restore_path = restore_backup(backup_path, restored)
            report = json.loads((restore_path / "restore-report.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["checks"]["open_webui_user_data"]["policy"], "recreate")
            self.assertTrue(report["checks"]["open_webui_user_data"]["complete_for_declared_policy"])

    def test_webui_data_policies_are_mutually_exclusive(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source, _, _, _ = self._source(root)
            with patch("scripts.backup._runtime_metadata", return_value={"python": "test", "containers": {}}):
                with self.assertRaisesRegex(BackupError, "choose either"):
                    create_backup(
                        source_root=source,
                        repository_root=REPOSITORY,
                        output=root / "must-not-exist",
                        include_webui_volume=True,
                        recreate_webui_data=True,
                    )
            self.assertFalse((root / "must-not-exist").exists())


if __name__ == "__main__":
    unittest.main()
