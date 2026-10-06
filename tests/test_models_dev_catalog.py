from __future__ import annotations

import json
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

from services.model_catalog.models_dev import (
    ModelsDevError,
    get_catalog,
    lookup_model,
    normalize_catalog,
    read_cache,
    write_cache,
)


SAMPLE = {
    "providers": {
        "openrouter": {
            "id": "openrouter",
            "name": "OpenRouter",
            "api": "https://openrouter.ai/api/v1",
            "doc": "https://openrouter.ai/docs",
            "env": ["OPENROUTER_API_KEY"],
            "models": {
                "deepseek/deepseek-r1:free": {
                    "id": "deepseek/deepseek-r1:free",
                    "canonical_model_id": "deepseek/deepseek-r1",
                    "name": "DeepSeek R1 Free",
                    "description": "test",
                    "attachment": False,
                    "reasoning": True,
                    "tool_call": True,
                    "structured_output": True,
                    "release_date": "2026-01",
                    "last_updated": "2026-09",
                    "modalities": {"input": ["text"], "output": ["text"]},
                    "open_weights": True,
                    "limit": {"context": 131072, "output": 32768},
                    "cost": {"input": 0, "output": 0},
                }
            },
        }
    },
    "models": {
        "deepseek/deepseek-r1": {
            "id": "deepseek/deepseek-r1",
            "name": "DeepSeek R1",
            "description": "canonical",
            "reasoning": True,
            "tool_call": True,
            "structured_output": True,
            "open_weights": True,
            "modalities": {"input": ["text"], "output": ["text"]},
            "limit": {"context": 131072, "output": 32768},
        }
    },
}


class ModelsDevCatalogTests(unittest.TestCase):
    def test_normalize_catalog_counts_providers_and_offerings(self):
        value = normalize_catalog(SAMPLE)
        self.assertEqual(value["stats"]["providers"], 1)
        self.assertEqual(value["stats"]["canonical_models"], 1)
        self.assertEqual(value["stats"]["provider_offerings"], 1)

    def test_lookup_canonical_model(self):
        value = lookup_model(normalize_catalog(SAMPLE), "deepseek/deepseek-r1")
        self.assertEqual(value["canonical"]["name"], "DeepSeek R1")
        self.assertEqual(value["providers"], [])

    def test_lookup_provider_model_resolves_canonical(self):
        value = lookup_model(
            normalize_catalog(SAMPLE),
            "deepseek/deepseek-r1:free",
        )
        self.assertEqual(value["canonical"]["id"], "deepseek/deepseek-r1")
        self.assertEqual(value["providers"][0]["provider_id"], "openrouter")
        self.assertEqual(value["providers"][0]["cost"]["input"], 0)

    def test_cache_round_trip_and_stale_guard(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.json"
            write_cache(normalize_catalog(SAMPLE), path=path)
            self.assertEqual(read_cache(path)["stats"]["providers"], 1)

            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["fetched_at"] = time.time() - 1000
            path.write_text(json.dumps(envelope), encoding="utf-8")
            with self.assertRaisesRegex(ModelsDevError, "stale"):
                read_cache(path, max_age_seconds=10)

    def test_refresh_fetches_and_persists_a_fresh_cache(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.json"
            catalog = normalize_catalog(SAMPLE)
            source_url = "https://example.com/catalog.json"

            with patch(
                "services.model_catalog.models_dev.fetch_catalog",
                return_value=catalog,
            ) as fetch:
                value, source = get_catalog(
                    cache_path=path,
                    refresh=True,
                    url=source_url,
                )

            fetch.assert_called_once_with(url=source_url)
            self.assertEqual(source, "network")
            self.assertEqual(value["stats"]["provider_offerings"], 1)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(envelope["source_url"], source_url)
            self.assertGreater(envelope["fetched_at"], 0)

            cached, cache_source = get_catalog(cache_path=path, max_age_seconds=60)

        self.assertEqual(cache_source, "cache")
        self.assertEqual(cached["stats"]["provider_offerings"], 1)

    def test_get_catalog_falls_back_to_stale_cache(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.json"
            write_cache(normalize_catalog(SAMPLE), path=path)
            envelope = json.loads(path.read_text(encoding="utf-8"))
            envelope["fetched_at"] = time.time() - 1000
            path.write_text(json.dumps(envelope), encoding="utf-8")

            with patch(
                "services.model_catalog.models_dev.fetch_catalog",
                side_effect=ModelsDevError("offline"),
            ):
                value, source = get_catalog(
                    cache_path=path,
                    max_age_seconds=10,
                    allow_stale=True,
                )

            self.assertEqual(source, "stale-cache")
            self.assertEqual(value["stats"]["canonical_models"], 1)

    def test_invalid_catalog_rejected(self):
        with self.assertRaisesRegex(ModelsDevError, "providers"):
            normalize_catalog({"models": {}})

    def test_cache_rejects_unsupported_schema_version(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "catalog.json"
            for schema in (2, True, 1.0):
                path.write_text(
                    json.dumps({"schema": schema, "source": "models.dev"}),
                    encoding="utf-8",
                )
                with self.assertRaisesRegex(ModelsDevError, "cache envelope"):
                    read_cache(path)


if __name__ == "__main__":
    unittest.main()
