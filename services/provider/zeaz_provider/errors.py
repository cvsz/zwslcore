from __future__ import annotations

import math
from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class ErrorKind(StrEnum):
    AUTHENTICATION = "authentication"
    BAD_REQUEST = "bad_request"
    NOT_FOUND = "not_found"
    RATE_LIMIT = "rate_limit"
    TIMEOUT = "timeout"
    NETWORK = "network"
    UPSTREAM = "upstream"
    PROTOCOL = "protocol"
    CIRCUIT_OPEN = "circuit_open"
    CONFIGURATION = "configuration"


@dataclass(slots=True)
class ProviderErrorConfig:
    status_code: int = 502
    retryable: bool = False
    kind: ErrorKind = ErrorKind.UPSTREAM
    fallback_allowed: bool | None = None
    circuit_failure: bool | None = None
    retry_after: float | None = None
    details: dict[str, Any] | None = None


class ProviderError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        config: ProviderErrorConfig | None = None,
    ):
        cfg = config or ProviderErrorConfig()
        super().__init__(message)
        self.status_code = cfg.status_code
        self.retryable = cfg.retryable
        self.kind = cfg.kind
        self.fallback_allowed = cfg.retryable if cfg.fallback_allowed is None else cfg.fallback_allowed
        self.circuit_failure = cfg.retryable if cfg.circuit_failure is None else cfg.circuit_failure
        self.retry_after = cfg.retry_after
        self.details = cfg.details or {}


def _safe_retry_after(value: float | None) -> float | None:
    return (
        value
        if isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
        and value >= 0
        else None
    )


# HTTP status code constants
_HTTP_AUTH_CODES = {401, 403}
_HTTP_NOT_FOUND = 404
_HTTP_RATE_LIMIT = 429
_HTTP_TEMPORARY_CODES = {408, 409, 425}
_HTTP_SERVER_ERROR_THRESHOLD = 500


def classify_http_error(
    status_code: int,
    message: str,
    *,
    retry_after: float | None = None,
) -> ProviderError:
    safe_retry_after = _safe_retry_after(retry_after)
    if status_code in _HTTP_AUTH_CODES:
        return ProviderError(
            "Provider authentication failed",
            config=ProviderErrorConfig(
                status_code=status_code,
                kind=ErrorKind.AUTHENTICATION,
                fallback_allowed=False,
                circuit_failure=False,
            ),
        )
    if status_code == _HTTP_NOT_FOUND:
        return ProviderError(
            "Provider model or endpoint was not found",
            config=ProviderErrorConfig(
                status_code=status_code,
                kind=ErrorKind.NOT_FOUND,
                fallback_allowed=True,
                circuit_failure=False,
            ),
        )
    if status_code == _HTTP_RATE_LIMIT:
        return ProviderError(
            "Provider rate limit exceeded",
            config=ProviderErrorConfig(
                status_code=status_code,
                retryable=True,
                kind=ErrorKind.RATE_LIMIT,
                fallback_allowed=True,
                circuit_failure=True,
                retry_after=safe_retry_after,
            ),
        )
    if status_code in _HTTP_TEMPORARY_CODES:
        return ProviderError(
            "Provider request was rejected temporarily",
            config=ProviderErrorConfig(
                status_code=status_code,
                retryable=True,
                kind=ErrorKind.UPSTREAM,
                fallback_allowed=True,
                circuit_failure=True,
            ),
        )
    if status_code >= _HTTP_SERVER_ERROR_THRESHOLD:
        return ProviderError(
            "Provider service failure",
            config=ProviderErrorConfig(
                status_code=status_code,
                retryable=True,
                kind=ErrorKind.UPSTREAM,
                fallback_allowed=True,
                circuit_failure=True,
            ),
        )
    return ProviderError(
        "Provider rejected the request",
        config=ProviderErrorConfig(
            status_code=status_code,
            kind=ErrorKind.BAD_REQUEST,
            fallback_allowed=False,
            circuit_failure=False,
        ),
    )


__all__ = [
    "ErrorKind",
    "ProviderError",
    "classify_http_error",
]
