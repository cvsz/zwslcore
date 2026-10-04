from __future__ import annotations

import dataclasses
import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .models import EngineeringTask
from .store import SQLiteEngineeringStore


_SECRET_PATTERNS = (
    re.compile(r"(?i)(api[_-]?key|token|secret|password)\s*[=:]\s*[^\s,;]+"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{16,}\b"),
    re.compile(r"\bzw-[A-Za-z0-9_-]{16,}\b"),
)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _stable_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")


def _redact_text(value: str, limit: int = 1000) -> str:
    text = value[:limit]
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


class EvidenceExporter:
    """Write deterministic, secret-minimized engineering evidence bundles."""

    SCHEMA = 1

    def __init__(
        self,
        store: SQLiteEngineeringStore,
        root: str | Path | None = None,
    ) -> None:
        self.store = store
        self.root = Path(root or Path.home() / ".zwslcore" / "evidence")
        self.root.mkdir(parents=True, exist_ok=True)

    def export(self, task: EngineeringTask) -> tuple[Path, str]:
        bundle = self._bundle(task)
        encoded = json.dumps(bundle, indent=2, sort_keys=True, default=str).encode("utf-8") + b"\n"
        digest = _sha256_bytes(encoded)

        target_dir = self.root / task.id
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / "evidence.json"
        checksum = target_dir / "evidence.sha256"
        self._atomic_write(target, encoded)
        self._atomic_write(checksum, f"{digest}  evidence.json\n".encode("utf-8"))
        return target, digest

    def read(self, task_id: str) -> dict[str, Any] | None:
        path = self.root / task_id / "evidence.json"
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    def verify(self, task_id: str) -> bool:
        target_dir = self.root / task_id
        path = target_dir / "evidence.json"
        checksum = target_dir / "evidence.sha256"
        if not path.exists() or not checksum.exists():
            return False
        expected = checksum.read_text(encoding="utf-8").split()[0]
        return _sha256_bytes(path.read_bytes()) == expected

    def _bundle(self, task: EngineeringTask) -> dict[str, Any]:
        checkpoints = self.store.list_checkpoints(task.id)
        return {
            "schema": self.SCHEMA,
            "generated_at": time.time(),
            "task": self._task_summary(task),
            "git": self._git_evidence(task),
            "checkpoints": [self._checkpoint_summary(cp) for cp in checkpoints],
        }

    @staticmethod
    def _task_summary(task: EngineeringTask) -> dict[str, Any]:
        return {
            "id": task.id,
            "title": task.title,
            "description_sha256": _sha256_bytes(task.description.encode("utf-8")),
            "repository": str(Path(task.repository).resolve()),
            "risk": task.risk.value,
            "status": task.status.value,
            "push_policy": task.push_policy.value,
            "worktree_path": task.worktree_path,
            "branch_name": task.branch_name,
            "attempts": task.attempts,
            "max_attempts": task.max_attempts,
            "last_error": _redact_text(task.last_error),
            "created_at": task.created_at,
            "updated_at": task.updated_at,
            "metadata_sha256": _sha256_bytes(_stable_json(task.metadata)),
        }

    @staticmethod
    def _checkpoint_summary(checkpoint: Any) -> dict[str, Any]:
        payload = checkpoint.payload
        summary: dict[str, Any] = {
            "id": checkpoint.id,
            "phase": checkpoint.phase,
            "created_at": checkpoint.created_at,
            "payload_sha256": _sha256_bytes(_stable_json(payload)),
        }

        if checkpoint.phase == "VALIDATION":
            summary["passed"] = bool(payload.get("passed"))
            summary["failures"] = list(payload.get("failures") or [])
            summary["results"] = [
                {
                    "command": item.get("command", ""),
                    "returncode": item.get("returncode"),
                    "stdout_sha256": _sha256_bytes(str(item.get("stdout", "")).encode("utf-8")),
                    "stderr_sha256": _sha256_bytes(str(item.get("stderr", "")).encode("utf-8")),
                }
                for item in payload.get("results", [])
                if isinstance(item, dict)
            ]
        elif checkpoint.phase == "REVIEW":
            summary["findings"] = [
                {
                    "severity": finding.get("severity", ""),
                    "category": finding.get("category", ""),
                    "path": finding.get("path", ""),
                    "blocking": bool(finding.get("blocking", True)),
                }
                for finding in payload.get("findings", [])
                if isinstance(finding, dict)
            ]
        elif checkpoint.phase == "FAILED":
            summary["error"] = _redact_text(str(payload.get("error", "")))
        elif checkpoint.phase == "BASELINE":
            summary["branch"] = str(payload.get("branch", ""))
        elif checkpoint.phase == "COMMIT":
            summary["branch"] = str(payload.get("branch", ""))

        return summary

    @staticmethod
    def _git_evidence(task: EngineeringTask) -> dict[str, Any]:
        root = Path(task.worktree_path) if task.worktree_path else Path(task.repository)
        if not root.exists():
            return {"available": False, "reason": "repository path not available"}

        def run(args: list[str]) -> str:
            try:
                proc = subprocess.run(
                    ["git", "-C", str(root), *args],
                    check=True,
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
            except (OSError, subprocess.CalledProcessError, subprocess.TimeoutExpired):
                return ""
            return proc.stdout

        head = run(["rev-parse", "HEAD"]).strip()
        branch = run(["branch", "--show-current"]).strip()
        status = run(["status", "--porcelain=v1"])
        diff = run(["diff", "--no-ext-diff", "--binary"])
        names = sorted(
            {
                line.strip()
                for line in run(["diff", "--name-only"]).splitlines()
                if line.strip()
            }
        )
        return {
            "available": bool(head),
            "head": head,
            "branch": branch,
            "changed_paths": names,
            "status_sha256": _sha256_bytes(status.encode("utf-8")),
            "diff_sha256": _sha256_bytes(diff.encode("utf-8")),
            "diff_bytes": len(diff.encode("utf-8")),
        }

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        fd, raw = tempfile.mkstemp(prefix=f".{path.name}-", dir=path.parent)
        tmp = Path(raw)
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, path)
        finally:
            tmp.unlink(missing_ok=True)
