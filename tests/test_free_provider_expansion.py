"""Regression checks for opt-in free-tier providers and unchanged legacy routing."""
from __future__ import annotations

import os
import unittest
from pathlib import Path
from unittest.mock import patch

from services.provider.zeaz_provider.config import load_settings

CONFIG = Path(__file__).resolve().parents[1] / "services/provider/config/providers.yaml"
NEW_PROVIDERS = ("cerebras", "sambanova", "cloudflare")
NEW_ALIASES = ("zeaz-cloud-cerebras", "zeaz-cloud-sambanova", "zeaz-cloud-cloudflare")
OPT_IN = {
    "CEREBRAS_FREE_ENABLED": "true",
    "SAMBANOVA_FREE_ENABLED": "true",
    "CLOUDFLARE_FREE_ENABLED": "true",
}


class FreeProviderExpansionTests(unittest.TestCase):
    def test_defaults_do_not_expose_optional_providers(self):
        with patch.dict(os.environ, {key: "false" for key in OPT_IN}):
            settings = load_settings(CONFIG)
        for provider in NEW_PROVIDERS:
            self.assertNotIn(provider, settings.providers)
        for alias in NEW_ALIASES:
            self.assertNotIn(alias, settings.models)
        self.assertEqual(settings.default_model, "zeaz-free")
        self.assertIn("zeaz-fast", settings.models)
        self.assertIn("zeaz-coder", settings.models)

    def test_explicit_opt_in_exposes_routes(self):
        with patch.dict(os.environ, OPT_IN):
            settings = load_settings(CONFIG)
        for provider, alias in zip(NEW_PROVIDERS, NEW_ALIASES):
            self.assertIn(provider, settings.providers)
            self.assertEqual(settings.models[alias].primary.provider, provider)
            self.assertEqual(settings.providers[provider].cost_class, "FREE_REMOTE")
        self.assertTrue(
            {"cerebras", "sambanova", "cloudflare"}.issubset(
                {item.provider for item in settings.models["zeaz-cloud-auto"].fallbacks}
            )
        )

    def test_cloud_auto_is_local_first_when_optional_providers_disabled(self):
        with patch.dict(os.environ, {
            **{key: "false" for key in OPT_IN},
            "FREE_CLOUD_FALLBACK_ENABLED": "false",
        }):
            settings = load_settings(CONFIG)
        route = settings.models["zeaz-cloud-auto"]
        self.assertEqual(route.primary.provider, "ollama")
        self.assertFalse(route.fallbacks)


if __name__ == "__main__":
    unittest.main()
