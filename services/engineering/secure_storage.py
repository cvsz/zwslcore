from __future__ import annotations

import os
import stat
from pathlib import Path


def reject_symlink_components(path: str | Path) -> None:
    """Reject symlinks anywhere in an application-owned storage path."""
    candidate = Path(path).expanduser().absolute()
    for component in reversed((candidate, *candidate.parents)):
        try:
            metadata = component.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(metadata.st_mode):
            raise PermissionError(f"refusing symlinked storage path component: {component}")


def ensure_private_directory(path: str | Path) -> Path:
    """Create or tighten a zwslcore-owned data directory to mode 0700."""
    directory = Path(path).expanduser()
    reject_symlink_components(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    reject_symlink_components(directory)
    metadata = directory.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or metadata.st_uid != os.geteuid():
        raise PermissionError(
            f"zwslcore data directory must be a real directory owned by the current user: {directory}"
        )
    if stat.S_IMODE(metadata.st_mode) & 0o077:
        os.chmod(directory, 0o700)
        metadata = directory.lstat()
        if not stat.S_ISDIR(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) & 0o077:
            raise PermissionError(f"unable to make zwslcore data directory private: {directory}")
    return directory
