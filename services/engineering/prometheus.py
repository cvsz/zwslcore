from __future__ import annotations

import argparse
import hashlib
import http.server
import json
import os
import re
import sqlite3
import stat
import sys
from collections import Counter
from pathlib import Path
from typing import Callable


TASK_STATUSES = (
    "CREATED",
    "BASELINING",
    "PLANNING",
    "EDITING",
    "VALIDATING",
    "REVIEWING",
    "BLOCKED",
    "SUCCEEDED",
    "FAILED",
    "CANCELLED",
    "OTHER",
)
QUEUE_STATES = (
    "PENDING",
    "RUNNING",
    "SUCCEEDED",
    "BLOCKED",
    "CANCELLED",
    "QUARANTINED",
    "DEAD_LETTER",
    "OTHER",
)
EVIDENCE_STATES = ("available", "missing", "checksum_mismatch", "invalid")
CHECKPOINT_PHASES = (
    "BASELINE",
    "BASELINE_VALIDATION",
    "PLAN",
    "READ_ONLY_COMPLETE",
    "EDIT_RESPONSE_INVALID",
    "EDIT_RESPONSE_REPAIRED",
    "EDIT_RESPONSE_REGENERATED",
    "VALIDATION",
    "REVIEW",
    "COMMIT",
    "FAILED",
    "OTHER",
)
TERMINAL_STATUSES = {"SUCCEEDED", "FAILED", "BLOCKED", "CANCELLED"}
TASK_ID_PATTERN = re.compile(r"task_[a-f0-9]{20}\Z")


