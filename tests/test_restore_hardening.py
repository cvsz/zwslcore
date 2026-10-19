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
