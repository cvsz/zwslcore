from __future__ import annotations

import dataclasses
import math
from typing import Any, Iterable


@dataclasses.dataclass(frozen=True)
class ModelRequirements:
    structured_output: bool = False
    tool_call: bool = False
    reasoning: bool = False
    min_context: int = 0
    prefer_local: bool = True
    zero_cost_only: bool = True


@dataclasses.dataclass(frozen=True)
class ModelCandidate:
    id: str
    provider: str
    alias: str = ""
    local: bool = False
    enabled: bool = True
    cost_class: str = "UNKNOWN"
    input_cost: float | None = None
    output_cost: float | None = None
    context: int = 0
    structured_output: bool = False
    tool_call: bool = False
    reasoning: bool = False
    hardware_fit: int = 0
    source: str = "configured"


@dataclasses.dataclass(frozen=True)
class RankedModel:
    candidate: ModelCandidate
    score: int
    eligible: bool
    reasons: tuple[str, ...]
    blockers: tuple[str, ...]


FREE_CLASSES = {"FREE_LOCAL", "FREE_REMOTE"}


def _is_zero_cost(candidate: ModelCandidate) -> bool:
    if candidate.input_cost is not None or candidate.output_cost is not None:
        return candidate.input_cost == 0 and candidate.output_cost == 0
    return candidate.cost_class in FREE_CLASSES


def rank_candidate(
    candidate: ModelCandidate,
    requirements: ModelRequirements,
) -> RankedModel:
    blockers: list[str] = []
    reasons: list[str] = []
    score = 0

    if not candidate.enabled:
        blockers.append("provider disabled")
    if requirements.zero_cost_only and not _is_zero_cost(candidate):
        blockers.append("not zero cost")
    if requirements.structured_output and not candidate.structured_output:
        blockers.append("missing structured output")
    if requirements.tool_call and not candidate.tool_call:
        blockers.append("missing tool calling")
    if requirements.reasoning and not candidate.reasoning:
        blockers.append("missing reasoning")
    if requirements.min_context and candidate.context < requirements.min_context:
        blockers.append(
            f"context {candidate.context} < required {requirements.min_context}"
        )

    if candidate.local:
        score += 1000
        reasons.append("local")
    elif requirements.prefer_local:
        score -= 150

    if candidate.cost_class == "FREE_LOCAL":
        score += 500
        reasons.append("free-local")
    elif candidate.cost_class == "FREE_REMOTE":
        score += 350
        reasons.append("free-remote")
    elif _is_zero_cost(candidate):
        score += 300
        reasons.append("zero-price")

    if candidate.structured_output:
        score += 120
        reasons.append("structured-output")
    if candidate.tool_call:
        score += 80
        reasons.append("tool-call")
    if candidate.reasoning:
        score += 60
        reasons.append("reasoning")

    if candidate.context > 0:
        context_score = min(120, int(20 * math.log2(max(1, candidate.context / 4096))))
        score += max(0, context_score)
        reasons.append(f"context={candidate.context}")

    if candidate.hardware_fit:
        score += candidate.hardware_fit
        reasons.append(f"hardware-fit={candidate.hardware_fit}")

    if candidate.input_cost is not None and candidate.output_cost is not None:
        if candidate.input_cost == 0 and candidate.output_cost == 0:
            score += 60
        else:
            combined = max(0.0, candidate.input_cost) + max(0.0, candidate.output_cost)
            score -= min(300, int(combined * 10))
            reasons.append(
                f"cost={candidate.input_cost:g}/{candidate.output_cost:g}"
            )

    eligible = not blockers
    if not eligible:
        score -= 10_000

    return RankedModel(
        candidate=candidate,
        score=score,
        eligible=eligible,
        reasons=tuple(reasons),
        blockers=tuple(blockers),
    )


def rank_models(
    candidates: Iterable[ModelCandidate],
    requirements: ModelRequirements,
) -> list[RankedModel]:
    ranked = [rank_candidate(candidate, requirements) for candidate in candidates]
    ranked.sort(
        key=lambda item: (
            item.eligible,
            item.score,
            item.candidate.local,
            item.candidate.id,
        ),
        reverse=True,
    )
    return ranked


def select_best(
    candidates: Iterable[ModelCandidate],
    requirements: ModelRequirements,
) -> RankedModel | None:
    for item in rank_models(candidates, requirements):
        if item.eligible:
            return item
    return None


