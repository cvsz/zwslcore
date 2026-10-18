"""Behavioral regressions for Cloud Shell reviewer findings."""
from __future__ import annotations
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"


def embedded(script: str, marker: str) -> str:
    source = (SCRIPTS / script).read_text()
    return source.split("<<'" + marker + "'\n", 1)[1].split("\n" + marker + "\n", 1)[0]


def run_python(code, env, *argv):
    return subprocess.run(
        [sys.executable, "-c", code, *argv], capture_output=True,
        text=True, env={**os.environ, **env}, timeout=10,
    )


class CloudShellReviewRegressions(unittest.TestCase):
    def test_all_embedded_python_and_shell_parse(self):
        cases = (
            ("zwsl-cloudflare.sh", "PYCFG"),
            ("zwsl-ssh-repair.sh", "PYSSH"),
            ("install-zwsl-remote-exec.sh", "PYPATHS"),
            ("install-zwsl-remote-exec.sh", "PYMCP"),
            ("cloudshell-webhook.sh", "PYHEALTH"),
            ("cloudshell-webhook.sh", "PYROUTE"),
        )
        for script, marker in cases:
            with self.subTest(marker=marker):
                compile(embedded(script, marker), marker, "exec")
                result = subprocess.run(["bash", "-n", str(SCRIPTS / script)],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_cloudflare_list_hostname_and_custom_ssh_port(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            config, state = p / "config.yml", p / "backups"
            state.mkdir()
            config.write_text(
                "ingress:\n  - hostname: ssh.example.org\n"
                "    service: http_status:404\n  - service: http_status:404\n"
            )
            env = {"ZCLOUD_CONFIG": str(config), "ZCLOUD_HOSTNAME": "ssh.example.org",
                   "ZCLOUD_SSH_PORT": "2222", "ZCLOUD_STATE": str(state)}
            code = embedded("zwsl-cloudflare.sh", "PYCFG")
            first = run_python(code, env)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("service: ssh://127.0.0.1:2222", config.read_text())
            second = run_python(code, env)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(len(list(state.glob("config.*.yml"))), 1)

    def test_ssh_alias_does_not_delete_following_match(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            config, key = p / "config", p / "key"
            config.write_text(
                "Host zcloud\n    User olduser\n"
                "Match host *.example.org\n    PasswordAuthentication no\n"
                "Host other\n    User otheruser\n"
            )
            key.write_text("fixture only")
            env = {"ZCLOUD_CLIENT_CONFIG": str(config), "ZCLOUD_ALIAS": "zcloud",
                   "ZCLOUD_HOSTNAME": "ssh.example.org", "ZCLOUD_USER": "newuser",
                   "ZCLOUD_KEY": str(key)}
            result = run_python(embedded("zwsl-ssh-repair.sh", "PYSSH"), env)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = config.read_text()
            self.assertIn("StrictHostKeyChecking yes", data)
            self.assertIn("Match host *.example.org\n    PasswordAuthentication no", data)
            self.assertIn("Host other\n    User otheruser", data)
            self.assertNotIn("olduser", data)

    def test_webhook_route_uses_configured_ssh_port(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td)
            config, state = p / "config.yml", p / "backups"
            state.mkdir()
            config.write_text(
                "ingress:\n  - hostname: ssh.example.org\n"
                "    service: ssh://127.0.0.1:2222\n"
                "  - service: http_status:404\n"
            )
            env = {"ZCLOUD_CONFIG": str(config), "ZCLOUD_HOSTNAME": "ssh.example.org",
                   "ZCLOUD_SSH_PORT": "2222", "ZWSL_WEBHOOK_PORT": "8765",
                   "ZWSL_WEBHOOK_STATE": str(state)}
            result = run_python(embedded("cloudshell-webhook.sh", "PYROUTE"), env)
            self.assertEqual(result.returncode, 0, result.stderr)
            data = config.read_text()
            self.assertIn("path: ^/webhook/?$", data)
            self.assertIn("service: http://127.0.0.1:8765", data)
            self.assertIn("service: ssh://127.0.0.1:2222", data)
            self.assertLess(data.index("path:"), data.index("ssh://"))
            self.assertTrue((state / "last-backup").is_file())

    def test_webhook_health_fails_on_unrelated_service(self):
        class FakeHealth(BaseHTTPRequestHandler):
            payload = b'{"status":"healthy"}'
            def do_GET(self):
                self.send_response(200)
                self.end_headers()
                self.wfile.write(self.payload)
            def log_message(self, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), FakeHealth)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            cmd = ["bash", str(SCRIPTS / "cloudshell-webhook.sh"), "health"]
            env = {**os.environ, "ZWSL_WEBHOOK_PORT": str(server.server_port)}
            invalid = subprocess.run(cmd, env=env, capture_output=True,
                                     text=True, timeout=10)
            self.assertNotEqual(invalid.returncode, 0)
            FakeHealth.payload = (
                b'{"status":"healthy","service":"zwslcore-signed-webhook","version":1}'
            )
            valid = subprocess.run(cmd, env=env, capture_output=True,
                                   text=True, timeout=10)
            self.assertEqual(valid.returncode, 0, valid.stderr)
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=5)

    def test_mcp_saved_paths_and_bounded_stream(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            repo = base / "other-checkout-name"
            repo.mkdir()
            cloud = base / "alt-config.yml"
            cloud.write_text("ingress: []\n")
            metadata = {
                "ZWSL_MCP_REPO_ROOT": str(repo),
                "ZWSL_MCP_CLOUD_CONFIG": str(cloud),
                "ZWSL_MCP_CLOUDFLARED": "/usr/bin/cloudflared",
            }
            path = base / "paths.json"
            result = run_python(
                embedded("install-zwsl-remote-exec.sh", "PYPATHS"),
                metadata, str(path))
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(path.read_text())["repository"], str(repo))
            server_file = base / "server.py"
            server_file.write_text(embedded("install-zwsl-remote-exec.sh", "PYMCP"))
            class StubFastMCP:
                def __init__(self, *args):
                    pass
                def tool(self):
                    return lambda fn: fn
            code = server_file.read_text().replace(
                "from mcp.server.fastmcp import FastMCP", ""
            )
            ns = {"FastMCP": StubFastMCP, "__file__": str(server_file),
                  "__name__": "diagnostic_test"}
            exec(compile(code, str(server_file), "exec"), ns)
            self.assertEqual(ns["REPO"], repo)
            self.assertEqual(ns["CLOUD_CONFIG"], cloud)
            value = ns["run_fixed"](
                [sys.executable, "-c",
                 'import os; print(os.getenv("GIT_OPTIONAL_LOCKS")); print("X"*50000)']
            )
            self.assertIn("0", value)
            self.assertIn("[TRUNCATED", value)
            self.assertLess(len(value.encode()), 8200)

    def test_feature_inventory_uses_custom_mcp_home_consistently(self):
        source = (SCRIPTS / "feature-install.sh").read_text()
        self.assertGreaterEqual(source.count('$MCP_HOME/server.py'), 2)
        self.assertGreaterEqual(source.count('$MCP_HOME/paths.json'), 2)


if __name__ == "__main__":
    unittest.main()
