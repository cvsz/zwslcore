from __future__ import annotations

import unittest

from services.model_catalog.selector import (
    ModelCandidate,
    ModelRequirements,
    local_alias_candidates,
    models_dev_candidates,
    rank_models,
    select_best,
    select_engineering_alias,
)


class ModelSelectorTests(unittest.TestCase):
    def test_cpu_medium_prefers_zeaz_fast_for_engineering(self):
        selected = select_engineering_alias(
            {
                "ZEAZ_FAST_MODEL": "qwen2.5-coder:3b",
                "ZEAZ_CODER_MODEL": "qwen2.5-coder:7b",
                "ZEAZ_REASONING_MODEL": "qwen3:8b",
                "ZEAZ_LOCAL_MODEL": "qwen2.5-coder:7b",
                "ZEAZ_OLLAMA_CONTEXT_LENGTH": "4096",
            },
            hardware_profile="CPU_MEDIUM",
            ram_available_gb=13,
        )
        self.assertEqual(selected.candidate.alias, "zeaz-fast")
        self.assertTrue(selected.eligible)

    def test_gpu_ready_can_prefer_reasoning_alias(self):
        selected = select_engineering_alias(
            {
                "ZEAZ_FAST_MODEL": "qwen2.5-coder:3b",
                "ZEAZ_CODER_MODEL": "qwen2.5-coder:7b",
                "ZEAZ_REASONING_MODEL": "qwen3:8b",
                "ZEAZ_LOCAL_MODEL": "qwen3:8b",
                "ZEAZ_OLLAMA_CONTEXT_LENGTH": "16384",
            },
            hardware_profile="GPU_READY",
            ram_available_gb=24,
        )
        self.assertEqual(selected.candidate.alias, "zeaz-reasoning")

    def test_paid_remote_offering_is_blocked_under_zero_cost(self):
        candidate = ModelCandidate(
            id="paid-model",
            provider="openrouter",
            enabled=True,
            cost_class="FREE_REMOTE",
            input_cost=1.0,
            output_cost=2.0,
            context=65536,
            structured_output=True,
        )
        ranked = rank_models(
            [candidate],
            ModelRequirements(structured_output=True, zero_cost_only=True),
        )[0]
        self.assertFalse(ranked.eligible)
        self.assertIn("not zero cost", ranked.blockers)

    def test_disabled_remote_provider_is_ineligible(self):
        catalog = {
            "providers": {
                "openrouter": {
                    "models": {
                        "free-model": {
                            "id": "free-model",
                            "structured_output": True,
                            "tool_call": True,
                            "reasoning": False,
                            "limit": {"context": 32768},
                            "cost": {"input": 0, "output": 0},
                        }
                    }
                }
            }
        }
        candidates = models_dev_candidates(
            catalog,
            configured_providers={"openrouter"},
            enabled_providers=set(),
            cost_classes={"openrouter": "FREE_REMOTE"},
        )
        self.assertEqual(len(candidates), 1)
        self.assertFalse(candidates[0].enabled)
        selected = select_best(
            candidates,
            ModelRequirements(structured_output=True, zero_cost_only=True),
        )
        self.assertIsNone(selected)

    def test_remote_free_model_can_rank_when_explicitly_enabled(self):
        catalog = {
            "providers": {
                "openrouter": {
                    "models": {
                        "free-model": {
                            "id": "free-model",
                            "structured_output": True,
                            "tool_call": True,
                            "reasoning": True,
                            "limit": {"context": 131072},
                            "cost": {"input": 0, "output": 0},
                        }
                    }
                }
            }
        }
        candidates = models_dev_candidates(
            catalog,
            configured_providers={"openrouter"},
            enabled_providers={"openrouter"},
            cost_classes={"openrouter": "FREE_REMOTE"},
        )
        selected = select_best(
            candidates,
            ModelRequirements(
                structured_output=True,
                tool_call=True,
                reasoning=True,
                min_context=32768,
                zero_cost_only=True,
            ),
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected.candidate.id, "free-model")

    def test_local_candidates_are_zero_cost_and_structured(self):
        candidates = local_alias_candidates(
            {"ZEAZ_OLLAMA_CONTEXT_LENGTH": "4096"},
            hardware_profile="CPU_SMALL",
            ram_available_gb=8,
        )
        self.assertTrue(all(item.local for item in candidates))
        self.assertTrue(all(item.structured_output for item in candidates))
        self.assertTrue(all(item.cost_class == "FREE_LOCAL" for item in candidates))


if __name__ == "__main__":
    unittest.main()
