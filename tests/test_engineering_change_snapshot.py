from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from services.engineering.change_snapshot import ChangeSnapshotStore, SnapshotError
from services.engineering.worktree import WorktreeManager


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    (repo / "tracked.txt").write_text("one\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-m", "base"], check=True, capture_output=True)
    return repo


class ChangeSnapshotTests(unittest.TestCase):
    def test_tracked_and_untracked_round_trip(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            worktree, _ = manager.create(repo, "task_roundtrip", "roundtrip")
            (worktree / "tracked.txt").write_text("two\n", encoding="utf-8")
            (worktree / "new.txt").write_text("new\n", encoding="utf-8")

            snapshots = ChangeSnapshotStore(
                root=root / "snapshots",
                worktrees=manager,
            )
            created = snapshots.capture("task_roundtrip", worktree)
            self.assertEqual(created["state"], "applied")
            self.assertGreater(created["patch_bytes"], 0)
            self.assertEqual(len(created["patch_sha256"]), 64)

            undone = snapshots.undo("task_roundtrip", worktree)
            self.assertEqual(undone["state"], "undone")
            self.assertEqual((worktree / "tracked.txt").read_text(encoding="utf-8"), "one\n")
            self.assertFalse((worktree / "new.txt").exists())

            redone = snapshots.redo("task_roundtrip", worktree)
            self.assertEqual(redone["state"], "applied")
            self.assertEqual((worktree / "tracked.txt").read_text(encoding="utf-8"), "two\n")
            self.assertEqual((worktree / "new.txt").read_text(encoding="utf-8"), "new\n")

    def test_undo_refuses_worktree_drift(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            worktree, _ = manager.create(repo, "task_drift", "drift")
            (worktree / "tracked.txt").write_text("two\n", encoding="utf-8")
            snapshots = ChangeSnapshotStore(root=root / "snapshots", worktrees=manager)
            snapshots.capture("task_drift", worktree)

            (worktree / "tracked.txt").write_text("unexpected\n", encoding="utf-8")
            with self.assertRaisesRegex(SnapshotError, "drift"):
                snapshots.undo("task_drift", worktree)

    def test_redo_refuses_head_change(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            worktree, _ = manager.create(repo, "task_head", "head")
            (worktree / "tracked.txt").write_text("two\n", encoding="utf-8")
            snapshots = ChangeSnapshotStore(root=root / "snapshots", worktrees=manager)
            snapshots.capture("task_head", worktree)
            snapshots.undo("task_head", worktree)

            (worktree / "advance.txt").write_text("advance\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(worktree), "add", "."], check=True)
            subprocess.run(
                ["git", "-C", str(worktree), "commit", "-m", "advance"],
                check=True,
                capture_output=True,
            )
            with self.assertRaisesRegex(SnapshotError, "HEAD changed"):
                snapshots.redo("task_head", worktree)

    def test_unmanaged_worktree_is_refused(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            snapshots = ChangeSnapshotStore(
                root=root / "snapshots",
                worktrees=WorktreeManager(root / "managed"),
            )
            (repo / "tracked.txt").write_text("two\n", encoding="utf-8")
            with self.assertRaisesRegex(SnapshotError, "unmanaged worktree"):
                snapshots.capture("task_bad", repo)


if __name__ == "__main__":
    unittest.main()
