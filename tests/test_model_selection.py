from __future__ import annotations

import unittest
from unittest.mock import patch

from scripts.engineer import _engineering_alias
from services.engineering.hardware import HardwareProfile
from services.model_catalog.selection import (
    SelectionRequirements,
    configured_local_candidates,
    rank_models,
    select_model,
)


class ModelSelectionPolicyTests(unittest.TestCase):
    def test_local_hardware_recommendation_wins_for_engineering(self):
        candidates = configured_local_candidates(
            {
                "zeaz-fast": "qwen2.5-coder:3b",
                "zeaz-coder": "qwen2.5-coder:7b",
                "zeaz-reasoning": "qwen3:8b",
            },
            context_length=4096,
        )
        selected = select_model(
            candidates,
            SelectionRequirements(
                structured_output=True,
                tool_call=True,
                min_context=4096,
                cost_policy="ZERO_COST_ONLY",
            ),
            hardware_models=["qwen2.5-coder:3b"],
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected.id, "qwen2.5-coder:3b")
        self.assertEqual(selected.execution_alias, "zeaz-fast")
        self.assertTrue(selected.local)

    def test_zero_cost_policy_rejects_paid_remote(self):
        paid = [{
            "provider_id": "paid",
            "local": False,
            "model": {
                "id": "paid/model",
                "structured_output": True,
                "tool_call": True,
                "reasoning": True,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 131072, "output": 8192},
                "cost": {"input": 1.0, "output": 2.0},
            },
            "canonical": None,
        }]
        ranked = rank_models(
            paid,
            SelectionRequirements(cost_policy="ZERO_COST_ONLY"),
            include_ineligible=True,
        )
        self.assertFalse(ranked[0].eligible)
        self.assertIn("reject:not-explicit-zero-cost", ranked[0].reasons)

    def test_free_remote_can_be_selected_when_no_local_candidate_exists(self):
        free = [{
            "provider_id": "openrouter",
            "local": False,
            "model": {
                "id": "model:free",
                "structured_output": True,
                "tool_call": True,
                "reasoning": False,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 32768, "output": 4096},
                "cost": {"input": 0, "output": 0},
            },
            "canonical": None,
        }]
        selected = select_model(
            free,
            SelectionRequirements(
                structured_output=True,
                tool_call=True,
                min_context=8192,
                cost_policy="ZERO_COST_ONLY",
            ),
        )
        self.assertIsNotNone(selected)
        self.assertEqual(selected.provider, "openrouter")
        self.assertFalse(selected.local)

    def test_capability_requirement_filters_model(self):
        candidate = [{
            "provider_id": "remote",
            "local": False,
            "model": {
                "id": "plain:free",
                "structured_output": False,
                "tool_call": True,
                "reasoning": False,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": 32768, "output": 4096},
                "cost": {"input": 0, "output": 0},
            },
            "canonical": None,
        }]
        self.assertIsNone(
            select_model(
                candidate,
                SelectionRequirements(
                    structured_output=True,
                    cost_policy="ZERO_COST_ONLY",
                ),
            )
        )


class EngineeringAutoAliasTests(unittest.TestCase):
    def profile(self) -> HardwareProfile:
        return HardwareProfile(
            os="linux",
            architecture="x86_64",
            cpu="cpu",
            logical_cpus=8,
            ram_total_gb=14.6,
            ram_available_gb=13.4,
            gpu="none-detected",
            profile="CPU_MEDIUM",
        )

    def test_auto_resolves_cpu_medium_to_zeaz_fast(self):
        env = {
            "ZEAZ_ENGINEERING_MODEL": "auto",
            "ZEAZ_FAST_MODEL": "qwen2.5-coder:3b",
            "ZEAZ_CODER_MODEL": "qwen2.5-coder:7b",
            "ZEAZ_REASONING_MODEL": "qwen2.5-coder:7b",
            "ZEAZ_LOCAL_MODEL": "qwen2.5-coder:7b",
        }
        with patch("scripts.engineer.detect_hardware", return_value=self.profile()):
            alias, detail = _engineering_alias(env)
        self.assertEqual(alias, "zeaz-fast")
        self.assertEqual(detail["mode"], "auto")
        self.assertEqual(detail["model"], "qwen2.5-coder:3b")

    def test_explicit_alias_is_preserved(self):
        alias, detail = _engineering_alias({"ZEAZ_ENGINEERING_MODEL": "zeaz-coder"})
        self.assertEqual(alias, "zeaz-coder")
        self.assertEqual(detail["mode"], "explicit")


if __name__ == "__main__":
    unittest.main()
