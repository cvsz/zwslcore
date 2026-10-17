"""Offline smoke checks for the opt-in Cloud Shell tunnel lifecycle CLI."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "zcloud-tunnel.sh"


class CloudShellTunnelTests(unittest.TestCase):
    def test_bash_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_status_without_running_supervisor(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, XDG_STATE_HOME=f"{home}/state")
            result = subprocess.run(
                ["bash", str(SCRIPT), "status"],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("Supervisor STOPPED", result.stdout)

    def test_insecure_config_permissions_rejected(self):
        with tempfile.TemporaryDirectory() as home:
            config = Path(home) / "config.yml"
            config.write_text("tunnel: sample\\ningress:\\n  - service: http_status:404\\n")
            config.chmod(0o644)
            fake_bin = Path(home) / "bin"
            fake_bin.mkdir()
            cloudflared = fake_bin / "cloudflared"
            cloudflared.write_text("#!/bin/sh\\nexit 0\\n")
            cloudflared.chmod(0o700)
            env = dict(os.environ, HOME=home, XDG_STATE_HOME=f"{home}/state",
                       ZCLOUD_CONFIG=str(config),
                       PATH=f"{fake_bin}:{os.environ.get('PATH', '')}")
            result = subprocess.run(
                ["bash", str(SCRIPT), "preflight"],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("permissions", result.stderr)

    def test_missing_config_fails_closed(self):
        with tempfile.TemporaryDirectory() as home:
            env = dict(os.environ, HOME=home, XDG_STATE_HOME=f"{home}/state",
                       ZCLOUD_CONFIG=f"{home}/no-config.yml")
            result = subprocess.run(
                ["bash", str(SCRIPT), "preflight"],
                env=env, capture_output=True, text=True, timeout=10,
            )
            self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
