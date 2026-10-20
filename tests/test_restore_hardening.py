from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from scripts.restore import RestoreError, restore_backup


def _minimal_backup(root: Path) -> Path:
    backup = root / "backup"
    backup.mkdir()
    manifest = json.dumps({"schema": 1, "files": {}}).encode()
    (backup / "manifest.json").write_bytes(manifest)
    (backup / "manifest.sha256").write_text(
        hashlib.sha256(manifest).hexdigest() + "  manifest.json\n", encoding="utf-8"
    )
    return backup


class RestoreHardeningTests(unittest.TestCase):
    def test_target_inside_backup_is_refused_without_creating_anything(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = _minimal_backup(Path(directory))
            before = sorted(path.name for path in backup.iterdir())
            with self.assertRaisesRegex(RestoreError, "outside the backup directory"):
                restore_backup(backup, backup / "nested-target")
            self.assertEqual(sorted(path.name for path in backup.iterdir()), before)

    def test_symlink_target_is_rejected_without_touching_its_destination(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            backup = _minimal_backup(root)
            destination = root / "existing-empty-directory"
            destination.mkdir(mode=0o755)
            target = root / "restore-target"
            target.symlink_to(destination, target_is_directory=True)

            with self.assertRaisesRegex(RestoreError, "symlink path components"):
                restore_backup(backup, target)

            self.assertTrue(target.is_symlink())
            self.assertEqual(list(destination.iterdir()), [])
            self.assertEqual(destination.stat().st_mode & 0o777, 0o755)

    def test_automatic_target_inside_custom_tmpdir_backup_is_removed_and_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = _minimal_backup(Path(directory))
            before = sorted(path.name for path in backup.iterdir())
            previous_tempdir = tempfile.tempdir
            tempfile.tempdir = str(backup)
            try:
                with self.assertRaisesRegex(RestoreError, "outside the backup directory"):
                    restore_backup(backup)
                self.assertEqual(sorted(path.name for path in backup.iterdir()), before)
            finally:
                tempfile.tempdir = previous_tempdir

    def test_empty_manifest_checksum_is_a_clean_restore_error(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = _minimal_backup(Path(directory))
            (backup / "manifest.sha256").write_text("", encoding="utf-8")
            with self.assertRaisesRegex(RestoreError, "checksum file is empty"):
                restore_backup(backup, Path(directory) / "target")

    def test_non_object_manifest_entry_is_a_clean_restore_error(self):
        with tempfile.TemporaryDirectory() as directory:
            backup = _minimal_backup(Path(directory))
            manifest = json.dumps({"schema": 1, "files": {"state/engineering.db": "oops"}}).encode()
            (backup / "manifest.json").write_bytes(manifest)
            (backup / "manifest.sha256").write_text(
                hashlib.sha256(manifest).hexdigest() + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(RestoreError, "not an object"):
                restore_backup(backup, Path(directory) / "target")


if __name__ == "__main__":
    unittest.main()
