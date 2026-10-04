from __future__ import annotations

import dataclasses
import json
import sqlite3
import time
from pathlib import Path

from .models import Checkpoint, EngineeringTask, PushPolicy, TaskRisk, TaskStatus


class SQLiteEngineeringStore:
    """Crash-consistent local task/checkpoint store using SQLite WAL."""

    def __init__(self, path: str | Path | None = None) -> None:
        self.path = Path(path or Path.home() / ".zwslcore" / "state" / "engineering.db")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path, timeout=30)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=30000")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
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
                """
            )

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

    def latest_checkpoint(self, task_id: str) -> Checkpoint | None:
        with self._connect() as conn:
            row = conn.execute(
                """
                SELECT * FROM checkpoints
                WHERE task_id = ?
                ORDER BY created_at DESC LIMIT 1
                """,
                (task_id,),
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
