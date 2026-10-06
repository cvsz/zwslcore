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
import tarfile
import tempfile
import time
import tomllib
import uuid
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
    os.chmod(path, 0o600)
    with path.open("rb") as handle:
        os.fsync(handle.fileno())


def _copy_file(source: Path, relative: str, content: Path) -> None:
    if source.is_symlink() or not source.is_file():
        raise BackupError(f"refusing unsupported backup input: {relative}")
    target = content / relative
    target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    os.chmod(target, 0o600)


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
                counts[table] = int(dst.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0])
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
        )
        if result.returncode == 0:
            image_ref, image_id, running = (result.stdout.strip().split(" ", 2) + [""])[:3]
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
        os.chmod(target, 0o600)
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


def create_backup(
    *,
    source_root: str | Path | None = None,
    repository_root: str | Path = ROOT,
    output: str | Path | None = None,
    include_webui_volume: bool = False,
    recreate_webui_data: bool = False,
    gpg_recipient: str = "",
    webui_container: str = "zwslcore-open-webui",
) -> Path:
    if include_webui_volume and recreate_webui_data:
        raise BackupError("choose either encrypted Open WebUI capture or the recreate policy")
    started = time.monotonic()
    source = Path(source_root or Path.home() / ".zwslcore").expanduser().resolve()
    repository = Path(repository_root).expanduser().resolve()
    state = source / "state"
    db_path = state / "engineering.db"
    ledger_path = state / "continuous.json"
    if not db_path.is_file() or not ledger_path.is_file():
        raise BackupError("engineering.db and continuous.json must both exist before backup")

    if output:
        target = Path(output).expanduser().resolve()
        backup_parent = target.parent
    else:
        backup_parent = source / "backups"
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        target = backup_parent / f"zwslcore-{stamp}-{uuid.uuid4().hex[:8]}"
    if target.exists():
        raise BackupError(f"backup destination already exists: {target}")
    if source == target:
        raise BackupError("backup destination cannot replace the source state root")
    backup_parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    os.chmod(backup_parent, 0o700)
    stage = Path(tempfile.mkdtemp(prefix=".zwslcore-backup-", dir=backup_parent))
    os.chmod(stage, 0o700)
    content = stage / "content"
    content.mkdir(mode=0o700)

    sqlite_metadata: dict[str, Any]
    ledger_value: dict[str, Any]
    try:
        store = SQLiteEngineeringStore(db_path)
        ledger = JsonContinuousLedger(ledger_path)
        lock_paths = SQLiteRunnerLease.queue_lock_paths(store, ledger.path)
        with SQLiteRunnerLease(store, lock_paths=lock_paths):
            active = [task.id for task in store.list_tasks() if task.status in ACTIVE_TASK_STATES]
            if active:
                raise BackupError(f"backup refused while engineering tasks are active: {len(active)}")

            db_target = content / "state" / "engineering.db"
            db_target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            sqlite_metadata = _sqlite_online_backup(db_path, db_target)
            os.chmod(db_target, 0o600)

            ledger_bytes = ledger.snapshot_bytes()
            ledger_value = json.loads(ledger_bytes)
            if ledger_value.get("schema") != JsonContinuousLedger.SCHEMA:
                raise BackupError("continuous ledger schema version is unsupported")
            _write_private(content / "state" / "continuous.json", ledger_bytes)

        _copy_tree(source / "evidence", "evidence", content)
        _copy_tree(source / "cache", "cache", content)
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

        _validate_evidence_tree(content / "evidence")
        _validate_json_tree(content / "evidence")
        _validate_json_tree(content / "cache")
        files: dict[str, dict[str, Any]] = {}
        for path in sorted(content.rglob("*")):
            if path.is_file():
                relative = path.relative_to(content).as_posix()
                files[relative] = {"bytes": path.stat().st_size, "sha256": _sha256(path)}

        docker_state: dict[str, Any] | None = None
        excluded = [
            ".env and runtime credentials (managed through the operator's separate secret process)",
            "Ollama model volume (models are reproducible cache and must be pulled again if absent)",
        ]
        if include_webui_volume:
            docker_state = _include_webui_volume(
                stage,
                container=webui_container,
                recipient=gpg_recipient,
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
        elif recreate_webui_data:
            excluded.append("Open WebUI persistent volume (user-authorized recreate policy; not backed up)")
            webui_policy = "recreate"
        else:
            excluded.append(
                "Open WebUI persistent volume (sensitive user data; requires explicit encrypted capture or recreate policy)"
            )
            webui_policy = "unspecified"

        version = ""
        pyproject = repository / "services/provider/pyproject.toml"
        if pyproject.is_file():
            with pyproject.open("rb") as handle:
                version = str(tomllib.load(handle).get("project", {}).get("version", ""))
        manifest = {
            "schema": BACKUP_SCHEMA,
            "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "created_at_epoch": time.time(),
            "source": {
                "root": str(source),
                "repository": str(repository),
                "git": _git_metadata(repository),
                "provider_version": version,
            },
            "runtime": _runtime_metadata(),
            "sqlite": sqlite_metadata,
            "ledger": {
                "schema_version": ledger_value["schema"],
                "active_records": len(ledger_value.get("records", {})),
                "archived_records": len(ledger_value.get("archives", {})),
            },
            "docker_user_data": docker_state,
            "files": files,
            "policy": {
                "sensitivity": "restricted local application data",
                "local_file_mode": "0600; backup directories are 0700",
                "encrypt_before_off-host_transfer": True,
                "secrets_included": False,
                "open_webui_user_data": webui_policy,
                "rpo_target_hours": RPO_TARGET_HOURS,
                "rto_target_minutes": RTO_TARGET_MINUTES,
            },
            "excluded": excluded,
            "duration_seconds": round(time.monotonic() - started, 3),
        }
        encoded = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode("utf-8")
        _write_private(stage / "manifest.json", encoded)
        _write_private(stage / "manifest.sha256", f"{hashlib.sha256(encoded).hexdigest()}  manifest.json\n".encode())
        os.replace(stage, target)
        os.chmod(target, 0o700)
        return target
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
    try:
        result = create_backup(
            source_root=args.source_root,
            repository_root=args.repository,
            output=args.output,
            include_webui_volume=args.include_webui_volume,
            recreate_webui_data=args.recreate_webui_data,
            gpg_recipient=args.gpg_recipient,
            webui_container=args.webui_container,
        )
    except (BackupError, OSError, ValueError, sqlite3.Error, subprocess.SubprocessError) as exc:
        print(f"backup failed: {exc}", file=sys.stderr)
        return 2
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
