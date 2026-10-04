from __future__ import annotations

import dataclasses
import fnmatch
from typing import Iterable


VALID_ACTIONS = {"allow", "ask", "deny"}


@dataclasses.dataclass(frozen=True)
class PermissionRule:
    permission: str
    pattern: str = "*"
    action: str = "ask"

    def __post_init__(self) -> None:
        if self.action not in VALID_ACTIONS:
            raise ValueError(f"invalid permission action: {self.action}")
        if not self.permission.strip():
            raise ValueError("permission must not be empty")
        if not self.pattern:
            raise ValueError("pattern must not be empty")


@dataclasses.dataclass(frozen=True)
class PermissionDecision:
    permission: str
    pattern: str
    action: str
    matched_rule: PermissionRule | None


def evaluate_permission(
    permission: str,
    pattern: str,
    *rulesets: Iterable[PermissionRule],
) -> PermissionDecision:
    matched: PermissionRule | None = None
    for rule in [item for ruleset in rulesets for item in ruleset]:
        if fnmatch.fnmatchcase(permission, rule.permission) and fnmatch.fnmatchcase(pattern, rule.pattern):
            matched = rule
    if matched is None:
        return PermissionDecision(permission, pattern, "ask", None)
    return PermissionDecision(permission, pattern, matched.action, matched)


def require_allowed(
    permission: str,
    pattern: str,
    *rulesets: Iterable[PermissionRule],
) -> None:
    decision = evaluate_permission(permission, pattern, *rulesets)
    if decision.action != "allow":
        raise PermissionError(
            f"permission {permission!r} on {pattern!r} is {decision.action}; "
            "autonomous runtime requires explicit allow"
        )
