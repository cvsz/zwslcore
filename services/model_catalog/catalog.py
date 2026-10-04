from __future__ import annotations

import copy
import json
import re
from typing import Any, Iterable

MEDIA_TYPES = {
    "audio", "embedding", "image", "moderation", "rerank",
    "speech", "transcribe", "tts", "video",
}
MEDIA_OUTPUTS = {"audio", "image", "video"}


def _tokens(value: Any) -> set[str]:
    if isinstance(value, list):
        values = value
    elif value is None:
        values = []
    else:
        values = re.split(r"[^a-z0-9]+", str(value).lower())
    return {str(item).strip().lower() for item in values if str(item).strip()}


def is_chat_capable_model(item: dict[str, Any]) -> bool:
    model_type = str(item.get("type") or "").strip().lower()
    if model_type in MEDIA_TYPES:
        return False

    architecture = item.get("architecture")
    if isinstance(architecture, dict):
        outputs = _tokens(architecture.get("output_modalities"))
        if outputs and ("text" not in outputs or outputs & MEDIA_OUTPUTS):
            return False
    return True


def _zero(value: Any) -> bool:
    try:
        return float(str(value)) == 0.0
    except (TypeError, ValueError):
        return False


def is_explicitly_free(item: dict[str, Any]) -> bool:
    model_id = str(item.get("id") or item.get("name") or "")
    if model_id.endswith(":free") or model_id == "openrouter/free":
        return True
    pricing = item.get("pricing")
    return (
        isinstance(pricing, dict)
        and _zero(pricing.get("prompt"))
        and _zero(pricing.get("completion"))
    )


def select_free_chat_models(items: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    for raw in items:
        if not isinstance(raw, dict):
            continue
        model_id = str(raw.get("id") or raw.get("name") or "").strip()
        if not model_id or model_id in seen:
            continue
        if not is_explicitly_free(raw) or not is_chat_capable_model(raw):
            continue
        item = dict(raw)
        item["id"] = model_id
        selected.append(item)
        seen.add(model_id)

    return selected


def build_litellm_routes(
    provider: str,
    models: Iterable[dict[str, Any]],
    *,
    base_url: str,
    env_key: str,
) -> list[dict[str, Any]]:
    routes: list[dict[str, Any]] = []
    for item in select_free_chat_models(models):
        model_id = item["id"]
        params: dict[str, Any] = {
            "model": f"openai/{model_id}",
            "api_base": base_url.rstrip("/"),
        }
        if env_key:
            params["api_key"] = f"os.environ/{env_key}"
        routes.append(
            {
                "model_name": f"free/{provider}/{model_id}",
                "litellm_params": params,
            }
        )
    return routes


def merge_generated_routes(
    config: dict[str, Any],
    generated: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    result = copy.deepcopy(config)
    current = result.get("model_list")
    retained = [
        route
        for route in (current if isinstance(current, list) else [])
        if not (
            isinstance(route, dict)
            and str(route.get("model_name") or "").startswith("free/")
        )
    ]
    names = {
        str(route.get("model_name"))
        for route in retained
        if isinstance(route, dict) and route.get("model_name")
    }
    for route in generated:
        name = str(route.get("model_name") or "")
        if not name or name in names:
            continue
        retained.append(copy.deepcopy(route))
        names.add(name)
    result["model_list"] = retained
    return result


def render_config(config: dict[str, Any]) -> str:
    return json.dumps(config, indent=2, ensure_ascii=False) + "\n"
