import unittest

from services.model_catalog.catalog import (
    build_litellm_routes,
    is_chat_capable_model,
    merge_generated_routes,
    select_free_chat_models,
)


class ModelCatalogTests(unittest.TestCase):
    def test_filters_paid_and_media_models(self):
        items = [
            {"id": "chat:free", "type": "chat", "pricing": {"prompt": "0", "completion": "0"}},
            {"id": "paid", "type": "chat", "pricing": {"prompt": "0.01", "completion": "0"}},
            {"id": "image:free", "type": "image", "pricing": {"prompt": "0", "completion": "0"}},
        ]
        self.assertEqual([item["id"] for item in select_free_chat_models(items)], ["chat:free"])

    def test_rejects_audio_output(self):
        self.assertFalse(
            is_chat_capable_model(
                {
                    "id": "mixed",
                    "architecture": {"output_modalities": ["text", "audio"]},
                }
            )
        )

    def test_builds_openai_compatible_routes(self):
        routes = build_litellm_routes(
            "openrouter",
            [{"id": "model:free", "pricing": {"prompt": "0", "completion": "0"}}],
            base_url="https://openrouter.ai/api/v1",
            env_key="OPENROUTER_API_KEY",
        )
        self.assertEqual(routes[0]["model_name"], "free/openrouter/model:free")
        self.assertEqual(
            routes[0]["litellm_params"]["api_key"],
            "os.environ/OPENROUTER_API_KEY",
        )

    def test_merge_replaces_generated_free_routes_only(self):
        config = {
            "model_list": [
                {"model_name": "zeaz-local", "litellm_params": {"model": "ollama/qwen3:8b"}},
                {"model_name": "free/openrouter/old", "litellm_params": {"model": "openai/old"}},
            ]
        }
        merged = merge_generated_routes(
            config,
            [{"model_name": "free/openrouter/new", "litellm_params": {"model": "openai/new"}}],
        )
        self.assertEqual(
            [route["model_name"] for route in merged["model_list"]],
            ["zeaz-local", "free/openrouter/new"],
        )


if __name__ == "__main__":
    unittest.main()
