from __future__ import annotations

import datetime as dt
import ipaddress
import json
import re
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

DEFAULT_OLLAMA_TAGS_URL = "http://127.0.0.1:11434/api/tags"
REQUEST_TIMEOUT_SECONDS = 3
MAX_RESPONSE_BYTES = 4 * 1024 * 1024
_DIGEST = re.compile(r"^[a-f0-9]{64}$")
_IDENTITY_FIELDS = (
    "digest",
    "size_bytes",
    "format",
    "family",
    "families",
    "parameter_size",
    "quantization_level",
)


class ModelInventoryError(RuntimeError):
    """Raised when local Ollama model identity cannot be read safely."""


class _NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Keep the loopback-only inventory request from following redirects."""

    def redirect_request(self, request, response, code, message, headers, new_url):
        return None


def _require_loopback_url(url: str) -> None:
    try:
        parsed = urllib.parse.urlsplit(url)
        host = parsed.hostname
        address = ipaddress.ip_address(host) if host else None
    except ValueError as exc:
        raise ModelInventoryError("Ollama inventory URL must use a loopback address") from exc
    if parsed.scheme != "http" or not (
        host == "localhost" or (address is not None and address.is_loopback)
    ):
        raise ModelInventoryError("Ollama inventory URL must use HTTP on loopback")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ModelInventoryError("Ollama inventory URL must not contain credentials or query data")


def _fetch_json(url: str, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    try:
        opener = urllib.request.build_opener(
            urllib.request.ProxyHandler({}),
            _NoRedirectHandler(),
        )
        with opener.open(request, timeout=timeout) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ModelInventoryError("unable to read local Ollama inventory") from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise ModelInventoryError("Ollama inventory response exceeds the size limit")
    try:
        payload = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ModelInventoryError("Ollama returned invalid inventory JSON") from exc
    if not isinstance(payload, dict):
        raise ModelInventoryError("Ollama inventory root must be an object")
    return payload


def _normalize_model(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ModelInventoryError("Ollama inventory contains an invalid model record")
    name = value.get("name")
    digest = value.get("digest")
    size = value.get("size")
    modified_at = value.get("modified_at")
    details = value.get("details")
    if not isinstance(name, str) or not name or "\n" in name:
        raise ModelInventoryError("Ollama inventory contains an invalid model name")
    if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
        raise ModelInventoryError("Ollama inventory contains an invalid model digest")
    if type(size) is not int or size < 0:
        raise ModelInventoryError("Ollama inventory contains an invalid model size")
    if not isinstance(modified_at, str):
        raise ModelInventoryError("Ollama inventory contains an invalid modification time")
    if not isinstance(details, dict):
        details = {}
    normalized_details: dict[str, Any] = {}
    for field in ("format", "family", "parameter_size", "quantization_level"):
        field_value = details.get(field)
        if field_value is not None and not isinstance(field_value, str):
            raise ModelInventoryError(f"Ollama inventory contains invalid {field} metadata")
        normalized_details[field] = field_value
    families = details.get("families")
    if families is not None and (
        not isinstance(families, list) or any(not isinstance(item, str) for item in families)
    ):
        raise ModelInventoryError("Ollama inventory contains invalid families metadata")
    normalized_details["families"] = sorted(set(families or []))
    return {
        "name": name,
        "digest": digest,
        "size_bytes": size,
        "modified_at": modified_at,
        "source": "ollama_local_store",
        **normalized_details,
    }


def collect_inventory(
    *,
    url: str = DEFAULT_OLLAMA_TAGS_URL,
    timeout: int = REQUEST_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    """Capture model identities from the local Ollama tags endpoint only."""
    _require_loopback_url(url)
    payload = _fetch_json(url, timeout=timeout)
    models = payload.get("models")
    if not isinstance(models, list):
        raise ModelInventoryError("Ollama inventory is missing its models list")
    normalized = [_normalize_model(item) for item in models]
    names = [item["name"] for item in normalized]
    if len(set(names)) != len(names):
        raise ModelInventoryError("Ollama inventory contains duplicate model names")
    return {
        "schema_version": 1,
        "captured_at": dt.datetime.now(dt.UTC).isoformat(),
        "source": "ollama_local_api",
        "models": sorted(normalized, key=lambda item: item["name"]),
    }


def load_manifest(path: str | Path) -> dict[str, Any]:
    try:
        manifest = json.loads(Path(path).expanduser().read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelInventoryError("unable to read model inventory manifest") from exc
    return normalize_manifest(manifest)


def normalize_manifest(manifest: Any) -> dict[str, Any]:
    if not isinstance(manifest, dict) or type(manifest.get("schema_version")) is not int:
        raise ModelInventoryError("model inventory manifest has an invalid schema")
    if manifest["schema_version"] != 1:
        raise ModelInventoryError("unsupported model inventory manifest schema")
    if manifest.get("source") != "ollama_local_api":
        raise ModelInventoryError("model inventory manifest has an invalid source")
    models = manifest.get("models")
    if not isinstance(models, list):
        raise ModelInventoryError("model inventory manifest is missing its models list")
    normalized = [_normalize_manifest_model(item) for item in models]
    names = [item["name"] for item in normalized]
    if len(set(names)) != len(names):
        raise ModelInventoryError("model inventory manifest contains duplicate model names")
    captured_at = manifest.get("captured_at")
    if not isinstance(captured_at, str):
        raise ModelInventoryError("model inventory manifest is missing captured_at")
    return {
        "schema_version": 1,
        "captured_at": captured_at,
        "source": "ollama_local_api",
        "models": sorted(normalized, key=lambda item: item["name"]),
    }


def _normalize_manifest_model(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ModelInventoryError("model inventory manifest contains an invalid model record")
    normalized = _normalize_model(
        {
            "name": value.get("name"),
            "digest": value.get("digest"),
            "size": value.get("size_bytes"),
            "modified_at": value.get("modified_at"),
            "details": {
                field: value.get(field)
                for field in ("format", "family", "families", "parameter_size", "quantization_level")
            },
        }
    )
    if value.get("source") != "ollama_local_store":
        raise ModelInventoryError("model inventory manifest contains an invalid source")
    return normalized


def compare_manifests(current: dict[str, Any], reference: dict[str, Any]) -> dict[str, Any]:
    """Compare model identities, ignoring capture and local modification timestamps."""
    current = normalize_manifest(current)
    reference = normalize_manifest(reference)
    current_models = {item["name"]: item for item in current["models"]}
    reference_models = {item["name"]: item for item in reference["models"]}
    current_names = set(current_models)
    reference_names = set(reference_models)
    added = sorted(current_names - reference_names)
    removed = sorted(reference_names - current_names)
    changed: list[dict[str, Any]] = []
    unchanged = 0
    for name in sorted(current_names & reference_names):
        before = reference_models[name]
        after = current_models[name]
        fields = {
            field: {"reference": before[field], "current": after[field]}
            for field in _IDENTITY_FIELDS
            if before[field] != after[field]
        }
        if fields:
            changed.append({"name": name, "fields": fields})
        else:
            unchanged += 1
    return {
        "schema_version": 1,
        "reference_captured_at": reference.get("captured_at"),
        "current_captured_at": current.get("captured_at"),
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged_count": unchanged,
        "drift_detected": bool(added or removed or changed),
    }
