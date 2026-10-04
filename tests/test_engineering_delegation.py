from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from services.engineering.continuous import ContinuousEngineeringRunner
from services.engineering.delegation import (
    MAX_DELEGATION_DEPTH,
    children_of,
    descendants_of,
    make_child_task,
    task_lineage,
)
from services.engineering.ledger import JsonContinuousLedger
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.store import SQLiteEngineeringStore


class DelegationTests(unittest.TestCase):
    def test_child_records_parent_root_depth_and_agent(self):
        parent = EngineeringTask(title="parent", repository="/tmp/repo")
        child = make_child_task(
            parent,
            title="child",
            description="inspect provider",
            agent_name="explore",
        )
        self.assertEqual(child.metadata["parent_task_id"], parent.id)
        self.assertEqual(child.metadata["root_task_id"], parent.id)
        self.assertEqual(child.metadata["delegation_depth"], 1)
        self.assertEqual(child.metadata["delegated_agent"], "explore")
        self.assertEqual(task_lineage(child).depth, 1)

    def test_primary_agent_cannot_be_delegated(self):
        parent = EngineeringTask(title="parent")
        with self.assertRaisesRegex(ValueError, "not a subagent"):
            make_child_task(
                parent,
                title="bad",
                description="",
                agent_name="build",
            )

    def test_delegation_depth_is_bounded(self):
        task = EngineeringTask(title="root")
        for depth in range(1, MAX_DELEGATION_DEPTH + 1):
            task = make_child_task(
                task,
                title=f"child-{depth}",
                description="",
                agent_name="general",
            )
            self.assertEqual(task.metadata["delegation_depth"], depth)
        with self.assertRaisesRegex(ValueError, "exceeds maximum"):
            make_child_task(
                task,
                title="too-deep",
                description="",
                agent_name="general",
            )

    def test_children_and_descendants_are_deterministic(self):
        root = EngineeringTask(title="root")
        child_a = make_child_task(root, title="a", description="", agent_name="review")
        child_b = make_child_task(root, title="b", description="", agent_name="explore")
        grandchild = make_child_task(
            child_a,
            title="grandchild",
            description="",
            agent_name="general",
        )
        child_a.created_at = 2.0
        child_b.created_at = 1.0
        grandchild.created_at = 3.0
        tasks = [grandchild, child_a, root, child_b]

        self.assertEqual(
            [task.id for task in children_of(tasks, root.id)],
            [child_b.id, child_a.id],
        )
        self.assertEqual(
            [task.id for task in descendants_of(tasks, root.id)],
            [child_b.id, child_a.id, grandchild.id],
        )

    def test_child_completion_updates_parent_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            store = SQLiteEngineeringStore(root / "state.db")
            ledger = JsonContinuousLedger(root / "ledger.json")
            parent = EngineeringTask(title="parent")
            child = make_child_task(
                parent,
                title="child",
                description="",
                agent_name="general",
            )
            child.status = TaskStatus.SUCCEEDED
            child.attempts = 1
            child.metadata["agent"] = "general"
            child.metadata["evidence_path"] = "/tmp/evidence.json"
            store.save_task(parent)
            store.save_task(child)

            runner = ContinuousEngineeringRunner(
                store,
                ledger,
                runtime=object(),  # only parent-state helper is exercised here
            )
            runner._record_parent_state(child)
            saved = store.get_task(parent.id)
            summary = saved.metadata["subagent_children"][child.id]
            self.assertEqual(summary["status"], "SUCCEEDED")
            self.assertEqual(summary["agent"], "general")
            self.assertEqual(summary["attempts"], 1)
            self.assertEqual(summary["evidence_path"], "/tmp/evidence.json")


if __name__ == "__main__":
    unittest.main()
