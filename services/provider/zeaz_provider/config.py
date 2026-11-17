from __future__ import annotations

import ipaddress
import os
import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import yaml

from .cost import CostClass, CostPolicy, parse_cost_class, parse_cost_policy
from .security import client_key_digest

ENV_PATTERN = re.compile(r"\$\{([A-Z][A-Z0-9_]*)(?::-([^}]*))?\}")
CLIENT_KEY_HASH_PATTERN = re.compile(r"^(?:sha256:)?([a-fA-F0-9]{64})$")

# Constants for validation limits
MAX_NAME_LENGTH = 128
MAX_MODEL_LENGTH = 512
MAX_ALIAS_LENGTH = 256
MAX_URL_LENGTH = 2048
MAX_HEADERS_COUNT = 64
MAX_API_VERSION_LENGTH = 128
MAX_RATE_LIMIT_KEY_PREFIX_LENGTH = 128
ALLOWED_API_VERSION_CHARS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"
FORBIDDEN_CONTROL_CHARS = "\r\n\x00"
ALLOWED_PROVIDER_APIS = {"anthropic", "azure", "openai", "responses"}
ALLOWED_RATE_LIMIT_BACKENDS = {"memory", "redis"}


def _expand(value: Any) -> Any:
    if isinstance(value, str):
        def replace(match: re.Match[str]) -> str:
            name, default = match.group(1), match.group(2)
            return os.getenv(name, default or "")

        return ENV_PATTERN.sub(replace, value)
    if isinstance(value, list):
        return [_expand(item) for item in value]
    if isinstance(value, dict):
        return {key: _expand(item) for key, item in value.items()}
    return value


def _enabled(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() not in {"0", "false", "no", "off", ""}


def _validate_string_length(value: str, minimum: int, maximum: int, label: str) -> None:
    if not isinstance(value, str) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum} characters")


def _validate_no_control_chars(value: str, label: str) -> None:
    if any(character in value for character in FORBIDDEN_CONTROL_CHARS):
        raise ValueError(f"{label} contains invalid control characters")


def _validate_api_version(value: str, label: str) -> None:
    if (
        not isinstance(value, str)
        or len(value) > MAX_API_VERSION_LENGTH
        or any(character not in ALLOWED_API_VERSION_CHARS for character in value)
    ):
        raise ValueError(f"{label} is invalid")


def _validate_headers(headers: dict[str, str]) -> None:
    if not isinstance(headers, dict) or len(headers) > MAX_HEADERS_COUNT:
        raise ValueError("provider headers are invalid")
    for key, value in headers.items():
        if (
            not isinstance(key, str)
            or not key
            or len(key) > MAX_NAME_LENGTH
            or not isinstance(value, str)
            or "\r" in key
            or "\n" in key
            or "\r" in value
            or "\n" in value
        ):
            raise ValueError("provider headers are invalid")


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    api: str
    base_url: str
    api_key: str = ""
    account: str = "default"
    region: str = "global"
    headers: dict[str, str] = field(default_factory=dict)
    api_version: str = ""
    timeout_seconds: float = 120.0
    total_timeout_seconds: float = 135.0
    max_attempts: int = 3
    retry_base_seconds: float = 0.25
    retry_max_seconds: float = 5.0
    circuit_failure_threshold: int = 5
    circuit_reset_seconds: float = 30.0
    cost_class: str = CostClass.UNKNOWN.value
    native_structured_outputs: bool = False

    def __post_init__(self) -> None:
        _validate_string_length(self.name, 1, MAX_NAME_LENGTH, "provider name")
        if not isinstance(self.api, str) or self.api not in ALLOWED_PROVIDER_APIS:
            raise ValueError("provider API must be anthropic, azure, openai, or responses")
        _validate_origin(self.base_url, "provider base_url")
        parse_cost_class(self.cost_class)
        if type(self.native_structured_outputs) is not bool:
            raise ValueError("provider native_structured_outputs must be a boolean")
        if not isinstance(self.api_key, str) or "\x00" in self.api_key:
            raise ValueError("provider api_key is invalid")
        _validate_string_length(self.account, 1, MAX_NAME_LENGTH, "provider account")
        _validate_string_length(self.region, 1, MAX_NAME_LENGTH, "provider region")
        _validate_headers(self.headers)
        _validate_api_version(self.api_version, "provider api_version")
        _require_number(self.timeout_seconds, "provider timeout_seconds", minimum=0.001, maximum=600)
        _require_number(
            self.total_timeout_seconds,
            "provider total_timeout_seconds",
            minimum=0.001,
            maximum=3600,
        )
        _require_integer(self.max_attempts, "provider max_attempts", minimum=1, maximum=10)
        _require_number(
            self.retry_base_seconds,
            "provider retry_base_seconds",
            minimum=0,
            maximum=60,
        )
        _require_number(
            self.retry_max_seconds,
            "provider retry_max_seconds",
            minimum=0,
            maximum=120,
        )
        if self.retry_max_seconds < self.retry_base_seconds:
            raise ValueError("provider retry_max_seconds cannot be lower than retry_base_seconds")
        _require_integer(
            self.circuit_failure_threshold,
            "provider circuit_failure_threshold",
            minimum=1,
            maximum=100,
        )
        _require_number(
            self.circuit_reset_seconds,
            "provider circuit_reset_seconds",
            minimum=0.001,
            maximum=3600,
        )


