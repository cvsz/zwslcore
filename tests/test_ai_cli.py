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
        self.checkout = Path(self.temp.name) / "checkout"
        (self.checkout / "scripts").mkdir(parents=True)
        self.script = self.checkout / "scripts" / "ai.sh"
        self.script.write_bytes(SCRIPT.read_bytes())
        self.script.chmod(0o755)
        clean_env = {
            key: value for key, value in os.environ.items()
            if not key.startswith("AI_")
            and key not in {
                "GEMINI_API_KEY", "OPENROUTER_API_KEY", "GROQ_API_KEY",
                "PROVIDER_CLIENT_KEY", "OPENAI_API_KEY", "ZWSLCORE_AI_REPO_ROOT",
            }
        }
        self.env = dict(clean_env, XDG_STATE_HOME=self.temp.name,
            AI_API_URL=f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions",
            AI_API_KEY="test-token", AI_MODEL="zeaz-auto")
    def write_dotenv(self, value):
        path = self.checkout / ".env"
        path.write_text(value, encoding="utf-8")
        path.chmod(0o600)
        return path
    def run_cli(self,*args):
        return subprocess.run(["bash",str(self.script),*args],env=self.env,
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
    def test_network_error_redacts_endpoint_query_values(self):
        self.env["AI_API_URL"]=f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions?api_key=query-secret"
        result=self.run_cli("ask","hello")
        self.assertNotEqual(result.returncode,0)
        self.assertIn("HTTP 404",result.stderr)
        self.assertNotIn("query-secret",result.stderr)
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
        self.write_dotenv(
            'AI_API_URL="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"\n'
            'AI_MODEL="gemini-flash"\n'
            'GEMINI_API_KEY="test-secret"\n'
            'AI_API_KEY="${GEMINI_API_KEY}"\n'
            'APP_URL=<http://127.0.0.1:3000>\n'
        )
        for key in ("AI_API_URL", "AI_MODEL", "AI_API_KEY"):
            self.env.pop(key, None)
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("gemini-flash", result.stdout)
        self.assertIn("Credential configured: True", result.stdout)
        self.assertNotIn("test-secret", result.stdout)

    def test_dotenv_provider_key_is_not_used_for_untrusted_url(self):
        self.write_dotenv(
            'AI_API_URL="https://attacker.example/?next=generativelanguage.googleapis.com"\n'
            'GEMINI_API_KEY="test-secret"\n'
        )
        for key in ("AI_API_URL", "AI_API_KEY"):
            self.env.pop(key, None)
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Credential configured: False", result.stdout)
        self.assertNotIn("test-secret", result.stdout)

    def test_dotenv_loads_local_provider_key(self):
        self.write_dotenv('PROVIDER_CLIENT_KEY="test-provider-token"\n')
        self.env.pop("AI_API_KEY", None)
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Credential configured: True", result.stdout)
        self.assertNotIn("test-provider-token", result.stdout)

    def test_explicit_empty_key_suppresses_provider_fallback(self):
        self.write_dotenv(
            'AI_API_URL="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"\n'
            'GEMINI_API_KEY="test-secret"\n'
        )
        for key in ("AI_API_URL", "GEMINI_API_KEY"):
            self.env.pop(key, None)
        self.env["AI_API_KEY"] = ""
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Credential configured: False", result.stdout)

    def test_empty_dotenv_key_allows_provider_specific_key_fallback(self):
        self.write_dotenv(
            'AI_API_URL="https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"\n'
            'AI_API_KEY=""\n'
            'GEMINI_API_KEY="test-secret"\n'
        )
        for key in ("AI_API_URL", "AI_API_KEY"):
            self.env.pop(key, None)
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Credential configured: True", result.stdout)

    def test_invalid_endpoint_port_is_rejected_without_traceback(self):
        self.env["AI_API_URL"] = "http://127.0.0.1:99999/v1/chat/completions"
        result = self.run_cli("doctor")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid AI_API_URL", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_zero_endpoint_port_is_rejected(self):
        self.env["AI_API_URL"] = "http://127.0.0.1:0/v1/chat/completions"
        result = self.run_cli("doctor")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Invalid AI_API_URL", result.stderr)
        self.assertNotIn("Traceback", result.stderr)

    def test_dotenv_assignments_are_never_executed(self):
        marker = Path(self.temp.name) / "executed"
        self.write_dotenv(f'AI_MODEL="$(touch {marker})"\n')
        self.env.pop("AI_MODEL", None)
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(marker.exists())

    def test_dotenv_rejects_insecure_permissions(self):
        path = self.write_dotenv('AI_MODEL="test"\n')
        path.chmod(0o644)
        result = self.run_cli("doctor")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("chmod 600", result.stderr)

    def test_dotenv_symlink_is_rejected(self):
        path = self.checkout / ".env"
        path.symlink_to(Path(self.temp.name) / "outside.env")
        result = self.run_cli("doctor")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("symlink .env", result.stderr)

    def test_doctor_redacts_endpoint_query_parameters(self):
        self.env["AI_API_URL"] = f"http://127.0.0.1:{self.server.server_port}/v1/chat/completions?api_key=query-secret"
        result = self.run_cli("doctor")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn("query-secret", result.stdout)

if __name__=="__main__":
    unittest.main()
