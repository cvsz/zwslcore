"""Regression checks for port inventory and non-mutating Cloudflare previews."""
from __future__ import annotations

import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "ai-stack-port-map.py"
spec = importlib.util.spec_from_file_location("ai_stack_port_map", SCRIPT)
portmap = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(portmap)


class AIStackPortMapTests(unittest.TestCase):
    def test_cloudshell_ports_and_exposure(self):
        ports = {row["name"]: row for row in portmap.load_profile("cloudshell")}
        self.assertEqual(ports["ssh"]["host_port"], 22)
        self.assertEqual(ports["provider"]["host_port"], 8080)
        self.assertEqual(ports["open-webui"]["host_port"], 3000)
        self.assertEqual(ports["ollama"]["host_port"], 11434)
        self.assertEqual(ports["signed-webhook"]["host_port"], 8765)
        self.assertEqual(ports["ollama"]["exposure"], "private")
        self.assertIsNone(ports["ollama"]["hostname_role"])

    def test_compose_ports_are_host_to_container_correct(self):
        ports = {row["name"]: row for row in portmap.load_profile("compose")}
        self.assertEqual((ports["open-webui"]["host_port"], ports["open-webui"]["service_port"]), (3000, 8080))
        self.assertEqual(ports["litellm"]["host_port"], 4000)
        self.assertEqual(ports["provider"]["host_port"], 8080)

    def test_preview_maps_only_approved_public_roles(self):
        hosts = portmap.domains("ssh.example.net", "api.example.net", "ui.example.net")
        value = portmap.ingress_preview(portmap.load_profile("cloudshell"), hosts)
        self.assertIn("ssh://127.0.0.1:22", value)
        self.assertIn("http://127.0.0.1:8080", value)
        self.assertIn("http://127.0.0.1:3000", value)
        for forbidden in (":11434", ":4000", ":8765", "0.0.0.0"):
            self.assertNotIn(forbidden, value)
        self.assertTrue(value.rstrip().endswith("- service: http_status:404"))

    def test_cannot_reuse_hostname_between_ssh_and_api(self):
        with self.assertRaises(portmap.PortMapError):
            portmap.domains("same.example.net", "same.example.net", "")
        with self.assertRaises(portmap.PortMapError):
            portmap.domains("ssh.example.net", "api.example.net", "ssh.example.net")
        with self.assertRaises(portmap.PortMapError):
            portmap.domains("invalid", "api.example.net", "")

    def test_public_ollama_is_rejected_even_if_manifest_is_modified(self):
        data = json.loads(portmap.MANIFEST.read_text())
        for row in data["profiles"]["cloudshell"]:
            if row["name"] == "ollama":
                row["hostname_role"] = "api"
                row["exposure"] = "access"
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "ports.json"
            path.write_text(json.dumps(data))
            with patch.object(portmap, "MANIFEST", path):
                with self.assertRaisesRegex(portmap.PortMapError, "Internal AI service"):
                    portmap.load_profile("cloudshell")

    def test_provider_requires_unauthenticated_request_denial(self):
        item = next(row for row in portmap.load_profile("cloudshell") if row["name"] == "provider")
        with patch.object(portmap, "_request_code", side_effect=[200, 401]):
            self.assertTrue(portmap.probe(item))
        with patch.object(portmap, "_request_code", side_effect=[200, 200]):
            self.assertFalse(portmap.probe(item))
        with patch.object(portmap, "_request_code", side_effect=[200, 302]):
            self.assertFalse(portmap.probe(item))

    def test_missing_required_local_service_fails_check(self):
        with patch.object(portmap, "probe", return_value=False):
            rc = portmap.main(["verify-local", "--profile", "cloudshell"])
        self.assertEqual(rc, 1)

    def test_preview_requires_both_public_domains(self):
        with self.assertRaises(portmap.PortMapError):
            portmap.main(["ingress-preview", "--ssh-host", "ssh.example.net",
                          "--api-host", "ssh.example.net"])


if __name__ == "__main__":
    unittest.main()
