from __future__ import annotations

import fcntl
import os
import socket
import threading
import time
import uuid
from pathlib import Path
from collections.abc import Iterable

from .store import SQLiteEngineeringStore


class RunnerLeaseError(RuntimeError):
    """Base error for continuous-runner lease failures."""


class RunnerLeaseHeldError(RunnerLeaseError):
    """Raised when another process already owns the continuous-runner lease."""


class RunnerLeaseLostError(RunnerLeaseError):
    """Raised when the persisted lease no longer matches this process."""


class SQLiteRunnerLease:
    """Process-exclusive, SQLite-recorded lease for the continuous queue.

    The advisory lock prevents a live but paused process from being replaced just
    because its heartbeat expires. SQLite stores the owner, fencing generation,
    heartbeat, expiry, and crash-reclamation details. The operating system drops
    the advisory lock when the owning process exits, allowing the next runner to
    reclaim an abandoned database lease safely.
    """

    DEFAULT_NAME = "continuous-runner"

    @staticmethod
    def queue_lock_paths(
        store: SQLiteEngineeringStore,
        ledger_path: str | Path,
    ) -> tuple[Path, Path]:
        ledger_path = Path(ledger_path)
        return (
            store.path.with_name(f"{store.path.name}.continuous-runner.lock"),
            ledger_path.with_name(f"{ledger_path.name}.continuous-runner.lock"),
        )

    def __init__(
        self,
        store: SQLiteEngineeringStore,
        *,
        name: str = DEFAULT_NAME,
        ttl_seconds: float = 30.0,
        heartbeat_interval: float | None = None,
        owner_id: str | None = None,
        lock_path: str | Path | None = None,
        lock_paths: Iterable[str | Path] | None = None,
    ) -> None:
        if not name or ttl_seconds <= 0:
            raise ValueError("lease name and positive ttl_seconds are required")
        interval = heartbeat_interval if heartbeat_interval is not None else ttl_seconds / 3
        if interval <= 0 or interval >= ttl_seconds:
            raise ValueError("heartbeat_interval must be positive and shorter than ttl_seconds")
        self.store = store
        self.name = name
        self.ttl_seconds = ttl_seconds
        self.heartbeat_interval = interval
        self.owner_id = owner_id or f"{socket.gethostname()}:{os.getpid()}:{uuid.uuid4().hex}"
        self.fencing_token: int | None = None
        supplied_paths = list(lock_paths or ())
        if lock_path is not None:
            supplied_paths.append(lock_path)
        if not supplied_paths:
            supplied_paths.append(store.path.with_name(f"{store.path.name}.{name}.lock"))
        self._lock_paths = sorted({Path(path).resolve() for path in supplied_paths}, key=str)
        self._lock_fds: list[int] = []
        self._stop = threading.Event()
        self._lost = threading.Event()
        self._heartbeat_thread: threading.Thread | None = None

    def acquire(self) -> SQLiteRunnerLease:
        lock_fds: list[int] = []
        try:
            for lock_path in self._lock_paths:
                lock_path.parent.mkdir(parents=True, exist_ok=True)
                fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
                lock_fds.append(fd)
                os.fchmod(fd, 0o600)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError as exc:
                    current = self.store.get_runner_lease(self.name)
                    if current and current.get("status") == "HELD":
                        detail = (
                            f"owner={current.get('owner_id')} "
                            f"expires_at={current.get('expires_at')}"
                        )
                    else:
                        detail = "owner metadata unavailable"
                    raise RunnerLeaseHeldError(
                        f"continuous runner lease '{self.name}' is held ({detail})"
                    ) from exc

            now = time.time()
            record = self.store.claim_runner_lease(
                self.name,
                self.owner_id,
                now=now,
                expires_at=now + self.ttl_seconds,
            )
            self.fencing_token = int(record["fencing_token"])
            self._lock_fds = lock_fds
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name=f"zwslcore-lease-{self.name}",
                daemon=True,
            )
            self._heartbeat_thread.start()
            return self
        except Exception:
            self._unlock(lock_fds)
            raise

    def __enter__(self) -> SQLiteRunnerLease:
        return self.acquire()

    def __exit__(self, exc_type, exc, traceback) -> None:
        try:
            self.release()
        except Exception as release_error:
            if exc is None:
                raise
            if hasattr(exc, "add_note"):
                exc.add_note(f"runner lease release also failed: {release_error}")

    def heartbeat_once(self) -> bool:
        if self.fencing_token is None:
            raise RunnerLeaseLostError("runner lease was not acquired")
        now = time.time()
        ok = self.store.heartbeat_runner_lease(
            self.name,
            self.owner_id,
            self.fencing_token,
            now=now,
            expires_at=now + self.ttl_seconds,
        )
        if not ok:
            self._lost.set()
        return ok

    def assert_owned(self) -> None:
        if self.fencing_token is None or self._lost.is_set():
            raise RunnerLeaseLostError("continuous runner no longer owns its lease")
        current = self.store.get_runner_lease(self.name)
        if (
            not current
            or current.get("owner_id") != self.owner_id
            or current.get("fencing_token") != self.fencing_token
            or current.get("status") != "HELD"
            or float(current.get("expires_at", 0)) <= time.time()
        ):
            self._lost.set()
            raise RunnerLeaseLostError("continuous runner no longer owns its lease")

    def release(self) -> None:
        self._stop.set()
        thread = self._heartbeat_thread
        if thread and thread is not threading.current_thread():
            thread.join(timeout=max(1.0, self.heartbeat_interval * 2))

        release_error: Exception | None = None
        if self.fencing_token is not None:
            try:
                released = self.store.release_runner_lease(
                    self.name,
                    self.owner_id,
                    self.fencing_token,
                    now=time.time(),
                )
                if not released and not self._lost.is_set():
                    release_error = RunnerLeaseLostError(
                        "continuous runner could not release its persisted lease"
                    )
            except Exception as exc:  # the OS lock must still be released
                release_error = exc

        lock_fds, self._lock_fds = self._lock_fds, []
        self._unlock(lock_fds)

        if release_error:
            raise release_error

    def _heartbeat_loop(self) -> None:
        while not self._stop.wait(self.heartbeat_interval):
            try:
                if not self.heartbeat_once():
                    return
            except Exception:
                self._lost.set()
                return

    @staticmethod
    def _unlock(lock_fds: list[int]) -> None:
        for fd in reversed(lock_fds):
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            finally:
                os.close(fd)
