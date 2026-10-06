#!/usr/bin/env python3
"""Report workstation storage pressure and offer a guarded BuildKit-cache prune."""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_WARNING_PERCENT = 80.0
DEFAULT_CRITICAL_PERCENT = 90.0
DOCKER_TIMEOUT_SECONDS = 30
PRUNE_TIMEOUT_SECONDS = 300
MAX_INSPECT_CONTAINERS = 100
_SIZE = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(B|kB|MB|GB|TB|KiB|MiB|GiB|TiB)\s*$")
_UNIT_BYTES = {
    "B": 1,
    "kB": 1000,
    "MB": 1000**2,
    "GB": 1000**3,
    "TB": 1000**4,
    "KiB": 1024,
    "MiB": 1024**2,
    "GiB": 1024**3,
    "TiB": 1024**4,
}


def positive_bytes(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a positive byte count") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be a positive byte count")
    return parsed


def size_bytes(value: str | None) -> int | None:
    if not value:
        return None
    match = _SIZE.fullmatch(value)
    if not match:
        return None
    return int(float(match.group(1)) * _UNIT_BYTES[match.group(2)])


def pressure_state(used_percent: float, warning: float, critical: float) -> str:
    if used_percent >= critical:
        return "critical"
    if used_percent >= warning:
        return "warning"
    return "ok"


def build_cache_prune_command(max_used_bytes: int) -> list[str]:
    if type(max_used_bytes) is not int or max_used_bytes <= 0:
        raise ValueError("max_used_bytes must be a positive integer")
    return ["docker", "builder", "prune", "--max-used-space", str(max_used_bytes), "--force"]


def prune_allowed(state: str) -> bool:
    return state in {"warning", "critical"}


def existing_probe_path(path: Path) -> Path:
    probe = path.expanduser()
    while not probe.exists() and probe != probe.parent:
        probe = probe.parent
    return probe


def filesystem_report(
    label: str,
    path: Path,
    warning: float,
    critical: float,
) -> dict[str, Any]:
    probe = existing_probe_path(path)
    try:
        usage = shutil.disk_usage(probe)
    except OSError:
        return {
            "label": label,
            "path_exists": path.exists(),
            "available": False,
            "state": "unknown",
        }
    used_percent = round((usage.total - usage.free) * 100 / usage.total, 1) if usage.total else 0.0
    return {
        "label": label,
        "path_exists": path.exists(),
        "available": True,
        "total_bytes": usage.total,
        "free_bytes": usage.free,
        "used_percent": used_percent,
        "state": pressure_state(used_percent, warning, critical),
    }


def directory_report(path: Path) -> dict[str, Any]:
    """Measure regular-file bytes without following symlinks or recording filenames."""
    path = path.expanduser()
    if not path.is_dir():
        return {"exists": False, "bytes": 0, "files": 0, "errors": 0}
    total = 0
    files = 0
    errors = 0
    pending = [path]
    while pending:
        current = pending.pop()
        try:
            with os.scandir(current) as entries:
                for entry in entries:
                    try:
                        if entry.is_symlink():
                            continue
                        if entry.is_dir(follow_symlinks=False):
                            pending.append(Path(entry.path))
                        elif entry.is_file(follow_symlinks=False):
                            total += entry.stat(follow_symlinks=False).st_size
                            files += 1
                    except OSError:
                        errors += 1
        except OSError:
            errors += 1
    return {"exists": True, "bytes": total, "files": files, "errors": errors}


def parse_json_lines(value: str) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line in value.splitlines():
        if not line.strip():
            continue
        item = json.loads(line)
        if not isinstance(item, dict):
            raise ValueError("expected JSON objects")
        records.append(item)
    return records


