from __future__ import annotations

import dataclasses
from typing import Any, Iterable


@dataclasses.dataclass(frozen=True)
class SelectionRequirements:
    structured_output: bool = False
    tool_call: bool = False
    reasoning: bool = False
    min_context: int = 0
    text_output: bool = True
    cost_policy: str = "ZERO_COST_ONLY"


@dataclasses.dataclass(frozen=True)
class RankedModel:
    id: str
    provider: str
    canonical_model_id: str
    local: bool
    score: int
    eligible: bool
    reasons: tuple[str, ...]
    context: int
    cost_input: float | None
    cost_output: float | None
    structured_output: bool
    tool_call: bool
    reasoning: bool
    execution_alias: str = ""

    def as_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _context(item: dict[str, Any]) -> int:
    limit = item.get("limit")
    if not isinstance(limit, dict):
        return 0
    value = limit.get("context")
    return int(value) if isinstance(value, (int, float)) and value >= 0 else 0


def _text_output(item: dict[str, Any]) -> bool:
    modalities = item.get("modalities")
    if not isinstance(modalities, dict):
        return True
    outputs = modalities.get("output")
    if not isinstance(outputs, list) or not outputs:
        return True
    return "text" in {str(value).lower() for value in outputs}


def _cost(item: dict[str, Any]) -> tuple[float | None, float | None]:
    cost = item.get("cost")
    if not isinstance(cost, dict):
        return None, None
    return _number(cost.get("input")), _number(cost.get("output"))


def _explicit_zero_cost(item: dict[str, Any]) -> bool:
    model_id = str(item.get("id") or "")
    if model_id.endswith(":free") or model_id == "openrouter/free":
        return True
    input_cost, output_cost = _cost(item)
    return (
        input_cost is not None
        and output_cost is not None
        and input_cost == 0.0
        and output_cost == 0.0
    )


def _candidate(
    *,
    model_id: str,
    provider_id: str,
    item: dict[str, Any],
    canonical: dict[str, Any] | None,
    local: bool,
    requirements: SelectionRequirements,
    hardware_models: set[str],
) -> RankedModel:
    metadata = dict(canonical or {})
    metadata.update({key: value for key, value in item.items() if value is not None})

    structured = bool(metadata.get("structured_output"))
    tool_call = bool(metadata.get("tool_call"))
    reasoning = bool(metadata.get("reasoning"))
    context = _context(metadata)
    text_output = _text_output(metadata)
    cost_input, cost_output = _cost(item)
    reasons: list[str] = []
    eligible = True

    if requirements.text_output and not text_output:
        eligible = False
        reasons.append("reject:non-text-output")
    if requirements.structured_output and not structured:
        eligible = False
        reasons.append("reject:no-structured-output")
    if requirements.tool_call and not tool_call:
        eligible = False
        reasons.append("reject:no-tool-call")
    if requirements.reasoning and not reasoning:
        eligible = False
        reasons.append("reject:no-reasoning")
    if requirements.min_context and context < requirements.min_context:
        eligible = False
        reasons.append(f"reject:context<{requirements.min_context}")

    policy = requirements.cost_policy.upper()
    if policy == "ZERO_COST_ONLY" and not local and not _explicit_zero_cost(item):
        eligible = False
        reasons.append("reject:not-explicit-zero-cost")

    score = 0
    if local:
        score += 10_000
        reasons.append("local-first:+10000")
    elif _explicit_zero_cost(item):
        score += 2_000
        reasons.append("explicit-zero-cost:+2000")
    elif policy == "PREFER_ZERO_COST":
        score -= 500
        reasons.append("nonzero-or-unknown-cost:-500")

    if model_id in hardware_models:
        score += 2_000
        reasons.append("hardware-recommended:+2000")

    if structured:
        score += 400
        reasons.append("structured-output:+400")
    if tool_call:
        score += 300
        reasons.append("tool-call:+300")
    if reasoning:
        score += 250
        reasons.append("reasoning:+250")

    if context:
        if context >= 131_072:
            score += 500
            reasons.append("context>=131k:+500")
        elif context >= 32_768:
            score += 300
            reasons.append("context>=32k:+300")
        elif context >= 8_192:
            score += 150
            reasons.append("context>=8k:+150")

    status = str(metadata.get("status") or "").lower()
    if status == "deprecated":
        eligible = False
        reasons.append("reject:deprecated")
    elif status in {"alpha", "beta"}:
        score -= 100
        reasons.append(f"{status}:-100")

    return RankedModel(
        id=model_id,
        provider=provider_id,
        canonical_model_id=str(item.get("canonical_model_id") or metadata.get("id") or ""),
        local=local,
        score=score,
        eligible=eligible,
        reasons=tuple(reasons),
        context=context,
        cost_input=cost_input,
        cost_output=cost_output,
        structured_output=structured,
        tool_call=tool_call,
        reasoning=reasoning,
        execution_alias=str(item.get("_execution_alias") or ""),
    )


