from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable

from .agents import AgentRegistry
from .models import EngineeringTask, TaskRisk


MAX_DELEGATION_DEPTH = 4


def delegated_allowed_paths(
    parent: EngineeringTask,
    requested_paths: Iterable[str],
) -> list[str]:
    """Inherit the parent's scope and reject delegated scope expansion."""
    run_config = parent.metadata.get("run_config")
    parent_paths = _normalize_allowed_paths(
        run_config.get("allowed_paths", ())
        if isinstance(run_config, dict)
        else ()
    )
    child_paths = _normalize_allowed_paths(requested_paths)

    if not parent_paths:
        return sorted(child_paths)
    if not child_paths:
        return sorted(parent_paths)

    outside = sorted(
        path
        for path in child_paths
        if not any(_is_within(path, allowed) for allowed in parent_paths)
    )
    if outside:
        raise ValueError(
            "delegated allowed paths exceed parent scope: " + ", ".join(outside)
        )
    return sorted(child_paths)


def _normalize_allowed_paths(paths: Iterable[str] | None) -> set[str]:
    if paths is None:
        return set()
    if isinstance(paths, str):
        values = [paths]
    else:
        values = list(paths)

    normalized: set[str] = set()
    for value in values:
        if not isinstance(value, str):
            raise ValueError("allowed paths must be strings")
        raw = value.strip()
        path = PurePosixPath(raw)
        if (
            not raw
            or path.is_absolute()
            or path == PurePosixPath(".")
            or ".." in path.parts
        ):
            raise ValueError(
                f"allowed path must be a safe repository-relative path: {raw!r}"
            )
        normalized.add(path.as_posix())
    return normalized


def _is_within(path: str, allowed: str) -> bool:
    path_parts = PurePosixPath(path).parts
    allowed_parts = PurePosixPath(allowed).parts
    return path_parts[: len(allowed_parts)] == allowed_parts


@dataclass(frozen=True)
class Lineage:
    root_task_id: str
    parent_task_id: str | None
    depth: int


def task_lineage(task: EngineeringTask) -> Lineage:
    parent = str(task.metadata.get("parent_task_id") or "").strip() or None
    root = str(task.metadata.get("root_task_id") or task.id).strip() or task.id
    depth = int(task.metadata.get("delegation_depth", 0) or 0)
    return Lineage(root, parent, depth)


def make_child_task(
    parent: EngineeringTask,
    *,
    title: str,
    description: str,
    agent_name: str,
    risk: TaskRisk | None = None,
    max_attempts: int = 2,
    agent_registry: AgentRegistry | None = None,
) -> EngineeringTask:
    registry = agent_registry or AgentRegistry(path=None)
    agent = registry.get(agent_name)
    if agent.mode != "subagent":
        raise ValueError(
            f"agent {agent_name!r} is not a subagent; choose one of: explore, general, review"
        )

    lineage = task_lineage(parent)
    depth = lineage.depth + 1
    if depth > MAX_DELEGATION_DEPTH:
        raise ValueError(
            f"delegation depth {depth} exceeds maximum {MAX_DELEGATION_DEPTH}"
        )

    child = EngineeringTask(
        title=title,
        description=description,
        repository=parent.repository,
        risk=risk or parent.risk,
        max_attempts=max(1, int(max_attempts)),
    )
    child.metadata.update(
        {
            "parent_task_id": parent.id,
            "root_task_id": lineage.root_task_id,
            "delegation_depth": depth,
            "delegated_at": time.time(),
            "delegated_agent": agent.name,
        }
    )
    return child


def children_of(tasks: list[EngineeringTask], parent_task_id: str) -> list[EngineeringTask]:
    return sorted(
        [
            task
            for task in tasks
            if str(task.metadata.get("parent_task_id") or "") == parent_task_id
        ],
        key=lambda task: (task.created_at, task.id),
    )


def descendants_of(tasks: list[EngineeringTask], root_task_id: str) -> list[EngineeringTask]:
    return sorted(
        [
            task
            for task in tasks
            if str(task.metadata.get("root_task_id") or task.id) == root_task_id
            and task.id != root_task_id
        ],
        key=lambda task: (int(task.metadata.get("delegation_depth", 0) or 0), task.created_at, task.id),
    )
