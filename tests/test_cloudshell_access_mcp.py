"""Offline regression tests for optional Cloud Shell Access and MCP helpers."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    ROOT / "scripts" / "zwsl-cloudflare.sh",
    ROOT / "scripts" / "zwsl-ssh-repair.sh",
    ROOT / "scripts" / "install-zwsl-remote-exec.sh",
]

class CloudShellAccessTests(unittest.TestCase):
    def test_all_shell_scripts_parse(self):
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                result = subprocess.run(["bash", "-n", str(script)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_access_setup_is_fail_closed(self):
        source = SCRIPTS[0].read_text()
        self.assertIn("ZCLOUD_ACCESS_POLICY_VERIFIED", source)
        self.assertIn("ZCLOUD_AUTHORIZED_KEYS_VERIFIED", source)
        self.assertIn("rollback)", source)
        self.assertIn("ssh.example.com", source)

    def test_ssh_host_key_verification_is_required(self):
        source = SCRIPTS[1].read_text()
        self.assertIn("StrictHostKeyChecking yes", source)
        self.assertNotIn("StrictHostKeyChecking no", source)

    def test_mcp_is_local_and_read_only(self):
        source = SCRIPTS[2].read_text()
        self.assertIn('transport="stdio"', source)
        self.assertIn("run_fixed", source)
        self.assertNotIn("shell=True", source)
        self.assertNotIn("0.0.0.0", source)
        self.assertNotIn("execute_command", source)

    def test_no_real_hostnames_or_private_paths(self):
        for script in SCRIPTS:
            with self.subTest(script=script.name):
                source = script.read_text()
                self.assertNotIn("zeaz.dev", source)
                self.assertNotIn("/home/cvsitem", source)

if __name__ == "__main__":
    unittest.main()