def configured_local_candidates(
    alias_models: dict[str, str],
    *,
    context_length: int,
) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for alias, raw_model in alias_models.items():
        alias_name = str(alias).strip()
        model_id = str(raw_model).strip()
        if not alias_name or not model_id or (alias_name, model_id) in seen:
            continue
        seen.add((alias_name, model_id))
        lower = model_id.lower()
        reasoning = "qwen3" in lower or "reason" in lower
        candidates.append({
            "provider_id": "ollama",
            "local": True,
            "model": {
                "id": model_id,
                "_execution_alias": alias_name,
                "name": model_id,
                "structured_output": True,
                "tool_call": True,
                "reasoning": reasoning,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": max(0, int(context_length)), "output": 4096},
                "cost": {"input": 0, "output": 0},
                "open_weights": True,
            },
            "canonical": None,
        })
    return candidates


def local_candidates(
    recommended_models: dict[str, str],
    *,
    context_length: int,
) -> list[dict[str, Any]]:
    unique: list[str] = []
    for value in recommended_models.values():
        model = str(value).strip()
        if model and model not in unique:
            unique.append(model)

    candidates: list[dict[str, Any]] = []
    for model_id in unique:
        lower = model_id.lower()
        reasoning = "qwen3" in lower or "reason" in lower
        candidates.append({
            "provider_id": "ollama",
            "local": True,
            "model": {
                "id": model_id,
                "name": model_id,
                "structured_output": True,
                "tool_call": True,
                "reasoning": reasoning,
                "modalities": {"input": ["text"], "output": ["text"]},
                "limit": {"context": max(0, int(context_length)), "output": 4096},
                "cost": {"input": 0, "output": 0},
                "open_weights": True,
            },
            "canonical": None,
        })
    return candidates


def catalog_candidates(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    providers = catalog.get("providers")
    canonical_models = catalog.get("models")
    if not isinstance(providers, dict):
        return []
    if not isinstance(canonical_models, dict):
        canonical_models = {}

    output: list[dict[str, Any]] = []
    for provider_id, provider in providers.items():
        if not isinstance(provider, dict):
            continue
        offerings = provider.get("models")
        if not isinstance(offerings, dict):
            continue
        for model_id, raw in offerings.items():
            if not isinstance(model_id, str) or not isinstance(raw, dict):
                continue
            canonical_id = str(raw.get("canonical_model_id") or "")
            canonical = canonical_models.get(canonical_id)
            output.append({
                "provider_id": str(provider_id),
                "local": False,
                "model": dict(raw),
                "canonical": dict(canonical) if isinstance(canonical, dict) else None,
            })
    return output


def rank_models(
    candidates: Iterable[dict[str, Any]],
    requirements: SelectionRequirements,
    *,
    hardware_models: Iterable[str] = (),
    include_ineligible: bool = False,
) -> list[RankedModel]:
    hardware = {str(value).strip() for value in hardware_models if str(value).strip()}
    ranked: list[RankedModel] = []
    for candidate in candidates:
        item = candidate.get("model")
        if not isinstance(item, dict):
            continue
        model_id = str(item.get("id") or "").strip()
        provider_id = str(candidate.get("provider_id") or "").strip()
        if not model_id or not provider_id:
            continue
        result = _candidate(
            model_id=model_id,
            provider_id=provider_id,
            item=item,
            canonical=candidate.get("canonical") if isinstance(candidate.get("canonical"), dict) else None,
            local=bool(candidate.get("local")),
            requirements=requirements,
            hardware_models=hardware,
        )
        if result.eligible or include_ineligible:
            ranked.append(result)

    return sorted(
        ranked,
        key=lambda item: (
            not item.eligible,
            -item.score,
            not item.local,
            item.provider,
            item.id,
        ),
    )


def select_model(
    candidates: Iterable[dict[str, Any]],
    requirements: SelectionRequirements,
    *,
    hardware_models: Iterable[str] = (),
) -> RankedModel | None:
    ranked = rank_models(
        candidates,
        requirements,
        hardware_models=hardware_models,
        include_ineligible=False,
    )
    return ranked[0] if ranked else None
