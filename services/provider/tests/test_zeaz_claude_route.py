import os
import unittest
from unittest.mock import patch

from zeaz_provider.config import load_settings


class ZeazClaudeRouteTests(unittest.TestCase):
    def load_settings(self):
        with patch.dict(os.environ, {
            "ZEAZ_RATE_LIMIT_BACKEND": "memory",
            "ZEAZ_CLIENT_KEYS": "",
            "ZEAZ_CLIENT_KEY_HASHES": "",
        }):
            return load_settings()

    def test_zeaz_claude_route_exists(self):
        settings = self.load_settings()
        self.assertIn("zeaz-claude", settings.models)

    def test_zeaz_claude_uses_ollama_provider(self):
        settings = self.load_settings()
        route = settings.models["zeaz-claude"]
        self.assertEqual(route.primary.provider, "ollama")

    def test_zeaz_claude_uses_qwen_model(self):
        settings = self.load_settings()
        route = settings.models["zeaz-claude"]
        self.assertTrue("qwen" in route.primary.model.lower())

    def test_zeaz_claude_has_local_only_policy(self):
        settings = self.load_settings()
        route = settings.models["zeaz-claude"]
        self.assertEqual(route.cost_policy, "LOCAL_ONLY")

    def test_zeaz_claude_has_no_fallbacks(self):
        settings = self.load_settings()
        route = settings.models["zeaz-claude"]
        self.assertEqual(route.fallbacks, ())

    def test_zeaz_claude_in_model_list(self):
        import httpx
        from zeaz_provider.router import ProviderRouter
        settings = self.load_settings()
        async def check():
            async with httpx.AsyncClient() as client:
                router = ProviderRouter(settings, client)
                models = router.model_list()
                ids = [m["id"] for m in models]
                self.assertIn("zeaz-claude", ids)
        import asyncio
        asyncio.run(check())


if __name__ == "__main__":
    unittest.main()
