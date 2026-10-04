from __future__ import annotations

import dataclasses
import enum
import time
import uuid
from typing import Any


class TaskStatus(str, enum.Enum):
    CREATED = "CREATED"
    BASELINING = "BASELINING"
    PLANNING = "PLANNING"
    EDITING = "EDITING"
    VALIDATING = "VALIDATING"
    REVIEWING = "REVIEWING"
    BLOCKED = "BLOCKED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TaskRisk(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class PushPolicy(str, enum.Enum):
    AUTO_LOCAL_ONLY = "AUTO_LOCAL_ONLY"
    APPROVAL_BEFORE_PUSH = "APPROVAL_BEFORE_PUSH"
    AUTO_PUSH_ALLOWED = "AUTO_PUSH_ALLOWED"


@dataclasses.dataclass
class EngineeringTask:
    title: str
    description: str = ""
    repository: str = "."
    risk: TaskRisk = TaskRisk.MEDIUM
    status: TaskStatus = TaskStatus.CREATED
    push_policy: PushPolicy = PushPolicy.AUTO_LOCAL_ONLY
    id: str = dataclasses.field(default_factory=lambda: f"task_{uuid.uuid4().hex[:20]}")
    worktree_path: str = ""
    branch_name: str = ""
    attempts: int = 0
    max_attempts: int = 2
    last_error: str = ""
    created_at: float = dataclasses.field(default_factory=time.time)
    updated_at: float = dataclasses.field(default_factory=time.time)
    metadata: dict[str, Any] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class Checkpoint:
    task_id: str
    phase: str
    payload: dict[str, Any] = dataclasses.field(default_factory=dict)
    id: str = dataclasses.field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:20]}")
    created_at: float = dataclasses.field(default_factory=time.time)


@dataclasses.dataclass(frozen=True)
class ReviewFinding:
    severity: str
    category: str
    message: str
    path: str = ""
    blocking: bool = True
