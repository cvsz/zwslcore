from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from services.engineering.change_snapshot import ChangeSnapshotStore, SnapshotError
from services.engineering.worktree import WorktreeManager


def make_repo(root: Path) -> Path:
    repo = root / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "test@example.com"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "Test"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "commit.gpgsign", "false"], check=True)
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


class WorktreeOwnershipSecurityTests(unittest.TestCase):
    def test_reset_refuses_worktree_from_another_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a").mkdir()
            (root / "b").mkdir()
            repo_a = make_repo(root / "a")
            repo_b = make_repo(root / "b")
            manager = WorktreeManager(root / "worktrees")
            target, _ = manager.create(repo_a, "task_owner", "owner")

            with self.assertRaisesRegex(RuntimeError, "ownership"):
                manager._read_ownership(target, repository=repo_b)

    def test_forged_repository_marker_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a").mkdir()
            (root / "b").mkdir()
            repo_a = make_repo(root / "a")
            repo_b = make_repo(root / "b")
            manager = WorktreeManager(root / "worktrees")
            target, _ = manager.create(repo_a, "task_forged", "forged")

            marker = manager._marker(target)
            metadata = json.loads(marker.read_text(encoding="utf-8"))
            metadata["repository"] = str(repo_b.resolve())
            marker.write_text(json.dumps(metadata), encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "identity changed"):
                manager.reset(target)

    def test_legacy_marker_is_rejected_without_reset(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            target, _ = manager.create(repo, "task_legacy", "legacy")

            marker = manager._marker(target)
            marker.write_text("task_legacy\n", encoding="utf-8")

            with self.assertRaisesRegex(RuntimeError, "legacy or incomplete"):
                manager.reset(target)

            self.assertEqual(
                (target / "tracked.txt").read_text(encoding="utf-8"),
                "one\n",
            )

    def test_create_refuses_normalized_task_id_collision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            target, _ = manager.create(repo, "task/one", "first")

            with self.assertRaisesRegex(RuntimeError, "task ownership mismatch"):
                manager.create(repo, "task-one", "second")

            self.assertTrue(target.exists())

    def test_symlink_escape_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            target, _ = manager.create(repo, "task_symlink", "symlink")

            outside = root / "outside"
            outside.mkdir()
            link = manager.base_dir / "escape"
            link.symlink_to(outside, target_is_directory=True)

            with self.assertRaisesRegex(RuntimeError, "outside managed directory"):
                manager.reset(link)

            self.assertTrue(target.exists())

    def test_remove_refuses_wrong_repository(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a").mkdir()
            (root / "b").mkdir()
            repo_a = make_repo(root / "a")
            repo_b = make_repo(root / "b")
            manager = WorktreeManager(root / "worktrees")
            target, _ = manager.create(repo_a, "task_remove", "remove")

            with self.assertRaisesRegex(RuntimeError, "ownership mismatch"):
                manager.remove(repo_b, target)

            self.assertTrue(target.exists())
            self.assertTrue(manager._marker(target).exists())

    def test_reset_cleans_only_verified_managed_worktree(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            target, _ = manager.create(repo, "task_reset", "reset")

            (target / "tracked.txt").write_text("changed\n", encoding="utf-8")
            (target / "untracked.txt").write_text("temporary\n", encoding="utf-8")

            manager.reset(target)

            self.assertEqual(
                (target / "tracked.txt").read_text(encoding="utf-8"),
                "one\n",
            )
            self.assertFalse((target / "untracked.txt").exists())
            manager._read_ownership(target, repository=repo, task_id="task_reset")

    def test_create_rejects_existing_worktree_with_branch_mismatch(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")

            target, first_branch = manager.create(repo, "task_branch", "first")

            marker = manager._marker(target)
            before_marker = marker.read_text(encoding="utf-8")
            actual_branch = subprocess.run(
                ["git", "-C", str(target), "symbolic-ref", "--quiet", "--short", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(actual_branch, first_branch)

            mismatched_branch = manager.safe_branch_name("task_branch", "second")
            self.assertNotEqual(first_branch, mismatched_branch)

            # Same task_id, different slug: must fail closed instead of silently
            # returning a branch that does not match the existing worktree.
            with self.assertRaisesRegex(
                RuntimeError,
                "worktree branch does not match requested task configuration",
            ):
                manager.create(repo, "task_branch", "second")

            # Existing worktree, its branch, and the ownership marker are unchanged.
            self.assertTrue(target.exists())
            self.assertEqual(
                marker.read_text(encoding="utf-8"), before_marker
            )
            actual_branch_after = subprocess.run(
                ["git", "-C", str(target), "symbolic-ref", "--quiet", "--short", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertEqual(actual_branch_after, first_branch)

    def test_create_rolls_back_worktree_on_marker_write_failure(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_repo(root)
            manager = WorktreeManager(root / "worktrees")
            target = manager.base_dir / "task_marker_fail"
            marker = manager._marker(target)

            original_open = Path.open

            class _FailingWriteHandle:
                """Wraps a real handle but fails on every write."""

                def __init__(self, handle):
                    self._handle = handle

                def __enter__(self):
                    return self

                def __exit__(self, *exc_info):
                    self._handle.close()
                    return False

                def write(self, data):
                    raise OSError("simulated disk full")

                def __getattr__(self, name):
                    return getattr(self._handle, name)

            def failing_open(path, mode="r", *args, **kwargs):
                path = Path(path)
                if path == marker and "x" in mode:
                    # Create a partially written marker, then fail on write.
                    return _FailingWriteHandle(
                        original_open(path, mode, *args, **kwargs)
                    )
                return original_open(path, mode, *args, **kwargs)

            with patch.object(Path, "open", side_effect=failing_open):
                with self.assertRaisesRegex(RuntimeError, "marker"):
                    manager.create(repo, "task_marker_fail", "fail")

            # No marker falsely reported as created; the partial marker is cleaned up.
            self.assertFalse(marker.exists())

            # The newly created worktree was rolled back.
            self.assertFalse(target.exists())

            # git worktree list no longer registers the failed target.
            registered = subprocess.run(
                ["git", "-C", str(repo), "worktree", "list", "--porcelain"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout
            self.assertNotIn(str(target), registered)

            # Source repository remains intact.
            self.assertTrue((repo / "tracked.txt").exists())
            head = subprocess.run(
                ["git", "-C", str(repo), "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            self.assertTrue(head)


if __name__ == "__main__":
    unittest.main()
