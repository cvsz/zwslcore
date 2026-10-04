from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class ToolCapability:
    name: str
    permission: str
    mutates_repository: bool
    description: str


TOOLS: tuple[ToolCapability, ...] = (
    ToolCapability("snapshot", "snapshot", False, "Read bounded repository context."),
    ToolCapability("plan", "plan", False, "Create an implementation plan."),
    ToolCapability("edit", "edit", True, "Apply model-proposed file changes."),
    ToolCapability("validate", "validate", False, "Run operator-declared validators."),
    ToolCapability("review", "review", False, "Run deterministic static/security review."),
    ToolCapability("commit", "commit", True, "Create a local commit in the managed worktree."),
    ToolCapability("delegate", "delegate", False, "Delegate bounded work to a subagent."),
)


def list_tools() -> tuple[ToolCapability, ...]:
    return TOOLS


def get_tool(name: str) -> ToolCapability:
    for item in TOOLS:
        if item.name == name:
            return item
    raise ValueError(f"unknown tool capability: {name}")
