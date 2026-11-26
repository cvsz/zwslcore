from __future__ import annotations

import hashlib
import json
import logging
import math
import re
from dataclasses import dataclass
from datetime import UTC, datetime

# Uvicorn configures this logger at INFO for both CLI and programmatic startup.
# Using its message channel avoids silently dropping audit records at root's
# default WARNING level.
_LOGGER = logging.getLogger("uvicorn.error")
_KNOWN_PATHS = frozenset(
    {
        "/health/live",
        "/health/ready",
        "/metrics",
        "/v1/chat/completions",
        "/v1/messages",
        "/v1/models",
        "/v1/models/refresh",
        "/v1/responses",
    }
)
_KNOWN_METHODS = frozenset({"DELETE", "GET", "HEAD", "OPTIONS", "PATCH", "POST", "PUT"})
_CLIENT_BUCKET = re.compile(r"^[a-f0-9]{64}$")

# HTTP status code constants
_HTTP_SUCCESS_THRESHOLD = 400
_HTTP_AUTHENTICATION_CODES = {401, 403}
_HTTP_RATE_LIMIT_CODE = 429
_HTTP_SERVER_ERROR_THRESHOLD = 500


@dataclass(slots=True)
class AuditEvent:
    request_id: str
    method: str
    path: str
    status_code: int
    duration_ms: float
    client_id: str
    rate_limited: bool


def audit_path(path: str) -> str:
    """Return only a public route name, never an arbitrary user-supplied path."""
    return path if path in _KNOWN_PATHS else "unmatched"


def audit_method(method: str) -> str:
    normalized = method.upper()
    return normalized if normalized in _KNOWN_METHODS else "OTHER"


def audit_error_class(status_code: int) -> str | None:
    if status_code < _HTTP_SUCCESS_THRESHOLD:
        return None
    if status_code in _HTTP_AUTHENTICATION_CODES:
        return "authentication"
    if status_code == _HTTP_RATE_LIMIT_CODE:
        return "rate_limited"
    if status_code >= _HTTP_SERVER_ERROR_THRESHOLD:
        return "http_server_error"
    return "http_client_error"


def emit_request_audit(
    event: AuditEvent | None = None,
    *,
    request_id: str = "",
    method: str = "",
    path: str = "",
    status_code: int = 0,
    duration_ms: float = 0.0,
    client_id: str = "",
    rate_limited: bool = False,
) -> None:
    """Emit a JSON event made exclusively from explicitly allowed metadata."""
    if event is not None:
        request_id = event.request_id
        method = event.method
        path = event.path
        status_code = event.status_code
        duration_ms = event.duration_ms
        client_id = event.client_id
        rate_limited = event.rate_limited
    duration = duration_ms if math.isfinite(duration_ms) and duration_ms >= 0 else 0.0
    outcome = "success" if status_code < _HTTP_SUCCESS_THRESHOLD else "error"
    audit_event = {
        "schema_version": 1,
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "http_request",
        "component": "provider",
        "request_id": hashlib.sha256(request_id.encode()).hexdigest(),
        "task_id": None,
        "work_fingerprint": None,
        "phase": "request",
        "provider": "gateway",
        "model": None,
        "attempt": None,
        "outcome": outcome,
        "error_class": audit_error_class(status_code),
        "method": audit_method(method),
        "path": audit_path(path),
        "status_code": status_code,
        "latency_ms": round(duration, 3),
        "duration_ms": round(duration, 3),
        "client_id": client_id if _CLIENT_BUCKET.fullmatch(client_id) else "unknown",
        "rate_limited": rate_limited,
    }
    _LOGGER.info(json.dumps(audit_event, separators=(",", ":"), sort_keys=True))


__all__ = [
    "AuditEvent",
    "audit_error_class",
    "audit_method",
    "audit_path",
    "emit_request_audit",
]
