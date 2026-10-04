from __future__ import annotations

import hashlib
import json
import os
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

from .worktree import WorktreeManager

DEFAULT_ROOT = Path.home() / ".zwslcore" / "snapshots"
MAX_PATCH_BYTES = 8 * 1024 * 1024


class SnapshotError(RuntimeError):
    pass


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class ChangeSnapshotStore:
    def __init__(
        self,
        *,
        root: str | Path = DEFAULT_ROOT,
        worktrees: WorktreeManager | None = None,
    ) -> None:
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.worktrees = worktrees or WorktreeManager()

    def capture(self, task_id: str, worktree: str | Path) -> dict[str, Any]:
        target = Path(worktree).resolve()
        self._assert_managed(target)
        head = self._git(target, ["rev-parse", "HEAD"]).strip()
        patch = self._working_patch(target)
        if not patch:
            raise SnapshotError("refusing to snapshot a clean worktree")
        if len(patch) > MAX_PATCH_BYTES:
            raise SnapshotError(
                f"change patch exceeds {MAX_PATCH_BYTES} byte snapshot limit"
            )

        digest = _sha256(patch)
        directory = self.root / task_id
        directory.mkdir(parents=True, exist_ok=True)
        patch_path = directory / "change.patch"
        meta_path = directory / "snapshot.json"
        self._atomic_write(patch_path, patch)
        metadata = {
            "schema": 1,
            "task_id": task_id,
            "head": head,
            "patch_sha256": digest,
            "patch_bytes": len(patch),
            "captured_at": time.time(),
            "state": "applied",
        }
        self._atomic_write(
            meta_path,
            (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )
        return metadata | {"patch_path": str(patch_path), "metadata_path": str(meta_path)}

    def status(self, task_id: str) -> dict[str, Any]:
        directory = self.root / task_id
        meta_path = directory / "snapshot.json"
        patch_path = directory / "change.patch"
        try:
            metadata = json.loads(meta_path.read_text(encoding="utf-8"))
            patch = patch_path.read_bytes()
        except FileNotFoundError as exc:
            raise SnapshotError(f"snapshot not found for task {task_id}") from exc
        if not isinstance(metadata, dict) or metadata.get("schema") != 1:
            raise SnapshotError("invalid snapshot metadata")
        if _sha256(patch) != metadata.get("patch_sha256"):
            raise SnapshotError("snapshot patch checksum mismatch")
        return metadata | {
            "patch_path": str(patch_path),
            "metadata_path": str(meta_path),
        }

    def undo(self, task_id: str, worktree: str | Path) -> dict[str, Any]:
        target = Path(worktree).resolve()
        self._assert_managed(target)
        metadata = self.status(task_id)
        self._assert_head(target, metadata)
        if metadata.get("state") != "applied":
            raise SnapshotError(f"snapshot is not applied: {metadata.get('state')}")

        current = self._working_patch(target)
        if _sha256(current) != metadata["patch_sha256"]:
            raise SnapshotError("worktree drift detected; refusing undo")

        self.worktrees.reset(target)
        if self._working_patch(target):
            raise SnapshotError("worktree is not clean after undo")
        metadata["state"] = "undone"
        metadata["undone_at"] = time.time()
        self._write_metadata(task_id, metadata)
        return metadata

    def redo(self, task_id: str, worktree: str | Path) -> dict[str, Any]:
        target = Path(worktree).resolve()
        self._assert_managed(target)
        metadata = self.status(task_id)
        self._assert_head(target, metadata)
        if metadata.get("state") != "undone":
            raise SnapshotError(f"snapshot is not undone: {metadata.get('state')}")
        if self._working_patch(target):
            raise SnapshotError("worktree drift detected; refusing redo")

        patch_path = Path(metadata["patch_path"])
        result = subprocess.run(
            ["git", "-C", str(target), "apply", "--binary", "--whitespace=nowarn", str(patch_path)],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise SnapshotError(f"redo patch apply failed: {result.stderr.strip()[:1000]}")
        current = self._working_patch(target)
        if _sha256(current) != metadata["patch_sha256"]:
            self.worktrees.reset(target)
            raise SnapshotError("redo verification failed; worktree was reset")
        metadata["state"] = "applied"
        metadata["redone_at"] = time.time()
        self._write_metadata(task_id, metadata)
        return metadata

    def _working_patch(self, worktree: Path) -> bytes:
        tracked = subprocess.run(
            ["git", "-C", str(worktree), "diff", "--binary", "--no-ext-diff", "HEAD", "--", "."],
            check=True,
            capture_output=True,
        ).stdout
        other = subprocess.run(
            ["git", "-C", str(worktree), "ls-files", "--others", "--exclude-standard", "-z", "--", "."],
            check=True,
            capture_output=True,
        ).stdout
        patches = [tracked]
        for raw in [item for item in other.split(b"\0") if item]:
            rel = raw.decode("utf-8", errors="surrogateescape")
            path = (worktree / rel).resolve()
            try:
                path.relative_to(worktree)
            except ValueError as exc:
                raise SnapshotError(f"untracked path escaped worktree: {rel}") from exc
            if not path.is_file():
                continue
            result = subprocess.run(
                ["git", "-C", str(worktree), "diff", "--binary", "--no-index", "--", "/dev/null", rel],
                capture_output=True,
            )
            if result.returncode not in {0, 1}:
                raise SnapshotError(f"unable to snapshot untracked file: {rel}")
            patches.append(result.stdout)
            if sum(len(item) for item in patches) > MAX_PATCH_BYTES:
                raise SnapshotError(
                    f"change patch exceeds {MAX_PATCH_BYTES} byte snapshot limit"
                )
        return b"".join(patches)

    def _assert_managed(self, target: Path) -> None:
        try:
            target.relative_to(self.worktrees.base_dir)
        except ValueError as exc:
            raise SnapshotError(f"refusing unmanaged worktree: {target}") from exc
        marker = self.worktrees.base_dir / f".{target.name}.managed"
        if not marker.exists():
            raise SnapshotError(f"refusing unmanaged worktree: {target}")

    def _assert_head(self, target: Path, metadata: dict[str, Any]) -> None:
        current = self._git(target, ["rev-parse", "HEAD"]).strip()
        if current != metadata.get("head"):
            raise SnapshotError("worktree HEAD changed; refusing snapshot mutation")

    @staticmethod
    def _git(target: Path, args: list[str]) -> str:
        return subprocess.run(
            ["git", "-C", str(target), *args],
            check=True,
            capture_output=True,
            text=True,
        ).stdout

    def _write_metadata(self, task_id: str, metadata: dict[str, Any]) -> None:
        payload = {key: value for key, value in metadata.items() if key not in {"patch_path", "metadata_path"}}
        self._atomic_write(
            self.root / task_id / "snapshot.json",
            (json.dumps(payload, indent=2, sort_keys=True) + "\n").encode("utf-8"),
        )

    @staticmethod
    def _atomic_write(path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
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
