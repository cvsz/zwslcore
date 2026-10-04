"""Self-contained zwslcore engineering control plane."""

from .agents import AgentProfile, get_agent, list_agents
from .continuous import ContinuousEngineeringRunner
from .delegation import (
    Lineage,
    MAX_DELEGATION_DEPTH,
    children_of,
    descendants_of,
    make_child_task,
    task_lineage,
)
from .evidence import EvidenceExporter
from .hardware import HardwareProfile, detect_hardware
from .ledger import JsonContinuousLedger
from .reconcile import QueueReconciler, ReconcileFinding, ReconcileReport
from .loop import ContinuousEngineeringLoop, LoopPolicy, WorkKind, WorkItem
from .mcp import (
    MCPError,
    MCPServerConfig,
    MCPTool,
    StdioMCPSession,
    call_server_tool,
    list_server_tools,
    load_config as load_mcp_config,
    split_qualified_tool,
)
from .models import Checkpoint, EngineeringTask, PushPolicy, TaskRisk, TaskStatus
from .permissions import PermissionDecision, PermissionRule, evaluate_permission, require_allowed
from .review import SecurityGate, StaticReviewer
from .runtime import EngineeringRuntime, ProviderClient
from .snapshot import RepositorySnapshotter
from .store import SQLiteEngineeringStore
from .tools import ToolCapability, get_tool, list_tools
from .validation import evaluate_validation, validate_mode
from .worktree import WorktreeManager

__all__ = [
    "AgentProfile",
    "Checkpoint",
    "ContinuousEngineeringRunner",
    "ContinuousEngineeringLoop",
    "Lineage",
    "MAX_DELEGATION_DEPTH",
    "EngineeringRuntime",
    "EvidenceExporter",
    "HardwareProfile",
    "JsonContinuousLedger",
    "QueueReconciler",
    "ReconcileFinding",
    "ReconcileReport",
    "EngineeringTask",
    "LoopPolicy",
    "MCPError",
    "MCPServerConfig",
    "MCPTool",
    "PermissionDecision",
    "PermissionRule",
    "ProviderClient",
    "PushPolicy",
    "RepositorySnapshotter",
    "SQLiteEngineeringStore",
    "SecurityGate",
    "StaticReviewer",
    "StdioMCPSession",
    "TaskRisk",
    "TaskStatus",
    "WorkItem",
    "WorkKind",
    "ToolCapability",
    "WorktreeManager",
    "call_server_tool",
    "children_of",
    "descendants_of",
    "detect_hardware",
    "evaluate_permission",
    "get_agent",
    "get_tool",
    "list_agents",
    "list_server_tools",
    "list_tools",
    "load_mcp_config",
    "make_child_task",
    "require_allowed",
    "split_qualified_tool",
    "task_lineage",
    "evaluate_validation",
    "validate_mode",
]
