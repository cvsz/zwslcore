from __future__ import annotations

import io
import json
import tempfile
import unittest
import urllib.request
from pathlib import Path
from unittest.mock import patch

from services.engineering.continuous import ExecutionResult
from services.engineering.loop import ContinuousEngineeringLoop, LoopPolicy, WorkItem, WorkKind
from services.engineering.models import EngineeringTask
from services.engineering.runtime import ProviderClient, ProviderTransportError


class FakeResponse:
    def __init__(self, payload: dict):
        self._raw = io.BytesIO(json.dumps(payload).encode("utf-8"))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def read(self, *args, **kwargs):
        return self._raw.read(*args, **kwargs)


class ProviderTransportRetryTests(unittest.TestCase):
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
