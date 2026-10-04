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

from services.engineering.agents import (
    DEFAULT_AGENT_CONFIG,
    AgentConfigError,
    AgentRegistry,
)
from services.engineering.change_snapshot import ChangeSnapshotStore, SnapshotError
from services.engineering.continuous import ContinuousEngineeringRunner
from services.engineering.delegation import (
    children_of,
    descendants_of,
    make_child_task,
    task_lineage,
)
from services.engineering.evidence import EvidenceExporter
from services.engineering.hardware import detect_hardware
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.mcp import (
    DEFAULT_CONFIG as DEFAULT_MCP_CONFIG,
    MCPError,
    call_server_tool,
    list_server_tools,
    load_config as load_mcp_config,
    split_qualified_tool,
)
from services.engineering.loop import WorkItem, WorkKind
from services.engineering.models import Checkpoint, EngineeringTask, TaskRisk, TaskStatus
from services.engineering.reconcile import QueueReconciler
from services.engineering.runtime import EngineeringRuntime, ProviderClient
from services.engineering.snapshot import RepositorySnapshotter
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.tools import list_tools
from services.engineering.tui import run_tui
from services.model_catalog.selector import (
    engineering_model_ladder,
    select_engineering_alias,
    snapshot_budget_for_context,
)


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
    agent_config: str | Path = DEFAULT_AGENT_CONFIG,
) -> EngineeringRuntime:
    env = load_env(ROOT / ".env")
    key = env.get("PROVIDER_CLIENT_KEY", os.environ.get("PROVIDER_CLIENT_KEY", ""))
    if not key:
        raise RuntimeError("PROVIDER_CLIENT_KEY is missing; run make install first")
    provider_port = env.get("PROVIDER_PORT", os.environ.get("PROVIDER_PORT", "8080"))
    configured_model = env.get("ZEAZ_ENGINEERING_MODEL", "auto").strip() or "auto"
    profile = detect_hardware()
    context_length = int(env.get("ZEAZ_OLLAMA_CONTEXT_LENGTH", "4096") or 4096)
    ladder: tuple[str, ...] = ()
    if configured_model.lower() == "auto":
        ranked = select_engineering_alias(
            env,
            hardware_profile=profile.profile,
            ram_available_gb=profile.ram_available_gb,
        )
        configured_model = ranked.candidate.alias
        ladder = engineering_model_ladder(
            env,
            hardware_profile=profile.profile,
            ram_available_gb=profile.ram_available_gb,
        )
        if progress:
            progress(
                f"[engineering] MODEL_SELECT alias={configured_model} "
                f"model={ranked.candidate.id} score={ranked.score} "
                f"fallback={','.join(ladder[1:]) if len(ladder) > 1 else 'none'} "
                f"reasons={','.join(ranked.reasons)}"
            )
    else:
        ladder = (configured_model,)

    snapshot_budget = snapshot_budget_for_context(context_length)
    if progress:
        progress(
            f"[engineering] CONTEXT_POLICY ctx={context_length} "
            f"snapshot_budget={snapshot_budget}"
        )

    return EngineeringRuntime(
        store,
        ProviderClient(
            base_url=f"http://127.0.0.1:{provider_port}/v1",
            api_key=key,
            model=configured_model,
        ),
        progress=progress,
        snapshot_max_bytes=snapshot_budget,
        model_ladder=ladder,
        agent_registry=AgentRegistry(agent_config),
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="zwslcore engineering control plane")
    p.add_argument("--db", default=str(Path.home() / ".zwslcore/state/engineering.db"))
    p.add_argument("--ledger", default=str(Path.home() / ".zwslcore/state/continuous.json"))
    p.add_argument("--agent-config", default=str(DEFAULT_AGENT_CONFIG))
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("create")
    c.add_argument("title")
    c.add_argument("--description", default="")
    c.add_argument("--repository", default=".")
    c.add_argument("--risk", choices=[r.value for r in TaskRisk], default="medium")
    c.add_argument("--max-attempts", type=int, default=2)

    sub.add_parser("list")

    cancel = sub.add_parser("cancel")
    cancel.add_argument("task_id")
    cancel.add_argument("--reason", required=True)

    s = sub.add_parser("show")
    s.add_argument("task_id")

    ev = sub.add_parser("evidence")
    ev.add_argument("task_id")

    evs = sub.add_parser("evidence-show")
    evs.add_argument("task_id")

    evv = sub.add_parser("evidence-verify")
    evv.add_argument("task_id")

    snap_status = sub.add_parser("snapshot-status")
    snap_status.add_argument("task_id")

    undo = sub.add_parser("undo")
    undo.add_argument("task_id")

    redo = sub.add_parser("redo")
    redo.add_argument("task_id")

    snap = sub.add_parser("snapshot")
    snap.add_argument("--repository", default=".")

    sub.add_parser("profile")
    sub.add_parser("agents")
    sub.add_parser("tools")

    policy = sub.add_parser("policy-check")
    policy.add_argument("agent")
    policy.add_argument("permission")
    policy.add_argument("pattern", nargs="?", default="*")

    mcp_status = sub.add_parser("mcp-status")
    mcp_status.add_argument("--config", default=str(DEFAULT_MCP_CONFIG))

    mcp_tools = sub.add_parser("mcp-tools")
    mcp_tools.add_argument("server", nargs="?")
    mcp_tools.add_argument("--config", default=str(DEFAULT_MCP_CONFIG))

    mcp_call = sub.add_parser("mcp-call")
    mcp_call.add_argument("tool")
    mcp_call.add_argument("--json", default="{}")
    mcp_call.add_argument("--config", default=str(DEFAULT_MCP_CONFIG))

    delegate = sub.add_parser("delegate")
    delegate.add_argument("parent_task_id")
    delegate.add_argument("title")
    delegate.add_argument("--description", default="")
    delegate.add_argument(
        "--agent",
        default="general",
    )
    delegate.add_argument("--kind", choices=[kind.value for kind in WorkKind], default="IMPLEMENT_FEATURE")
    delegate.add_argument("--risk", choices=[r.value for r in TaskRisk], default=None)
    delegate.add_argument("--priority", type=int, default=50)
    delegate.add_argument("--max-attempts", type=int, default=2)
    delegate.add_argument("--validate", action="append", default=[])
    delegate.add_argument("--allow-path", action="append", default=[])
    delegate.add_argument("--validation-mode", choices=["strict", "delta"], default="strict")

    children = sub.add_parser("children")
    children.add_argument("task_id")

    lineage = sub.add_parser("lineage")
    lineage.add_argument("task_id")

    tui = sub.add_parser("tui")
    tui.add_argument("--interval", type=float, default=2.0)
    tui.add_argument("--once", action="store_true")
    tui.add_argument("--no-color", action="store_true")
    tui.add_argument("--limit", type=int, default=12)

    r = sub.add_parser("run")
    r.add_argument("task_id")
    r.add_argument("--validate", action="append", default=[])
    r.add_argument("--allow-path", action="append", default=[])
    r.add_argument("--commit", action="store_true")
    r.add_argument("--validation-mode", choices=["strict", "delta"], default="strict")
    r.add_argument("--agent", default="build")

    resume = sub.add_parser("resume")
    resume.add_argument("task_id")
    resume.add_argument("--validate", action="append", default=[])
    resume.add_argument("--allow-path", action="append", default=[])
    commit_group = resume.add_mutually_exclusive_group()
    commit_group.add_argument("--commit", action="store_true")
    commit_group.add_argument("--no-commit", action="store_true")
    resume.add_argument("--validation-mode", choices=["strict", "delta"], default=None)
    resume.add_argument("--agent", default=None)

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
    wa.add_argument("--agent", default="build")

    sub.add_parser("work-list")

    reconcile = sub.add_parser("reconcile")
    reconcile.add_argument("--apply", action="store_true")

    enqueue = sub.add_parser("enqueue-task")
    enqueue.add_argument("task_id")
    enqueue.add_argument("--kind", choices=[kind.value for kind in WorkKind], default="REPAIR")
    enqueue.add_argument("--priority", type=int, default=50)
    enqueue.add_argument("--max-attempts", type=int, default=None)
    enqueue.add_argument("--validate", action="append", default=[])
    enqueue.add_argument("--allow-path", action="append", default=[])
    enqueue.add_argument("--commit", action="store_true")
    enqueue.add_argument("--validation-mode", choices=["strict", "delta"], default=None)
    enqueue.add_argument("--agent", default=None)

    ws = sub.add_parser("work-status")
    ws.add_argument("fingerprint", nargs="?")

    cont = sub.add_parser("continuous")
    cont.add_argument("--max-iterations", type=int, default=12)
    cont.add_argument("--retry-blocked", action="store_true")

    recover = sub.add_parser("recover")
    recover.add_argument("--max-iterations", type=int, default=4)

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

    if args.command == "cancel":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        if task.status == TaskStatus.SUCCEEDED:
            print("refusing to cancel a succeeded task", file=sys.stderr)
            return 2
        if task.status == TaskStatus.CANCELLED:
            print(json.dumps({
                "task_id": task.id,
                "status": task.status.value,
                "idempotent": True,
            }, indent=2))
            return 0

        previous_status = task.status.value
        previous_attempts = task.attempts
        reason = args.reason.strip()
        if not reason:
            print("cancellation reason must not be empty", file=sys.stderr)
            return 2

        task.status = TaskStatus.CANCELLED
        task.last_error = f"cancelled: {reason}"[:2000]
        history = list(task.metadata.get("cancellation_history") or [])
        history.append({
            "at": time.time(),
            "reason": reason,
            "previous_status": previous_status,
            "previous_attempts": previous_attempts,
        })
        task.metadata["cancellation_history"] = history[-20:]
        store.save_task(task)
        store.save_checkpoint(
            Checkpoint(
                task_id=task.id,
                phase="CANCELLED",
                payload={
                    "reason": reason,
                    "previous_status": previous_status,
                    "previous_attempts": previous_attempts,
                },
            )
        )

        ledger = JsonContinuousLedger(args.ledger)
        linked = []
        for record in ledger.records():
            if record.get("task_id") != task.id:
                continue
            ledger.update(
                record["fingerprint"],
                state="CANCELLED",
                attempts=task.attempts,
                last_error=task.last_error,
            )
            linked.append(record["fingerprint"])

        exporter = EvidenceExporter(store)
        path, digest = exporter.export(task)
        task.metadata["evidence_path"] = str(path)
        task.metadata["evidence_sha256"] = digest
        store.save_task(task)

        print(json.dumps({
            "task_id": task.id,
            "status": task.status.value,
            "previous_status": previous_status,
            "reason": reason,
            "linked_work_items": linked,
            "evidence_path": str(path),
            "evidence_sha256": digest,
        }, indent=2))
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

    if args.command in {"snapshot-status", "undo", "redo"}:
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        if not task.worktree_path:
            print("task has no managed worktree", file=sys.stderr)
            return 2

        snapshots = ChangeSnapshotStore()
        try:
            if args.command == "snapshot-status":
                value = snapshots.status(task.id)
            elif args.command == "undo":
                value = snapshots.undo(task.id, task.worktree_path)
                task.metadata["change_snapshot"] = {
                    "head": value["head"],
                    "patch_sha256": value["patch_sha256"],
                    "patch_bytes": value["patch_bytes"],
                    "state": value["state"],
                }
                store.save_task(task)
            else:
                value = snapshots.redo(task.id, task.worktree_path)
                task.metadata["change_snapshot"] = {
                    "head": value["head"],
                    "patch_sha256": value["patch_sha256"],
                    "patch_bytes": value["patch_bytes"],
                    "state": value["state"],
                }
                store.save_task(task)
        except SnapshotError as exc:
            print(f"snapshot: {exc}", file=sys.stderr)
            return 1

        print(json.dumps({
            "task_id": task.id,
            "state": value["state"],
            "head": value["head"],
            "patch_sha256": value["patch_sha256"],
            "patch_bytes": value["patch_bytes"],
            "patch_path": value["patch_path"],
        }, indent=2))
        return 0

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

    if args.command == "agents":
        try:
            registry = AgentRegistry(args.agent_config)
        except AgentConfigError as exc:
            print(f"agent config: {exc}", file=sys.stderr)
            return 1
        print(json.dumps([
            {
                "name": agent.name,
                "description": agent.description,
                "mode": agent.mode,
                "hidden": agent.hidden,
                "source": agent.source,
                "custom_prompt": bool(agent.prompt),
                "permissions": [
                    {
                        "permission": rule.permission,
                        "pattern": rule.pattern,
                        "action": rule.action,
                    }
                    for rule in agent.rules
                ],
            }
            for agent in registry.list()
        ], indent=2))
        return 0

    if args.command == "tools":
        print(json.dumps([dataclasses.asdict(item) for item in list_tools()], indent=2))
        return 0

    if args.command == "policy-check":
        try:
            agent = AgentRegistry(args.agent_config).get(args.agent)
        except (AgentConfigError, ValueError) as exc:
            print(f"agent config: {exc}", file=sys.stderr)
            return 1
        decision = agent.decide(args.permission, args.pattern)
        print(json.dumps({
            "agent": agent.name,
            "permission": args.permission,
            "pattern": args.pattern,
            "action": decision,
        }, indent=2))
        return 0 if decision == "allow" else 1

    if args.command == "mcp-status":
        try:
            servers = load_mcp_config(args.config)
        except MCPError as exc:
            print(f"mcp: {exc}", file=sys.stderr)
            return 1
        print(json.dumps([
            {
                "name": item.name,
                "enabled": item.enabled,
                "command": list(item.command),
                "cwd": item.cwd,
                "inherit_env": list(item.inherit_env),
                "timeout_seconds": item.timeout_seconds,
                "protocol_version": item.protocol_version,
            }
            for item in sorted(servers.values(), key=lambda item: item.name)
        ], indent=2))
        return 0

    if args.command == "mcp-tools":
        try:
            servers = load_mcp_config(args.config)
            selected = (
                {args.server: servers[args.server]}
                if args.server
                else servers
            )
        except KeyError:
            print(f"mcp server not found: {args.server}", file=sys.stderr)
            return 2
        except MCPError as exc:
            print(f"mcp: {exc}", file=sys.stderr)
            return 1

        output = []
        failures = []
        for name, server in sorted(selected.items()):
            if not server.enabled:
                output.append({"server": name, "status": "disabled", "tools": []})
                continue
            try:
                defs = list_server_tools(server)
            except MCPError as exc:
                failures.append(name)
                output.append({"server": name, "status": "failed", "error": str(exc), "tools": []})
                continue
            output.append({
                "server": name,
                "status": "connected",
                "tools": [
                    {
                        "name": tool.name,
                        "qualified_name": tool.qualified_name,
                        "description": tool.description,
                        "input_schema": tool.input_schema,
                    }
                    for tool in defs
                ],
            })
        print(json.dumps(output, indent=2))
        return 1 if failures else 0

    if args.command == "mcp-call":
        try:
            server_name, tool_name = split_qualified_tool(args.tool)
            servers = load_mcp_config(args.config)
            server = servers.get(server_name)
            if server is None:
                print(f"mcp server not found: {server_name}", file=sys.stderr)
                return 2
            if not server.enabled:
                print(f"mcp server is disabled: {server_name}", file=sys.stderr)
                return 2
            arguments = json.loads(args.json)
            if not isinstance(arguments, dict):
                raise MCPError("--json must decode to an object")
            result = call_server_tool(server, tool_name, arguments)
        except (MCPError, json.JSONDecodeError) as exc:
            print(f"mcp call failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result, indent=2, default=str))
        return 0

    if args.command == "delegate":
        parent = store.get_task(args.parent_task_id)
        if not parent:
            print("parent task not found", file=sys.stderr)
            return 2
        if parent.status in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}:
            print(
                f"refusing to delegate from terminal parent task: {parent.status.value}",
                file=sys.stderr,
            )
            return 2

        risk = TaskRisk(args.risk) if args.risk else parent.risk
        try:
            registry = AgentRegistry(args.agent_config)
            child = make_child_task(
                parent,
                title=args.title,
                description=args.description,
                agent_name=args.agent,
                risk=risk,
                max_attempts=max(1, args.max_attempts),
                agent_registry=registry,
            )
        except ValueError as exc:
            print(f"delegation refused: {exc}", file=sys.stderr)
            return 2

        validators = args.validate or ["git diff --check"]
        child.metadata["run_config"] = {
            "validators": list(validators),
            "allowed_paths": list(args.allow_path),
            "commit": False,
            "validation_mode": args.validation_mode,
            "agent": args.agent,
        }
        store.save_task(child)

        item = WorkItem(
            title=child.title,
            kind=WorkKind(args.kind),
            payload={
                "description": child.description,
                "repository": child.repository,
                "risk": child.risk.value,
                "validators": validators,
                "allowed_paths": args.allow_path,
                "commit": False,
                "validation_mode": args.validation_mode,
                "agent": args.agent,
                "parent_task_id": parent.id,
                "root_task_id": child.metadata["root_task_id"],
                "delegation_depth": child.metadata["delegation_depth"],
            },
            priority=args.priority,
            max_attempts=child.max_attempts,
        )
        ledger = JsonContinuousLedger(args.ledger)
        record = ledger.register(item)
        record = ledger.update(
            item.fingerprint,
            task_id=child.id,
            state="PENDING",
            attempts=0,
            last_error="",
        )

        children_state = dict(parent.metadata.get("subagent_children") or {})
        children_state[child.id] = {
            "status": child.status.value,
            "agent": args.agent,
            "attempts": 0,
            "last_error": "",
            "evidence_path": "",
        }
        parent.metadata["subagent_children"] = children_state
        store.save_task(parent)

        print(json.dumps({
            "parent_task_id": parent.id,
            "child_task_id": child.id,
            "fingerprint": record["fingerprint"],
            "agent": args.agent,
            "root_task_id": child.metadata["root_task_id"],
            "delegation_depth": child.metadata["delegation_depth"],
            "state": record["state"],
        }, indent=2))
        return 0

    if args.command == "children":
        parent = store.get_task(args.task_id)
        if not parent:
            print("task not found", file=sys.stderr)
            return 2
        output = [
            {
                "id": task.id,
                "title": task.title,
                "status": task.status.value,
                "agent": task.metadata.get("delegated_agent", ""),
                "depth": task.metadata.get("delegation_depth", 0),
                "attempts": task.attempts,
                "evidence_path": task.metadata.get("evidence_path", ""),
            }
            for task in children_of(store.list_tasks(), parent.id)
        ]
        print(json.dumps(output, indent=2))
        return 0

    if args.command == "lineage":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        lineage_info = task_lineage(task)
        root = store.get_task(lineage_info.root_task_id)
        descendants = descendants_of(store.list_tasks(), lineage_info.root_task_id)
        print(json.dumps({
            "selected_task_id": task.id,
            "root_task_id": lineage_info.root_task_id,
            "parent_task_id": lineage_info.parent_task_id,
            "depth": lineage_info.depth,
            "root": (
                {
                    "id": root.id,
                    "title": root.title,
                    "status": root.status.value,
                }
                if root else None
            ),
            "descendants": [
                {
                    "id": item.id,
                    "parent_task_id": item.metadata.get("parent_task_id"),
                    "title": item.title,
                    "status": item.status.value,
                    "agent": item.metadata.get("delegated_agent", ""),
                    "depth": item.metadata.get("delegation_depth", 0),
                }
                for item in descendants
            ],
        }, indent=2))
        return 0

    if args.command == "run":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        try:
            result = build_runtime(store, progress=emit_progress, agent_config=args.agent_config).run(
                task,
                validators=args.validate or ["git diff --check"],
                allowed_paths=set(args.allow_path) if args.allow_path else None,
                commit=args.commit,
                validation_mode=args.validation_mode,
                agent_name=args.agent,
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
        agent_name = args.agent or str(config.get("agent", "build"))

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
            result = build_runtime(store, progress=emit_progress, agent_config=args.agent_config).run(
                task,
                validators=validators,
                allowed_paths=set(allowed) if allowed else None,
                commit=commit,
                resume=True,
                validation_mode=validation_mode,
                agent_name=agent_name,
            )
        except Exception as exc:
            print(f"engineering resume failed: {exc}", file=sys.stderr)
            return 1
        print(f"{result.id}\t{result.status.value}\t{result.branch_name}\t{result.worktree_path}")
        return 0

    ledger = JsonContinuousLedger(args.ledger)

    if args.command == "tui":
        env = load_env(ROOT / ".env")
        return run_tui(
            store,
            ledger,
            env=env,
            interval=max(0.25, args.interval),
            once=args.once,
            color=False if args.no_color else None,
            limit=max(1, args.limit),
        )

    if args.command == "work-add":
        try:
            AgentRegistry(args.agent_config).get(args.agent)
        except (AgentConfigError, ValueError) as exc:
            print(f"agent config: {exc}", file=sys.stderr)
            return 2
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
                "agent": args.agent,
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

    if args.command == "reconcile":
        reconciler = QueueReconciler(store, ledger)
        report = reconciler.apply_safe() if args.apply else reconciler.inspect()
        print(json.dumps({
            "applied": [dataclasses.asdict(item) for item in report.applied],
            "findings": [dataclasses.asdict(item) for item in report.findings],
            "orphan_tasks": list(report.orphan_tasks),
        }, indent=2))
        return 0 if not any(item.safe_fix for item in report.findings) else 1

    if args.command == "enqueue-task":
        task = store.get_task(args.task_id)
        if not task:
            print("task not found", file=sys.stderr)
            return 2
        if task.status in {TaskStatus.SUCCEEDED, TaskStatus.CANCELLED}:
            print(f"refusing to enqueue terminal task: {task.status.value}", file=sys.stderr)
            return 2

        config = dict(task.metadata.get("run_config") or {})
        validators = args.validate or list(config.get("validators") or ["git diff --check"])
        allowed_paths = args.allow_path or list(config.get("allowed_paths") or [])
        commit = args.commit or bool(config.get("commit", False))
        validation_mode = args.validation_mode or str(config.get("validation_mode", "strict"))
        agent_name = args.agent or str(config.get("agent", "build"))
        try:
            AgentRegistry(args.agent_config).get(agent_name)
        except (AgentConfigError, ValueError) as exc:
            print(f"agent config: {exc}", file=sys.stderr)
            return 2
        max_attempts = args.max_attempts or task.max_attempts or 2
        item = WorkItem(
            title=task.title,
            kind=WorkKind(args.kind),
            payload={
                "description": task.description,
                "repository": str(Path(task.repository).resolve()),
                "risk": task.risk.value,
                "validators": validators,
                "allowed_paths": allowed_paths,
                "commit": commit,
                "validation_mode": validation_mode,
                "agent": agent_name,
            },
            priority=args.priority,
            max_attempts=max(1, int(max_attempts)),
        )
        record = ledger.register(item)
        record = ledger.update(
            item.fingerprint,
            task_id=task.id,
            state="PENDING",
            attempts=task.attempts if task.status in {TaskStatus.BLOCKED, TaskStatus.FAILED} else 0,
            last_error=task.last_error,
        )
        print(json.dumps(record, indent=2))
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

    if args.command in {"continuous", "recover"}:
        try:
            if args.command == "recover":
                report = QueueReconciler(store, ledger).apply_safe()
                if report.applied:
                    emit_progress(
                        f"[continuous] RECONCILE applied={len(report.applied)} "
                        f"orphans={len(report.orphan_tasks)}"
                    )
                elif report.orphan_tasks:
                    emit_progress(
                        f"[continuous] RECONCILE applied=0 "
                        f"orphans={len(report.orphan_tasks)}"
                    )
            runner = ContinuousEngineeringRunner(
                store,
                ledger,
                build_runtime(store, progress=emit_progress, agent_config=args.agent_config),
                progress=emit_progress,
            )
            result = runner.run(
                max_iterations=max(1, args.max_iterations),
                retry_blocked=True if args.command == "recover" else args.retry_blocked,
            )
        except Exception as exc:
            label = "engineering recovery" if args.command == "recover" else "continuous engineering"
            print(f"{label} failed: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(dataclasses.asdict(result), indent=2))
        return 0 if not result.blocked else 1

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
