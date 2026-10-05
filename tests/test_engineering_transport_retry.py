from __future__ import annotations

import io
import json
import subprocess
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from services.engineering.evidence import EvidenceExporter
from services.engineering.continuous import ExecutionResult
from services.engineering.loop import ContinuousEngineeringLoop, LoopPolicy, WorkItem, WorkKind
from services.engineering.models import EngineeringTask, TaskStatus
from services.engineering.runtime import (
    EngineeringRuntime,
    ProviderClient,
    ProviderTransportError,
)
from services.engineering.store import SQLiteEngineeringStore
from services.engineering.worktree import WorktreeManager


class FakeResponse:
    def __init__(self, payload: dict):
        self._raw = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *args, **kwargs):
        return self._raw.read(*args, **kwargs)


class PlanningTransportFailureProvider:
    model = "zeaz-fast"

    def preflight(self) -> None:
        return None

    def chat(self, prompt, system, **kwargs):
        raise ProviderTransportError("provider transport failed: timeout")


def make_runtime_repo(root: Path) -> Path:
    repo = root / "repo"
    (repo / "services").mkdir(parents=True)
    (repo / "services" / "example.py").write_text("value = 1\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "init"], check=True, capture_output=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "test@example.com"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.name", "Test"],
        check=True,
    )
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "commit", "-m", "base"],
        check=True,
        capture_output=True,
    )
    return repo


class ProviderTransportRetryTests(unittest.TestCase):
    def test_request_id_is_forwarded_only_when_it_has_the_generated_format(self):
        client = ProviderClient()
        request_id = "a" * 32
        request = urllib.request.Request("http://127.0.0.1:8080/health/ready")

        with patch(
            "urllib.request.urlopen",
            return_value=FakeResponse({"status": "ready"}),
        ):
            client._request_json(request, attempts=1, request_id=request_id)

        self.assertEqual(request.get_header("X-request-id"), request_id)

        unsafe_request = urllib.request.Request("http://127.0.0.1:8080/health/ready")
        with patch(
            "urllib.request.urlopen",
            return_value=FakeResponse({"status": "ready"}),
        ):
            client._request_json(unsafe_request, attempts=1, request_id="api_key=private")

        self.assertIsNone(unsafe_request.get_header("X-request-id"))

    def test_request_json_retries_connection_reset_then_succeeds(self):
        client = ProviderClient()
        request = urllib.request.Request("http://127.0.0.1:8080/health/ready")
        calls = {"count": 0}

        def fake_urlopen(req, timeout=None):
            calls["count"] += 1
            if calls["count"] < 3:
                raise ConnectionResetError(104, "Connection reset by peer")
            return FakeResponse({"status": "ready"})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch("time.sleep"):
            value = client._request_json(request, attempts=3, timeout=1)

        self.assertEqual(value, {"status": "ready"})
        self.assertEqual(calls["count"], 3)

    def test_malformed_and_non_object_responses_are_infrastructure_failures(self):
        client = ProviderClient()
        request = urllib.request.Request("http://127.0.0.1:8080/health/ready")
        for body in (b"{invalid", b"[]"):
            with self.subTest(body=body), patch(
                "urllib.request.urlopen", return_value=io.BytesIO(body)
            ):
                with self.assertRaises(ProviderTransportError):
                    client._request_json(request, attempts=1, timeout=1)

    def test_transient_provider_http_error_retries_within_budget(self):
        client = ProviderClient()
        request = urllib.request.Request("http://127.0.0.1:8080/health/ready")
        calls = {"count": 0}

        def fake_urlopen(req, timeout=None):
            calls["count"] += 1
            if calls["count"] == 1:
                raise urllib.error.HTTPError(req.full_url, 503, "unavailable", {}, io.BytesIO(b"busy"))
            return FakeResponse({"status": "ready"})

        with patch("urllib.request.urlopen", side_effect=fake_urlopen), patch("time.sleep"):
            value = client._request_json(request, attempts=2, timeout=1)

        self.assertEqual(value, {"status": "ready"})
        self.assertEqual(calls["count"], 2)

    def test_exhausted_provider_http_error_omits_untrusted_response_body(self):
        client = ProviderClient()
        request = urllib.request.Request("http://127.0.0.1:8080/health/ready")
        with patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.HTTPError(
                request.full_url, 503, "unavailable", {}, io.BytesIO(b"api_key=private-value")
            ),
        ), patch("time.sleep"):
            with self.assertRaises(ProviderTransportError) as raised:
                client._request_json(request, attempts=1, timeout=1)
        self.assertIn("HTTP 503", str(raised.exception))
        self.assertNotIn("private-value", str(raised.exception))

    def test_structured_edit_violation_is_rejected_at_the_edit_gate(self):
        with self.assertRaisesRegex(ValueError, r"changes\[\]"):
            EngineeringRuntime._parse_changes('{"changes":{}}')
        parsed = EngineeringRuntime._parse_changes(
            '{"changes":[{"path":"../escape.py","content":"bad"}]}'
        )
        self.assertFalse(EngineeringRuntime._changes_within_scope(parsed, {"services"}))

    def test_real_engineering_failure_consumes_the_bounded_loop_attempt(self):
        item = WorkItem("real validation failure", WorkKind.REPAIR, max_attempts=1)
        checkpoints = []
        result = ContinuousEngineeringLoop(
            lambda _: ExecutionResult(False, EngineeringTask(title="failed"), "validation failed"),
            lambda _item, _result: (False, ()),
            checkpoint=checkpoints.append,
            policy=LoopPolicy(max_iterations=3),
        ).run([item])
        self.assertEqual(result.blocked, (item.fingerprint,))
        self.assertEqual(len(checkpoints), 1)
        self.assertEqual(checkpoints[0]["state"], "BLOCKED_ATTEMPTS")
        self.assertEqual(checkpoints[0]["attempt"], 1)

    def test_request_json_raises_transport_error_after_budget(self):
        client = ProviderClient()
        request = urllib.request.Request("http://127.0.0.1:8080/health/ready")

        with patch(
            "urllib.request.urlopen",
            side_effect=ConnectionResetError(104, "Connection reset by peer"),
        ), patch("time.sleep"):
            with self.assertRaisesRegex(ProviderTransportError, "after 3 attempt"):
                client._request_json(request, attempts=3, timeout=1)


