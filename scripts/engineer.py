#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.engineering.continuous import ContinuousEngineeringRunner
from services.engineering.evidence import EvidenceExporter
from services.engineering.hardware import detect_hardware
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.loop import WorkItem, WorkKind
from services.engineering.models import EngineeringTask, TaskRisk, TaskStatus
from services.engineering.runtime import EngineeringRuntime, ProviderClient
from services.engineering.snapshot import RepositorySnapshotter
from services.engineering.store import SQLiteEngineeringStore
from services.model_catalog.selector import select_engineering_alias


def load_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value
    return values


def emit_progress(message: str) -> None:
    print(message, flush=True)


def build_runtime(
    store: SQLiteEngineeringStore,
    *,
    progress=None,
) -> EngineeringRuntime:
    env = load_env(ROOT / ".env")
    key = env.get("PROVIDER_CLIENT_KEY", os.environ.get("PROVIDER_CLIENT_KEY", ""))
    if not key:
        raise RuntimeError("PROVIDER_CLIENT_KEY is missing; run make install first")
    provider_port = env.get("PROVIDER_PORT", os.environ.get("PROVIDER_PORT", "8080"))
    configured_model = env.get("ZEAZ_ENGINEERING_MODEL", "auto").strip() or "auto"
    if configured_model.lower() == "auto":
        profile = detect_hardware()
        ranked = select_engineering_alias(
            env,
            hardware_profile=profile.profile,
            ram_available_gb=profile.ram_available_gb,
        )
        configured_model = ranked.candidate.alias
        if progress:
            progress(
                f"[engineering] MODEL_SELECT alias={configured_model} "
                f"model={ranked.candidate.id} score={ranked.score} "
                f"reasons={','.join(ranked.reasons)}"
            )

    return EngineeringRuntime(
        store,
        ProviderClient(
            base_url=f"http://127.0.0.1:{provider_port}/v1",
            api_key=key,
            model=configured_model,
        ),
        progress=progress,
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="zwslcore engineering control plane")
    p.add_argument("--db", default=str(Path.home() / ".zwslcore/state/engineering.db"))
    p.add_argument("--ledger", default=str(Path.home() / ".zwslcore/state/continuous.json"))
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create")
    c.add_argument("title")
    c.add_argument("--description", default="")
    c.add_argument("--repository", default=".")
    c.add_argument("--risk", choices=[r.value for r in TaskRisk], default="medium")
    c.add_argument("--max-attempts", type=int, default=2)

    sub.add_parser("list")

    s = sub.add_parser("show")
    s.add_argument("task_id")

    ev = sub.add_parser("evidence")
    ev.add_argument("task_id")

    evs = sub.add_parser("evidence-show")
    evs.add_argument("task_id")

    evv = sub.add_parser("evidence-verify")
    evv.add_argument("task_id")

    snap = sub.add_parser("snapshot")
    snap.add_argument("--repository", default=".")

    sub.add_parser("profile")

    r = sub.add_parser("run")
    r.add_argument("task_id")
    r.add_argument("--validate", action="append", default=[])
    r.add_argument("--allow-path", action="append", default=[])
    r.add_argument("--commit", action="store_true")
    r.add_argument("--validation-mode", choices=["strict", "delta"], default="strict")

    resume = sub.add_parser("resume")
    resume.add_argument("task_id")
    resume.add_argument("--validate", action="append", default=[])
    resume.add_argument("--allow-path", action="append", default=[])
    commit_group = resume.add_mutually_exclusive_group()
    commit_group.add_argument("--commit", action="store_true")
    commit_group.add_argument("--no-commit", action="store_true")
    resume.add_argument("--validation-mode", choices=["strict", "delta"], default=None)

    wa = sub.add_parser("work-add")
    wa.add_argument("title")
    wa.add_argument("--kind", choices=[kind.value for kind in WorkKind], default="IMPLEMENT_FEATURE")
    wa.add_argument("--description", default="")
    wa.add_argument("--repository", default=".")
    wa.add_argument("--risk", choices=[r.value for r in TaskRisk], default="medium")
    wa.add_argument("--priority", type=int, default=50)
    wa.add_argument("--max-attempts", type=int, default=2)
    wa.add_argument("--validate", action="append", default=[])
    wa.add_argument("--allow-path", action="append", default=[])
    wa.add_argument("--commit", action="store_true")
    wa.add_argument("--validation-mode", choices=["strict", "delta"], default="strict")

    sub.add_parser("work-list")

    ws = sub.add_parser("work-status")
    ws.add_argument("fingerprint", nargs="?")

    cont = sub.add_parser("continuous")
    cont.add_argument("--max-iterations", type=int, default=12)
    cont.add_argument("--retry-blocked", action="store_true")

    return p


