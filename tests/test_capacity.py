from __future__ import annotations

import argparse
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from scripts.capacity import (
    build_cache_prune_command,
    directory_report,
    main,
    parse_json_lines,
    parse_log_inspect_line,
    positive_bytes,
    pressure_state,
    prune_allowed,
    size_bytes,
)


class CapacityReportTests(unittest.TestCase):
    def test_pressure_thresholds_are_inclusive_and_ordered(self):
        self.assertEqual(pressure_state(79.9, 80, 90), "ok")
        self.assertEqual(pressure_state(80, 80, 90), "warning")
        self.assertEqual(pressure_state(90, 80, 90), "critical")

    def test_size_parser_supports_decimal_and_binary_units(self):
        self.assertEqual(size_bytes("1.5 GB"), 1_500_000_000)
        self.assertEqual(size_bytes("2 MiB"), 2 * 1024 * 1024)
        self.assertIsNone(size_bytes("unknown"))

    def test_directory_report_skips_symlinks_and_does_not_return_names(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            root = Path(temporary_directory) / "data"
            root.mkdir()
            (root / "visible.bin").write_bytes(b"1234")
            external = Path(temporary_directory) / "external.bin"
            external.write_bytes(b"outside")
            (root / "linked.bin").symlink_to(external)

            result = directory_report(root)

        self.assertEqual(result, {"exists": True, "bytes": 4, "files": 1, "errors": 0})
        self.assertNotIn("visible.bin", json.dumps(result))

    def test_json_lines_requires_object_records(self):
        self.assertEqual(
            parse_json_lines('{"Type":"Images"}\n\n{"Type":"Volumes"}'),
            [{"Type": "Images"}, {"Type": "Volumes"}],
        )
        with self.assertRaises(ValueError):
            parse_json_lines('[1, 2]')

    def test_log_inspect_parser_identifies_bounded_and_unbounded_configs(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            log_path = Path(temporary_directory) / "container-json.log"
            log_path.write_bytes(b"log")
            bounded = parse_log_inspect_line(
                f"/private-container|json-file|{{\"max-size\":\"10m\",\"max-file\":\"3\"}}|{log_path}"
            )
            unbounded = parse_log_inspect_line("/private-container|json-file|{}|/missing/log")

        self.assertTrue(bounded["bounded"])
        self.assertEqual(bounded["log_bytes"], 3)
        self.assertFalse(unbounded["bounded"])
        self.assertNotIn("private-container", json.dumps([bounded, unbounded]))

    def test_prune_plan_is_explicit_and_blocked_below_warning_threshold(self):
        self.assertEqual(
            build_cache_prune_command(2 * 1024**3),
            ["docker", "builder", "prune", "--max-used-space", str(2 * 1024**3), "--force"],
        )
        self.assertTrue(prune_allowed("warning"))
        self.assertTrue(prune_allowed("critical"))
        self.assertFalse(prune_allowed("ok"))
        with self.assertRaises(ValueError):
            build_cache_prune_command(0)
        with self.assertRaises(argparse.ArgumentTypeError):
            positive_bytes("0")

    def test_apply_is_blocked_when_capacity_cannot_be_measured(self):
        with patch("scripts.capacity.report", return_value={"summary": {"state": "unknown"}}), patch(
            "scripts.capacity.docker_run"
        ) as docker_run, redirect_stdout(io.StringIO()) as output:
            exit_code = main(["--prune-build-cache-max-used-bytes", "1024", "--apply"])

        self.assertEqual(exit_code, 3)
        self.assertEqual(json.loads(output.getvalue())["prune_plan"]["mode"], "blocked_unknown_capacity")
        docker_run.assert_not_called()

    def test_apply_runs_only_the_explicit_buildkit_prune_at_warning_threshold(self):
        report_result = {"summary": {"state": "warning"}}
        with patch("scripts.capacity.report", side_effect=[report_result.copy(), report_result.copy()]), patch(
            "scripts.capacity.docker_run", return_value=("", None)
        ) as docker_run, redirect_stdout(io.StringIO()) as output:
            exit_code = main(["--prune-build-cache-max-used-bytes", "1024", "--apply"])

        self.assertEqual(exit_code, 1)
        docker_run.assert_called_once_with(
            ["docker", "builder", "prune", "--max-used-space", "1024", "--force"],
            timeout=300,
        )
        self.assertEqual(json.loads(output.getvalue())["prune_plan"]["mode"], "applied")


if __name__ == "__main__":
    unittest.main()