@dataclass(frozen=True)
class RouteTarget:
    provider: str
    model: str

    def __post_init__(self) -> None:
        _validate_string_length(self.provider, 1, MAX_NAME_LENGTH, "route provider")
        if (
            not isinstance(self.model, str)
            or not 1 <= len(self.model) <= MAX_MODEL_LENGTH
            or any(character in self.model for character in FORBIDDEN_CONTROL_CHARS)
        ):
            raise ValueError("route model is invalid")


@dataclass(frozen=True)
class ModelRoute:
    alias: str
    primary: RouteTarget
    fallbacks: tuple[RouteTarget, ...] = ()

    def __post_init__(self) -> None:
        _validate_string_length(self.alias, 1, MAX_ALIAS_LENGTH, "model alias")


@dataclass(frozen=True)
class Settings:
    providers: dict[str, ProviderConfig]
    models: dict[str, ModelRoute]
    client_key_hashes: frozenset[bytes]
    default_model: str
    max_request_bytes: int = 4 * 1024 * 1024
    max_output_tokens: int = 131072
    rate_limit_per_minute: int = 120
    metrics_enabled: bool = True
    otlp_metrics_enabled: bool = False
    rate_limit_backend: str = "memory"
    redis_url: str = ""
    rate_limit_key_prefix: str = "zeaz:rate-limit:"
    trusted_proxy_cidrs: tuple[str, ...] = ()
    max_concurrent_requests: int = 100
    max_response_bytes: int = 16 * 1024 * 1024
    cost_policy: str = CostPolicy.ZERO_COST_ONLY.value


