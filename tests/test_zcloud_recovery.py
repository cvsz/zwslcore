#!/usr/bin/env python3
"""Regression tests for Cloud Shell connector recovery admission and downloads."""
import hashlib
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
RECOVERY = ROOT / "scripts" / "zcloud-recovery.sh"
TUNNEL = ROOT / "scripts" / "zcloud-tunnel.sh"
PAYLOAD = b"cloudflared-test-fixture\n"


class ZCloudRecoveryTests(unittest.TestCase):
    def run_install(self, home: Path, stub_dir: Path, checksum: str):
        env = os.environ.copy()
        bin_dir = home / "bin"
        env.update({
            "HOME": str(home),
            "ZCLOUD_BIN_DIR": str(bin_dir),
            "ZCLOUD_CLOUDFLARED": str(bin_dir / "cloudflared"),
            "ZCLOUD_CLOUDFLARED_URL": "https://example.invalid/cloudflared",
            "ZCLOUD_CLOUDFLARED_SHA256": checksum,
            "PATH": str(stub_dir) + os.pathsep + env.get("PATH", ""),
        })
        return subprocess.run(
            ["bash", str(RECOVERY), "install"],
            cwd=ROOT,
            env=env,
            text=True,
            capture_output=True,
            timeout=15,
        )

    def make_curl_stub(self, stub_dir: Path):
        stub_dir.mkdir(parents=True, exist_ok=True)
        curl = stub_dir / "curl"
        curl.write_text(
            "#!/usr/bin/env bash\n"
            "set -euo pipefail\n"
            "output=''\n"
            "while (($#)); do\n"
            "  if [[ \"$1\" == '--output' ]]; then output=\"$2\"; shift 2; else shift; fi\n"
            "done\n"
            "test -n \"$output\"\n"
            "printf '%s' 'cloudflared-test-fixture\n' > \"$output\"\n",
            encoding="utf-8",
        )
        curl.chmod(0o700)

    def test_shell_syntax(self):
        for script in (RECOVERY, TUNNEL):
            result = subprocess.run(
                ["bash", "-n", str(script)], text=True, capture_output=True, timeout=10
            )
            self.assertEqual(result.returncode, 0, f"{script.name}: {result.stderr}")

    def test_release_url_is_version_pinned(self):
        source = RECOVERY.read_text(encoding="utf-8")
        self.assertIn("/releases/download/2026.10.1/cloudflared-linux-amd64", source)
        self.assertNotIn("/releases/latest/", source)

    def test_tunnel_identity_has_no_repository_specific_default(self):
        source = RECOVERY.read_text(encoding="utf-8")
        self.assertIn('TUNNEL_ID="${ZCLOUD_TUNNEL_ID:-}"', source)
        self.assertIn('HOSTNAME_VALUE="${ZCLOUD_HOSTNAME:-}"', source)
        self.assertIn("require_tunnel_identity", source)

    def test_missing_binary_downloads_and_checksums_before_install(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            home.mkdir()
            stub_dir = root / "stubs"
            self.make_curl_stub(stub_dir)
            checksum = hashlib.sha256(PAYLOAD).hexdigest()

            result = self.run_install(home, stub_dir, checksum)

            target = home / "bin" / "cloudflared"
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            self.assertEqual(target.read_bytes(), PAYLOAD)
            self.assertEqual(stat.S_IMODE(target.stat().st_mode), 0o700)

    def test_symlinked_binary_target_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            bin_dir = home / "bin"
            bin_dir.mkdir(parents=True)
            stub_dir = root / "stubs"
            self.make_curl_stub(stub_dir)
            real_binary = bin_dir / "real-cloudflared"
            real_binary.write_bytes(PAYLOAD)
            target = bin_dir / "cloudflared"
            target.symlink_to(real_binary)

            result = self.run_install(home, stub_dir, hashlib.sha256(PAYLOAD).hexdigest())

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr.lower())
            self.assertTrue(target.is_symlink())

    def test_checksum_mismatch_never_installs_binary(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            home = root / "home"
            home.mkdir()
            stub_dir = root / "stubs"
            self.make_curl_stub(stub_dir)

            result = self.run_install(home, stub_dir, "0" * 64)

            self.assertNotEqual(result.returncode, 0)
            self.assertIn("checksum mismatch", result.stderr.lower())
            self.assertFalse((home / "bin" / "cloudflared").exists())

    def test_recovery_checks_credentials_and_exact_ssh_ingress(self):
        source = RECOVERY.read_text(encoding="utf-8")
        self.assertIn("check_credentials_file", source)
        self.assertIn('[[ -f "$credentials" && ! -L "$credentials" ]]', source)
        self.assertIn("Tunnel credentials file must be owned by the current user", source)
        self.assertIn("Tunnel credentials directory is group/world accessible", source)
        self.assertIn('ingress rule "https://$HOSTNAME_VALUE"', source)
        self.assertIn("does not route to ssh://127.0.0.1:22", source)

    def test_recovery_invokes_readable_lifecycle_script_with_verified_binary(self):
        recovery = RECOVERY.read_text(encoding="utf-8")
        tunnel = TUNNEL.read_text(encoding="utf-8")
        self.assertIn('[[ -r "$TUNNEL_SCRIPT" && ! -L "$TUNNEL_SCRIPT" ]]', recovery)
        self.assertIn('ZCLOUD_CLOUDFLARED="$CLOUDFLARED" bash "$TUNNEL_SCRIPT" start', recovery)
        self.assertIn('"$CLOUDFLARED" tunnel --config "$CONFIG" run', tunnel)
        self.assertIn('CLOUDFLARED="${ZCLOUD_CLOUDFLARED:-', tunnel)

    def test_verification_rejects_failed_or_malformed_http_status(self):
        source = RECOVERY.read_text(encoding="utf-8")
        self.assertIn('if ! code="$(curl --silent --show-error', source)
        self.assertIn('[[ "$code" =~ ^[1-5][0-9]{2}$ ]]', source)
        self.assertIn('[[ "$code" != "530" ]]', source)


if __name__ == "__main__":
    unittest.main()