class EngineeringMetrics:
    """Read-only, low-cardinality Prometheus view of local engineering state."""

    def __init__(
        self,
        database: str | Path,
        ledger: str | Path,
        evidence_root: str | Path,
    ) -> None:
        self.database = Path(database)
        self.ledger = Path(ledger)
        self.evidence_root = Path(evidence_root)

    def render(self) -> str:
        store_up = 0
        ledger_up = 0
        task_counts = Counter({status: 0 for status in TASK_STATUSES})
        attempt_counts = Counter({status: 0 for status in TASK_STATUSES})
        evidence_counts = Counter({state: 0 for state in EVIDENCE_STATES})
        phase_counts = Counter({phase: 0 for phase in CHECKPOINT_PHASES})
        queue_counts = Counter({state: 0 for state in QUEUE_STATES})
        evidence_write_errors = 0
        structured_repairs = 0

        try:
            (
                task_rows,
                checkpoint_rows,
                evidence_write_errors,
            ) = self._read_store()
            store_up = 1
            for row in task_rows:
                status = str(row["status"])
                status_label = status if status in task_counts else "OTHER"
                task_counts[status_label] += 1
                attempt_counts[status_label] += max(0, int(row["attempts"]))
                if status in TERMINAL_STATUSES:
                    evidence_counts[self._evidence_state(str(row["id"]))] += 1
            for row in checkpoint_rows:
                phase = str(row["phase"])
                label = phase if phase in phase_counts else "OTHER"
                phase_counts[label] += int(row["total"])
                if phase == "EDIT_RESPONSE_REPAIRED":
                    structured_repairs += int(row["total"])
        except (OSError, sqlite3.Error, ValueError, TypeError, KeyError, json.JSONDecodeError):
            pass

        try:
            queue_counts.update(self._read_ledger())
            ledger_up = 1
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            pass

        lines = [
            "# HELP zeaz_engineering_store_up Whether the engineering SQLite store was read successfully.",
            "# TYPE zeaz_engineering_store_up gauge",
            f"zeaz_engineering_store_up {store_up}",
            "# HELP zeaz_engineering_ledger_up Whether the continuous work ledger was read successfully.",
            "# TYPE zeaz_engineering_ledger_up gauge",
            f"zeaz_engineering_ledger_up {ledger_up}",
            "# HELP zeaz_engineering_tasks Current persisted task count by latest status.",
            "# TYPE zeaz_engineering_tasks gauge",
        ]
        lines.extend(
            f'zeaz_engineering_tasks{{status="{status}"}} {task_counts[status]}'
            for status in TASK_STATUSES
        )
        lines.extend(
            [
                "# HELP zeaz_engineering_task_attempts Current persisted attempt count grouped by latest task status.",
                "# TYPE zeaz_engineering_task_attempts gauge",
            ]
        )
        lines.extend(
            f'zeaz_engineering_task_attempts{{status="{status}"}} {attempt_counts[status]}'
            for status in TASK_STATUSES
        )
        lines.extend(
            [
                "# HELP zeaz_engineering_checkpoints Persisted checkpoint count by bounded phase label.",
                "# TYPE zeaz_engineering_checkpoints gauge",
            ]
        )
        lines.extend(
            f'zeaz_engineering_checkpoints{{phase="{phase}"}} {phase_counts[phase]}'
            for phase in CHECKPOINT_PHASES
        )
        lines.extend(
            [
                "# HELP zeaz_engineering_structured_output_repairs Persisted structured-output repair checkpoint count.",
                "# TYPE zeaz_engineering_structured_output_repairs gauge",
                f"zeaz_engineering_structured_output_repairs {structured_repairs}",
                "# HELP zeaz_engineering_queue_items Current non-archived queue item count by state.",
                "# TYPE zeaz_engineering_queue_items gauge",
            ]
        )
        lines.extend(
            f'zeaz_engineering_queue_items{{state="{state}"}} {queue_counts[state]}'
            for state in QUEUE_STATES
        )
        lines.extend(
            [
                "# HELP zeaz_engineering_evidence_bundles Terminal-task evidence bundle checksum state.",
                "# TYPE zeaz_engineering_evidence_bundles gauge",
            ]
        )
        lines.extend(
            f'zeaz_engineering_evidence_bundles{{state="{state}"}} {evidence_counts[state]}'
            for state in EVIDENCE_STATES
        )
        lines.extend(
            [
                "# HELP zeaz_engineering_tasks_with_evidence_write_error Tasks retaining an evidence export error in metadata.",
                "# TYPE zeaz_engineering_tasks_with_evidence_write_error gauge",
                f"zeaz_engineering_tasks_with_evidence_write_error {evidence_write_errors}",
                "",
            ]
        )
        return "\n".join(lines)

    def _read_store(self) -> tuple[list[sqlite3.Row], list[sqlite3.Row], int]:
        if not self.database.is_file():
            raise FileNotFoundError(self.database)
        uri = f"{self.database.resolve().as_uri()}?mode=ro"
        with sqlite3.connect(uri, uri=True, timeout=1) as connection:
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA query_only = ON")
            tasks = connection.execute(
                "SELECT id, status, attempts, metadata_json FROM tasks"
            ).fetchall()
            checkpoints = connection.execute(
                "SELECT phase, COUNT(*) AS total FROM checkpoints GROUP BY phase"
            ).fetchall()
        errors = 0
        for row in tasks:
            metadata = json.loads(row["metadata_json"])
            if not isinstance(metadata, dict):
                raise ValueError("task metadata is not an object")
            if metadata.get("evidence_error"):
                errors += 1
        return tasks, checkpoints, errors

    def _read_ledger(self) -> Counter[str]:
        if not self.ledger.is_file():
            return Counter()
        value = json.loads(self.ledger.read_text(encoding="utf-8"))
        if (
            not isinstance(value, dict)
            or type(value.get("schema")) is not int
            or not isinstance(value.get("records"), dict)
        ):
            raise ValueError("continuous ledger has an invalid shape")
        states: Counter[str] = Counter()
        for record in value["records"].values():
            if not isinstance(record, dict):
                raise ValueError("continuous ledger contains an invalid record")
            state = record.get("state")
            label = state if isinstance(state, str) and state in QUEUE_STATES else "OTHER"
            states[label] += 1
        return states

    def _evidence_state(self, task_id: str) -> str:
        if not TASK_ID_PATTERN.fullmatch(task_id):
            return "invalid"
        task_dir = self.evidence_root / task_id
        evidence = task_dir / "evidence.json"
        checksum = task_dir / "evidence.sha256"
        if task_dir.is_symlink() or not task_dir.is_dir():
            return "missing"
        try:
            if evidence.is_symlink() or checksum.is_symlink():
                return "invalid"
            if not evidence.is_file() and not checksum.is_file():
                return "missing"
            if not evidence.is_file() or not checksum.is_file():
                return "invalid"
            expected_line = checksum.read_text(encoding="utf-8").splitlines()[0]
            expected = expected_line.split()[0]
            if not re.fullmatch(r"[a-f0-9]{64}", expected):
                return "invalid"
            descriptor = os.open(evidence, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):
                    return "invalid"
                digest = hashlib.sha256()
                with os.fdopen(descriptor, "rb", closefd=False) as stream:
                    for block in iter(lambda: stream.read(65536), b""):
                        digest.update(block)
                actual = digest.hexdigest()
            finally:
                os.close(descriptor)
        except (OSError, UnicodeDecodeError, IndexError):
            return "invalid"
        return "available" if actual == expected else "checksum_mismatch"


def serve(
    metrics: EngineeringMetrics,
    port: int,
    server_factory: Callable = http.server.ThreadingHTTPServer,
) -> None:
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path != "/metrics":
                self.send_error(404)
                return
            body = metrics.render().encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            return

    with server_factory(("127.0.0.1", port), Handler) as server:
        print(f"Engineering metrics listening on http://127.0.0.1:{port}/metrics", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Loopback-only engineering Prometheus exporter")
    parser.add_argument("--db", default=str(Path.home() / ".zwslcore/state/engineering.db"))
    parser.add_argument("--ledger", default=str(Path.home() / ".zwslcore/state/continuous.json"))
    parser.add_argument("--evidence-root", default=str(Path.home() / ".zwslcore/evidence"))
    parser.add_argument("--port", type=int, default=9464)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    serve(EngineeringMetrics(args.db, args.ledger, args.evidence_root), args.port)
    return 0


if __name__ == "__main__":
    sys.exit(main())
