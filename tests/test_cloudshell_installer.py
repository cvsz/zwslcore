#!/usr/bin/env python3
"""Regression tests for Cloud Shell installer safety and CLI-only mode."""
import os
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/cloudshell.sh"

class CloudShellInstallerTests(unittest.TestCase):
    def run_script(self, *args):
        env = dict(os.environ, DEVSHELL_PROJECT_ID="test-project", CLOUD_SHELL="true")
        return subprocess.run(["bash", str(SCRIPT), *args], cwd=ROOT, env=env,
                              text=True, capture_output=True, timeout=45)

    def test_shell_syntax(self):
        result = subprocess.run(["bash", "-n", str(SCRIPT)], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_help(self):
        result = self.run_script("--help")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("--install-ollama", result.stdout)

    def test_unknown_option_fails_closed(self):
        result = self.run_script("--not-an-option")
        self.assertEqual(result.returncode, 2)

    def test_missing_model_value(self):
        result = self.run_script("--model")
        self.assertEqual(result.returncode, 2)

    def test_default_does_not_install_packages(self):
        script = SCRIPT.read_text()
        self.assertIn('if [[ "$INSTALL" == true ]]', script)
        self.assertNotIn("apt-get install -y zstd\n", script)
        self.assertIn("Cloud Shell", script)

    def test_symlink_env_rejected(self):
        """A dangling symlinked .env must be refused, not mistaken for absent."""
        env_file = ROOT / ".env"
        # Create a dangling symlink
        env_file.symlink_to("/nonexistent/path/.env")
        try:
            result = self.run_script()
            self.assertNotEqual(result.returncode, 0)
            self.assertIn("symlink", result.stderr.lower())
        finally:
            if env_file.is_symlink():
                env_file.unlink()

    def test_env_loads_ai_settings(self):
        """Allowlisted AI settings from .env are loaded without leaking secrets."""
        env_file = ROOT / ".env"
        try:
            env_file.write_text(
                'AI_API_URL="https://generativelanguage.googleapis.com/v1"\n'
                'AI_MODEL="gemini-3.8-flash"\n'
                'GEMINI_API_KEY="test-secret"\n'
                '# this is not a setting\n'
                'NOT_ALLOWED=ignored\n'
            )
            env_file.chmod(0o600)
            result = self.run_script()
            self.assertEqual(result.returncode, 0, result.stderr)
            # Confirm .env was loaded (non-sensitive confirmation only)
            self.assertIn("Repository .env loaded", result.stdout)
            # Secrets must never appear in output
            self.assertNotIn("test-secret", result.stdout)
        finally:
            if env_file.exists():
                env_file.unlink()

    def test_installer_downloads_before_execute(self):
        """--install-ollama must download the installer before executing it."""
        script = SCRIPT.read_text()
        # Must not pipe curl directly to sh
        self.assertNotIn("curl -fsSL https://ollama.com/install.sh | sh", script)
        self.assertNotIn("| sh", script)
        # Must download to a file first
        self.assertIn("-o ", script)
        self.assertIn("mktemp", script)

    def test_disk_space_checks_model_store(self):
        """Free space check must target the Ollama model store, not just $HOME."""
        script = SCRIPT.read_text()
        self.assertIn(".ollama", script)
        self.assertIn("df -Pk", script)

if __name__ == "__main__":
    unittest.main()
