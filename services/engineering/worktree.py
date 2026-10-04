from __future__ import annotations

import re
import subprocess
from pathlib import Path


class WorktreeManager:
    """Ownership-aware isolated Git worktrees under ~/.zwslcore/worktrees."""

    def __init__(self, base_dir: str | Path | None = None) -> None:
        self.base_dir = Path(base_dir or Path.home() / ".zwslcore" / "worktrees").resolve()
        self.base_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def safe_branch_name(task_id: str, slug: str = "") -> str:
        safe_slug = re.sub(r"[^A-Za-z0-9._-]+", "-", slug).strip("-")[:40]
        safe_task = re.sub(r"[^A-Za-z0-9._-]+", "-", task_id).strip("-")[:40]
        suffix = f"-{safe_slug}" if safe_slug else ""
        return f"agent/{safe_task}{suffix}"

    def create(self, repository: str | Path, task_id: str, slug: str = "") -> tuple[Path, str]:
        repo = Path(repository).resolve()
        self._assert_git_repo(repo)
        branch = self.safe_branch_name(task_id, slug)
        target = (self.base_dir / re.sub(r"[^A-Za-z0-9._-]+", "-", task_id)).resolve()
        target.relative_to(self.base_dir)

        marker = self._marker(target)
        if target.exists():
            if not marker.exists():
                raise RuntimeError(f"refusing unmanaged existing path: {target}")
            return target, branch

        subprocess.run(
            ["git", "-C", str(repo), "worktree", "add", "-b", branch, str(target), "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        marker.write_text(task_id + "\n", encoding="utf-8")
        return target, branch

    def remove(self, repository: str | Path, target: str | Path) -> None:
        repo = Path(repository).resolve()
        target_path = Path(target).resolve()
        target_path.relative_to(self.base_dir)
        marker = self._marker(target_path)
        if not marker.exists():
            raise RuntimeError(f"refusing to remove unmanaged worktree: {target_path}")
        subprocess.run(
            ["git", "-C", str(repo), "worktree", "remove", "--force", str(target_path)],
            check=True,
            capture_output=True,
            text=True,
        )
        marker.unlink(missing_ok=True)

    def _marker(self, target: Path) -> Path:
        return self.base_dir / f".{target.name}.managed"

    @staticmethod
    def _assert_git_repo(repo: Path) -> None:
        result = subprocess.run(
            ["git", "-C", str(repo), "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            raise RuntimeError(f"not a Git repository: {repo}")
