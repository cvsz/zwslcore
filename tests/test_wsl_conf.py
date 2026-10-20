from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from scripts.wsl_conf import ensure_settings


class WslConfTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path = Path(self.temp_dir.name) / "wsl.conf"

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def test_adds_only_required_keys_and_preserves_existing_content(self) -> None:
        initial = "# keep this comment\n[boot]\ncommand=/usr/local/bin/start\n[interop]\nenabled=false\n"
        self.path.write_text(initial)

        self.assertTrue(ensure_settings(self.path, "cvsz"))
        updated = self.path.read_text()
        self.assertIn("# keep this comment\n", updated)
        self.assertIn("command=/usr/local/bin/start\n", updated)
        self.assertIn("enabled=false\n", updated)
        self.assertIn("systemd=true\n", updated)
        self.assertIn("default=cvsz\n", updated)

    def test_preserves_existing_user_default_and_is_idempotent(self) -> None:
        self.path.write_text("[boot]\nsystemd=true\n[user]\ndefault=existing\n")

        self.assertFalse(ensure_settings(self.path, "cvsz"))
        self.assertEqual(self.path.read_text(), "[boot]\nsystemd=true\n[user]\ndefault=existing\n")

    def test_refuses_to_override_systemd_false(self) -> None:
        original = "[boot]\nsystemd=false\n"
        self.path.write_text(original)

        with self.assertRaisesRegex(ValueError, "refusing to override"):
            ensure_settings(self.path, "cvsz")
        self.assertEqual(self.path.read_text(), original)

    def test_rejects_symlink_and_invalid_user(self) -> None:
        target = Path(self.temp_dir.name) / "target"
        target.write_text("preserve")
        self.path.symlink_to(target)
        with self.assertRaisesRegex(ValueError, "symlinked"):
            ensure_settings(self.path, "cvsz")
        self.path.unlink()
        with self.assertRaisesRegex(ValueError, "valid Linux"):
            ensure_settings(self.path, "bad;user")
        self.assertEqual(target.read_text(), "preserve")

    @unittest.skipUnless(os.name == "posix", "POSIX file modes are unavailable")
    def test_preserves_existing_mode(self) -> None:
        self.path.write_text("# existing\n")
        self.path.chmod(0o640)
        ensure_settings(self.path, "cvsz")
        self.assertEqual(self.path.stat().st_mode & 0o777, 0o640)


if __name__ == "__main__":
    unittest.main()
