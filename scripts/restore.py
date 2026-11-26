#!/usr/bin/env python3
"""Verify a zwslcore backup into a new isolated directory without touching live state."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import shutil
import sqlite3
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any


@dataclass(slots=True)
class RestoreReportData:
    backup_path: Path
    target_path: Path
    manifest: dict[str, Any]
    copied: dict[str, Any]
    sqlite_result: dict[str, Any]
    ledger_result: dict[str, Any]
    evidence_result: dict[str, Any]
    cache_result: dict[str, Any]
    elapsed: float
    created_epoch: float
    webui_policy: str
    webui_excluded: bool
    started: float


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
    if not isinstance(manifest, dict):
        raise RestoreError("backup manifest root must be an object")
    if manifest.get("schema") != BACKUP_SCHEMA or not isinstance(manifest.get("files"), dict):
        raise RestoreError("backup manifest schema is unsupported")
    if not isinstance(manifest.get("policy", {}), dict):
        raise RestoreError("backup manifest policy must be an object")
    excluded = manifest.get("excluded", [])
    if not isinstance(excluded, list) or any(not isinstance(item, str) for item in excluded):
        raise RestoreError("backup manifest exclusions must be a string list")
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
        destination.chmod(0o600)
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
            _raise_integrity_error(integrity)
        tables = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        required = {"tasks", "checkpoints", "runner_leases"}
        if not required.issubset(tables):
            _raise_missing_tables_error()
        return {
            "integrity_check": integrity,
            "schema_version": int(connection.execute("PRAGMA user_version").fetchone()[0]),
            "tasks": int(connection.execute("SELECT count(*) FROM tasks").fetchone()[0]),
            "checkpoints": int(connection.execute("SELECT count(*) FROM checkpoints").fetchone()[0]),
        }
    finally:
        connection.close()


def _raise_integrity_error(integrity: str) -> None:
    raise RestoreError(f"restored engineering database failed integrity check: {integrity}")


def _raise_missing_tables_error() -> None:
    raise RestoreError("restored engineering database is missing required tables")


def _verify_ledger(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RestoreError("restored continuous ledger is missing")
    value = json.loads(path.read_text(encoding="utf-8"))
    _validate_ledger_schema(value)
    archives = value.get("archives", {})
    if not isinstance(archives, dict):
        _raise_invalid_ledger_archives_error()
    return {"schema_version": value["schema"], "active_records": len(value["records"]), "archived_records": len(archives)}


def _validate_ledger_schema(value: dict[str, Any]) -> None:
    if value.get("schema") != 1 or not isinstance(value.get("records"), dict):
        _raise_invalid_ledger_schema_error()


def _raise_invalid_ledger_schema_error() -> None:
    raise RestoreError("restored continuous ledger has an invalid schema")


def _raise_invalid_ledger_archives_error() -> None:
    raise RestoreError("restored continuous ledger archives are invalid")


def _verify_evidence(root: Path) -> dict[str, Any]:
    evidence_root = root / "evidence"
    checked = 0
    if not evidence_root.exists():
        return {"bundles": 0, "checksums_passed": 0}
    for evidence in evidence_root.rglob("evidence.json"):
        sidecar = evidence.with_name("evidence.sha256")
        if not sidecar.is_file():
            _raise_missing_evidence_checksum_error(evidence, evidence_root)
        if _sha256(evidence) != sidecar.read_text(encoding="utf-8").split()[0]:
            _raise_failed_evidence_checksum_error(evidence, evidence_root)
        checked += 1
    return {"bundles": checked, "checksums_passed": checked}


def _raise_missing_evidence_checksum_error(evidence: Path, evidence_root: Path) -> None:
    raise RestoreError(f"restored evidence checksum is missing: {evidence.relative_to(evidence_root)}")


def _raise_failed_evidence_checksum_error(evidence: Path, evidence_root: Path) -> None:
    raise RestoreError(f"restored evidence checksum failed: {evidence.relative_to(evidence_root)}")


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
    target_path.chmod(0o700)
    copied = _verify_and_copy_files(backup_path, target_path, manifest)
    sqlite_result = _verify_sqlite(target_path / "state" / "engineering.db")
    ledger_result = _verify_ledger(target_path / "state" / "continuous.json")
    evidence_result = _verify_evidence(target_path)
    cache_result = _verify_cache(target_path)
    elapsed = round(time.monotonic() - started, 3)
    created_epoch = float(manifest.get("created_at_epoch", time.time()))
    policy = manifest.get("policy", {})
    webui_excluded = any(
        "Open WebUI persistent volume" in item
        for item in manifest.get("excluded", [])
    )
    webui_policy = policy.get("open_webui_user_data")
    if webui_policy is None:
        webui_policy = "unspecified" if webui_excluded else (
            "encrypted_backup" if manifest.get("docker_user_data") else "unspecified"
        )
    _validate_webui_policy(webui_policy)
    if webui_policy == "recreate" and not webui_excluded:
        _raise_recreate_policy_error()
    if webui_policy == "recreate" and manifest.get("docker_user_data") is not None:
        _raise_recreate_with_volume_error()
    if webui_policy == "encrypted_backup":
        _validate_encrypted_webui_policy(manifest, copied)
    report_data = RestoreReportData(
        backup_path=backup_path,
        target_path=target_path,
        manifest=manifest,
        copied=copied,
        sqlite_result=sqlite_result,
        ledger_result=ledger_result,
        evidence_result=evidence_result,
        cache_result=cache_result,
        elapsed=elapsed,
        created_epoch=created_epoch,
        webui_policy=webui_policy,
        webui_excluded=webui_excluded,
        started=started,
    )
    return _build_restore_report(report_data)


def _validate_webui_policy(webui_policy: str | None) -> None:
    if not isinstance(webui_policy, str) or webui_policy not in {
        "unspecified",
        "recreate",
        "encrypted_backup",
    }:
        _raise_unsupported_webui_policy_error()


def _raise_unsupported_webui_policy_error() -> None:
    raise RestoreError("backup Open WebUI user-data policy is unsupported")


def _raise_recreate_policy_error() -> None:
    raise RestoreError("recreate policy is inconsistent with the backup exclusions")


def _raise_recreate_with_volume_error() -> None:
    raise RestoreError("recreate policy cannot also include Open WebUI volume data")


def _validate_encrypted_webui_policy(manifest: dict[str, Any], copied: dict[str, Any]) -> None:
    user_data = manifest.get("docker_user_data")
    if not isinstance(user_data, dict):
        _raise_missing_encrypted_volume_error()
    assert isinstance(user_data, dict)
    if not user_data.get("encrypted"):
        _raise_missing_encrypted_volume_error()
    user_data_path = str(user_data.get("path") or "")
    if not isinstance(user_data_path, str):
        _raise_missing_encrypted_archive_error()
    if user_data_path not in copied:
        _raise_missing_encrypted_archive_error()


def _raise_missing_encrypted_volume_error() -> None:
    raise RestoreError("encrypted Open WebUI policy is missing its encrypted volume record")


def _raise_missing_encrypted_archive_error() -> None:
    raise RestoreError("encrypted Open WebUI archive is missing from the restored copy")


def _build_restore_report(data: RestoreReportData) -> Path:
    rpo_hours = max(0.0, (time.time() - data.created_epoch) / 3600)
    checks = {
        "file_checksums": {"passed": True, "files": len(data.copied)},
        "engineering_sqlite": data.sqlite_result,
        "continuous_ledger": data.ledger_result,
        "evidence": data.evidence_result,
        "cache": data.cache_result,
        "rpo": {
            "target_hours": RPO_TARGET_HOURS,
            "backup_age_hours": round(rpo_hours, 4),
            "met": rpo_hours <= RPO_TARGET_HOURS,
        },
        "rto": {
            "target_minutes": RTO_TARGET_MINUTES,
            "restore_duration_seconds": data.elapsed,
            "met": data.elapsed <= RTO_TARGET_MINUTES * 60,
        },
    }
    checks["open_webui_user_data"] = {
        "policy": data.webui_policy,
        "excluded_by_policy": data.webui_policy == "recreate",
        "complete_for_declared_policy": data.webui_policy != "unspecified",
    }
    report = {
        "schema": 1,
        "status": _compute_restore_status(checks, data.webui_policy, data.webui_excluded),
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "backup": str(data.backup_path),
        "backup_source": data.manifest.get("source", {}),
        "isolated_target": str(data.target_path),
        "checks": checks,
        "encrypted_user_data_artifacts": [
            raw for raw in data.copied if raw.endswith(".gpg")
        ],
    }
    report_path = data.target_path / "restore-report.json"
    report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.chmod(0o600)
    return data.target_path


def _compute_restore_status(checks: dict[str, Any], webui_policy: str, webui_excluded: bool) -> str:
    if not checks["file_checksums"]["passed"] or not checks["rpo"]["met"] or not checks["rto"]["met"]:
        return "FAIL"
    if webui_policy == "unspecified" and webui_excluded:
        return "PARTIAL"
    return "PASS"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("backup", help="backup directory created by scripts/backup.sh")
    parser.add_argument("--target", help="new isolated restore directory; defaults to a retained temporary directory")
    args = parser.parse_args()
    try:
        result = restore_backup(args.backup, args.target)
    except (RestoreError, OSError, ValueError, sqlite3.Error, json.JSONDecodeError):
        return 2
    report = json.loads((result / "restore-report.json").read_text(encoding="utf-8"))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