def _load_providers(raw: dict[str, Any]) -> dict[str, ProviderConfig]:
    providers: dict[str, ProviderConfig] = {}
    raw_providers = raw.get("providers", {})
    if not isinstance(raw_providers, Mapping):
        raise TypeError("Provider configuration providers must be an object")
    for name, value in raw_providers.items():
        if not isinstance(name, str):
            raise TypeError("Provider configuration names must be strings")
        if not isinstance(value, Mapping):
            raise TypeError("Provider configuration entries must be objects")
        if not _enabled(value.get("enabled", True)):
            continue
        provider_value = dict(value)
        provider_value.pop("enabled", None)
        try:
            providers[name] = ProviderConfig(name=name, **provider_value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid provider configuration: {name}") from exc
    return providers


def _load_models(
    raw: dict[str, Any],
    providers: dict[str, ProviderConfig],
) -> dict[str, ModelRoute]:
    models: dict[str, ModelRoute] = {}
    raw_models = raw.get("models", {})
    if not isinstance(raw_models, Mapping):
        raise TypeError("Provider configuration models must be an object")
    for alias, value in raw_models.items():
        if not isinstance(alias, str):
            raise TypeError("Model route names must be strings")
        if not isinstance(value, Mapping):
            raise TypeError("Model route entries must be objects")
        try:
            primary = RouteTarget(provider=value["provider"], model=value["model"])
        except (KeyError, TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid model route: {alias}") from exc
        if primary.provider not in providers:
            continue
        raw_fallbacks = value.get("fallbacks", [])
        if not isinstance(raw_fallbacks, list):
            raise TypeError(f"Invalid model route fallbacks: {alias}")
        fallbacks: list[RouteTarget] = []
        for item in raw_fallbacks:
            if not isinstance(item, Mapping) or "provider" not in item or "model" not in item:
                raise TypeError(f"Invalid model route fallback: {alias}")
            try:
                fallback = RouteTarget(provider=item["provider"], model=item["model"])
            except (TypeError, ValueError) as exc:
                raise RuntimeError(f"Invalid model route fallback: {alias}") from exc
            if fallback.provider not in providers:
                continue
            fallbacks.append(fallback)
        try:
            models[alias] = ModelRoute(alias=alias, primary=primary, fallbacks=tuple(fallbacks))
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Invalid model route: {alias}") from exc
    return models


def _load_client_key_hashes() -> frozenset[bytes]:
    key_hashes: set[bytes] = {
        client_key_digest(key.strip())
        for key in os.getenv("ZEAZ_CLIENT_KEYS", "").split(",")
        if key.strip()
    }
    for configured_hash in os.getenv("ZEAZ_CLIENT_KEY_HASHES", "").split(","):
        if not configured_hash.strip():
            continue
        match = CLIENT_KEY_HASH_PATTERN.fullmatch(configured_hash.strip())
        if not match:
            raise RuntimeError("ZEAZ_CLIENT_KEY_HASHES contains an invalid SHA-256 hash")
        key_hashes.add(bytes.fromhex(match.group(1)))
    return frozenset(key_hashes)


def _load_settings_from_env() -> dict[str, Any]:
    rate_limit_backend = os.getenv("ZEAZ_RATE_LIMIT_BACKEND", "memory").strip().lower()
    if rate_limit_backend not in ALLOWED_RATE_LIMIT_BACKENDS:
        raise RuntimeError("ZEAZ_RATE_LIMIT_BACKEND must be memory or redis")
    redis_url = os.getenv("ZEAZ_REDIS_URL", "")
    if rate_limit_backend == "redis" and not redis_url:
        raise RuntimeError("ZEAZ_REDIS_URL is required for the Redis rate-limit backend")
    trusted_proxy_cidrs = tuple(
        item.strip()
        for item in os.getenv("ZEAZ_TRUSTED_PROXY_CIDRS", "").split(",")
        if item.strip()
    )
    try:
        trusted_proxy_cidrs = tuple(
            str(ipaddress.ip_network(item, strict=False)) for item in trusted_proxy_cidrs
        )
    except ValueError as exc:
        raise RuntimeError("ZEAZ_TRUSTED_PROXY_CIDRS contains an invalid CIDR") from exc
    max_request_bytes = _env_int(
        "ZEAZ_MAX_REQUEST_BYTES",
        4 * 1024 * 1024,
        minimum=1024,
        maximum=67_108_864,
    )
    max_output_tokens = _env_int(
        "ZEAZ_MAX_OUTPUT_TOKENS",
        131072,
        minimum=1,
        maximum=1_000_000,
    )
    rate_limit_per_minute = _env_int(
        "ZEAZ_RATE_LIMIT_PER_MINUTE",
        120,
        minimum=1,
        maximum=1_000_000,
    )
    max_concurrent_requests = _env_int(
        "ZEAZ_MAX_CONCURRENT_REQUESTS",
        100,
        minimum=1,
        maximum=10_000,
    )
    max_response_bytes = _env_int(
        "ZEAZ_MAX_RESPONSE_BYTES",
        16 * 1024 * 1024,
        minimum=1024,
        maximum=1_073_741_824,
    )
    rate_limit_key_prefix = os.getenv("ZEAZ_RATE_LIMIT_KEY_PREFIX", "zeaz:rate-limit:")
    if (
        not 1 <= len(rate_limit_key_prefix) <= MAX_RATE_LIMIT_KEY_PREFIX_LENGTH
        or any(character in rate_limit_key_prefix for character in FORBIDDEN_CONTROL_CHARS)
    ):
        raise RuntimeError("ZEAZ_RATE_LIMIT_KEY_PREFIX is invalid")
    try:
        cost_policy = parse_cost_policy(os.getenv("ZEAZ_COST_POLICY", CostPolicy.ZERO_COST_ONLY.value))
    except ValueError as exc:
        raise RuntimeError("ZEAZ_COST_POLICY is invalid") from exc
    return {
        "rate_limit_backend": rate_limit_backend,
        "redis_url": redis_url,
        "trusted_proxy_cidrs": trusted_proxy_cidrs,
        "max_request_bytes": max_request_bytes,
        "max_output_tokens": max_output_tokens,
        "rate_limit_per_minute": rate_limit_per_minute,
        "max_concurrent_requests": max_concurrent_requests,
        "max_response_bytes": max_response_bytes,
        "rate_limit_key_prefix": rate_limit_key_prefix,
        "cost_policy": cost_policy.value,
        "metrics_enabled": _enabled(os.getenv("ZEAZ_METRICS_ENABLED", "true")),
        "otlp_metrics_enabled": _enabled(os.getenv("OTEL_EXPORTER_OTLP_METRICS_ENDPOINT", "")),
    }


def load_settings(path: str | Path | None = None) -> Settings:
    config_path = Path(path if path is not None else os.getenv("ZEAZ_CONFIG", "config/providers.yaml"))
    raw_value = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if raw_value is None:
        raw_value = {}
    if not isinstance(raw_value, Mapping):
        raise TypeError("Provider configuration must be a YAML object")
    raw = _expand(dict(raw_value))

    providers = _load_providers(raw)
    if not providers:
        raise RuntimeError("No providers are enabled")

    models = _load_models(raw, providers)
    if not models:
        raise RuntimeError("No model routes are configured")

    client_key_hashes = _load_client_key_hashes()
    default_model = raw.get("default_model") or next(iter(models))
    if not isinstance(default_model, str):
        raise TypeError("Default model route must be a string")
    if default_model not in models:
        raise RuntimeError(f"Default model route is missing: {default_model}")

    env_settings = _load_settings_from_env()

    return Settings(
        providers=providers,
        models=models,
        client_key_hashes=client_key_hashes,
        default_model=default_model,
        **env_settings,
    )


def _validate_origin(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value or len(value) > MAX_URL_LENGTH:
        raise ValueError(f"{label} is invalid")
    if any(character in value for character in FORBIDDEN_CONTROL_CHARS):
        raise ValueError(f"{label} is invalid")
    parsed = urlsplit(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError(f"{label} must be an HTTP(S) URL")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError(f"{label} must not contain credentials, query, or fragment")
    try:
        _port = parsed.port
    except ValueError as exc:
        raise ValueError(f"{label} has an invalid port") from exc


def _require_integer(value: Any, label: str, *, minimum: int, maximum: int) -> None:
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")


def _require_number(value: Any, label: str, *, minimum: float, maximum: float) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not minimum <= value <= maximum:
        raise ValueError(f"{label} must be between {minimum} and {maximum}")


def _env_int(name: str, default: int, *, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    try:
        value = int(default if raw is None else raw)
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"{name} must be an integer") from exc
    if value < minimum:
        raise RuntimeError(f"{name} must be at least {minimum}")
    if value > maximum:
        raise RuntimeError(f"{name} must be at most {maximum}")
    return value


__all__ = [
    "ModelRoute",
    "ProviderConfig",
    "RouteTarget",
    "Settings",
    "load_settings",
]
