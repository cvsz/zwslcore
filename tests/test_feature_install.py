"""Static safeguards for the feature-aware installation entrypoint."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
INSTALLER = ROOT / "scripts" / "feature-install.sh"

class FeatureInstallerTests(unittest.TestCase):
    def test_make_targets_present(self):
        makefile = (ROOT / "Makefile").read_text()
        for target in ("feature-preflight", "feature-install", "feature-verify",
                       "cloudflare-preflight", "cloudshell-full-install"):
            self.assertIn(f"\n{target}:\n", makefile)
        self.assertIn('ZWSL_INSTALL_WEBUI=1 ZWSL_INSTALL_MCP=1', makefile)
        self.assertIn('ZWSL_CHECK_CLOUDFLARE=1', makefile)

    def test_bash_syntax(self):
        result = subprocess.run(["bash", "-n", str(INSTALLER)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_no_implicit_model_download_on_cloud_shell(self):
        source = INSTALLER.read_text()
        self.assertIn('MODEL_POLICY="${ZWSL_MODEL_POLICY:-reuse}"', source)
        self.assertIn('make -C "$ROOT" cloudshell', source)
        self.assertIn('make -C "$ROOT" ai-test', source)
        self.assertIn('ZWSL_MODEL_POLICY=provision', source)
        self.assertNotIn("ollama pull", source)
        self.assertNotIn("docker compose up -d", source)

    def test_cloudflare_requires_opt_in_and_explicit_hostname(self):
        source = INSTALLER.read_text()
        self.assertIn('ZWSL_CHECK_CLOUDFLARE:-0', source)
        self.assertIn('ZCLOUD_HOSTNAME', source)
        self.assertIn('bash "$ROOT/scripts/zwsl-cloudflare.sh" verify', source)

    def test_reuses_existing_native_components(self):
        source = INSTALLER.read_text()
        self.assertIn('SKIP: native Open WebUI is already installed', source)
        self.assertIn('SKIP: existing MCP installation', source)

    def test_optional_installers_not_started_automatically(self):
        source = INSTALLER.read_text()
        self.assertIn('INSTALL_WEBUI="${ZWSL_INSTALL_WEBUI:-0}"', source)
        self.assertIn('INSTALL_MCP="${ZWSL_INSTALL_MCP:-0}"', source)
        self.assertNotIn('"$ROOT/scripts/cloudshell-webui.sh" start', source)
        self.assertNotIn('cloudflared tunnel run', source)

if __name__ == "__main__":
    unittest.main()