def _bool(value: Any) -> bool:
    return value is True


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def models_dev_candidates(
    catalog: dict[str, Any],
    *,
    configured_providers: set[str] | None = None,
    enabled_providers: set[str] | None = None,
    cost_classes: dict[str, str] | None = None,
) -> list[ModelCandidate]:
    configured = configured_providers or set()
    enabled = enabled_providers
    classes = cost_classes or {}
    providers = catalog.get("providers")
    if not isinstance(providers, dict):
        return []

    result: list[ModelCandidate] = []
    for provider_id, provider in providers.items():
        if not isinstance(provider_id, str) or not isinstance(provider, dict):
            continue
        if configured and provider_id not in configured:
            continue
        offerings = provider.get("models")
        if not isinstance(offerings, dict):
            continue
        for model_id, raw in offerings.items():
            if not isinstance(model_id, str) or not isinstance(raw, dict):
                continue
            cost = raw.get("cost")
            cost = cost if isinstance(cost, dict) else {}
            limit = raw.get("limit")
            limit = limit if isinstance(limit, dict) else {}
            result.append(
                ModelCandidate(
                    id=model_id,
                    provider=provider_id,
                    enabled=True if enabled is None else provider_id in enabled,
                    cost_class=classes.get(provider_id, "UNKNOWN"),
                    input_cost=_number(cost.get("input")),
                    output_cost=_number(cost.get("output")),
                    context=int(limit.get("context") or 0),
                    structured_output=_bool(raw.get("structured_output")),
                    tool_call=_bool(raw.get("tool_call")),
                    reasoning=_bool(raw.get("reasoning")),
                    source="models.dev",
                )
            )
    return result


def local_alias_candidates(
    env: dict[str, str],
    *,
    hardware_profile: str,
    ram_available_gb: float,
) -> list[ModelCandidate]:
    context = int(env.get("ZEAZ_OLLAMA_CONTEXT_LENGTH", "4096") or 4096)
    fast_model = env.get("ZEAZ_FAST_MODEL", "qwen2.5-coder:3b")
    coder_model = env.get("ZEAZ_CODER_MODEL", "qwen2.5-coder:7b")
    reasoning_model = env.get("ZEAZ_REASONING_MODEL", "qwen3:8b")
    local_model = env.get("ZEAZ_LOCAL_MODEL", reasoning_model)

    def fit(alias: str) -> int:
        if alias == "zeaz-fast":
            return 320 if hardware_profile.startswith("CPU_") else 220
        if alias == "zeaz-coder":
            return 260 if ram_available_gb >= 10 else -250
        if alias in {"zeaz-reasoning", "zeaz-local"}:
            if hardware_profile == "GPU_READY":
                return 280
            return 220 if ram_available_gb >= 14 else -300
        return 0

    values = (
        ("zeaz-fast", fast_model, False),
        ("zeaz-coder", coder_model, False),
        ("zeaz-reasoning", reasoning_model, True),
        ("zeaz-local", local_model, "qwen3" in local_model.lower()),
    )
    return [
        ModelCandidate(
            id=model,
            provider="ollama",
            alias=alias,
            local=True,
            enabled=True,
            cost_class="FREE_LOCAL",
            input_cost=0.0,
            output_cost=0.0,
            context=context,
            structured_output=True,
            tool_call=False,
            reasoning=reasoning,
            hardware_fit=fit(alias),
            source="local-route",
        )
        for alias, model, reasoning in values
    ]


def engineering_model_ladder(
    env: dict[str, str],
    *,
    hardware_profile: str,
    ram_available_gb: float,
) -> tuple[str, ...]:
    requirements = ModelRequirements(
        structured_output=True,
        min_context=min(
            4096,
            int(env.get("ZEAZ_OLLAMA_CONTEXT_LENGTH", "4096") or 4096),
        ),
        prefer_local=True,
        zero_cost_only=True,
    )
    ranked = rank_models(
        local_alias_candidates(
            env,
            hardware_profile=hardware_profile,
            ram_available_gb=ram_available_gb,
        ),
        requirements,
    )
    aliases = [
        item.candidate.alias
        for item in ranked
        if item.eligible
        and item.candidate.alias
        and item.candidate.hardware_fit >= 0
    ]
    return tuple(dict.fromkeys(aliases))


def snapshot_budget_for_context(context_length: int) -> int:
    context = max(2048, int(context_length))
    return min(32 * 1024, max(8 * 1024, context * 2))


def select_engineering_alias(
    env: dict[str, str],
    *,
    hardware_profile: str,
    ram_available_gb: float,
) -> RankedModel:
    requirements = ModelRequirements(
        structured_output=True,
        min_context=min(
            4096,
            int(env.get("ZEAZ_OLLAMA_CONTEXT_LENGTH", "4096") or 4096),
        ),
        prefer_local=True,
        zero_cost_only=True,
    )
    selected = select_best(
        local_alias_candidates(
            env,
            hardware_profile=hardware_profile,
            ram_available_gb=ram_available_gb,
        ),
        requirements,
    )
    if selected is None:
        raise RuntimeError("no eligible local engineering model alias")
    return selected
