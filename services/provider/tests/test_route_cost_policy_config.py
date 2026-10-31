import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from zeaz_provider.config import load_settings

VALID_CONFIG = """
default_model: claude
providers:
  ollama:
    api: openai
    base_url: http://ollama:11434/v1
    cost_class: FREE_LOCAL
models:
  claude:
    provider: ollama
    model: qwen2.5-coder:3b
    cost_policy: LOCAL_ONLY
    fallbacks: []
"""


class RouteCostPolicyConfigTests(unittest.TestCase):
    def load_config(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "providers.yaml"
            path.write_text(content, encoding="utf-8")
            return load_settings(path)

    def test_loads_route_level_local_only_policy(self):
        with patch.dict(os.environ, {
            "ZEAZ_COST_POLICY": "PERMIT_PAID",
            "ZEAZ_RATE_LIMIT_BACKEND": "memory",
            "ZEAZ_CLIENT_KEYS": "",
            "ZEAZ_CLIENT_KEY_HASHES": "",
        }):
            settings = self.load_config(VALID_CONFIG)

        self.assertEqual(settings.cost_policy, "PERMIT_PAID")
        self.assertEqual(
            settings.models["claude"].cost_policy,
            "LOCAL_ONLY",
        )

    def test_legacy_route_without_policy_keeps_global_policy(self):
        config = VALID_CONFIG.replace(
            "    cost_policy: LOCAL_ONLY\n",
            "",
        )
        with patch.dict(os.environ, {
            "ZEAZ_COST_POLICY": "ZERO_COST_ONLY",
            "ZEAZ_RATE_LIMIT_BACKEND": "memory",
            "ZEAZ_CLIENT_KEYS": "",
            "ZEAZ_CLIENT_KEY_HASHES": "",
        }):
            settings = self.load_config(config)

        self.assertIsNone(settings.models["claude"].cost_policy)
        self.assertEqual(settings.cost_policy, "ZERO_COST_ONLY")

    def test_invalid_route_policy_fails_closed(self):
        config = VALID_CONFIG.replace("LOCAL_ONLY", "REMOTE_ALLOWED")
        with patch.dict(os.environ, {
            "ZEAZ_COST_POLICY": "ZERO_COST_ONLY",
            "ZEAZ_RATE_LIMIT_BACKEND": "memory",
            "ZEAZ_CLIENT_KEYS": "",
            "ZEAZ_CLIENT_KEY_HASHES": "",
        }), self.assertRaisesRegex(
            RuntimeError,
            "Invalid model route cost policy",
        ):
            self.load_config(config)


if __name__ == "__main__":
    unittest.main()
