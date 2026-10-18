#!/usr/bin/env python3
"""Offline integration tests for the standalone Bash/Python AI CLI."""
import http.server
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "ai.sh"

class Handler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/v1/chat/completions":
            self.send_error(404)
            return
        if self.headers.get("Authorization") != "Bearer test-token":
            self.send_error(401)
            return
        length = int(self.headers["Content-Length"])
        payload = json.loads(self.rfile.read(length))
        if payload["model"] != "zeaz-auto":
            self.send_error(400)
            return
        response = json.dumps({"choices":[{"message":{"content":"mock-response"}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(response)))
        self.end_headers()
        self.wfile.write(response)
    def log_message(self, *args):
        pass

class CliTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = http.server.ThreadingHTTPServer(("127.0.0.1",0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.env = dict(os.environ, XDG_STATE_HOME=self.temp.name,
            AI_API_URL=f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions",
            AI_API_KEY="test-token", AI_MODEL="zeaz-auto")
    def run_cli(self,*args):
        return subprocess.run(["bash",str(SCRIPT),*args],env=self.env,
            capture_output=True,text=True,timeout=20)
    def test_offline_selftest(self):
        result=self.run_cli("selftest")
        self.assertEqual(result.returncode,0,result.stderr)
    def test_authenticated_inference_and_history(self):
        result=self.run_cli("ask","hello")
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn("mock-response",result.stdout)
        history=Path(self.temp.name)/"zwslcore-ai"/"default.json"
        self.assertTrue(history.exists())
        self.assertEqual(history.stat().st_mode & 0o077,0)
        self.assertEqual(len(json.loads(history.read_text())),2)
    def test_remote_http_rejected(self):
        self.env["AI_API_URL"]="http://example.com/v1/chat/completions"
        result=self.run_cli("ask","hello")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("HTTPS",result.stderr)
    def test_invalid_timeout_rejected(self):
        self.env["AI_TIMEOUT"]="-1"
        result=self.run_cli("ask","hello")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("AI_TIMEOUT",result.stderr)
    def test_symlink_session_rejected(self):
        state=Path(self.temp.name)/"zwslcore-ai"
        state.mkdir()
        (state/"default.json").symlink_to(Path(self.temp.name)/"target.json")
        result=self.run_cli("ask","hello")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("symlink",result.stderr.lower())

    def test_dotenv_gemini_configuration(self):
        # The repository .env is shared, so test with a private script copy.
        root = Path(self.temp.name) / "checkout"
        (root / "scripts").mkdir(parents=True)
        script = root / "scripts" / "ai.sh"
        script.write_bytes(SCRIPT.read_bytes())
        (root / ".env").write_text(
            'AI_API_URL="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"\n'
            'AI_MODEL="gemini-3.8-flash"\n'
            'GEMINI_API_KEY="test-secret"\n'
            'AI_API_KEY="${GEMINI_API_KEY}"\n'
            'APP_URL=<http://127.0.0.1:3000>\n'
        )
        (root / ".env").chmod(0o600)
        env = dict(self.env)
        for key in ("AI_API_URL", "AI_MODEL", "AI_API_KEY", "GEMINI_API_KEY"):
            env.pop(key, None)
        result = subprocess.run(["bash", str(script), "doctor"], env=env,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gemini-3.8-flash", result.stdout)
        self.assertIn("Credential configured: True", result.stdout)
        self.assertNotIn("test-secret", result.stdout)

    def test_dotenv_does_not_execute_commands(self):
        root = Path(self.temp.name) / "checkout"
        (root / "scripts").mkdir(parents=True)
        script = root / "scripts" / "ai.sh"
        script.write_bytes(SCRIPT.read_bytes())
        marker = root / "executed"
        (root / ".env").write_text(f'AI_MODEL="$(touch {marker})"\\n')
        (root / ".env").chmod(0o600)
        env = dict(self.env)
        env.pop("AI_MODEL", None)
        result = subprocess.run(["bash", str(script), "doctor"], env=env,
                                capture_output=True, text=True, timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_dotenv_rejects_insecure_permissions(self):
        root = Path(self.temp.name) / "checkout"
        (root / "scripts").mkdir(parents=True)
        script = root / "scripts" / "ai.sh"
        script.write_bytes(SCRIPT.read_bytes())
        (root / ".env").write_text('AI_MODEL="test"\\n')
        (root / ".env").chmod(0o644)
        result = subprocess.run(["bash", str(script), "doctor"], env=self.env,
                                capture_output=True, text=True, timeout=20)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chmod 600", result.stderr)

if __name__=="__main__":
    unittest.main()
