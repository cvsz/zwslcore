from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any

from .loop import WorkItem, WorkKind


class ContinuousLedgerError(RuntimeError):
    pass


class JsonContinuousLedger:
    SCHEMA = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".zwslcore" / "state" / "continuous.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": self.SCHEMA, "records": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContinuousLedgerError(f"unable to read continuous ledger: {exc}") from exc
        if value.get("schema") != self.SCHEMA or not isinstance(value.get("records"), dict):
            raise ContinuousLedgerError("invalid continuous ledger structure")
        return value

    def _write(self, value: dict[str, Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, raw_path = tempfile.mkstemp(prefix=".continuous-", suffix=".json", dir=self.path.parent)
        tmp = Path(raw_path)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                json.dump(value, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(tmp, self.path)
        finally:
            tmp.unlink(missing_ok=True)

    def register(self, item: WorkItem) -> dict[str, Any]:
        data = self._read()
        record = data["records"].get(item.fingerprint)
        if record is None:
            record = {
                "fingerprint": item.fingerprint,
                "title": item.title,
                "kind": item.kind.value,
                "payload": item.payload,
                "priority": item.priority,
                "max_attempts": item.max_attempts,
                "state": "PENDING",
                "attempts": 0,
                "last_error": "",
                "task_id": "",
                "updated_at": time.time(),
            }
            data["records"][item.fingerprint] = record
            self._write(data)
        return dict(record)

    def update(self, fingerprint: str, **changes: Any) -> dict[str, Any]:
        data = self._read()
        try:
            record = data["records"][fingerprint]
        except KeyError as exc:
            raise ContinuousLedgerError(f"unknown work item: {fingerprint}") from exc
        record.update(changes)
        record["updated_at"] = time.time()
        self._write(data)
        return dict(record)

    def pending(self, *, retry_blocked: bool = False) -> list[WorkItem]:
        data = self._read()
        items: list[WorkItem] = []
        for record in data["records"].values():
            state = record.get("state")
            if state == "SUCCEEDED":
                continue
            if state == "BLOCKED" and not retry_blocked:
                continue
            items.append(
                WorkItem(
                    title=record["title"],
                    kind=WorkKind(record["kind"]),
                    payload=dict(record.get("payload", {})),
                    priority=int(record.get("priority", 50)),
                    max_attempts=int(record.get("max_attempts", 2)),
                )
            )
        return items

    def records(self) -> list[dict[str, Any]]:
        data = self._read()
        return sorted(
            (dict(record) for record in data["records"].values()),
            key=lambda record: (-int(record.get("priority", 50)), record["fingerprint"]),
        )
