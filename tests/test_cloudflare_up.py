"""Security regression tests for the Cloudflare Compose profile launcher."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class CloudflareUpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "repo"
        (self.root / "scripts" / "lib").mkdir(parents=True)
        shutil.copy(ROOT / "scripts/cloudflare-up.sh", self.root / "scripts/cloudflare-up.sh")
        shutil.copy(ROOT / "scripts/lib/env.sh", self.root / "scripts/lib/env.sh")
        shutil.copy(ROOT / ".env.cloudflare.example", self.root / ".env.cloudflare.example")
        (self.root / ".env").write_text("TEST=value\n", encoding="utf-8")
        (self.root / "compose.yaml").write_text("services: {}\n", encoding="utf-8")
        self.profile = self.root / ".env.cloudflare"
        self.profile.write_text(
            "OPENWEBUI_BIND_ADDRESS=127.0.0.1\nPROVIDER_PORT=18086\nOPENWEBUI_PORT=18087\n",
            encoding="utf-8",
        )
        self.profile.chmod(0o600)
        self.bin = Path(self.temp.name) / "bin"
        self.bin.mkdir()
        self.docker_log = Path(self.temp.name) / "docker.log"
        docker = self.bin / "docker"
        docker.write_text(
            "#!/bin/sh\nprintf '%s\\n' \"$*\" >> \"$DOCKER_LOG\"\nexit 0\n",
            encoding="utf-8",
        )
        docker.chmod(0o700)
        self.env = dict(os.environ, PATH=f"{self.bin}:{os.environ.get('PATH', '')}",
                        DOCKER_LOG=str(self.docker_log))

    def run_launcher(self):
        return subprocess.run(
            ["bash", str(self.root / "scripts/cloudflare-up.sh")],
            env=self.env, capture_output=True, text=True, timeout=10,
        )

    def test_profile_is_data_and_ports_are_used(self):
        marker = Path(self.temp.name) / "profile-was-executed"
        with self.profile.open("a", encoding="utf-8") as profile:
            profile.write(f"\n$(touch {marker})\n")
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())
        self.assertIn("127.0.0.1:18086", result.stdout)
        self.assertIn("127.0.0.1:18087", result.stdout)
        self.assertEqual(self.docker_log.read_text(encoding="utf-8").count(" config --quiet"), 1)
        self.assertEqual(self.docker_log.read_text(encoding="utf-8").count(" up --detach provider open-webui"), 1)

    def test_non_loopback_bind_is_rejected_before_docker(self):
        self.profile.write_text("OPENWEBUI_BIND_ADDRESS=0.0.0.0\n", encoding="utf-8")
        self.profile.chmod(0o600)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 2)
        self.assertIn("requires OPENWEBUI_BIND_ADDRESS=127.0.0.1", result.stderr)
        self.assertFalse(self.docker_log.exists())

    def test_open_permissions_and_invalid_ports_are_rejected(self):
        self.profile.chmod(0o644)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 2)
        self.assertIn("chmod 600", result.stderr)
        self.assertFalse(self.docker_log.exists())

        self.profile.write_text(
            "OPENWEBUI_BIND_ADDRESS=127.0.0.1\nPROVIDER_PORT=$(touch /tmp/nope)\n",
            encoding="utf-8",
        )
        self.profile.chmod(0o600)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid port", result.stderr)
        self.assertFalse(self.docker_log.exists())

    def test_port_bounds_use_decimal_not_shell_octal(self):
        self.profile.write_text(
            "OPENWEBUI_BIND_ADDRESS=127.0.0.1\nPROVIDER_PORT=080\nOPENWEBUI_PORT=65535\n",
            encoding="utf-8",
        )
        self.profile.chmod(0o600)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 0, result.stderr)

        self.docker_log.unlink()
        self.profile.write_text(
            "OPENWEBUI_BIND_ADDRESS=127.0.0.1\nPROVIDER_PORT=65536\nOPENWEBUI_PORT=3000\n",
            encoding="utf-8",
        )
        self.profile.chmod(0o600)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 2)
        self.assertIn("invalid port", result.stderr)
        self.assertFalse(self.docker_log.exists())

    def test_profile_symlink_is_rejected(self):
        backup = self.root / "profile-copy"
        self.profile.rename(backup)
        self.profile.symlink_to(backup)
        result = self.run_launcher()
        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink Cloudflare profile", result.stderr)
        self.assertFalse(self.docker_log.exists())

    def test_dangling_profile_symlink_is_rejected_without_replacing_it(self):
        self.profile.unlink()
        target = self.root / "missing-profile-target"
        self.profile.symlink_to(target)

        result = self.run_launcher()

        self.assertEqual(result.returncode, 2)
        self.assertIn("symlink Cloudflare profile", result.stderr)
        self.assertTrue(self.profile.is_symlink())
        self.assertFalse(target.exists())
        self.assertFalse(self.docker_log.exists())


if __name__ == "__main__":
    unittest.main()