class InfrastructureBudgetTests(unittest.TestCase):
    def test_runtime_transport_failure_does_not_consume_task_attempt_budget(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            repo = make_runtime_repo(root)
            store = SQLiteEngineeringStore(root / "state.db")
            evidence = EvidenceExporter(store, root / "evidence")
            runtime = EngineeringRuntime(
                store,
                PlanningTransportFailureProvider(),
                worktrees=WorktreeManager(root / "worktrees"),
                evidence=evidence,
            )
            task = EngineeringTask(
                title="transport failure",
                repository=str(repo),
                max_attempts=1,
            )

            with self.assertRaises(ProviderTransportError):
                runtime.run(
                    task,
                    validators=["git diff --check"],
                    allowed_paths={"services"},
                )

            saved = store.get_task(task.id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved.attempts, 0)
            self.assertEqual(saved.status, TaskStatus.BLOCKED)
            self.assertTrue(evidence.verify(task.id))
            bundle = evidence.read(task.id)
            self.assertEqual(bundle["task"]["attempts"], 0)
            self.assertEqual(bundle["task"]["status"], TaskStatus.BLOCKED.value)

    def test_infrastructure_retry_does_not_consume_work_attempt_budget(self):
        item = WorkItem("infra", WorkKind.REPAIR, max_attempts=2)
        checkpoints = []
        calls = []

        def implement(work):
            calls.append(work.fingerprint)
            return ExecutionResult(
                False,
                EngineeringTask(title="infra"),
                "provider transport failed",
                consume_attempt=False,
            )

        result = ContinuousEngineeringLoop(
            implement,
            lambda work, execution: (execution.passed, ()),
            checkpoint=checkpoints.append,
            policy=LoopPolicy(max_iterations=3),
        ).run([item])

        self.assertEqual(len(calls), 3)
        self.assertEqual(result.blocked, ())
        self.assertEqual(result.halt_reason, "iteration_budget")
        self.assertTrue(checkpoints)
        self.assertTrue(all(cp["state"] == "RETRY_INFRA" for cp in checkpoints))
        self.assertTrue(all(cp["attempt"] == 0 for cp in checkpoints))


if __name__ == "__main__":
    unittest.main()
