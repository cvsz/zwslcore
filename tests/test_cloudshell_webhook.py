"""Static and unit checks for the optional signed webhook receiver."""
from pathlib import Path
import subprocess
import os
import sys
import tempfile
import socket
import time
import json
import hmac
import hashlib
import urllib.request
import urllib.error
import unittest

ROOT = Path(__file__).resolve().parents[1]

class WebhookTests(unittest.TestCase):
    def test_python_compiles_without_importing_server(self):
        src = (ROOT / "scripts/cloudshell-webhook.py").read_text()
        compile(src, "cloudshell-webhook.py", "exec")

    def test_shell_syntax(self):
        p = subprocess.run(["bash", "-n", str(ROOT / "scripts/cloudshell-webhook.sh")], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)

    def test_signed_delivery_and_replay_end_to_end(self):
        with tempfile.TemporaryDirectory() as directory:
            secret = "a" * 64
            key = Path(directory) / "webhook.key"
            key.write_text(secret)
            key.chmod(0o600)
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            env = dict(os.environ, ZWSL_WEBHOOK_PORT=str(port), ZWSL_WEBHOOK_SECRET_FILE=str(key),
                       ZWSL_WEBHOOK_REPLAY_DB=str(Path(directory) / "replay" / "events.sqlite3"))
            proc = subprocess.Popen(
                [sys.executable, str(ROOT / "scripts/cloudshell-webhook.py")],
                env=env, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE,
            )
            base = f"http://127.0.0.1:{port}"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
            def status(path, data=None, headers=None):
                req = urllib.request.Request(base + path, data=data, headers=headers or {})
                try:
                    with opener.open(req, timeout=2) as res:
                        return res.status
                except urllib.error.HTTPError as err:
                    return err.code
            try:
                for _ in range(60):
                    if proc.poll() is not None:
                        self.fail("receiver terminated during startup")
                    try:
                        if status("/health") == 200:
                            break
                    except OSError:
                        time.sleep(0.05)
                else:
                    self.fail("receiver did not start")
                body = json.dumps({"action": "status"}).encode()
                stamp = str(int(time.time()))
                event = "case-001"
                digest = hmac.new(secret.encode(), (stamp+"."+event+".").encode()+body, hashlib.sha256).hexdigest()
                headers = {"Content-Type": "application/json", "X-ZWSL-Timestamp": stamp,
                           "X-ZWSL-Event-ID": event, "X-ZWSL-Signature": "sha256=" + digest}
                self.assertEqual(status("/webhook", body), 401)
                self.assertEqual(status("/webhook", body, headers), 202)
                self.assertEqual(status("/webhook", body, headers), 409)
                self.assertEqual(status("/webhook", body, {**headers, "X-ZWSL-Event-ID": "case-002"}), 401)
                self.assertEqual(status("/wrong", body, headers), 404)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)

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
