#!/usr/bin/env python3
"""Make the minimum WSL settings zwslcore needs without replacing user config."""

from __future__ import annotations

import os
import re
import stat
import sys
import tempfile
from pathlib import Path


SECTION = re.compile(r"^\s*\[([^]]+)\]\s*(?:[#;].*)?$")
SETTING = re.compile(r"^\s*([^=:#;]+?)\s*=\s*(.*?)\s*(?:[#;].*)?$")


def ensure_settings(path: Path, default_user: str) -> bool:
    if not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", default_user):
        raise ValueError("default user must be a valid Linux account name")
    if path.is_symlink():
        raise ValueError("refusing to replace symlinked wsl.conf")

    existed = path.exists()
    original = path.read_text(encoding="utf-8") if existed else ""
    lines = original.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in original else "\n"
    sections: dict[str, list[int]] = {}
    active = ""
    for index, line in enumerate(lines):
        match = SECTION.match(line.rstrip("\r\n"))
        if match:
            active = match.group(1).strip().lower()
            sections.setdefault(active, []).append(index)

    insertions: list[tuple[int, str]] = []
    for section, key, value in (("boot", "systemd", "true"), ("user", "default", default_user)):
        starts = sections.get(section, [])
        found: list[str] = []
        for start in starts:
            end = next((i for i in range(start + 1, len(lines)) if SECTION.match(lines[i].rstrip("\r\n"))), len(lines))
            for line in lines[start + 1 : end]:
                match = SETTING.match(line.rstrip("\r\n"))
                if match and match.group(1).strip().lower() == key:
                    found.append(match.group(2).strip().lower())
        if found:
            if section == "boot" and any(value != "true" for value in found):
                raise ValueError("existing boot.systemd setting is not true; refusing to override it")
            # Preserve an existing default user and all duplicate user settings.
            continue
        if starts:
            start = starts[-1]
            end = next((i for i in range(start + 1, len(lines)) if SECTION.match(lines[i].rstrip("\r\n"))), len(lines))
            insertions.append((end, f"{key}={value}{newline}"))
        else:
            if lines and not lines[-1].endswith(("\n", "\r")):
                lines[-1] += newline
            if lines and lines[-1].strip():
                lines.append(newline)
            lines.extend((f"[{section}]{newline}", f"{key}={value}{newline}"))

    for index, line in sorted(insertions, reverse=True):
        lines.insert(index, line)
    updated = "".join(lines)
    if updated == original:
        return False

    mode = stat.S_IMODE(path.stat().st_mode) if existed else 0o644
    owner = path.stat() if existed else None
    fd, temp_name = tempfile.mkstemp(prefix=".wsl.conf.", dir=path.parent)
    temp = Path(temp_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temp, mode)
        if owner is not None and hasattr(os, "chown"):
            os.chown(temp, owner.st_uid, owner.st_gid)
        os.replace(temp, path)
        return True
    finally:
        temp.unlink(missing_ok=True)


def main(argv: list[str]) -> int:
    if len(argv) != 3:
        print("Usage: wsl_conf.py WSL_CONF DEFAULT_LINUX_USER", file=sys.stderr)
        return 2
    try:
        changed = ensure_settings(Path(argv[1]), argv[2])
    except (OSError, ValueError) as exc:
        print(f"Unable to safely configure WSL: {exc}", file=sys.stderr)
        return 1
    print("Updated WSL systemd configuration." if changed else "WSL configuration already satisfies zwslcore.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