def parse_log_inspect_line(value: str) -> dict[str, Any] | None:
    parts = value.rstrip("\n").split("|", 3)
    if len(parts) != 4:
        return None
    _, driver, options_json, log_path = parts
    try:
        options = json.loads(options_json)
    except json.JSONDecodeError:
        options = {}
    if not isinstance(options, dict):
        options = {}
    max_size = options.get("max-size")
    max_files = options.get("max-file")
    bounded = driver == "local" or (driver == "json-file" and bool(max_size) and bool(max_files))
    try:
        log_bytes = Path(log_path).stat().st_size if log_path else None
    except OSError:
        log_bytes = None
    return {
        "driver": driver or "unknown",
        "bounded": bounded,
        "max_size": max_size if isinstance(max_size, str) else None,
        "max_files": max_files if isinstance(max_files, str) else None,
        "log_bytes": log_bytes,
    }


def docker_run(args: list[str], *, timeout: int = DOCKER_TIMEOUT_SECONDS) -> tuple[str | None, str | None]:
    try:
        result = subprocess.run(
            ["docker", *args],
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )
    except FileNotFoundError:
        return None, "docker_not_installed"
    except subprocess.TimeoutExpired:
        return None, "docker_timeout"
    if result.returncode:
        return None, "docker_command_failed"
    return result.stdout.strip(), None


def docker_report() -> dict[str, Any]:
    root, root_error = docker_run(["info", "--format", "{{.DockerRootDir}}"])
    summary_raw, summary_error = docker_run(["system", "df", "--format", "json"])
    details_raw, details_error = docker_run(["system", "df", "--verbose", "--format", "json"])
    ids_raw, ids_error = docker_run(["ps", "--quiet"])
    report: dict[str, Any] = {
        "available": not (root_error and summary_error and details_error and ids_error),
        "docker_root_available": bool(root),
        "summary": [],
        "volumes": [],
        "build_cache": {"entries": 0, "bytes": None, "in_use_entries": None},
        "logs": {"containers": 0, "unbounded_count": None, "entries": []},
        "errors": sorted({e for e in (root_error, summary_error, details_error, ids_error) if e}),
    }
    if root:
        report["docker_root"] = root
    if summary_raw is not None:
        try:
            report["summary"] = [
                {
                    "type": row.get("Type", "unknown"),
                    "objects": row.get("TotalCount"),
                    "size": row.get("Size"),
                    "reclaimable": row.get("Reclaimable"),
                }
                for row in parse_json_lines(summary_raw)
            ]
        except (json.JSONDecodeError, ValueError):
            report["errors"].append("docker_summary_unparseable")
    if details_raw is not None:
        try:
            details = json.loads(details_raw)
            if isinstance(details, dict):
                report["volumes"] = [
                    {
                        "size": row.get("Size"),
                        "links": row.get("Links"),
                    }
                    for row in details.get("Volumes", [])
                    if isinstance(row, dict)
                ]
                cache_entries = [row for row in details.get("BuildCache", []) if isinstance(row, dict)]
                cache_sizes = [size_bytes(row.get("Size")) for row in cache_entries]
                report["build_cache"] = {
                    "entries": len(cache_entries),
                    "bytes": sum(x for x in cache_sizes if x is not None)
                    if cache_entries and all(x is not None for x in cache_sizes)
                    else None,
                    "in_use_entries": sum(row.get("InUse") == "true" for row in cache_entries),
                }
        except (json.JSONDecodeError, TypeError):
            report["errors"].append("docker_details_unparseable")
    if ids_raw is not None:
        ids = [value for value in ids_raw.splitlines() if value][:MAX_INSPECT_CONTAINERS]
        report["logs"]["containers"] = len(ids)
        if ids:
            template = "{{.Name}}|{{.HostConfig.LogConfig.Type}}|{{json .HostConfig.LogConfig.Config}}|{{.LogPath}}"
            inspected, inspect_error = docker_run(
                ["inspect", "--format", template, *ids], timeout=DOCKER_TIMEOUT_SECONDS
            )
            if inspected is None:
                report["errors"].append(inspect_error or "docker_inspect_failed")
            else:
                entries = [parsed for line in inspected.splitlines() if (parsed := parse_log_inspect_line(line))]
                report["logs"]["entries"] = entries
                report["logs"]["unbounded_count"] = sum(not row["bounded"] for row in entries)
                if len(report["logs"]["entries"]) == MAX_INSPECT_CONTAINERS:
                    report["logs"]["truncated"] = True
    return report


