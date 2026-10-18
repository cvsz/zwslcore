"""Regression checks for the non-disruptive Cloudflare tunnel staging flow."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cloudflare-tunnel-migrate.py"
spec = importlib.util.spec_from_file_location("cloudflare_tunnel_migrate", SCRIPT)
migrate = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(migrate)

SOURCE = """tunnel: 09f176a3-8ebe-4e08-aae7-c56e4b8d7314
credentials-file: /home/user/.cloudflared/old.json
ingress:
  - hostname: ssh.example.org
    service: ssh://127.0.0.1:22
  - service: http_status:404
"""
TARGET = "45667e7e-7383-4265-b53e-6a9e770a8554"


class TunnelMigrationTests(unittest.TestCase):
    def test_exact_ssh_hostname_route(self):
        self.assertTrue(migrate.ssh_ingress_present(SOURCE, "ssh.example.org"))
        self.assertFalse(migrate.ssh_ingress_present(SOURCE, "other.example.org"))
        self.assertFalse(migrate.ssh_ingress_present(
            SOURCE.replace("ssh://127.0.0.1:22", "http://10.88.0.3:22"),
            "ssh.example.org",
        ))

    def test_target_uuid_required(self):
        with self.assertRaises(migrate.MigrationError):
            migrate.validated_uuid("zwslcore")

    def test_stage_requires_destination_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            with self.assertRaises(migrate.MigrationError):
                migrate.stage(base / "config.yml", base / "state",
                              TARGET, base / "missing.json", SOURCE, "ssh.example.org")
            self.assertFalse((base / "state").exists())

    def test_rejects_mismatched_tunnel_credential(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "wrong.json"
            path.write_text(json.dumps({"TunnelID": "09f176a3-8ebe-4e08-aae7-c56e4b8d7314"}))
            path.chmod(0o600)
            with self.assertRaisesRegex(migrate.MigrationError, "different tunnel"):
                migrate.target_credentials_ready(path, TARGET)

    def test_rejects_world_readable_credentials(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "token.json"
            path.write_text(json.dumps({"TunnelID": TARGET}))
            path.chmod(0o644)
            with self.assertRaisesRegex(migrate.MigrationError, "private"):
                migrate.target_credentials_ready(path, TARGET)

    def test_stage_changes_only_staged_copy(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            original = base / "config.yml"
            original.write_text(SOURCE)
            original.chmod(0o600)
            cred = base / "destination.json"
            cred.write_text(json.dumps({"TunnelID": TARGET}))
            cred.chmod(0o600)
            with patch.object(migrate, "ssh_listener_ready", return_value=True), \
                 patch.object(migrate, "run_cloudflared", return_value="") as validate:
                staged = migrate.stage(original, base / "state", TARGET,
                                       cred, SOURCE, "ssh.example.org")
            self.assertEqual(original.read_text(), SOURCE)
            self.assertIn(f"tunnel: {TARGET}", staged.read_text())
            self.assertIn(f"credentials-file: {cred}", staged.read_text())
            self.assertEqual(staged.stat().st_mode & 0o777, 0o600)
            self.assertEqual(validate.call_count, 1)
            with self.assertRaisesRegex(migrate.MigrationError, "exists"):
                with patch.object(migrate, "ssh_listener_ready", return_value=True):
                    migrate.stage(original, base / "state", TARGET, cred,
                                  SOURCE, "ssh.example.org")

    def test_failed_validation_does_not_leave_stage(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            cred = base / "destination.json"
            cred.write_text(json.dumps({"TunnelID": TARGET}))
            cred.chmod(0o600)
            with patch.object(migrate, "ssh_listener_ready", return_value=True), \
                 patch.object(migrate, "run_cloudflared",
                              side_effect=migrate.MigrationError("validation failed")):
                with self.assertRaises(migrate.MigrationError):
                    migrate.stage(base / "config.yml", base / "state",
                                  TARGET, cred, SOURCE, "ssh.example.org")
            self.assertFalse((base / "state" / "staged-config.yml").exists())
            self.assertEqual(list((base / "state").glob(".stage-*")), [])

    def test_no_live_cutover_commands(self):
        code = SCRIPT.read_text()
        for disallowed in ("tunnel route dns", "tunnel delete",
                           "kill -9", "os.kill(", "cloudflared tunnel run",
                           "api.cloudflare.com/client/v4"):
            self.assertNotIn(disallowed, code)


if __name__ == "__main__":
    unittest.main()
