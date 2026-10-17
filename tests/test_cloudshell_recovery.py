"""Cloud Shell selective tool recovery regression checks.

No test installs a package or starts an actual tunnel/ollama process.
"""
from pathlib import Path
import os
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/cloudshell-recover.sh"


class CloudShellRecoveryTests(unittest.TestCase):
    def invoke(self, action, *, cloud_shell=False):
        with tempfile.TemporaryDirectory() as tmp:
            env = dict(os.environ)
            env.update(HOME=tmp, XDG_STATE_HOME=tmp, ZCLOUD_CONFIG=str(Path(tmp) / "missing.yml"))
            for key in ("CLOUD_SHELL", "DEVSHELL_PROJECT_ID", "ZWSL_ALLOW_NON_CLOUDSHELL", "ZCLOUD_HOSTNAME"):
                env.pop(key, None)
            if cloud_shell:
                env["CLOUD_SHELL"] = "true"
            return subprocess.run(["bash", str(SCRIPT), action], cwd=ROOT,
                                  env=env, capture_output=True, text=True, timeout=15)

    def test_bash_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_status_is_nonmutating_even_without_cloud_shell(self):
        result = self.invoke("status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("external_access_and_model_inference=NOT_VERIFIED", result.stdout)
        self.assertIn("tunnel_config=MISSING_OR_INVALID", result.stdout)

    def test_repair_requires_cloud_shell(self):
        result = self.invoke("repair")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Mutation is Cloud Shell only", result.stderr)

    def test_tunnel_start_requires_cloud_shell(self):
        result = self.invoke("tunnel-start")
        self.assertEqual(result.returncode, 2)

    def test_tunnel_start_requires_authorized_hostname(self):
        result = self.invoke("tunnel-start", cloud_shell=True)
        self.assertEqual(result.returncode, 2)
        self.assertIn("ZCLOUD_HOSTNAME", result.stderr)

    def test_installer_reuses_existing_without_model_pull_or_routing_changes(self):
        source = SCRIPT.read_text()
        self.assertIn("SKIP: cloudflared installed", source)
        self.assertIn("SKIP: Ollama installed", source)
        self.assertIn("SKIP: Ollama already responding", source)
        self.assertIn("https://pkg.cloudflare.com/cloudflared any main", source)
        self.assertIn("https://ollama.com/install.sh", source)
        self.assertIn("OLLAMA_HOST=127.0.0.1:11434", source)
        self.assertIn('bash "$ROOT/scripts/zcloud-tunnel.sh" start', source)
        for forbidden in ("ollama pull", "tunnel route dns", "tunnel delete",
                          "rm -rf ~/.cloudflared", "docker compose down", "systemctl restart ssh"):
            self.assertNotIn(forbidden, source)

    def test_makefile_exposes_recovery_and_native_model_fallback(self):
        makefile = (ROOT / "Makefile").read_text()
        for target in ("cloudshell-recover-status", "cloudshell-recover",
                       "cloudshell-tunnel-start"):
            self.assertIn(f"\n{target}:\n", makefile)
        self.assertIn("docker exec zwslcore-ollama ollama list", makefile)
        self.assertIn("elif command -v ollama", makefile)


if __name__ == "__main__":
    unittest.main()
