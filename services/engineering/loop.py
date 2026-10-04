from __future__ import annotations

import dataclasses
import enum
import hashlib
import json
from collections.abc import Callable, Iterable
from typing import Any


class WorkKind(str, enum.Enum):
    UPGRADE = "UPGRADE"
    UPDATE = "UPDATE"
    IMPLEMENT_FEATURE = "IMPLEMENT_FEATURE"
    REPAIR = "REPAIR"


@dataclasses.dataclass(frozen=True)
class WorkItem:
    title: str
    kind: WorkKind
    payload: dict[str, Any] = dataclasses.field(default_factory=dict)
    priority: int = 50
    max_attempts: int = 2

    @property
    def fingerprint(self) -> str:
        raw = json.dumps(
            {
                "title": self.title,
                "kind": self.kind.value,
                "payload": self.payload,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
        return hashlib.sha256(raw).hexdigest()


@dataclasses.dataclass(frozen=True)
class LoopPolicy:
    max_iterations: int = 12
    max_no_progress_iterations: int = 3
    stop_on_regression: bool = True


@dataclasses.dataclass(frozen=True)
class LoopResult:
    completed: tuple[str, ...]
    blocked: tuple[str, ...]
    iterations: int
    halt_reason: str = ""


class ContinuousEngineeringLoop:
    """Bounded one-slice-at-a-time orchestration with dedupe and regression halt."""

    def __init__(
        self,
        implement: Callable[[WorkItem], Any],
        validate: Callable[[WorkItem, Any], tuple[bool, tuple[str, ...]]],
        *,
        discover: Callable[[], Iterable[WorkItem]] | None = None,
        rollback: Callable[[WorkItem, Any], None] | None = None,
        checkpoint: Callable[[dict[str, Any]], None] | None = None,
        policy: LoopPolicy | None = None,
    ) -> None:
        self.implement = implement
        self.validate = validate
        self.discover = discover
        self.rollback = rollback
        self.checkpoint = checkpoint
        self.policy = policy or LoopPolicy()

    def run(self, seed: Iterable[WorkItem] = ()) -> LoopResult:
        queue: dict[str, WorkItem] = {item.fingerprint: item for item in seed}
        attempts: dict[str, int] = {}
        completed: list[str] = []
        blocked: list[str] = []
        no_progress = 0
        previous_signature: tuple[str, ...] | None = None

        for iteration in range(1, self.policy.max_iterations + 1):
            if self.discover:
                for item in self.discover():
                    if item.fingerprint not in completed and item.fingerprint not in blocked:
                        queue.setdefault(item.fingerprint, item)

            candidates = [
                item for fp, item in queue.items()
                if fp not in completed and fp not in blocked
            ]
            if not candidates:
                return LoopResult(tuple(completed), tuple(blocked), iteration - 1)

            item = sorted(candidates, key=lambda x: (-x.priority, x.fingerprint))[0]
            fp = item.fingerprint
            attempts[fp] = attempts.get(fp, 0) + 1

            result = self.implement(item)
            passed, regressions = self.validate(item, result)
            signature = tuple(sorted(regressions))

            if passed:
                completed.append(fp)
                no_progress = 0
            else:
                if self.rollback:
                    self.rollback(item, result)
                if self.policy.stop_on_regression and regressions:
                    blocked.append(fp)
                    self._checkpoint(iteration, item, "BLOCKED_REGRESSION", attempts[fp], regressions)
                    return LoopResult(tuple(completed), tuple(blocked), iteration, "regression")
                if attempts[fp] >= item.max_attempts:
                    blocked.append(fp)
                if signature and signature == previous_signature:
                    no_progress += 1
                else:
                    no_progress = 0
                if no_progress >= self.policy.max_no_progress_iterations:
                    blocked.append(fp)
                    self._checkpoint(iteration, item, "BLOCKED_NO_PROGRESS", attempts[fp], regressions)
                    return LoopResult(tuple(completed), tuple(dict.fromkeys(blocked)), iteration, "no_progress")

            previous_signature = signature
            self._checkpoint(
                iteration,
                item,
                "SUCCEEDED" if passed else "RETRY",
                attempts[fp],
                regressions,
            )

        return LoopResult(tuple(completed), tuple(dict.fromkeys(blocked)), self.policy.max_iterations, "iteration_budget")

    def _checkpoint(
        self,
        iteration: int,
        item: WorkItem,
        state: str,
        attempt: int,
        regressions: tuple[str, ...],
    ) -> None:
        if self.checkpoint:
            self.checkpoint(
                {
                    "iteration": iteration,
                    "item_id": item.fingerprint,
                    "title": item.title,
                    "kind": item.kind.value,
                    "state": state,
                    "attempt": attempt,
                    "regressions": list(regressions),
                }
            )
