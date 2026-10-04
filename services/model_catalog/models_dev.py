from __future__ import annotations

import json
import os
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_URL = "https://models.dev/catalog.json?type=all"
DEFAULT_CACHE = Path.home() / ".zwslcore" / "cache" / "models.dev.catalog.json"
MAX_CATALOG_BYTES = 16 * 1024 * 1024


class ModelsDevError(RuntimeError):
    pass


def _provider_models(provider: dict[str, Any]) -> dict[str, dict[str, Any]]:
    models = provider.get("models")
    if not isinstance(models, dict):
        return {}
    return {
        str(model_id): dict(model)
        for model_id, model in models.items()
        if isinstance(model_id, str) and isinstance(model, dict)
    }


def normalize_catalog(payload: dict[str, Any]) -> dict[str, Any]:
    providers = payload.get("providers")
    models = payload.get("models")
    if not isinstance(providers, dict) or not isinstance(models, dict):
        raise ModelsDevError("models.dev catalog must contain providers{} and models{}")

    normalized_providers: dict[str, Any] = {}
    offerings = 0
    for provider_id, raw_provider in providers.items():
        if not isinstance(provider_id, str) or not isinstance(raw_provider, dict):
            continue
        provider_models = _provider_models(raw_provider)
        offerings += len(provider_models)
        normalized_providers[provider_id] = {
            "id": str(raw_provider.get("id") or provider_id),
            "name": str(raw_provider.get("name") or provider_id),
            "api": raw_provider.get("api"),
            "doc": raw_provider.get("doc"),
            "env": list(raw_provider.get("env") or []),
            "models": provider_models,
        }

    normalized_models = {
        str(model_id): dict(raw_model)
        for model_id, raw_model in models.items()
        if isinstance(model_id, str) and isinstance(raw_model, dict)
    }
    return {
        "providers": normalized_providers,
        "models": normalized_models,
        "stats": {
            "providers": len(normalized_providers),
            "canonical_models": len(normalized_models),
            "provider_offerings": offerings,
        },
    }


def fetch_catalog(
    *,
    url: str = DEFAULT_URL,
    timeout: int = 20,
    max_bytes: int = MAX_CATALOG_BYTES,
) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "User-Agent": "zwslcore-models-dev-sync/1",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read(max_bytes + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ModelsDevError(f"unable to fetch models.dev catalog: {exc}") from exc

    if len(raw) > max_bytes:
        raise ModelsDevError(
            f"models.dev catalog exceeds maximum size of {max_bytes} bytes"
        )
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelsDevError(f"models.dev returned invalid JSON: {exc}") from exc
    if not isinstance(payload, dict):
        raise ModelsDevError("models.dev catalog root must be an object")
    return normalize_catalog(payload)


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, raw_path = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
    tmp = Path(raw_path)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def write_cache(
    catalog: dict[str, Any],
    *,
    path: str | Path = DEFAULT_CACHE,
    source_url: str = DEFAULT_URL,
) -> Path:
    target = Path(path)
    envelope = {
        "schema": 1,
        "source": "models.dev",
        "source_url": source_url,
        "fetched_at": time.time(),
        "catalog": catalog,
    }
    encoded = (
        json.dumps(envelope, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n"
    )
    _atomic_write(target, encoded)
    return target


def read_cache(
    path: str | Path = DEFAULT_CACHE,
    *,
    max_age_seconds: int | None = None,
) -> dict[str, Any]:
    target = Path(path)
    try:
        envelope = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ModelsDevError(f"models.dev cache not found: {target}") from exc
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelsDevError(f"unable to read models.dev cache: {exc}") from exc

    if envelope.get("schema") != 1 or envelope.get("source") != "models.dev":
        raise ModelsDevError("invalid models.dev cache envelope")
    fetched_at = envelope.get("fetched_at")
    if not isinstance(fetched_at, (int, float)):
        raise ModelsDevError("models.dev cache is missing fetched_at")
    if max_age_seconds is not None and time.time() - float(fetched_at) > max_age_seconds:
        raise ModelsDevError("models.dev cache is stale")
    catalog = envelope.get("catalog")
    if not isinstance(catalog, dict):
        raise ModelsDevError("models.dev cache is missing catalog")
    return normalize_catalog(catalog)


def get_catalog(
    *,
    cache_path: str | Path = DEFAULT_CACHE,
    refresh: bool = False,
    max_age_seconds: int = 24 * 60 * 60,
    allow_stale: bool = True,
    url: str = DEFAULT_URL,
) -> tuple[dict[str, Any], str]:
    if not refresh:
        try:
            return read_cache(cache_path, max_age_seconds=max_age_seconds), "cache"
        except ModelsDevError:
            pass

    try:
        catalog = fetch_catalog(url=url)
        write_cache(catalog, path=cache_path, source_url=url)
        return catalog, "network"
    except ModelsDevError:
        if allow_stale:
            try:
                return read_cache(cache_path, max_age_seconds=None), "stale-cache"
            except ModelsDevError:
                pass
        raise


def provider_env_registry(catalog: dict[str, Any]) -> list[dict[str, Any]]:
    providers = catalog.get("providers")
    if not isinstance(providers, dict):
        return []
    output: list[dict[str, Any]] = []
    for provider_id, provider in sorted(providers.items()):
        if not isinstance(provider, dict):
            continue
        env = provider.get("env")
        if not isinstance(env, list):
            env = []
        keys = sorted({
            str(value).strip()
            for value in env
            if isinstance(value, str) and str(value).strip()
        })
        output.append({
            "id": str(provider_id),
            "name": str(provider.get("name") or provider_id),
            "api": provider.get("api"),
            "doc": provider.get("doc"),
            "env": keys,
        })
    return output


def lookup_model(catalog: dict[str, Any], model_id: str) -> dict[str, Any] | None:
    models = catalog.get("models")
    if isinstance(models, dict) and isinstance(models.get(model_id), dict):
        return {"canonical": dict(models[model_id]), "providers": []}

    providers = catalog.get("providers")
    if not isinstance(providers, dict):
        return None

    found: list[dict[str, Any]] = []
    canonical_id = ""
    for provider_id, provider in providers.items():
        if not isinstance(provider, dict):
            continue
        offerings = provider.get("models")
        if not isinstance(offerings, dict):
            continue
        raw = offerings.get(model_id)
        if not isinstance(raw, dict):
            continue
        candidate = dict(raw)
        candidate["provider_id"] = provider_id
        found.append(candidate)
        if not canonical_id:
            canonical_id = str(candidate.get("canonical_model_id") or "")

    if not found:
        return None

    canonical = None
    models = catalog.get("models")
    if canonical_id and isinstance(models, dict) and isinstance(models.get(canonical_id), dict):
        canonical = dict(models[canonical_id])
    return {"canonical": canonical, "providers": found}
