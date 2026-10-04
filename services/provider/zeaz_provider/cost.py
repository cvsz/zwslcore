from __future__ import annotations

import enum


class CostClass(str, enum.Enum):
    FREE_LOCAL = "FREE_LOCAL"
    FREE_REMOTE = "FREE_REMOTE"
    CUSTOMER_KEY = "CUSTOMER_KEY"
    PAID_PLATFORM = "PAID_PLATFORM"
    UNKNOWN = "UNKNOWN"


class CostPolicy(str, enum.Enum):
    ZERO_COST_ONLY = "ZERO_COST_ONLY"
    PREFER_ZERO_COST = "PREFER_ZERO_COST"
    PERMIT_PAID = "PERMIT_PAID"


_RANK = {
    CostClass.FREE_LOCAL: 0,
    CostClass.FREE_REMOTE: 1,
    CostClass.CUSTOMER_KEY: 2,
    CostClass.PAID_PLATFORM: 3,
    CostClass.UNKNOWN: 4,
}


def parse_cost_class(value: str) -> CostClass:
    try:
        return CostClass(str(value).strip().upper())
    except ValueError as exc:
        raise ValueError(f"unsupported cost class: {value}") from exc


def parse_cost_policy(value: str) -> CostPolicy:
    try:
        return CostPolicy(str(value).strip().upper())
    except ValueError as exc:
        raise ValueError(f"unsupported cost policy: {value}") from exc


def cost_allowed(cost_class: CostClass, policy: CostPolicy) -> bool:
    if policy == CostPolicy.ZERO_COST_ONLY:
        return cost_class in {CostClass.FREE_LOCAL, CostClass.FREE_REMOTE}
    if policy == CostPolicy.PREFER_ZERO_COST:
        return cost_class != CostClass.UNKNOWN
    return True


def cost_rank(cost_class: CostClass) -> int:
    return _RANK[cost_class]
