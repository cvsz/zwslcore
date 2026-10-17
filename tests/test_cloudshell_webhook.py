"""Static and unit checks for the optional signed webhook receiver."""
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WebhookTests(unittest.TestCase):
    def test_python_compiles_without_importing_server(self):
        src = (ROOT / "scripts/cloudshell-webhook.py").read_text()
        compile(src, "cloudshell-webhook.py", "exec")

    def test_shell_syntax(self):
        p = subprocess.run(["bash", "-n", str(ROOT / "scripts/cloudshell-webhook.sh")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_security_invariants(self):
        receiver = (ROOT / "scripts/cloudshell-webhook.py").read_text()
        installer = (ROOT / "scripts/cloudshell-webhook.sh").read_text()
        self.assertIn('("127.0.0.1", PORT)', receiver)
        self.assertIn("hmac.compare_digest", receiver)
        self.assertIn('X-ZWSL-Timestamp', receiver)
        self.assertIn('X-ZWSL-Event-ID', receiver)
        self.assertIn('"replay"', receiver)
        self.assertIn('ZWSL_WEBHOOK_ACCESS_VERIFIED', installer)
        self.assertIn('rollback)', installer)
        self.assertNotIn("shell=True", receiver)

if __name__ == "__main__":
    unittest.main()
