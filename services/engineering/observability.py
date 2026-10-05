from __future__ import annotations

import hashlib
import json
import logging
import math
import re
import sys
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import TextIO

_LOGGER = logging.getLogger("zeaz.engineering")
_SAFE_ID = re.compile(r"^(?:task|work)_[a-f0-9]{20}$")
_SAFE_REQUEST_ID = re.compile(r"^[a-f0-9]{32}$")
_SAFE_LABEL = re.compile(r"^[A-Za-z0-9_.:/-]{1,96}$")
_SAFE_FINGERPRINT = re.compile(r"^[a-f0-9]{64}$")
_SENSITIVE_LABEL = re.compile(
    r"(?i)(?:api[_-]?key|(?:^|[_-])token(?:[_-]|$)|secret|password|bearer|"
    r"(?:sk|zw)-[A-Za-z0-9_-]{16,}|AIza[A-Za-z0-9_-]{20,}|AKIA[0-9A-Z]{16})"
)
_PHASES = frozenset(
    {"preflight", "baseline", "planning", "editing", "validating", "reviewing", "evidence"}
)
_OUTCOMES = frozenset({"started", "success", "failure", "blocked", "failed", "read_only"})
_ERROR_CLASSES = frozenset(
    {
        "AssertionError",
        "ContinuousLedgerError",
        "EvidenceWriteError",
        "FileNotFoundError",
        "KeyError",
        "OSError",
        "PermissionError",
        "MCPError",
        "ProviderTransportError",
        "RunnerLeaseError",
        "RunnerLeaseHeldError",
        "RunnerLeaseLostError",
        "RuntimeError",
        "SnapshotError",
        "TimeoutError",
        "ValueError",
    }
)


@contextmanager
def engineering_logging(stream: TextIO | None = None) -> Iterator[None]:
    """Temporarily enable one-line JSON events without changing root logging."""
    previous_level = _LOGGER.level
    previous_propagate = _LOGGER.propagate
    handler: logging.Handler | None = None
    _LOGGER.setLevel(logging.INFO)
    _LOGGER.propagate = False
    if not _LOGGER.handlers:
        handler = logging.StreamHandler(stream if stream is not None else sys.stderr)
        handler.setFormatter(logging.Formatter("%(message)s"))
        _LOGGER.addHandler(handler)
    try:
        yield
    finally:
        if handler is not None:
            _LOGGER.removeHandler(handler)
            handler.close()
        _LOGGER.setLevel(previous_level)
        _LOGGER.propagate = previous_propagate


def task_work_fingerprint(title: str, description: str) -> str:
    """Return a stable correlation hash without retaining user task text in logs."""
    return hashlib.sha256(f"{title}\0{description}".encode("utf-8")).hexdigest()


def valid_request_id(value: str | None) -> str | None:
    return value if isinstance(value, str) and _SAFE_REQUEST_ID.fullmatch(value) else None


def _safe_label(value: str) -> str:
    return value if _SAFE_LABEL.fullmatch(value) and not _SENSITIVE_LABEL.search(value) else "unknown"


def safe_error_class(error: BaseException) -> str:
    name = type(error).__name__
    return name if name in _ERROR_CLASSES else "Other"


def safe_error_summary(error: BaseException) -> str:
    """Return a fixed safe operator hint for known failures, without messages."""
    name = type(error).__name__
    if name == "RunnerLeaseHeldError":
        return "continuous runner lease is held by another process"
    if name == "RunnerLeaseLostError":
        return "continuous runner lease ownership was lost"
    return f"error_class={safe_error_class(error)}"


def emit_engineering_event(
    *,
    request_id: str,
    task_id: str,
    work_fingerprint: str,
    phase: str,
    provider: str,
    model: str,
    attempt: int,
    latency_ms: float,
    outcome: str,
    error_class: str | None = None,
) -> None:
    """Emit JSON containing bounded correlation and lifecycle metadata only."""
    safe_task_id = task_id if _SAFE_ID.fullmatch(task_id) else (
        f"task_{hashlib.sha256(task_id.encode()).hexdigest()[:20]}"
    )
    safe_fingerprint = (
        work_fingerprint if _SAFE_FINGERPRINT.fullmatch(work_fingerprint)
        else hashlib.sha256(work_fingerprint.encode()).hexdigest()
    )
    safe_request_id = (
        hashlib.sha256(request_id.encode()).hexdigest()
        if valid_request_id(request_id)
        else "unknown"
    )
    safe_provider = _safe_label(provider)
    safe_model = _safe_label(model)
    safe_phase = phase if phase in _PHASES else "other"
    safe_outcome = outcome if outcome in _OUTCOMES else "other"
    safe_error = error_class if error_class in _ERROR_CLASSES else None
    duration = latency_ms if math.isfinite(latency_ms) and latency_ms >= 0 else 0.0
    event = {
        "schema_version": 1,
        "timestamp": datetime.now(UTC).isoformat(),
        "event": "engineering_phase",
        "component": "engineering",
        "request_id": safe_request_id,
        "task_id": safe_task_id,
        "work_fingerprint": safe_fingerprint,
        "phase": safe_phase,
        "provider": safe_provider,
        "model": safe_model,
        "attempt": max(0, attempt) if type(attempt) is int else 0,
        "latency_ms": round(duration, 3),
        "outcome": safe_outcome,
        "error_class": safe_error,
    }
    _LOGGER.info(json.dumps(event, separators=(",", ":"), sort_keys=True))
