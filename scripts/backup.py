#!/usr/bin/env python3
"""Create an owner-only, checksummed backup of zwslcore's durable local state."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import tomllib
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.engineering.lease import SQLiteRunnerLease
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.models import TaskStatus
from services.engineering.store import SQLiteEngineeringStore

BACKUP_SCHEMA = 1
RPO_TARGET_HOURS = 24
RTO_TARGET_MINUTES = 60
ACTIVE_TASK_STATES = {
    TaskStatus.BASELINING,
    TaskStatus.PLANNING,
    TaskStatus.EDITING,
    TaskStatus.VALIDATING,
    TaskStatus.REVIEWING,
}


class BackupError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_private(path: Path, value: bytes) -> None:
    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    path.write_bytes(value)
    path.chmod(0o600)
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _copy_file(source: Path, relative: str, content: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise BackupError(f"refusing unsupported backup input: {relative}")
    target = content / relative
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    target.chmod(0o600)


def _copy_tree(source: Path, relative_root: str, content: Path) -> None:
    if not source.exists():
        return
    if source.is_symlink() or not source.is_dir():
        raise BackupError(f"refusing unsupported backup directory: {relative_root}")
    for path in sorted(source.rglob("*")):
        relative = path.relative_to(source)
        target = content / relative_root / relative
        if path.is_symlink():
            raise BackupError(f"refusing symbolic link in backup input: {relative_root}/{relative}")
        if path.is_dir():
            target.mkdir(mode=0o700, parents=True, exist_ok=True)
        elif path.is_file():
            _copy_file(path, f"{relative_root}/{relative.as_posix()}", content)
        else:
            raise BackupError(f"refusing unsupported backup entry: {relative_root}/{relative}")


def _sqlite_online_backup(source: Path, destination: Path) -> dict[str, Any]:
    source_uri = f"file:{source.resolve().as_posix()}?mode=ro"
    src = sqlite3.connect(source_uri, uri=True, timeout=30)
    dst = sqlite3.connect(destination, timeout=30)
    try:
        src.backup(dst, pages=256, sleep=0.05)
        integrity = str(dst.execute("PRAGMA integrity_check").fetchone()[0])
        if integrity != "ok":
            raise BackupError(f"SQLite online backup failed integrity check: {integrity}")
        schema_version = int(dst.execute("PRAGMA user_version").fetchone()[0])
        tables = {
            str(row[0])
            for row in dst.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        counts: dict[str, int] = {}
        for table in ("tasks", "checkpoints", "runner_leases"):
            if table in tables:
                # Table name is from a known allowlist, safe to interpolate
                counts[table] = int(dst.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])  # nosec B608
        return {"integrity_check": integrity, "schema_version": schema_version, "row_counts": counts}
    finally:
        dst.close()
        src.close()


def _git_metadata(repository: Path) -> dict[str, Any]:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(repository), *args],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout.strip()

    try:
        return {
            "head": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "dirty": bool(git("status", "--porcelain=v1")),
        }
    except (OSError, subprocess.SubprocessError):
        return {"head": "", "branch": "", "dirty": True, "available": False}


def _runtime_metadata() -> dict[str, Any]:
    containers: dict[str, Any] = {}
    for name in (
        "zwslcore-ollama",
        "zwslcore-litellm",
        "zwslcore-provider",
        "zwslcore-open-webui",
    ):
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.Config.Image}} {{.Image}} {{.State.Running}}", name],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
        )
        if result.returncode == 0:
            image_ref, image_id, running = ([*result.stdout.strip().split(" ", 2), ""])[:3]
            containers[name] = {
                "image_ref": image_ref,
                "image_id": image_id,
                "running": running.lower() == "true",
            }
    return {
        "python": sys.version.split()[0],
        "sqlite": sqlite3.sqlite_version,
        "containers": containers,
    }


def _validate_evidence_tree(path: Path) -> None:
    if not path.exists():
        return
    for evidence in path.rglob("evidence.json"):
        sidecar = evidence.with_name("evidence.sha256")
        if not sidecar.exists():
            raise BackupError(f"evidence checksum is missing: {evidence.relative_to(path)}")
        expected = sidecar.read_text(encoding="utf-8").split()[0]
        if _sha256(evidence) != expected:
            raise BackupError(f"evidence checksum failed: {evidence.relative_to(path)}")


def _validate_json_tree(path: Path) -> None:
    if not path.exists():
        return
    for item in path.rglob("*.json"):
        with item.open("r", encoding="utf-8") as handle:
            json.load(handle)


def _include_webui_volume(
    stage: Path,
    *,
    container: str,
    recipient: str,
) -> dict[str, Any]:
    if not recipient.strip():
        raise BackupError("Open WebUI volume backup requires --gpg-recipient")
    inspected = subprocess.run(
        ["docker", "inspect", "--format", "{{json .Mounts}}", container],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    )
    mounts = json.loads(inspected.stdout)
    volume = next(
        (
            item
            for item in mounts
            if item.get("Type") == "volume" and item.get("Destination") == "/app/backend/data"
        ),
        None,
    )
    if not volume:
        raise BackupError(f"expected Open WebUI data volume is not mounted in {container}")
    image = subprocess.run(
        ["docker", "inspect", "--format", "{{.Image}}", container],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip()
    running = subprocess.run(
        ["docker", "inspect", "--format", "{{.State.Running}}", container],
        check=True,
        capture_output=True,
        text=True,
        timeout=15,
    ).stdout.strip().lower() == "true"
    if not image:
        raise BackupError("could not resolve the local Open WebUI image identity")

    target = stage / "content" / "docker" / "open-webui-data.tar.gz.gpg"
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    stopped = False
    try:
        if running:
            subprocess.run(["docker", "stop", "--time", "15", container], check=True, capture_output=True, timeout=30)
            stopped = True
        tar_code = (
            "import sys,tarfile; "
            "archive=tarfile.open(fileobj=sys.stdout.buffer,mode='w|gz'); "
            "archive.add('/app/backend/data',arcname='open-webui-data',recursive=True); "
            "archive.close()"
        )
        docker_command = [
            "docker", "run", "--rm", "--network", "none",
            "--volumes-from", f"{container}:ro",
            "--entrypoint", "python", image, "-c", tar_code,
        ]
        producer = subprocess.Popen(docker_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        assert producer.stdout is not None
        encryptor = subprocess.Popen(
            ["gpg", "--batch", "--yes", "--output", str(target), "--recipient", recipient, "--encrypt"],
            stdin=producer.stdout,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
        )
        producer.stdout.close()
        _, gpg_error = encryptor.communicate(timeout=1800)
        _, docker_error = producer.communicate(timeout=1800)
        if producer.returncode != 0 or encryptor.returncode != 0:
            target.unlink(missing_ok=True)
            raise BackupError(
                "Open WebUI volume capture/encryption failed "
                f"(docker={producer.returncode}, gpg={encryptor.returncode}); "
                f"gpg={gpg_error.decode(errors='replace')[:300]!r}; "
                f"docker={docker_error.decode(errors='replace')[:300]!r}"
            )
        target.chmod(0o600)
    finally:
        if stopped:
            subprocess.run(["docker", "start", container], check=True, capture_output=True, timeout=60)
    return {
        "path": "docker/open-webui-data.tar.gz.gpg",
        "volume_name": str(volume.get("Name") or ""),
        "container": container,
        "image_id": image,
        "gpg_recipient": recipient,
        "encrypted": True,
        "container_was_running": running,
    }


@dataclass(frozen=True, slots=True)
class BackupConfig:
    source_root: str | Path | None
    repository_root: str | Path
    output: str | Path | None
    include_webui_volume: bool
    recreate_webui_data: bool
    gpg_recipient: str
    webui_container: str


@dataclass(frozen=True, slots=True)
class ManifestData:
    config: BackupConfig
    source: Path
    repository: Path
    started: float
    git_meta: dict[str, Any]
    runtime_meta: dict[str, Any]
    sqlite_meta: dict[str, Any]
    ledger_value: dict[str, Any]
    docker_state: dict[str, Any] | None
    files: dict[str, dict[str, Any]]
    excluded: list[str]
    webui_policy: str


def _validate_config(config: BackupConfig) -> None:
    if config.include_webui_volume and config.recreate_webui_data:
        raise BackupError("choose either encrypted Open WebUI capture or the recreate policy")


def _resolve_paths(config: BackupConfig) -> tuple[Path, Path, Path, Path]:
    source = Path(config.source_root or Path.home() / ".zwslcore").expanduser().resolve()
    repository = Path(config.repository_root).expanduser().resolve()
    state = source / "state"
    db_path = state / "engineering.db"
    ledger_path = state / "continuous.json"
    if not db_path.is_file() or not ledger_path.is_file():
        raise BackupError("engineering.db and continuous.json must both exist before backup")
    return source, repository, db_path, ledger_path


def _resolve_target(config: BackupConfig, source: Path) -> tuple[Path, Path]:
    if config.output:
        target = Path(config.output).expanduser().resolve()
        backup_parent = target.parent
    else:
        backup_parent = source / "backups"
        stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%dT%H%M%SZ")
        target = backup_parent / f"zwslcore-{stamp}-{uuid.uuid4().hex[:8]}"
    if target.exists():
        raise BackupError(f"backup destination already exists: {target}")
    if source == target:
        raise BackupError("backup destination cannot replace the source state root")
    backup_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    backup_parent.chmod(0o700)
    stage = Path(tempfile.mkdtemp(prefix=".zwslcore-backup-", dir=backup_parent))
    stage.chmod(0o700)
    return target, stage


def _prepare_content_dir(stage: Path) -> Path:
    content = stage / "content"
    content.mkdir(mode=0o700)
    return content


def _check_active_tasks(store: SQLiteEngineeringStore) -> None:
    active = [task.id for task in store.list_tasks() if task.status in ACTIVE_TASK_STATES]
    if active:
        raise BackupError(f"backup refused while engineering tasks are active: {len(active)}")


def _backup_database(db_path: Path, content: Path) -> dict[str, Any]:
    db_target = content / "state" / "engineering.db"
    db_target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    sqlite_metadata = _sqlite_online_backup(db_path, db_target)
    db_target.chmod(0o600)
    return sqlite_metadata


def _backup_ledger(ledger: JsonContinuousLedger, content: Path) -> dict[str, Any]:
    ledger_bytes = ledger.snapshot_bytes()
    ledger_value: dict[str, Any] = json.loads(ledger_bytes)
    if ledger_value.get("schema") != JsonContinuousLedger.SCHEMA:
        raise BackupError("continuous ledger schema version is unsupported")
    _write_private(content / "state" / "continuous.json", ledger_bytes)
    return ledger_value


def _copy_config_files(repository: Path, content: Path) -> None:
    for relative in (
        ".env.example",
        "compose.yaml",
        "config",
        "services/provider/config",
        "services/provider/pyproject.toml",
    ):
        path = repository / relative
        if path.is_dir():
            _copy_tree(path, f"config/{relative}", content)
        elif path.is_file():
            _copy_file(path, f"config/{relative}", content)


def _validate_backup_content(content: Path) -> None:
    _validate_evidence_tree(content / "evidence")
    _validate_json_tree(content / "evidence")
    _validate_json_tree(content / "cache")


def _collect_file_metadata(content: Path) -> dict[str, dict[str, Any]]:
    files: dict[str, dict[str, Any]] = {}
    for path in sorted(content.rglob("*")):
        if path.is_file():
            relative = path.relative_to(content).as_posix()
            files[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}
    return files


def _determine_webui_policy(
    config: BackupConfig,
    stage: Path,
    content: Path,
    files: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[str], str]:
    excluded = [
        ".env and runtime credentials (managed through the operator's separate secret process)",
        "Ollama model volume (models are reproducible cache and must be pulled again if absent)",
    ]
    docker_state: dict[str, Any] | None = None
    webui_policy = "unspecified"
    if config.include_webui_volume:
        docker_state = _include_webui_volume(
            stage,
            container=config.webui_container,
            recipient=config.gpg_recipient,
        )
        volume_path = content / str(docker_state["path"])
        files[str(docker_state["path"])] = {
            "bytes": volume_path.stat().st_size,
            "sha256": _sha256(volume_path),
            "classification": "restricted encrypted user data",
        }
        excluded = [item for item in excluded if not item.startswith("Ollama")]
        excluded.append("Open WebUI data volume is included as GPG-encrypted user data")
        webui_policy = "encrypted_backup"
    elif config.recreate_webui_data:
        excluded.append("Open WebUI persistent volume (user-authorized recreate policy; not backed up)")
        webui_policy = "recreate"
    else:
        excluded.append(
            "Open WebUI persistent volume (sensitive user data; requires explicit encrypted capture or recreate policy)"
        )
        webui_policy = "unspecified"
    return docker_state, excluded, webui_policy


def _get_provider_version(repository: Path) -> str:
    version = ""
    pyproject = repository / "services/provider/pyproject.toml"
    if pyproject.is_file():
        with pyproject.open("rb") as handle:
            version = str(tomllib.load(handle).get("project", {}).get("version", ""))
    return version


def _build_manifest(data: ManifestData) -> dict[str, Any]:
    version = _get_provider_version(data.repository)
    return {
        "schema": BACKUP_SCHEMA,
        "created_at": dt.datetime.now(dt.UTC).isoformat(),
        "created_at_epoch": time.time(),
        "source": {
            "root": str(data.source),
            "repository": str(data.repository),
            "git": data.git_meta,
            "provider_version": version,
        },
        "runtime": data.runtime_meta,
        "sqlite": data.sqlite_meta,
        "ledger": {
            "schema_version": data.ledger_value["schema"],
            "active_records": len(data.ledger_value.get("records", {})),
            "archived_records": len(data.ledger_value.get("archives", {})),
        },
        "docker_user_data": data.docker_state,
        "files": data.files,
        "policy": {
            "sensitivity": "restricted local application data",
            "local_file_mode": "0600; backup directories are 0700",
            "encrypt_before_off_host_transfer": True,
            "secrets_included": False,
            "open_webui_user_data": data.webui_policy,
            "rpo_target_hours": RPO_TARGET_HOURS,
            "rto_target_minutes": RTO_TARGET_MINUTES,
        },
        "excluded": data.excluded,
        "duration_seconds": round(time.monotonic() - data.started, 3),
    }


def _write_manifest(stage: Path, manifest: dict[str, Any]) -> bytes:
    encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
    _write_private(stage / "manifest.json", encoded)
    _write_private(stage / "manifest.sha256", f"{hashlib.sha256(encoded).hexdigest()}  manifest.json\n".encode())
    return encoded


def _finalize_backup(stage: Path, target: Path) -> Path:
    stage.replace(target)
    target.chmod(0o700)
    return target


def create_backup(
    *,
    source_root: str | Path | None = None,
    repository_root: str | Path = ROOT,
    output: str | Path | None = None,
    include_webui_volume: bool = False,
    recreate_webui_data: bool = False,
    gpg_recipient: str = "",
    webui_container: str = "zwslcore-open-webui",
    _config: BackupConfig | None = None,
) -> Path:
    if _config is not None:
        config = _config
    else:
        config = BackupConfig(
            source_root=source_root,
            repository_root=repository_root,
            output=output,
            include_webui_volume=include_webui_volume,
            recreate_webui_data=recreate_webui_data,
            gpg_recipient=gpg_recipient,
            webui_container=webui_container,
        )
    _validate_config(config)
    started = time.monotonic()
    source, repository, db_path, ledger_path = _resolve_paths(config)
    target, stage = _resolve_target(config, source)
    content = _prepare_content_dir(stage)

    try:
        store = SQLiteEngineeringStore(db_path)
        ledger = JsonContinuousLedger(ledger_path)
        lock_paths = SQLiteRunnerLease.queue_lock_paths(store, ledger.path)
        with SQLiteRunnerLease(store, lock_paths=lock_paths):
            _check_active_tasks(store)
            sqlite_metadata = _backup_database(db_path, content)
            ledger_value = _backup_ledger(ledger, content)

        _copy_tree(source / "evidence", "evidence", content)
        _copy_tree(source / "cache", "cache", content)
        _copy_config_files(repository, content)

        _validate_backup_content(content)
        files = _collect_file_metadata(content)

        git_meta = _git_metadata(repository)
        runtime_meta = _runtime_metadata()

        docker_state, excluded, webui_policy = _determine_webui_policy(
            config, stage, content, files
        )

        manifest = _build_manifest(ManifestData(
            config=config,
            source=source,
            repository=repository,
            started=started,
            git_meta=git_meta,
            runtime_meta=runtime_meta,
            sqlite_meta=sqlite_metadata,
            ledger_value=ledger_value,
            docker_state=docker_state,
            files=files,
            excluded=excluded,
            webui_policy=webui_policy,
        ))
        _write_manifest(stage, manifest)

        return _finalize_backup(stage, target)
    except Exception:
        shutil.rmtree(stage, ignore_errors=True)
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", default=str(Path.home() / ".zwslcore"))
    parser.add_argument("--repository", default=str(ROOT))
    parser.add_argument("--output", help="destination directory; defaults to SOURCE_ROOT/backups")
    webui_policy = parser.add_mutually_exclusive_group()
    webui_policy.add_argument("--include-webui-volume", action="store_true")
    webui_policy.add_argument(
        "--recreate-webui-data",
        action="store_true",
        help="record that Open WebUI user data is intentionally recreatable and excluded",
    )
    parser.add_argument("--gpg-recipient", default="")
    parser.add_argument("--webui-container", default="zwslcore-open-webui")
    args = parser.parse_args()
    config = BackupConfig(
        source_root=args.source_root,
        repository_root=args.repository,
        output=args.output,
        include_webui_volume=args.include_webui_volume,
        recreate_webui_data=args.recreate_webui_data,
        gpg_recipient=args.gpg_recipient,
        webui_container=args.webui_container,
    )
    try:
        create_backup(
            source_root=config.source_root,
            repository_root=config.repository_root,
            output=config.output,
            include_webui_volume=config.include_webui_volume,
            recreate_webui_data=config.recreate_webui_data,
            gpg_recipient=config.gpg_recipient,
            webui_container=config.webui_container,
        )
    except (BackupError, OSError, ValueError, sqlite3.Error, subprocess.SubprocessError):
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
