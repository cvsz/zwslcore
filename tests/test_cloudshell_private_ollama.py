"""Fail-closed Cloud Shell private Ollama/WARP route regression tests."""
import importlib.util
from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import threading
import urllib.request
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "cloudshell_private_ollama.py"
spec = importlib.util.spec_from_file_location("cloudshell_private_ollama", SCRIPT)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

TUNNEL = "11111111-1111-4111-8111-111111111111"
VNET = "33333333-3333-4333-8333-333333333333"
IP = "10.20.30.4"


class PrivateOllamaTests(unittest.TestCase):
    def args(self, apply):
        return types.SimpleNamespace(interface="eth0", config="/tmp/config", model="test-model",
                                     vnet=VNET, tunnel_id=TUNNEL, apply=apply)

    def test_interface_detection_and_rejection(self):
        with patch.object(module, "run", return_value="7: eth0 inet 10.20.30.4/24 scope global"):
            self.assertEqual(module.private_ip("eth0"), IP)
        with patch.object(module, "run", return_value="7: eth0 inet 203.0.113.9/24 scope global"):
            with self.assertRaises(module.Failed):
                module.private_ip("eth0")
        with self.assertRaises(module.Failed):
            module.private_ip("eth0; echo")

    def test_parse_local_tunnel_uuid(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yml"
            path.write_text(f"tunnel: {TUNNEL}\ncredentials-file: /safe/local.json\n")
            self.assertEqual(module.tunnel_id(path), TUNNEL)

    def test_exact_cidr_only(self):
        listing = f"row 10.20.0.0/16 {TUNNEL} {VNET}\nrow {IP}/32 {TUNNEL} {VNET}"
        self.assertEqual(module.route_lines(listing, f"{IP}/32"), [listing.splitlines()[1]])

    def test_dry_run_never_modifies_route(self):
        with patch.object(module, "local_status", return_value=(IP, TUNNEL)), \
             patch.object(module, "run", return_value="NETWORK\n") as run:
            module.sync_route(self.args(False))
            self.assertEqual(run.call_count, 1)

    def test_conflicting_existing_route_fails_closed(self):
        with patch.object(module, "local_status", return_value=(IP, TUNNEL)), \
             patch.object(module, "run", return_value=f"row {IP}/32 OTHER_TUNNEL {VNET}"):
            with self.assertRaises(module.Failed):
                module.sync_route(self.args(True))

    def test_existing_owned_route_does_not_mutate(self):
        with patch.object(module, "local_status", return_value=(IP, TUNNEL)), \
             patch.object(module, "run", return_value=f"row {IP}/32 {TUNNEL} {VNET}") as run:
            module.sync_route(self.args(True))
        self.assertEqual(run.call_count, 1)

    def test_apply_requires_connector_on_same_host(self):
        with patch.object(module, "local_status", return_value=(IP, TUNNEL)), \
             patch.object(module, "run", return_value="NETWORK\n"), \
             patch.object(module, "local_connector_running", return_value=False):
            with self.assertRaises(module.Failed):
                module.sync_route(self.args(True))

    def test_apply_verifies_route_ownership(self):
        replies = iter(["NETWORK", "CONNECTOR ID", "Added route",
                        f"row {IP}/32 {TUNNEL} {VNET}"])
        with patch.object(module, "local_status", return_value=(IP, TUNNEL)), \
             patch.object(module, "local_connector_running", return_value=True), \
             patch.object(module, "run", side_effect=lambda *a, **kw: next(replies)) as run:
            module.sync_route(self.args(True))
        self.assertEqual(run.call_count, 4)

    def test_private_opener_disables_proxy_configuration(self):
        with patch.dict(os.environ, {"http_proxy": "http://127.0.0.1:9999",
                                    "https_proxy": "http://127.0.0.1:9999"}):
            opener = module.private_opener()
        proxy_handlers = [handler for handler in opener.handlers
                          if isinstance(handler, urllib.request.ProxyHandler)]
        self.assertEqual(len(proxy_handlers), 1)
        self.assertEqual(proxy_handlers[0].proxies, {})
        self.assertTrue(any(isinstance(handler, module.NoRedirect)
                            for handler in opener.handlers))

    def test_private_inventory_rejects_redirect(self):
        class Redirect(BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", "https://example.com/untrusted")
                self.end_headers()

            def log_message(self, fmt, *args):
                pass

        server = HTTPServer(("127.0.0.1", 0), Redirect)
        worker = threading.Thread(target=server.serve_forever, daemon=True)
        worker.start()
        try:
            with self.assertRaisesRegex(module.Failed, "redirected"):
                module.fetch_json(f"http://127.0.0.1:{server.server_port}/api/tags")
        finally:
            server.shutdown()
            server.server_close()
            worker.join(timeout=3)

    def test_public_client_target_rejected(self):
        args = types.SimpleNamespace(ip="203.0.113.9", model="test-model")
        with self.assertRaises(module.Failed):
            module.client_check(args)


if __name__ == "__main__":
    unittest.main()
