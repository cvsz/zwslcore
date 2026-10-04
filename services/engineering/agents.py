from __future__ import annotations

import dataclasses

from .permissions import PermissionRule, evaluate_permission


@dataclasses.dataclass(frozen=True)
class AgentProfile:
    name: str
    description: str
    mode: str
    hidden: bool
    rules: tuple[PermissionRule, ...]

    def decide(self, permission: str, pattern: str = "*") -> str:
        return evaluate_permission(permission, pattern, self.rules).action


_BASE = (
    PermissionRule("*", "*", "deny"),
    PermissionRule("snapshot", "*", "allow"),
    PermissionRule("plan", "*", "allow"),
    PermissionRule("review", "*", "allow"),
)

_BUILTINS: dict[str, AgentProfile] = {
    "build": AgentProfile(
        "build",
        "Default implementation agent with bounded edit/validate/commit capabilities.",
        "primary",
        False,
        _BASE + (
            PermissionRule("edit", "*", "allow"),
            PermissionRule("validate", "*", "allow"),
            PermissionRule("commit", "*", "allow"),
            PermissionRule("delegate", "*", "allow"),
        ),
    ),
    "plan": AgentProfile(
        "plan",
        "Read-only planning agent. Never edits files, runs validators, or commits.",
        "primary",
        False,
        _BASE,
    ),
    "review": AgentProfile(
        "review",
        "Read-only review agent for static/security analysis.",
        "subagent",
        False,
        _BASE,
    ),
    "explore": AgentProfile(
        "explore",
        "Read-only repository exploration agent.",
        "subagent",
        False,
        _BASE,
    ),
    "general": AgentProfile(
        "general",
        "General-purpose delegated agent with edit and validation capability but no commit.",
        "subagent",
        False,
        _BASE + (
            PermissionRule("edit", "*", "allow"),
            PermissionRule("validate", "*", "allow"),
            PermissionRule("delegate", "*", "allow"),
        ),
    ),
}


def get_agent(name: str) -> AgentProfile:
    try:
        return _BUILTINS[name]
    except KeyError as exc:
        raise ValueError(
            f"unknown agent {name!r}; available={','.join(sorted(_BUILTINS))}"
        ) from exc


def list_agents() -> tuple[AgentProfile, ...]:
    return tuple(_BUILTINS[name] for name in sorted(_BUILTINS))
