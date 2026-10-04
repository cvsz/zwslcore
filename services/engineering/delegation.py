from __future__ import annotations

import time
from dataclasses import dataclass

from .agents import get_agent
from .models import EngineeringTask, TaskRisk


MAX_DELEGATION_DEPTH = 4


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
) -> EngineeringTask:
    agent = get_agent(agent_name)
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
