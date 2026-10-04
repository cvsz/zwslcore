from __future__ import annotations

from typing import Any


VALIDATION_MODES = {"strict", "delta"}


def validate_mode(value: str) -> str:
    mode = str(value).strip().lower()
    if mode not in VALIDATION_MODES:
        raise ValueError(f"unsupported validation mode: {value}")
    return mode


def evaluate_validation(
    baseline: dict[str, Any] | None,
    final: dict[str, Any],
    *,
    mode: str,
) -> dict[str, Any]:
    mode = validate_mode(mode)
    final_results = list(final.get("results") or [])
    final_codes = {
        str(item.get("command", "")): int(item.get("returncode", 1))
        for item in final_results
        if isinstance(item, dict) and item.get("command")
    }

    if mode == "strict":
        failures = [
            command
            for command, code in final_codes.items()
            if code != 0
        ]
        return {
            **final,
            "mode": mode,
            "passed": not failures,
            "failures": failures,
            "baseline_failures": [],
            "regressions": failures,
            "improvements": [],
            "residual_failures": [],
        }

    if baseline is None:
        raise ValueError("delta validation requires a baseline result")

    baseline_results = list(baseline.get("results") or [])
    baseline_codes = {
        str(item.get("command", "")): int(item.get("returncode", 1))
        for item in baseline_results
        if isinstance(item, dict) and item.get("command")
    }

    baseline_failures = [
        command for command, code in baseline_codes.items() if code != 0
    ]
    regressions = [
        command
        for command, final_code in final_codes.items()
        if baseline_codes.get(command, 0) == 0 and final_code != 0
    ]
    improvements = [
        command
        for command, baseline_code in baseline_codes.items()
        if baseline_code != 0 and final_codes.get(command, baseline_code) == 0
    ]
    residual_failures = [
        command
        for command, baseline_code in baseline_codes.items()
        if baseline_code != 0 and final_codes.get(command, 0) != 0
    ]

    return {
        **final,
        "mode": mode,
        "passed": not regressions,
        "failures": [command for command, code in final_codes.items() if code != 0],
        "baseline_failures": baseline_failures,
        "regressions": regressions,
        "improvements": improvements,
        "residual_failures": residual_failures,
    }
