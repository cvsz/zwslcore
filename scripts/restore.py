#!/usr/bin/env python3
"""Verify a zwslcore backup into a new isolated directory without touching live state."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
from pathlib import Path, PurePosixPath
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.backup import BACKUP_SCHEMA, RPO_TARGET_HOURS, RTO_TARGET_MINUTES


class RestoreError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_manifest(backup: Path) -> dict[str, Any]:
    manifest_path = backup / "manifest.json"
    checksum_path = backup / "manifest.sha256"
    if not manifest_path.is_file() or not checksum_path.is_file():
        raise RestoreError("backup manifest or checksum is missing")
    encoded = manifest_path.read_bytes()
    expected = checksum_path.read_text(encoding="utf-8").split()[0]
    if hashlib.sha256(encoded).hexdigest() != expected:
        raise RestoreError("backup manifest checksum failed")
    manifest = json.loads(encoded)
    if manifest.get("schema") != BACKUP_SCHEMA or not isinstance(manifest.get("files"), dict):
        raise RestoreError("backup manifest schema is unsupported")
    return manifest


def _safe_relative(raw: str) -> PurePosixPath:
    relative = PurePosixPath(raw)
    if relative.is_absolute() or not relative.parts or any(part in {"", ".", ".."} for part in relative.parts):
        raise RestoreError(f"unsafe backup path: {raw!r}")
    return relative


def _verify_and_copy_files(backup: Path, target: Path, manifest: dict[str, Any]) -> dict[str, Any]:
    content = backup / "content"
    results: dict[str, Any] = {}
    for raw, metadata in manifest["files"].items():
        relative = _safe_relative(raw)
        source = content.joinpath(*relative.parts)
        try:
            source.resolve().relative_to(content.resolve())
        except ValueError as exc:
            raise RestoreError(f"backup path escapes content root: {raw}") from exc
        if source.is_symlink() or not source.is_file():
            raise RestoreError(f"backup file is missing or not regular: {raw}")
        actual_hash = _sha256(source)
        actual_size = source.stat().st_size
        if actual_hash != metadata.get("sha256") or actual_size != metadata.get("bytes"):
            raise RestoreError(f"backup file checksum or size mismatch: {raw}")
        destination = target.joinpath(*relative.parts)
        destination.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
        os.chmod(destination, 0o600)
        results[raw] = {"verified": True, "sha256": actual_hash, "bytes": actual_size}
    return results


def _verify_sqlite(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RestoreError("restored engineering database is missing")
    uri = f"file:{path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=10)
    try:
        integrity = str(connection.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise RestoreError(f"restored engineering database failed integrity check: {integrity}")
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"tasks", "checkpoints", "runner_leases"}
        if not required.issubset(tables):
            raise RestoreError("restored engineering database is missing required tables")
        return {
            "integrity_check": integrity,
            "schema_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
            "tasks": int(connection.execute("SELECT count(*) FROM tasks").fetchone()[0]),
            "checkpoints": int(connection.execute("SELECT count(*) FROM checkpoints").fetchone()[0]),
        }
    finally:
        connection.close()


def _verify_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RestoreError("restored continuous ledger is missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != 1 or not isinstance(value.get("records"), dict):
        raise RestoreError("restored continuous ledger has an invalid schema")
    archives = value.get("archives", {})
    if not isinstance(archives, dict):
        raise RestoreError("restored continuous ledger archives are invalid")
    return {"schema_version": value["schema"], "active_records": len(value["records"]), "archived_records": len(archives)}


def _verify_evidence(root: Path) -> dict[str, Any]:
    evidence_root = root / "evidence"
    checked = 0
    if not evidence_root.exists():
        return {"bundles": 0, "checksums_passed": 0}
    for evidence in evidence_root.rglob("evidence.json"):
        sidecar = evidence.with_name("evidence.sha256")
        if not sidecar.is_file():
            raise RestoreError(f"restored evidence checksum is missing: {evidence.relative_to(evidence_root)}")
        if _sha256(evidence) != sidecar.read_text(encoding="utf-8").split()[0]:
            raise RestoreError(f"restored evidence checksum failed: {evidence.relative_to(evidence_root)}")
        checked += 1
    return {"bundles": checked, "checksums_passed": checked}


def _verify_cache(root: Path) -> dict[str, Any]:
    cache_root = root / "cache"
    checked = 0
    if cache_root.exists():
        for item in cache_root.rglob("*.json"):
            with item.open("r", encoding="utf-8") as handle:
                json.load(handle)
            checked += 1
    return {"json_files_readable": checked}


def restore_backup(backup: str | Path, target: str | Path | None = None) -> Path:
    started = time.monotonic()
    backup_path = Path(backup).expanduser().resolve()
    manifest = _load_manifest(backup_path)
    if target is None:
        target_path = Path(tempfile.mkdtemp(prefix="zwslcore-restore-"))
    else:
        target_path = Path(target).expanduser().resolve()
        if target_path.exists() and any(target_path.iterdir()):
            raise RestoreError("restore target must be a new or empty directory")
        target_path.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target_path == backup_path or backup_path in target_path.parents:
        raise RestoreError("restore target must be outside the backup directory")
    os.chmod(target_path, 0o700)
    try:
        copied = _verify_and_copy_files(backup_path, target_path, manifest)
        sqlite_result = _verify_sqlite(target_path / "state" / "engineering.db")
        ledger_result = _verify_ledger(target_path / "state" / "continuous.json")
        evidence_result = _verify_evidence(target_path)
        cache_result = _verify_cache(target_path)
        elapsed = round(time.monotonic() - started, 3)
        created_epoch = float(manifest.get("created_at_epoch", time.time()))
        rpo_hours = max(0.0, (time.time() - created_epoch) / 3600)
        checks = {
            "file_checksums": {"passed": True, "files": len(copied)},
            "engineering_sqlite": sqlite_result,
            "continuous_ledger": ledger_result,
            "evidence": evidence_result,
            "cache": cache_result,
            "rpo": {"target_hours": RPO_TARGET_HOURS, "backup_age_hours": round(rpo_hours, 4), "met": rpo_hours <= RPO_TARGET_HOURS},
            "rto": {"target_minutes": RTO_TARGET_MINUTES, "restore_duration_seconds": elapsed, "met": elapsed <= RTO_TARGET_MINUTES * 60},
        }
        report = {
            "schema": 1,
            "status": (
                "FAIL"
                if not checks["file_checksums"]["passed"] or not checks["rpo"]["met"] or not checks["rto"]["met"]
                else "PARTIAL"
                if any("Open WebUI persistent volume" in item for item in manifest.get("excluded", []))
                else "PASS"
            ),
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "backup": str(backup_path),
            "backup_source": manifest.get("source", {}),
            "isolated_target": str(target_path),
            "checks": checks,
            "encrypted_user_data_artifacts": [
                raw for raw in copied if raw.endswith(".gpg")
            ],
        }
        report_path = target_path / "restore-report.json"
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.chmod(report_path, 0o600)
        return target_path
    except Exception:
        # Keep failed isolated restores available for diagnosis; never touch live paths.
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", help="backup directory created by scripts/backup.sh")
    parser.add_argument("--target", help="new isolated restore directory; defaults to a retained temporary directory")
    args = parser.parse_args()
    try:
        result = restore_backup(args.backup, args.target)
    except (RestoreError, OSError, ValueError, sqlite3.Error, json.JSONDecodeError) as exc:
        print(f"restore failed: {exc}", file=sys.stderr)
        return 2
    report = json.loads((result / "restore-report.json").read_text(encoding="utf-8"))
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
