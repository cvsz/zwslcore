from __future__ import annotations

import fcntl
import json
import os
import tempfile
import time
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator
from typing import Any

from .evidence import redact_sensitive_text
from .loop import WorkItem, WorkKind


class ContinuousLedgerError(RuntimeError):
    pass


class JsonContinuousLedger:
    SCHEMA = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".zwslcore" / "state" / "continuous.json")
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def _exclusive(self) -> Iterator[None]:
        lock_path = self.path.with_name(f"{self.path.name}.write.lock")
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(fd, 0o600)
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)

    def _read(self) -> dict[str, Any]:
        if not self.path.exists():
            return {"schema": self.SCHEMA, "records": {}, "archives": {}}
        try:
            value = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ContinuousLedgerError(f"unable to read continuous ledger: {exc}") from exc
        if (
            not isinstance(value, dict)
            or type(value.get("schema")) is not int
            or value.get("schema") != self.SCHEMA
            or not isinstance(value.get("records"), dict)
        ):
            raise ContinuousLedgerError("invalid continuous ledger structure")
        if "archives" not in value:
            value["archives"] = {}
        if not isinstance(value["archives"], dict):
            raise ContinuousLedgerError("invalid continuous ledger archive structure")
        return value

    def snapshot_bytes(self) -> bytes:
        """Return a validated, consistent ledger snapshot under its writer lock."""
        with self._exclusive():
            self._read()
            if not self.path.exists():
                raise ContinuousLedgerError("continuous ledger does not exist")
            return self.path.read_bytes()

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

    def register(
        self,
        item: WorkItem,
        *,
        initial_fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._exclusive():
            data = self._read()
            record = data["records"].get(item.fingerprint)
            if record is None:
                archived = data["archives"].get(item.fingerprint)
                if archived is not None:
                    return dict(archived)
                now = time.time()
                record = {
                    "fingerprint": item.fingerprint,
                    "title": item.title,
                    "kind": item.kind.value,
                    "payload": item.payload,
                    "priority": item.priority,
                    "max_attempts": item.max_attempts,
                    "state": "PENDING",
                    "attempts": 0,
                    "attempt_history": [],
                    "retry_history": [],
                    "requeue_history": [],
                    "model_history": [],
                    "last_error": "",
                    "task_id": "",
                    "created_at": now,
                    "updated_at": now,
                }
                data["records"][item.fingerprint] = record
            if initial_fields:
                state = str(record.get("state", "PENDING"))
                if state in {"RUNNING", "SUCCEEDED", "CANCELLED", "QUARANTINED", "DEAD_LETTER"}:
                    raise ContinuousLedgerError(f"cannot relink work item in state {state}")
                requested_task = str(initial_fields.get("task_id") or "")
                existing_task = str(record.get("task_id") or "")
                if existing_task and requested_task and existing_task != requested_task:
                    raise ContinuousLedgerError("work item is already linked to a different task")
                initial_fields = dict(initial_fields)
                if "last_error" in initial_fields:
                    initial_fields["last_error"] = redact_sensitive_text(
                        str(initial_fields["last_error"]), 2000
                    )
                record.update(initial_fields)
                record["updated_at"] = time.time()
            self._write(data)
            return dict(record)

    def update(self, fingerprint: str, **changes: Any) -> dict[str, Any]:
        with self._exclusive():
            data = self._read()
            try:
                record = data["records"][fingerprint]
            except KeyError as exc:
                raise ContinuousLedgerError(f"unknown work item: {fingerprint}") from exc
            changes = dict(changes)
            if "last_error" in changes:
                changes["last_error"] = redact_sensitive_text(str(changes["last_error"]), 2000)
            record.update(changes)
            record["updated_at"] = time.time()
            self._write(data)
            return dict(record)

    def record_attempt(
        self,
        fingerprint: str,
        *,
        attempts: int,
        status: str,
        error: str = "",
        task_id: str = "",
        model: str = "",
        evidence_path: str = "",
    ) -> dict[str, Any]:
        with self._exclusive():
            data = self._read()
            try:
                record = data["records"][fingerprint]
            except KeyError as exc:
                raise ContinuousLedgerError(f"unknown work item: {fingerprint}") from exc
            now = time.time()
            history = list(record.get("attempt_history") or [])
            history.append({
                "attempt": int(attempts),
                "at": now,
                "status": status,
                "error": redact_sensitive_text(error, 1000),
                "task_id": task_id,
                "model": model,
                "evidence_path": evidence_path,
            })
            models = list(record.get("model_history") or [])
            if model:
                models.append({"at": now, "attempt": int(attempts), "model": model})
            record.update({
                "attempts": int(attempts),
                "attempt_history": history,
                "model_history": models,
                "last_error": redact_sensitive_text(error, 2000),
                "task_id": task_id or record.get("task_id", ""),
                "updated_at": now,
            })
            self._write(data)
            return dict(record)

    def record_infrastructure_failure(
        self,
        fingerprint: str,
        error: str,
        *,
        state: str | None = None,
    ) -> dict[str, Any]:
        with self._exclusive():
            data = self._read()
            try:
                record = data["records"][fingerprint]
            except KeyError as exc:
                raise ContinuousLedgerError(f"unknown work item: {fingerprint}") from exc
            history = list(record.get("infrastructure_history") or [])
            history.append({"at": time.time(), "error": redact_sensitive_text(error, 1000)})
            record["infrastructure_history"] = history
            record["last_error"] = redact_sensitive_text(error, 2000)
            if state is not None:
                record["state"] = state
            record["updated_at"] = time.time()
            self._write(data)
            return dict(record)

    def get_record(self, fingerprint: str) -> tuple[dict[str, Any], bool] | None:
        data = self._read()
        record = data["records"].get(fingerprint)
        if record is not None:
            return dict(record), False
        archived = data["archives"].get(fingerprint)
        if archived is not None:
            return dict(archived), True
        return None

    def cancel(self, fingerprint: str, reason: str) -> dict[str, Any]:
        return self._transition(fingerprint, "CANCELLED", reason, allowed_from=None)

    def retry(self, fingerprint: str, reason: str = "operator requested retry") -> dict[str, Any]:
        with self._exclusive():
            if not reason.strip():
                raise ContinuousLedgerError("retry reason must not be empty")
            data = self._read()
            record = self._active_record(data, fingerprint)
            state = str(record.get("state", "PENDING"))
            attempts = int(record.get("attempts", 0))
            maximum = int(record.get("max_attempts", 2))
            if state == "RUNNING":
                raise ContinuousLedgerError("cannot retry work while it is running")
            if record.get("retry_requested") and state == "PENDING":
                return dict(record)
            if state not in {"BLOCKED", "FAILED"} and attempts < maximum:
                raise ContinuousLedgerError(
                    f"work item is not blocked or exhausted (state={state}, attempts={attempts}/{maximum})"
                )
            now = time.time()
            history = list(record.get("retry_history") or [])
            history.append({
                "at": now,
                "from_state": state,
                "previous_attempts": attempts,
                "reason": redact_sensitive_text(reason.strip(), 1000),
            })
            record.update({
                "state": "PENDING",
                "attempts": 0,
                "retry_requested": True,
                "retry_history": history,
                "last_error": "",
                "updated_at": now,
            })
            self._write(data)
            return dict(record)

    def requeue(self, fingerprint: str, reason: str) -> dict[str, Any]:
        with self._exclusive():
            if not reason.strip():
                raise ContinuousLedgerError("requeue reason must not be empty")
            data = self._read()
            archived = False
            record = data["records"].get(fingerprint)
            if record is None:
                record = data["archives"].get(fingerprint)
                archived = record is not None
            if record is None:
                raise ContinuousLedgerError(f"unknown work item: {fingerprint}")
            state = str(record.get("state", ""))
            if state not in {"QUARANTINED", "DEAD_LETTER"}:
                raise ContinuousLedgerError(
                    f"only quarantined or dead-letter work can be requeued (state={state})"
                )
            record = dict(record)
            now = time.time()
            history = list(record.get("requeue_history") or [])
            history.append({
                "at": now,
                "from_state": state,
                "previous_attempts": int(record.get("attempts", 0)),
                "reason": redact_sensitive_text(reason.strip(), 1000),
                "was_archived": archived,
            })
            if archived:
                data["archives"].pop(fingerprint, None)
            record.update({
                "state": "PENDING",
                "attempts": 0,
                "retry_requested": True,
                "requeue_history": history,
                "last_error": "",
                "updated_at": now,
            })
            record.pop("archived_at", None)
            record.pop("archive_reason", None)
            if record.get("dead_letter"):
                record["dead_letter"]["requeued_at"] = now
            data["records"][fingerprint] = record
            self._write(data)
            return dict(record)

    def quarantine(self, fingerprint: str, reason: str) -> dict[str, Any]:
        with self._exclusive():
            if not reason.strip():
                raise ContinuousLedgerError("quarantine reason must not be empty")
            data = self._read()
            record = self._active_record(data, fingerprint)
            state = str(record.get("state", "PENDING"))
            if state in {"RUNNING", "SUCCEEDED", "CANCELLED", "DEAD_LETTER"}:
                raise ContinuousLedgerError(f"cannot quarantine work in state {state}")
            now = time.time()
            record["state"] = "QUARANTINED"
            safe_reason = redact_sensitive_text(reason.strip(), 2000)
            record["quarantine"] = {"reason": safe_reason, "quarantined_at": now}
            record["last_error"] = safe_reason
            record["updated_at"] = now
            self._write(data)
            return dict(record)

    def dead_letter(
        self,
        fingerprint: str,
        reason: str,
        *,
        task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        with self._exclusive():
            if not reason.strip():
                raise ContinuousLedgerError("dead-letter reason must not be empty")
            data = self._read()
            record = self._active_record(data, fingerprint)
            state = str(record.get("state", "PENDING"))
            if state in {"RUNNING", "SUCCEEDED", "CANCELLED"}:
                raise ContinuousLedgerError(f"cannot dead-letter work in state {state}")
            now = time.time()
            task = task or {}
            metadata = task.get("metadata") if isinstance(task.get("metadata"), dict) else {}
            model_history = []
            for item in list(record.get("model_history") or []):
                if isinstance(item, dict):
                    entry = dict(item)
                    if "error" in entry:
                        entry["error"] = redact_sensitive_text(str(entry["error"]), 1000)
                    model_history.append(entry)
                else:
                    model_history.append(item)
            for item in list(metadata.get("model_escalation_history") or []):
                if isinstance(item, dict):
                    entry = dict(item)
                    if "error" in entry:
                        entry["error"] = redact_sensitive_text(str(entry["error"]), 1000)
                    model_history.append(entry)
            current_model = str(
                metadata.get("model_working")
                or metadata.get("model_escalated_to")
                or metadata.get("model_selected_for_run")
                or metadata.get("model_current")
                or ""
            )
            if current_model and not any(item.get("model") == current_model for item in model_history if isinstance(item, dict)):
                model_history.append({"at": now, "model": current_model, "source": "last_task_model"})
            attempt_history = []
            for item in list(record.get("attempt_history") or []):
                if isinstance(item, dict):
                    entry = dict(item)
                    if "error" in entry:
                        entry["error"] = redact_sensitive_text(str(entry["error"]), 1000)
                    attempt_history.append(entry)
                else:
                    attempt_history.append(item)
            if not attempt_history and int(record.get("attempts", 0)):
                attempt_history.append({
                    "attempt": int(record["attempts"]),
                    "at": record.get("updated_at", now),
                    "status": state,
                    "error": redact_sensitive_text(str(record.get("last_error") or reason), 1000),
                    "task_id": str(record.get("task_id") or task.get("id") or ""),
                    "model": current_model,
                    "evidence_path": str(metadata.get("evidence_path") or ""),
                    "source": "legacy_summary",
                })
            task_id = str(record.get("task_id") or task.get("id") or "")
            latest_attempt = attempt_history[-1] if attempt_history else {}
            evidence_path = str(
                metadata.get("evidence_path")
                or (latest_attempt.get("evidence_path") if isinstance(latest_attempt, dict) else "")
                or ""
            )
            dead_letter = {
                "fingerprint": fingerprint,
                "task_id": task_id,
                "failure_reason": redact_sensitive_text(reason.strip(), 2000),
                "attempt_history": attempt_history,
                "model_history": model_history,
                "evidence_path": evidence_path,
                "created_at": record.get("created_at", record.get("updated_at", now)),
                "dead_lettered_at": now,
                "updated_at": now,
            }
            record.update({
                "state": "DEAD_LETTER",
                "last_error": redact_sensitive_text(reason.strip(), 2000),
                "model_history": model_history,
                "dead_letter": dead_letter,
                "dead_lettered_at": now,
                "updated_at": now,
            })
            self._write(data)
            return dict(record)

    def archive(self, fingerprint: str, reason: str = "operator archived terminal work") -> dict[str, Any]:
        with self._exclusive():
            if not reason.strip():
                raise ContinuousLedgerError("archive reason must not be empty")
            data = self._read()
            record = self._active_record(data, fingerprint)
            state = str(record.get("state", ""))
            if state not in {"SUCCEEDED", "CANCELLED", "DEAD_LETTER"}:
                raise ContinuousLedgerError(f"only completed, cancelled, or dead-letter work can be archived (state={state})")
            if state == "DEAD_LETTER":
                dead = record.get("dead_letter")
                required = {
                    "fingerprint", "task_id", "failure_reason", "attempt_history",
                    "model_history", "evidence_path", "created_at", "dead_lettered_at",
                }
                if not isinstance(dead, dict) or not required.issubset(dead):
                    raise ContinuousLedgerError("dead-letter evidence is incomplete; refusing to archive")
            now = time.time()
            snapshot = dict(record)
            snapshot.update({"archived_at": now, "archive_reason": redact_sensitive_text(reason.strip(), 1000)})
            data["archives"][fingerprint] = snapshot
            del data["records"][fingerprint]
            self._write(data)
            return snapshot

    def _transition(
        self,
        fingerprint: str,
        target: str,
        reason: str,
        *,
        allowed_from: set[str] | None,
    ) -> dict[str, Any]:
        with self._exclusive():
            if not reason.strip():
                raise ContinuousLedgerError("lifecycle reason must not be empty")
            data = self._read()
            record = self._active_record(data, fingerprint)
            state = str(record.get("state", "PENDING"))
            if state == target:
                return dict(record)
            if state == "RUNNING":
                raise ContinuousLedgerError("cannot change lifecycle state while work is running")
            if target == "CANCELLED" and state == "SUCCEEDED":
                raise ContinuousLedgerError("cannot cancel succeeded work")
            if allowed_from is not None and state not in allowed_from:
                raise ContinuousLedgerError(f"cannot transition work from {state} to {target}")
            now = time.time()
            history = list(record.get("lifecycle_history") or [])
            safe_reason = redact_sensitive_text(reason.strip(), 2000)
            history.append({"at": now, "from_state": state, "to_state": target, "reason": safe_reason})
            record.update({
                "state": target,
                "last_error": safe_reason,
                "lifecycle_history": history,
                "updated_at": now,
            })
            if target == "CANCELLED":
                record["cancelled_at"] = now
                record["cancel_reason"] = safe_reason
            self._write(data)
            return dict(record)

    @staticmethod
    def _active_record(data: dict[str, Any], fingerprint: str) -> dict[str, Any]:
        try:
            return data["records"][fingerprint]
        except KeyError as exc:
            raise ContinuousLedgerError(f"unknown active work item: {fingerprint}") from exc

    def pending(self, *, retry_blocked: bool = False) -> list[WorkItem]:
        with self._exclusive():
            data = self._read()
            changed = False
            items: list[WorkItem] = []
            for record in data["records"].values():
                state = record.get("state")
                if state in {"SUCCEEDED", "CANCELLED", "QUARANTINED", "DEAD_LETTER"}:
                    continue
                max_attempts = int(record.get("max_attempts", 2))
                attempts = int(record.get("attempts", 0))
                exhausted = attempts >= max_attempts

                if retry_blocked and (state == "BLOCKED" or exhausted):
                    record["state"] = "PENDING"
                    record["attempts"] = 0
                    record["retry_requested"] = True
                    record["last_error"] = ""
                    record["updated_at"] = time.time()
                    attempts = 0
                    exhausted = False
                    changed = True

                if state == "BLOCKED" and not retry_blocked:
                    continue
                if exhausted:
                    continue

                items.append(
                    WorkItem(
                        title=record["title"],
                        kind=WorkKind(record["kind"]),
                        payload=dict(record.get("payload", {})),
                        priority=int(record.get("priority", 50)),
                        max_attempts=max(1, max_attempts - attempts),
                    )
                )
            if changed:
                self._write(data)
            return items

    def records(self) -> list[dict[str, Any]]:
        data = self._read()
        return sorted(
            (dict(record) for record in data["records"].values()),
            key=lambda record: (-int(record.get("priority", 50)), record["fingerprint"]),
        )

    def archived_records(self) -> list[dict[str, Any]]:
        data = self._read()
        return sorted(
            (dict(record) for record in data["archives"].values()),
            key=lambda record: (float(record.get("archived_at", 0)), record["fingerprint"]),
        )
