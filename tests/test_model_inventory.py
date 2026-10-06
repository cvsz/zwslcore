from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts import model_manifest
from services.model_catalog.inventory import (
    DEFAULT_OLLAMA_TAGS_URL,
    ModelInventoryError,
    collect_inventory,
    compare_manifests,
    load_manifest,
    normalize_manifest,
)


def model(name: str, digest: str, *, modified_at: str = "2026-10-01T00:00:00Z") -> dict:
    return {
        "name": name,
        "digest": digest,
        "size": 1024,
        "modified_at": modified_at,
        "details": {
            "format": "gguf",
            "family": "qwen2",
            "families": ["qwen2"],
            "parameter_size": "3.1B",
            "quantization_level": "Q4_K_M",
        },
    }


def manifest_model(name: str, digest: str, *, modified_at: str = "2026-10-01T00:00:00Z") -> dict:
    api_model = model(name, digest, modified_at=modified_at)
    return {
        "name": api_model["name"],
        "digest": api_model["digest"],
        "size_bytes": api_model["size"],
        "modified_at": api_model["modified_at"],
        "source": "ollama_local_store",
        **api_model["details"],
    }


class OllamaInventoryTests(unittest.TestCase):
    def test_capture_uses_loopback_tags_and_records_immutable_identity(self):
        digest = "a" * 64
        with patch(
            "services.model_catalog.inventory._fetch_json",
            return_value={"models": [model("qwen2.5-coder:3b", digest)]},
        ) as fetch:
            manifest = collect_inventory()

        fetch.assert_called_once_with(DEFAULT_OLLAMA_TAGS_URL, timeout=3)
        self.assertEqual(manifest["source"], "ollama_local_api")
        self.assertEqual(manifest["models"][0]["digest"], digest)
        self.assertEqual(manifest["models"][0]["size_bytes"], 1024)
        self.assertEqual(manifest["models"][0]["quantization_level"], "Q4_K_M")
        self.assertNotIn("modelfile", json.dumps(manifest).lower())

    def test_non_loopback_endpoint_is_rejected_before_network_access(self):
        with patch("services.model_catalog.inventory._fetch_json") as fetch:
            with self.assertRaisesRegex(ModelInventoryError, "loopback"):
                collect_inventory(url="http://example.com:11434/api/tags")
        fetch.assert_not_called()

    def test_redirect_handler_blocks_redirects(self):
        from services.model_catalog.inventory import _NoRedirectHandler

        handler = _NoRedirectHandler()
        redirected = handler.redirect_request(
            None, None, 302, "Found", {}, "http://example.com/api/tags"
        )
        self.assertIsNone(redirected)

    def test_inventory_request_uses_direct_no_proxy_opener(self):
        from services.model_catalog.inventory import _fetch_json

        opener = unittest.mock.MagicMock()
        opener.open.return_value.__enter__.return_value.read.return_value = b'{"models": []}'
        with patch("services.model_catalog.inventory.urllib.request.build_opener", return_value=opener) as build:
            self.assertEqual(_fetch_json(DEFAULT_OLLAMA_TAGS_URL), {"models": []})

        handlers = build.call_args.args
        self.assertEqual(handlers[0].proxies, {})
        self.assertEqual(type(handlers[1]).__name__, "_NoRedirectHandler")

    def test_invalid_digest_and_duplicate_tags_fail_closed(self):
        with patch(
            "services.model_catalog.inventory._fetch_json",
            return_value={"models": [model("bad", "short")]},
        ):
            with self.assertRaisesRegex(ModelInventoryError, "digest"):
                collect_inventory()

        duplicated = model("same", "b" * 64)
        with patch(
            "services.model_catalog.inventory._fetch_json",
            return_value={"models": [duplicated, duplicated]},
        ):
            with self.assertRaisesRegex(ModelInventoryError, "duplicate"):
                collect_inventory()

    def test_compare_detects_add_remove_and_identity_change_but_ignores_timestamps(self):
        reference = normalize_manifest({
            "schema_version": 1,
            "captured_at": "2026-10-01T00:00:00Z",
            "source": "ollama_local_api",
            "models": [
                manifest_model("changed", "a" * 64),
                manifest_model("removed", "b" * 64),
            ],
        })
        current = normalize_manifest({
            "schema_version": 1,
            "captured_at": "2026-10-02T00:00:00Z",
            "source": "ollama_local_api",
            "models": [
                manifest_model("changed", "c" * 64, modified_at="2026-10-02T00:00:00Z"),
                manifest_model("added", "d" * 64),
            ],
        })

        result = compare_manifests(current, reference)

        self.assertEqual(result["added"], ["added"])
        self.assertEqual(result["removed"], ["removed"])
        self.assertEqual(result["changed"][0]["name"], "changed")
        self.assertEqual(set(result["changed"][0]["fields"]), {"digest"})
        self.assertEqual(result["unchanged_count"], 0)
        self.assertTrue(result["drift_detected"])

    def test_manifest_load_rejects_unsupported_schema(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "manifest.json"
            path.write_text(json.dumps({"schema_version": 2}), encoding="utf-8")
            with self.assertRaisesRegex(ModelInventoryError, "unsupported"):
                load_manifest(path)

    def test_cli_fail_on_drift_returns_nonzero(self):
        reference = {
            "schema_version": 1,
            "captured_at": "2026-10-01T00:00:00Z",
            "source": "ollama_local_api",
            "models": [manifest_model("same", "a" * 64)],
        }
        current = {
            "schema_version": 1,
            "captured_at": "2026-10-02T00:00:00Z",
            "source": "ollama_local_api",
            "models": [manifest_model("same", "b" * 64)],
        }
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "reference.json"
            path.write_text(json.dumps(reference), encoding="utf-8")
            with patch("scripts.model_manifest.collect_inventory", return_value=current), redirect_stdout(io.StringIO()) as output:
                status = model_manifest.main(["--compare", str(path), "--fail-on-drift"])

        self.assertEqual(status, 1)
        self.assertTrue(json.loads(output.getvalue())["drift_detected"])


if __name__ == "__main__":
    unittest.main()
