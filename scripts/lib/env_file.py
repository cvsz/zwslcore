"""Private, atomic writes for local environment configuration."""

from __future__ import annotations

import os
from pathlib import Path
import stat
import tempfile


def write_private_file(path: str | Path, content: str) -> None:
    """Atomically replace a private file without truncating the prior copy."""
    destination = Path(path)
    if destination.is_symlink() or (destination.exists() and not destination.is_file()):
        raise ValueError("destination must be a regular non-symlink file")

    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, destination)
        directory_fd = os.open(
            destination.parent,
            os.O_RDONLY | getattr(os, "O_DIRECTORY", 0),
        )
        try:
            os.fsync(directory_fd)
        finally:
            os.close(directory_fd)
    finally:
        temporary.unlink(missing_ok=True)
