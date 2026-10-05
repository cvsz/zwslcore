from __future__ import annotations

import hashlib
import json
import unittest

from services.engineering.observability import (
    emit_engineering_event,
    task_work_fingerprint,
)


class EngineeringObservabilityTests(unittest.TestCase):
    def test_event_has_common_fields_and_redacts_untrusted_correlation_values(self):
        private_value = "api_key=sk-PRIVATE-ENGINEERING-CANARY-012345"
        fingerprint = task_work_fingerprint("configure " + private_value, "secret description")

        with self.assertLogs("zeaz.engineering", level="INFO") as captured:
            emit_engineering_event(
                request_id=private_value,
                task_id=private_value,
                work_fingerprint=fingerprint,
                phase="planning",
                provider="zeaz-provider",
                model=private_value,
                attempt=2,
                latency_ms=123.4567,
                outcome="success",
            )

        message = captured.records[0].getMessage()
        self.assertNotIn(private_value, message)
        event = json.loads(message)
        self.assertEqual(
            {
                "component",
                "request_id",
                "task_id",
                "work_fingerprint",
                "phase",
                "provider",
                "model",
                "attempt",
                "latency_ms",
                "outcome",
                "error_class",
            }
            - event.keys(),
            set(),
        )
        self.assertEqual(event["request_id"], "unknown")
        self.assertRegex(event["task_id"], r"^task_[a-f0-9]{20}$")
        self.assertEqual(event["work_fingerprint"], fingerprint)
        self.assertEqual(event["model"], "unknown")
        self.assertEqual(event["latency_ms"], 123.457)
        self.assertEqual(event["error_class"], None)

    def test_valid_request_ids_are_pseudonymized_for_cross_service_correlation(self):
        request_id = "a" * 32
        fingerprint = task_work_fingerprint("task", "description")

        with self.assertLogs("zeaz.engineering", level="INFO") as captured:
            emit_engineering_event(
                request_id=request_id,
                task_id="task_0123456789abcdefabcd",
                work_fingerprint=fingerprint,
                phase="planning",
                provider="zeaz-provider",
                model="zeaz-fast",
                attempt=1,
                latency_ms=0,
                outcome="success",
            )

        event = json.loads(captured.records[0].getMessage())
        self.assertEqual(event["request_id"], hashlib.sha256(request_id.encode()).hexdigest())


if __name__ == "__main__":
    unittest.main()
