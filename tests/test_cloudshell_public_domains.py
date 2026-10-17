"""Unit checks for protected dual-host Cloudflare ingress and public Provider profile."""
import importlib.util
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load(filename, alias):
    spec = importlib.util.spec_from_file_location(alias, ROOT / "scripts" / filename)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


ingress = load("cloudshell-public-ingress.py", "cloudshell_public_ingress")
provider = load("cloudshell-provider-runtime.py", "cloudshell_provider_runtime")

SSH_HOST = "ssh.example.net"
API_HOST = "api.example.net"
TUNNEL = "11111111-1111-4111-8111-111111111111"
SOURCE = ("tunnel: " + TUNNEL + "\ncredentials-file: /home/user/.cloudflared/tunnel.json\n"
          "ingress:\n  - hostname: " + SSH_HOST + "\n    service: ssh://127.0.0.1:22\n"
          "  - service: http_status:404\n")


class PublicIngressTests(unittest.TestCase):
    def test_api_route_does_not_change_ssh_origin_or_tunnel(self):
        rendered = ingress.render(SOURCE, API_HOST, SSH_HOST)
        self.assertIn("tunnel: " + TUNNEL, rendered)
        self.assertIn("service: ssh://127.0.0.1:22", rendered)
        self.assertIn("- hostname: " + API_HOST + "\n    service: http://127.0.0.1:8080\n", rendered)
        self.assertEqual(ingress.render(rendered, API_HOST, SSH_HOST), rendered)
        self.assertTrue(rendered.rstrip().endswith("- service: http_status:404"))

    def test_rejects_conflicting_api_origin_and_invalid_ssh(self):
        original = SOURCE.replace("ssh://127.0.0.1:22", "ssh://192.168.1.5:22")
        with self.assertRaises(ingress.Blocked):
            ingress.render(original, API_HOST, SSH_HOST)
        conflict = SOURCE.replace("  - service: http_status:404\n",
                                  "  - hostname: api.example.net\n    service: http://127.0.0.1:11434\n"
                                  "  - service: http_status:404\n")
        with self.assertRaises(ingress.Blocked):
            ingress.render(conflict, API_HOST, SSH_HOST)
        with self.assertRaises(ingress.Blocked):
            ingress.render(SOURCE, SSH_HOST, SSH_HOST)

    def test_local_staging_preserves_active_config(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = base / "config.yml"
            config.write_text(SOURCE)
            config.chmod(0o600)
            state = base / "state"
            with patch.object(ingress, "STATE", state), \
                 patch.object(ingress, "local_ssh"), \
                 patch.object(ingress, "origin_auth_verified"), \
                 patch.object(ingress, "run_cloudflared") as validate:
                staged, actual = ingress.stage(config, SSH_HOST, API_HOST)
            self.assertEqual(actual, TUNNEL)
            self.assertEqual(config.read_text(), SOURCE)
            self.assertIn("- hostname: " + API_HOST, staged.read_text())
            self.assertEqual(staged.stat().st_mode & 0o777, 0o600)
            validate.assert_called_once_with(staged)

    def test_apply_refuses_unverified_access(self):
        with patch.dict(os.environ, {"ZWSL_API_ACCESS_VERIFIED": ""}):
            with self.assertRaisesRegex(ingress.Blocked, "Access"):
                ingress.apply_ingress(Path("/not-a-real-config"), SSH_HOST, API_HOST)

    def test_dns_cas_refuses_unreviewed_existing_target(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "config.yml"
            source = ingress.render(SOURCE, API_HOST, SSH_HOST)
            path.write_text(source)
            path.chmod(0o600)
            args = type("Args", (), {"config": str(path), "zone": "example.net",
                                     "api_host": API_HOST, "expect_cname": ""})()
            def cloudflare(method, route, payload=None):
                if method == "GET" and route == "/zones/" + "a" * 32:
                    return {"result": {"name": "example.net"}, "success": True}
                return {"result": [{"type": "CNAME", "content": "other-tunnel.cfargotunnel.com",
                                    "id": "b" * 32, "proxied": True}], "success": True}
            with patch.dict(os.environ, {"CLOUDFLARE_ZONE_ID": "a" * 32,
                                          "ZWSL_API_ACCESS_VERIFIED": "YES"}), \
                 patch.object(ingress, "cf_request", side_effect=cloudflare), \
                 patch.object(ingress, "origin_auth_verified"):
                with self.assertRaisesRegex(ingress.Blocked, "expect-cname"):
                    ingress.dns(args, True)

    def test_route_has_no_automatic_tunnel_restart(self):
        src = (ROOT / "scripts/cloudshell-public-ingress.py").read_text()
        for banned in ("os.kill(", "subprocess.Popen(", "tunnel delete", "shell=True", "load_dotenv"):
            self.assertNotIn(banned, src)


class ProviderBootstrapTests(unittest.TestCase):
    def test_renders_only_private_ollama_origin(self):
        text = provider.render_config("qwen2.5-coder:7b")
        self.assertIn("http://127.0.0.1:11434/v1", text)
        self.assertIn("default_model: zeaz-free", text)
        self.assertNotIn("0.0.0.0:11434", text)
        self.assertNotIn("openrouter", text)

    def test_installed_model_selects_existing_only(self):
        with patch.object(provider, "local_json", return_value={
            "models": [{"name": "qwen2.5-coder:7b"}, {"name": "qwen3:8b"}]
        }):
            self.assertEqual(provider.model_name(), "qwen2.5-coder:7b")
            with self.assertRaises(provider.Blocked):
                provider.model_name("not-installed")

    def test_secret_file_is_private_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            state = Path(tmp) / "state"
            with patch.object(provider, "STATE", state), \
                 patch.object(provider, "KEY", state / "provider.key"):
                token = provider.token_file()
                self.assertGreaterEqual(len(token), 32)
                self.assertEqual((state / "provider.key").stat().st_mode & 0o777, 0o600)
                self.assertEqual(provider.token_file(), token)

    def test_provider_source_does_not_read_env_file(self):
        src = (ROOT / "scripts/cloudshell-provider-runtime.py").read_text()
        self.assertNotIn("load_dotenv", src)
        self.assertNotIn("shell=True", src)
        self.assertNotIn("http://0.0.0.0", src)


if __name__ == "__main__":
    unittest.main()
