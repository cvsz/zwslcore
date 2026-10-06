from __future__ import annotations

import dataclasses
import json
import sqlite3
import time
from contextlib import contextmanager
from pathlib import Path
from collections.abc import Iterator

from .models import Checkpoint, EngineeringTask, PushPolicy, TaskRisk, TaskStatus


class SQLiteEngineeringStore:
    """Crash-consistent local task/checkpoint store using SQLite WAL."""

    SCHEMA_VERSION = 1

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".zwslcore" / "state" / "engineering.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    @contextmanager
    def _connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def _init_schema(self) -> None:
        with self._connect() as conn:
            version = int(conn.execute("PRAGMA user_version").fetchone()[0])
            if version > self.SCHEMA_VERSION:
                raise RuntimeError(
                    f"engineering database schema {version} is newer than supported "
                    f"schema {self.SCHEMA_VERSION}"
                )
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    repository TEXT NOT NULL,
                    risk TEXT NOT NULL,
                    status TEXT NOT NULL,
                    push_policy TEXT NOT NULL,
                    worktree_path TEXT NOT NULL,
                    branch_name TEXT NOT NULL,
                    attempts INTEGER NOT NULL,
                    max_attempts INTEGER NOT NULL,
                    last_error TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    updated_at REAL NOT NULL,
                    metadata_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS checkpoints (
                    id TEXT PRIMARY KEY,
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    phase TEXT NOT NULL,
                    created_at REAL NOT NULL,
                    payload_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_tasks_status_updated
                    ON tasks(status, updated_at);
                CREATE INDEX IF NOT EXISTS idx_checkpoints_task_created
                    ON checkpoints(task_id, created_at);
                CREATE TABLE IF NOT EXISTS runner_leases (
                    lease_name TEXT PRIMARY KEY,
                    owner_id TEXT NOT NULL,
                    fencing_token INTEGER NOT NULL,
                    acquired_at REAL NOT NULL,
                    heartbeat_at REAL NOT NULL,
                    expires_at REAL NOT NULL,
                    status TEXT NOT NULL,
                    previous_owner_id TEXT NOT NULL DEFAULT '',
                    reclaimed_at REAL,
                    released_at REAL
                );
                """
            )
            if version < self.SCHEMA_VERSION:
                conn.execute(f"PRAGMA user_version = {self.SCHEMA_VERSION}")

    def claim_runner_lease(
        self,
        lease_name: str,
        owner_id: str,
        *,
        now: float,
        expires_at: float,
    ) -> dict[str, object]:
        """Persist a new lease generation after the caller owns its process lock."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            previous = conn.execute(
                "SELECT * FROM runner_leases WHERE lease_name = ?",
                (lease_name,),
            ).fetchone()
            fencing_token = int(previous["fencing_token"]) + 1 if previous else 1
            previous_owner = (
                str(previous["owner_id"])
                if previous and previous["status"] == "HELD"
                else ""
            )
            reclaimed_at = now if previous_owner else None
            conn.execute(
                """
                INSERT INTO runner_leases (
                    lease_name, owner_id, fencing_token, acquired_at, heartbeat_at,
                    expires_at, status, previous_owner_id, reclaimed_at, released_at
                ) VALUES (?, ?, ?, ?, ?, ?, 'HELD', ?, ?, NULL)
                ON CONFLICT(lease_name) DO UPDATE SET
                    owner_id=excluded.owner_id,
                    fencing_token=excluded.fencing_token,
                    acquired_at=excluded.acquired_at,
                    heartbeat_at=excluded.heartbeat_at,
                    expires_at=excluded.expires_at,
                    status='HELD',
                    previous_owner_id=excluded.previous_owner_id,
                    reclaimed_at=excluded.reclaimed_at,
                    released_at=NULL
                """,
                (
                    lease_name,
                    owner_id,
                    fencing_token,
                    now,
                    now,
                    expires_at,
                    previous_owner,
                    reclaimed_at,
                ),
            )
            conn.commit()
        return self.get_runner_lease(lease_name) or {}

    def heartbeat_runner_lease(
        self,
        lease_name: str,
        owner_id: str,
        fencing_token: int,
        *,
        now: float,
        expires_at: float,
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runner_leases
                SET heartbeat_at = ?, expires_at = ?
                WHERE lease_name = ? AND owner_id = ? AND fencing_token = ?
                    AND status = 'HELD' AND released_at IS NULL
                """,
                (now, expires_at, lease_name, owner_id, fencing_token),
            )
            return cursor.rowcount == 1

    def release_runner_lease(
        self,
        lease_name: str,
        owner_id: str,
        fencing_token: int,
        *,
        now: float,
    ) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                """
                UPDATE runner_leases
                SET heartbeat_at = ?, expires_at = ?, status = 'RELEASED', released_at = ?
                WHERE lease_name = ? AND owner_id = ? AND fencing_token = ?
                    AND status = 'HELD' AND released_at IS NULL
                """,
                (now, now, now, lease_name, owner_id, fencing_token),
            )
            return cursor.rowcount == 1

    def get_runner_lease(self, lease_name: str) -> dict[str, object] | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM runner_leases WHERE lease_name = ?",
                (lease_name,),
            ).fetchone()
        return dict(row) if row else None

    def save_task(self, task: EngineeringTask) -> None:
        task.updated_at = time.time()
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    title=excluded.title,
                    description=excluded.description,
                    repository=excluded.repository,
                    risk=excluded.risk,
                    status=excluded.status,
                    push_policy=excluded.push_policy,
                    worktree_path=excluded.worktree_path,
                    branch_name=excluded.branch_name,
                    attempts=excluded.attempts,
                    max_attempts=excluded.max_attempts,
                    last_error=excluded.last_error,
                    updated_at=excluded.updated_at,
                    metadata_json=excluded.metadata_json
                """,
                (
                    task.id,
                    task.title,
                    task.description,
                    task.repository,
                    task.risk.value,
                    task.status.value,
                    task.push_policy.value,
                    task.worktree_path,
                    task.branch_name,
                    task.attempts,
                    task.max_attempts,
                    task.last_error,
                    task.created_at,
                    task.updated_at,
                    json.dumps(task.metadata, sort_keys=True),
                ),
            )

    def get_task(self, task_id: str) -> EngineeringTask | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        return self._row_to_task(row) if row else None

    def list_tasks(self, status: TaskStatus | None = None) -> list[EngineeringTask]:
        with self._connect() as conn:
            if status is None:
                rows = conn.execute("SELECT * FROM tasks ORDER BY updated_at DESC").fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM tasks WHERE status = ? ORDER BY updated_at DESC",
                    (status.value,),
                ).fetchall()
        return [self._row_to_task(row) for row in rows]

    def save_checkpoint(self, checkpoint: Checkpoint) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO checkpoints
                (id, task_id, phase, created_at, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    checkpoint.id,
                    checkpoint.task_id,
                    checkpoint.phase,
                    checkpoint.created_at,
                    json.dumps(checkpoint.payload, sort_keys=True),
                ),
            )

    def list_checkpoints(self, task_id: str) -> list[Checkpoint]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM checkpoints
                WHERE task_id = ?
                ORDER BY created_at ASC, id ASC
                """,
                (task_id,),
            ).fetchall()
        return [
            Checkpoint(
                id=row["id"],
                task_id=row["task_id"],
                phase=row["phase"],
                created_at=row["created_at"],
                payload=json.loads(row["payload_json"]),
            )
            for row in rows
        ]

    def latest_checkpoint(self, task_id: str, phase: str | None = None) -> Checkpoint | None:
        with self._connect() as conn:
            if phase is None:
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE task_id = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (task_id,),
                ).fetchone()
            else:
                row = conn.execute(
                    """
                    SELECT * FROM checkpoints
                    WHERE task_id = ? AND phase = ?
                    ORDER BY created_at DESC LIMIT 1
                    """,
                    (task_id, phase),
                ).fetchone()
        if not row:
            return None
        return Checkpoint(
            id=row["id"],
            task_id=row["task_id"],
            phase=row["phase"],
            created_at=row["created_at"],
            payload=json.loads(row["payload_json"]),
        )

    @staticmethod
    def _row_to_task(row: sqlite3.Row) -> EngineeringTask:
        return EngineeringTask(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            repository=row["repository"],
            risk=TaskRisk(row["risk"]),
            status=TaskStatus(row["status"]),
            push_policy=PushPolicy(row["push_policy"]),
            worktree_path=row["worktree_path"],
            branch_name=row["branch_name"],
            attempts=row["attempts"],
            max_attempts=row["max_attempts"],
            last_error=row["last_error"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
            metadata=json.loads(row["metadata_json"]),
        )
