from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from .permissions import PermissionRule, evaluate_permission

DEFAULT_AGENT_CONFIG = Path.home() / ".zwslcore" / "agents.json"
VALID_MODES = {"primary", "subagent"}


@dataclasses.dataclass(frozen=True)
class AgentProfile:
    name: str
    description: str
    mode: str
    hidden: bool
    rules: tuple[PermissionRule, ...]
    prompt: str = ""
    source: str = "builtin"

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


class AgentConfigError(ValueError):
    pass


class AgentRegistry:
    def __init__(self, path: str | Path | None = DEFAULT_AGENT_CONFIG) -> None:
        self.path = Path(path).expanduser() if path is not None else None
        self._agents = dict(_BUILTINS)
        if self.path is not None and self.path.exists():
            self._load(self.path)

    def _load(self, path: Path) -> None:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise AgentConfigError(f"unable to read agent config {path}: {exc}") from exc
        if not isinstance(payload, dict):
            raise AgentConfigError("agent config root must be an object")
        raw_agents = payload.get("agents", {})
        if not isinstance(raw_agents, dict):
            raise AgentConfigError("agent config agents must be an object")

        for name, raw in raw_agents.items():
            if not isinstance(name, str) or not name.strip():
                raise AgentConfigError("custom agent names must be non-empty strings")
            if name in _BUILTINS:
                raise AgentConfigError(
                    f"custom agent {name!r} collides with a built-in profile"
                )
            if not isinstance(raw, dict):
                raise AgentConfigError(f"custom agent {name!r} must be an object")

            enabled = raw.get("enabled", True)
            if type(enabled) is not bool:
                raise AgentConfigError(f"agent {name!r} enabled must be boolean")
            if not enabled:
                continue

            base_name = raw.get("extends", "plan")
            if not isinstance(base_name, str) or base_name not in _BUILTINS:
                raise AgentConfigError(
                    f"agent {name!r} extends must name a built-in profile"
                )
            base = _BUILTINS[base_name]

            mode = raw.get("mode", base.mode)
            if mode not in VALID_MODES:
                raise AgentConfigError(
                    f"agent {name!r} mode must be one of {sorted(VALID_MODES)}"
                )
            hidden = raw.get("hidden", base.hidden)
            if type(hidden) is not bool:
                raise AgentConfigError(f"agent {name!r} hidden must be boolean")

            description = raw.get("description", base.description)
            prompt = raw.get("prompt", "")
            if not isinstance(description, str) or not isinstance(prompt, str):
                raise AgentConfigError(
                    f"agent {name!r} description and prompt must be strings"
                )
            if len(prompt.encode("utf-8")) > 16 * 1024:
                raise AgentConfigError(f"agent {name!r} prompt exceeds 16 KiB")

            rules = list(base.rules)
            raw_rules = raw.get("permissions", [])
            if not isinstance(raw_rules, list):
                raise AgentConfigError(f"agent {name!r} permissions must be a list")
            for index, item in enumerate(raw_rules):
                if not isinstance(item, dict):
                    raise AgentConfigError(
                        f"agent {name!r} permission #{index} must be an object"
                    )
                permission = item.get("permission")
                pattern = item.get("pattern", "*")
                action = item.get("action", "ask")
                if not all(isinstance(value, str) for value in (permission, pattern, action)):
                    raise AgentConfigError(
                        f"agent {name!r} permission #{index} fields must be strings"
                    )
                try:
                    rules.append(PermissionRule(permission, pattern, action))
                except ValueError as exc:
                    raise AgentConfigError(
                        f"agent {name!r} permission #{index}: {exc}"
                    ) from exc

            self._agents[name] = AgentProfile(
                name=name,
                description=description,
                mode=mode,
                hidden=hidden,
                rules=tuple(rules),
                prompt=prompt,
                source=str(path),
            )

    def get(self, name: str) -> AgentProfile:
        try:
            return self._agents[name]
        except KeyError as exc:
            raise ValueError(
                f"unknown agent {name!r}; available={','.join(sorted(self._agents))}"
            ) from exc

    def list(self, *, include_hidden: bool = False) -> tuple[AgentProfile, ...]:
        return tuple(
            self._agents[name]
            for name in sorted(self._agents)
            if include_hidden or not self._agents[name].hidden
        )


_DEFAULT_REGISTRY = AgentRegistry(path=None)


def get_agent(name: str) -> AgentProfile:
    return _DEFAULT_REGISTRY.get(name)


def list_agents() -> tuple[AgentProfile, ...]:
    return _DEFAULT_REGISTRY.list()