def overall_state(filesystems: list[dict[str, Any]]) -> str:
    states = {row.get("state") for row in filesystems}
    if "critical" in states:
        return "critical"
    if "warning" in states:
        return "warning"
    if "ok" in states:
        return "ok"
    return "unknown"


def report(args: argparse.Namespace) -> dict[str, Any]:
    data_root = Path(args.data_root).expanduser()
    workspace = Path(args.workspace).expanduser()
    docker = docker_report()
    filesystem_paths = [
        ("root", Path("/")),
        ("workspace", workspace),
        ("zwslcore_data", data_root),
    ]
    if docker.get("docker_root"):
        filesystem_paths.append(("docker_root", Path(docker["docker_root"])))
    filesystems = [
        filesystem_report(label, path, args.warning_used_percent, args.critical_used_percent)
        for label, path in filesystem_paths
    ]
    components = {
        label: directory_report(data_root / relative)
        for label, relative in (
            ("state", "state"),
            ("cache", "cache"),
            ("evidence", "evidence"),
            ("backups", "backups"),
            ("worktrees", "worktrees"),
        )
    }
    return {
        "schema_version": 1,
        "generated_at_utc": dt.datetime.now(dt.UTC).isoformat(),
        "thresholds": {
            "warning_used_percent": args.warning_used_percent,
            "critical_used_percent": args.critical_used_percent,
        },
        "summary": {"state": overall_state(filesystems)},
        "filesystems": filesystems,
        "zwslcore_components": components,
        "docker": docker,
        "prune_plan": None,
    }


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Read-only filesystem and Docker storage report; BuildKit pruning is opt-in."
    )
    p.add_argument("--data-root", default=str(Path.home() / ".zwslcore"))
    p.add_argument("--workspace", default=str(Path.cwd()))
    p.add_argument("--warning-used-percent", type=float, default=DEFAULT_WARNING_PERCENT)
    p.add_argument("--critical-used-percent", type=float, default=DEFAULT_CRITICAL_PERCENT)
    p.add_argument(
        "--prune-build-cache-max-used-bytes",
        type=positive_bytes,
        help="show a BuildKit cache prune plan for this retained cache size (bytes); no change without --apply",
    )
    p.add_argument(
        "--apply",
        action="store_true",
        help="apply the BuildKit cache limit only when a monitored filesystem is warning/critical",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if not 0 < args.warning_used_percent < args.critical_used_percent < 100:
        p.error("thresholds must satisfy 0 < warning < critical < 100")
    if args.apply and args.prune_build_cache_max_used_bytes is None:
        p.error("--apply requires --prune-build-cache-max-used-bytes")
    result = report(args)
    if args.prune_build_cache_max_used_bytes is not None:
        max_bytes = args.prune_build_cache_max_used_bytes
        plan: dict[str, Any] = {
            "target": "Docker BuildKit cache only",
            "max_used_bytes": max_bytes,
            "command": build_cache_prune_command(max_bytes),
            "mode": "not_applied",
            "note": "No volumes, images, container logs, backups, evidence, models, or worktrees are targeted.",
        }
        capacity_state = result["summary"]["state"]
        if args.apply and not prune_allowed(capacity_state):
            plan["mode"] = (
                "not_needed_below_warning_threshold"
                if capacity_state == "ok"
                else "blocked_unknown_capacity"
            )
        elif args.apply:
            _, error = docker_run(plan["command"], timeout=PRUNE_TIMEOUT_SECONDS)
            plan["mode"] = "applied" if error is None else error
            if error is None:
                result = report(args)
        result["prune_plan"] = plan
    print(json.dumps(result, indent=2, sort_keys=True))
    state = result["summary"]["state"]
    return {"ok": 0, "warning": 1, "critical": 2}.get(state, 3)


if __name__ == "__main__":
    raise SystemExit(main())
