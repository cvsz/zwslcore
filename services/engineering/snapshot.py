from __future__ import annotations

import os
from pathlib import Path


class RepositorySnapshotter:
    """Bounded, secret-aware repository text snapshot."""

    EXCLUDED_DIRS = {
        ".git", ".zwslcore", ".venv", "venv", "node_modules", "vendor",
        "dist", "build", "__pycache__", ".pytest_cache", ".mypy_cache",
    }
    SECRET_NAMES = {
        ".env", ".env.local", ".env.production", "id_rsa", "id_ed25519",
    }
    SECRET_SUFFIXES = {".pem", ".key", ".p12", ".pfx"}

    def __init__(
        self,
        root: str | Path,
        *,
        max_files: int = 400,
        max_file_bytes: int = 256 * 1024,
        max_total_bytes: int = 4 * 1024 * 1024,
    ) -> None:
        self.root = Path(root).resolve()
        self.max_files = max_files
        self.max_file_bytes = max_file_bytes
        self.max_total_bytes = max_total_bytes

    def snapshot(self) -> str:
        chunks: list[str] = []
        total = 0
        count = 0

        for current, dirs, files in os.walk(self.root, followlinks=False):
            current_path = Path(current)
            dirs[:] = sorted(
                d for d in dirs
                if d not in self.EXCLUDED_DIRS and not (current_path / d).is_symlink()
            )
            for name in sorted(files):
                if count >= self.max_files or total >= self.max_total_bytes:
                    return "".join(chunks)
                path = current_path / name
                if self._excluded(path):
                    continue
                try:
                    size = path.stat().st_size
                except OSError:
                    continue
                if size > self.max_file_bytes or path.is_symlink():
                    continue
                try:
                    raw = path.read_bytes()
                    text = raw.decode("utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                encoded = text.encode("utf-8")
                remaining = self.max_total_bytes - total
                if remaining <= 0:
                    return "".join(chunks)
                encoded = encoded[:remaining]
                text = encoded.decode("utf-8", errors="ignore")
                rel = path.relative_to(self.root).as_posix()
                block = f"\n--- FILE: {rel} ---\n{text}\n"
                block_bytes = len(block.encode("utf-8"))
                if block_bytes > remaining:
                    block = block.encode("utf-8")[:remaining].decode("utf-8", errors="ignore")
                    block_bytes = len(block.encode("utf-8"))
                chunks.append(block)
                total += block_bytes
                count += 1
        return "".join(chunks)

    def _excluded(self, path: Path) -> bool:
        name = path.name.lower()
        if name in self.SECRET_NAMES or name.startswith(".env."):
            return True
        if path.suffix.lower() in self.SECRET_SUFFIXES:
            return True
        try:
            path.resolve().relative_to(self.root)
        except ValueError:
            return True
        return False
