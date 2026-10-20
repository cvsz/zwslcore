from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.lib.env_file import write_private_file


class AtomicEnvironmentFileTests(unittest.TestCase):
    def test_replaces_file_atomically_with_private_permissions(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("OLD=value\n", encoding="utf-8")

            write_private_file(path, "NEW=value\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "NEW=value\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(directory).glob(".env.*.tmp")), [])

    def test_failed_replace_preserves_existing_file_and_removes_temporary_file(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".env"
            path.write_text("KEEP=unchanged\n", encoding="utf-8")
            path.chmod(0o600)

            with patch("scripts.lib.env_file.os.replace", side_effect=OSError("simulated replace failure")):
                with self.assertRaisesRegex(OSError, "simulated replace failure"):
                    write_private_file(path, "NEW=value\n")

            self.assertEqual(path.read_text(encoding="utf-8"), "KEEP=unchanged\n")
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(list(Path(directory).glob(".env.*.tmp")), [])

    def test_refuses_symlink_destination_without_touching_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "outside"
            target.write_text("KEEP=unchanged\n", encoding="utf-8")
            link = root / ".env"
            link.symlink_to(target)

            with self.assertRaisesRegex(ValueError, "non-symlink"):
                write_private_file(link, "NEW=value\n")

            self.assertEqual(target.read_text(encoding="utf-8"), "KEEP=unchanged\n")


if __name__ == "__main__":
    unittest.main()