def main() -> int:
    args = parser().parse_args()
    store = SQLiteEngineeringStore(args.db)

    if args.command == "create":
        task = EngineeringTask(
            title=args.title,
            description=args.description,
            repository=str(Path(args.repository).resolve()),
            risk=TaskRisk(args.risk),
            max_attempts=max(1, args.max_attempts),
        )
        store.save_task(task)
        print(task.id)
        return 0

    if args.command == "list":
        for task in store.list_tasks():
            print(f"{task.id}\t{task.status.value}\t{task.risk.value}\t{task.title}")
        return 0

    if args.command == "show":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        checkpoint = store.latest_checkpoint(task.id)
        print(json.dumps({
            "task": task.__dict__ | {
                "risk": task.risk.value,
                "status": task.status.value,
                "push_policy": task.push_policy.value,
            },
            "latest_checkpoint": checkpoint.__dict__ if checkpoint else None,
        }, indent=2, default=str))
        return 0

    if args.command == "evidence":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        exporter = EvidenceExporter(store)
        path, digest = exporter.export(task)
        print(json.dumps({
            "task_id": task.id,
            "path": str(path),
            "sha256": digest,
            "verified": exporter.verify(task.id),
        }, indent=2))
        return 0

    if args.command == "evidence-show":
        exporter = EvidenceExporter(store)
        bundle = exporter.read(args.task_id)
        if bundle is None:
            print("evidence not found", file=sys.stderr)
            return 2
        print(json.dumps(bundle, indent=2, default=str))
        return 0

    if args.command == "evidence-verify":
        exporter = EvidenceExporter(store)
        ok = exporter.verify(args.task_id)
        print("PASS" if ok else "FAIL")
        return 0 if ok else 1

    if args.command == "snapshot":
        print(RepositorySnapshotter(args.repository).snapshot())
        return 0

    if args.command == "profile":
        profile = detect_hardware()
        print(json.dumps(
            dataclasses.asdict(profile) | {
                "recommended_models": profile.recommended_models(),
                "recommended_runtime": profile.recommended_runtime(),
            },
            indent=2,
        ))
        return 0

    if args.command == "run":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        try:
            result = build_runtime(store, progress=emit_progress).run(
                task,
                validators=args.validate or ["git diff --check"],
                allowed_paths=set(args.allow_path) if args.allow_path else None,
                commit=args.commit,
                validation_mode=args.validation_mode,
            )
        except Exception as exc:
            print(f"engineering run failed: {exc}", file=sys.stderr)
            return 1
        print(f"{result.id}\t{result.status.value}\t{result.branch_name}\t{result.worktree_path}")
        return 0

    if args.command == "resume":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        if task.status == TaskStatus.SUCCEEDED:
            print("refusing to resume a succeeded task", file=sys.stderr)
            return 2

        config = dict(task.metadata.get("run_config") or {})
        validators = args.validate or list(config.get("validators") or ["git diff --check"])
        allowed = args.allow_path or list(config.get("allowed_paths") or [])
        if args.commit:
            commit = True
        elif args.no_commit:
            commit = False
        else:
            commit = bool(config.get("commit", False))
        validation_mode = args.validation_mode or str(config.get("validation_mode", "strict"))

        history = list(task.metadata.get("resume_history") or [])
        history.append({
            "at": time.time(),
            "previous_status": task.status.value,
            "previous_attempts": task.attempts,
            "phase_cursor": task.metadata.get("phase_cursor", ""),
            "baseline_head": task.metadata.get("baseline_head", ""),
        })
        task.metadata["resume_history"] = history[-20:]
        task.attempts = 0
        task.status = TaskStatus.CREATED
        task.last_error = ""
        store.save_task(task)

        try:
            result = build_runtime(store, progress=emit_progress).run(
                task,
                validators=validators,
                allowed_paths=set(allowed) if allowed else None,
                commit=commit,
                resume=True,
                validation_mode=validation_mode,
            )
        except Exception as exc:
            print(f"engineering resume failed: {exc}", file=sys.stderr)
            return 1
        print(f"{result.id}\t{result.status.value}\t{result.branch_name}\t{result.worktree_path}")
        return 0

    ledger = JsonContinuousLedger(args.ledger)

    if args.command == "work-add":
        item = WorkItem(
            title=args.title,
            kind=WorkKind(args.kind),
            payload={
                "description": args.description,
                "repository": str(Path(args.repository).resolve()),
                "risk": args.risk,
                "validators": args.validate or ["git diff --check"],
                "allowed_paths": args.allow_path,
                "commit": args.commit,
                "validation_mode": args.validation_mode,
            },
            priority=args.priority,
            max_attempts=max(1, args.max_attempts),
        )
        record = ledger.register(item)
        print(record["fingerprint"])
        return 0

    if args.command == "work-list":
        for record in ledger.records():
            print(
                f"{record['fingerprint'][:12]}\t{record['state']}\t"
                f"{record['kind']}\t{record['priority']}\t{record['title']}"
            )
        return 0

    if args.command == "work-status":
        records = ledger.records()
        if args.fingerprint:
            matches = [
                record for record in records
                if record["fingerprint"].startswith(args.fingerprint)
            ]
            if not matches:
                print("work item not found", file=sys.stderr)
                return 2
            if len(matches) > 1:
                print("fingerprint prefix is ambiguous", file=sys.stderr)
                return 2
            records = matches

        output = []
        for record in records:
            item = dict(record)
            task_id = item.get("task_id")
            if task_id:
                task = store.get_task(task_id)
                checkpoint = store.latest_checkpoint(task_id) if task else None
                item["task"] = (
                    task.__dict__ | {
                        "risk": task.risk.value,
                        "status": task.status.value,
                        "push_policy": task.push_policy.value,
                    }
                    if task else None
                )
                item["latest_task_checkpoint"] = checkpoint.__dict__ if checkpoint else None
            output.append(item)

        print(json.dumps(output[0] if args.fingerprint else output, indent=2, default=str))
        return 0

    if args.command == "continuous":
        try:
            runner = ContinuousEngineeringRunner(
                store,
                ledger,
                build_runtime(store, progress=emit_progress),
                progress=emit_progress,
            )
            result = runner.run(
                max_iterations=max(1, args.max_iterations),
                retry_blocked=args.retry_blocked,
            )
        except Exception as exc:
            print(f"continuous engineering failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(dataclasses.asdict(result), indent=2))
        return 0 if not result.blocked else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
