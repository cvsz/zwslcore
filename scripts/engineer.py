#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.engineering.models import EngineeringTask, TaskRisk
from services.engineering.runtime import EngineeringRuntime, ProviderClient
from services.engineering.snapshot import RepositorySnapshotter
from services.engineering.store import SQLiteEngineeringStore


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


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="zwslcore engineering control plane")
    p.add_argument("--db", default=str(Path.home() / ".zwslcore/state/engineering.db"))
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

    snap = sub.add_parser("snapshot")
    snap.add_argument("--repository", default=".")

    r = sub.add_parser("run")
    r.add_argument("task_id")
    r.add_argument("--validate", action="append", default=[])
    r.add_argument("--allow-path", action="append", default=[])
    r.add_argument("--commit", action="store_true")
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

    if args.command == "snapshot":
        print(RepositorySnapshotter(args.repository).snapshot())
        return 0

    if args.command == "run":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        env = load_env(ROOT / ".env")
        key = env.get("PROVIDER_CLIENT_KEY", os.environ.get("PROVIDER_CLIENT_KEY", ""))
        if not key:
            print("PROVIDER_CLIENT_KEY is missing; run make install first", file=sys.stderr)
            return 2
        provider_port = env.get("PROVIDER_PORT", os.environ.get("PROVIDER_PORT", "8080"))
        runtime = EngineeringRuntime(
            store,
            ProviderClient(
                base_url=f"http://127.0.0.1:{provider_port}/v1",
                api_key=key,
                model=env.get("ZEAZ_ENGINEERING_MODEL", "zeaz-local"),
            ),
        )
        try:
            result = runtime.run(
                task,
                validators=args.validate or ["git diff --check"],
                allowed_paths=set(args.allow_path) if args.allow_path else None,
                commit=args.commit,
            )
        except Exception as exc:
            print(f"engineering run failed: {exc}", file=sys.stderr)
            return 1
        print(f"{result.id}\t{result.status.value}\t{result.branch_name}\t{result.worktree_path}")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
