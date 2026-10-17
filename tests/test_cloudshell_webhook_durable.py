"""Restart and concurrency regressions for durable signed webhook replay protection."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import hmac
import importlib.util
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "scripts" / "cloudshell-webhook.py"


class DurableReplayTests(unittest.TestCase):
    def test_replay_survives_restart_and_concurrent_delivery(self):
        with tempfile.TemporaryDirectory() as folder:
            key = Path(folder) / "secret"
            key.write_text("a" * 64)
            key.chmod(0o600)
            db = Path(folder) / "private" / "replay.sqlite3"
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            env = dict(os.environ, ZWSL_WEBHOOK_PORT=str(port),
                       ZWSL_WEBHOOK_SECRET_FILE=str(key), ZWSL_WEBHOOK_REPLAY_DB=str(db))
            base = f"http://127.0.0.1:{port}"
            opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))

            def send(event):
                body = b'{"action":"status"}'
                timestamp = str(int(time.time()))
                signed = hmac.new(("a" * 64).encode(),
                                  (timestamp + "." + event + ".").encode() + body,
                                  hashlib.sha256).hexdigest()
                headers = {"X-ZWSL-Timestamp": timestamp, "X-ZWSL-Event-ID": event,
                           "X-ZWSL-Signature": "sha256=" + signed}
                request = urllib.request.Request(base + "/webhook/", data=body, headers=headers)
                try:
                    with opener.open(request, timeout=5) as response:
                        return response.status
                except urllib.error.HTTPError as error:
                    return error.code

            def start():
                process = subprocess.Popen([sys.executable, str(SERVER)], env=env,
                                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                for _ in range(60):
                    if process.poll() is not None:
                        self.fail("webhook receiver exited on startup")
                    try:
                        with opener.open(base + "/health", timeout=1) as response:
                            if response.status == 200:
                                return process
                    except OSError:
                        time.sleep(0.05)
                process.terminate()
                self.fail("webhook receiver did not become ready")

            def stop(process):
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=5)

            process = start()
            try:
                self.assertEqual(send("once"), 202)
                self.assertEqual(send("once"), 409)
                with ThreadPoolExecutor(max_workers=8) as pool:
                    results = list(pool.map(send, ["concurrent"] * 8))
                self.assertEqual(results.count(202), 1)
                self.assertEqual(results.count(409), 7)
            finally:
                stop(process)
            self.assertEqual(db.stat().st_mode & 0o777, 0o600)
            process = start()
            try:
                self.assertEqual(send("once"), 409)
                self.assertEqual(send("new-event"), 202)
            finally:
                stop(process)

    def test_refuses_insecure_replay_file(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "replay.sqlite3"
            path.write_text("test")
            path.chmod(0o644)
            spec = importlib.util.spec_from_file_location("webhook_for_security_test", SERVER)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            with self.assertRaises(RuntimeError):
                module.ReplayStore(path, b"a" * 64)


if __name__ == "__main__":
    unittest.main()
