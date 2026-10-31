from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from typing import Any


class WorktreeManager:
    """Manage isolated Git worktrees with verifiable ownership metadata."""

    MARKER_VERSION = 1

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(
            base_dir or Path.home() / ".zwslcore" / "worktrees"
        ).resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_branch_name(task_id: str, slug: str = "") -> str:
        safe_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-")[:40]
        safe_task = re.sub(r"[^A-Za-z0-9._-]+", "-", task_id).strip("-")[:40]
        if not safe_task or safe_task in {".", ".."}:
            raise ValueError("task_id must produce a valid branch name")
        suffix = f"-{safe_slug}" if safe_slug else ""
        return f"agent/{safe_task}{suffix}"

    @staticmethod
    def _run(
        args: list[str],
        *,
        check: bool = True,
    ) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            check=check,
            capture_output=True,
            text=True,
        )

    @classmethod
    def _git_path(cls, repo: Path, argument: str) -> Path:
        value = cls._run(
            ["git", "-C", str(repo), "rev-parse", argument]
        ).stdout.strip()
        path = Path(value)
        return (repo / path).resolve() if not path.is_absolute() else path.resolve()

    @classmethod
    def _repo_root(cls, repository: str | Path) -> Path:
        candidate = Path(repository).resolve()
        result = cls._run(
            ["git", "-C", str(candidate), "rev-parse", "--show-toplevel"],
            check=False,
        )
        if result.returncode != 0:
            raise RuntimeError(f"not a Git repository: {candidate}")
        return Path(result.stdout.strip()).resolve()

    def _target_path(self, target: str | Path) -> Path:
        target_path = Path(target).resolve()
        try:
            target_path.relative_to(self.base_dir)
        except ValueError as exc:
            raise RuntimeError(
                f"worktree path is outside managed directory: {target_path}"
            ) from exc

        if target_path == self.base_dir:
            raise RuntimeError("worktree target cannot be the managed directory")
        return target_path

    def _marker(self, target: Path) -> Path:
        return self.base_dir / f".{target.name}.managed"

    def _read_ownership(
        self,
        target: Path,
        repository: str | Path | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        target_path = self._target_path(target)
        marker = self._marker(target_path)

        if marker.is_symlink() or not marker.is_file():
            raise RuntimeError(
                f"refusing unmanaged worktree: ownership marker missing or invalid: {target_path}"
            )

        try:
            marker_content = marker.read_text(encoding="utf-8")
        except OSError as exc:
            raise RuntimeError(
                f"unable to read ownership marker: {marker}"
            ) from exc

        try:
            metadata = json.loads(marker_content)
        except json.JSONDecodeError as exc:
            # Previous versions stored task_id as plain text.
            if marker_content.strip() and not marker_content.lstrip().startswith(
                ("{", "[")
            ):
                raise RuntimeError(
                    f"legacy or incomplete ownership marker; "
                    f"manual verification required: {marker}"
                ) from exc
            raise RuntimeError(
                f"invalid ownership marker; manual verification required: {marker}"
            ) from exc

        if not isinstance(metadata, dict):
            raise RuntimeError(f"invalid ownership metadata: {marker}")

        required = {
            "version",
            "task_id",
            "repository",
            "repository_common_dir",
            "branch",
        }
        if not required.issubset(metadata):
            raise RuntimeError(
                f"legacy or incomplete ownership marker; refusing operation: {marker}"
            )

        if metadata["version"] != self.MARKER_VERSION:
            raise RuntimeError(f"unsupported ownership marker version: {marker}")

        if not all(isinstance(metadata[key], str) and metadata[key] for key in required - {"version"}):
            raise RuntimeError(f"invalid ownership marker fields: {marker}")

        if task_id is not None and metadata["task_id"] != task_id:
            raise RuntimeError(
                f"task ownership mismatch: expected {task_id!r}, "
                f"found {metadata['task_id']!r}"
            )

        recorded_repo = Path(metadata["repository"]).resolve()
        recorded_common = Path(metadata["repository_common_dir"]).resolve()

        if not recorded_repo.is_dir():
            raise RuntimeError(
                f"recorded source repository is unavailable: {recorded_repo}"
            )

        actual_common = self._git_path(recorded_repo, "--git-common-dir")
        if actual_common != recorded_common:
            raise RuntimeError(
                f"source repository identity changed: {recorded_repo}"
            )

        if repository is not None:
            supplied_repo = self._repo_root(repository)
            supplied_common = self._git_path(supplied_repo, "--git-common-dir")
            if supplied_common != recorded_common:
                raise RuntimeError(
                    "repository ownership mismatch: target belongs to a different Git repository"
                )

        if not target_path.is_dir():
            raise RuntimeError(f"worktree directory does not exist: {target_path}")

        top_level = Path(
            self._run(
                ["git", "-C", str(target_path), "rev-parse", "--show-toplevel"]
            ).stdout.strip()
        ).resolve()

        if top_level != target_path:
            raise RuntimeError(
                f"Git worktree root mismatch: expected {target_path}, found {top_level}"
            )

        target_common = self._git_path(target_path, "--git-common-dir")
        if target_common != recorded_common:
            raise RuntimeError(
                "Git common directory mismatch: target is not owned by the recorded repository"
            )

        registered = self._run(
            ["git", "-C", str(recorded_repo), "worktree", "list", "--porcelain"]
        ).stdout.splitlines()

        registered_paths = {
            Path(line.removeprefix("worktree ")).resolve()
            for line in registered
            if line.startswith("worktree ")
        }
        if target_path not in registered_paths:
            raise RuntimeError(
                f"target is not registered as a worktree of its source repository: {target_path}"
            )

        branch_result = self._run(
            ["git", "-C", str(target_path), "symbolic-ref", "--quiet", "--short", "HEAD"],
            check=False,
        )
        if branch_result.returncode != 0 or branch_result.stdout.strip() != metadata["branch"]:
            raise RuntimeError(
                f"worktree branch ownership mismatch: {target_path}"
            )

        return metadata

    def create(
        self,
        repository: str | Path,
        task_id: str,
        slug: str = "",
    ) -> tuple[Path, str]:
        if not task_id.strip():
            raise ValueError("task_id must not be empty")

        repo = self._repo_root(repository)
        common_dir = self._git_path(repo, "--git-common-dir")
        branch = self.safe_branch_name(task_id, slug)

        directory_name = re.sub(
            r"[^A-Za-z0-9._-]+", "-", task_id
        ).strip("-")
        if not directory_name or directory_name in {".", ".."}:
            raise ValueError("task_id must produce a valid worktree directory")

        target = self._target_path(self.base_dir / directory_name)
        marker = self._marker(target)

        if target.exists() or target.is_symlink():
            metadata = self._read_ownership(target, repository=repo, task_id=task_id)
            if metadata["branch"] != branch:
                raise RuntimeError(
                    "worktree branch does not match requested task configuration: "
                    f"expected {branch}, found {metadata['branch']}"
                )
            return target, branch

        if marker.exists() or marker.is_symlink():
            raise RuntimeError(
                f"orphaned ownership marker exists; manual verification required: {marker}"
            )

        self._run(
            [
                "git", "-C", str(repo), "worktree", "add",
                "-b", branch, str(target), "HEAD",
            ]
        )

        metadata = {
            "version": self.MARKER_VERSION,
            "task_id": task_id,
            "repository": str(repo),
            "repository_common_dir": str(common_dir),
            "branch": branch,
        }

        try:
            with marker.open("x", encoding="utf-8") as handle:
                json.dump(metadata, handle, indent=2, sort_keys=True)
                handle.write("\n")
        except Exception as exc:
            # The worktree was just created by this invocation; roll it back so an
            # unmarked Git worktree cannot be silently reused.
            rollback_error = None
            try:
                self._rollback_new_worktree(repo, target, common_dir)
            except Exception as rollback_exc:
                rollback_error = rollback_exc
            # Best-effort removal of any partially written marker we created.
            try:
                marker.unlink(missing_ok=True)
            except Exception as unlink_exc:
                if rollback_error is None:
                    rollback_error = unlink_exc
            if rollback_error is not None:
                raise RuntimeError(
                    f"worktree marker write failed ({exc}); rollback also failed "
                    f"({rollback_error}); target may be orphaned: {target}"
                ) from exc
            raise RuntimeError(
                f"worktree created but ownership marker could not be written; "
                f"worktree rolled back: {target}"
            ) from exc

        self._read_ownership(target, repository=repo, task_id=task_id)
        return target, branch

    def _rollback_new_worktree(
        self,
        repo: Path,
        target: Path,
        common_dir: Path,
    ) -> None:
        """Remove a worktree created by the current invocation only.

        Refuses to remove anything that is not a registered worktree of the
        expected source repository with a matching common directory, so a
        pre-existing or foreign worktree is never deleted.
        """
        target_path = self._target_path(target)

        registered = self._run(
            ["git", "-C", str(repo), "worktree", "list", "--porcelain"]
        ).stdout.splitlines()
        registered_paths = {
            Path(line.removeprefix("worktree ")).resolve()
            for line in registered
            if line.startswith("worktree ")
        }
        if target_path not in registered_paths:
            raise RuntimeError(
                f"refusing rollback: target is not registered in the source repository: {target_path}"
            )

        target_common = self._git_path(target_path, "--git-common-dir")
        if target_common != common_dir:
            raise RuntimeError(
                f"refusing rollback: common directory mismatch for {target_path}"
            )

        self._run(
            [
                "git", "-C", str(repo), "worktree",
                "remove", "--force", str(target_path),
            ]
        )

    def remove(self, repository: str | Path, target: str | Path) -> None:
        target_path = self._target_path(target)
        self._read_ownership(target_path, repository=repository)

        repo = self._repo_root(repository)
        self._run(
            [
                "git", "-C", str(repo), "worktree",
                "remove", "--force", str(target_path),
            ]
        )
        self._marker(target_path).unlink(missing_ok=True)

    def reset(self, target: str | Path) -> None:
        target_path = self._target_path(target)
        self._read_ownership(target_path)

        self._run(
            ["git", "-C", str(target_path), "reset", "--hard", "HEAD"]
        )
        self._run(
            ["git", "-C", str(target_path), "clean", "-fd"]
        )

    def sync_to_source(
        self,
        repository: str | Path,
        target: str | Path,
    ) -> tuple[str, str]:
        repo = self._repo_root(repository)
        target_path = self._target_path(target)
        self._read_ownership(target_path, repository=repo)

        source_head = self._run(
            ["git", "-C", str(repo), "rev-parse", "HEAD"]
        ).stdout.strip()

        previous_head = self._run(
            ["git", "-C", str(target_path), "rev-parse", "HEAD"]
        ).stdout.strip()

        self._run(
            ["git", "-C", str(target_path), "reset", "--hard", source_head]
        )
        self._run(
            ["git", "-C", str(target_path), "clean", "-fd"]
        )
        return previous_head, source_head

    @staticmethod
    def _assert_git_repo(repo: Path) -> None:
        WorktreeManager._repo_root(repo)
