#!/usr/bin/env python3
"""Regression tests for Cloud Shell installer safety and CLI-only mode."""
import os
from pathlib import Path
import subprocess
import unittest

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

if __name__ == "__main__":
    unittest.main()
