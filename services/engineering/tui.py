from __future__ import annotations

import shutil
import sys
import time
from typing import Any

from .hardware import detect_hardware
from .ledger import JsonContinuousLedger
from .store import SQLiteEngineeringStore
from services.model_catalog.selector import select_engineering_alias


RESET = "\x1b[0m"
BOLD = "\x1b[1m"
DIM = "\x1b[2m"
GREEN = "\x1b[32m"
YELLOW = "\x1b[33m"
RED = "\x1b[31m"
CYAN = "\x1b[36m"
MAGENTA = "\x1b[35m"


def _clip(value: Any, width: int) -> str:
    text = str(value or "")
    if width <= 1:
        return text[:width]
    if len(text) <= width:
        return text
    return text[: width - 1] + "…"


def _state_color(state: str) -> str:
    value = state.upper()
    if value in {"SUCCEEDED", "PASS", "READY"}:
        return GREEN
    if value in {"FAILED", "BLOCKED", "BLOCKED_ATTEMPTS"}:
        return RED
    if value in {"RUNNING", "PLANNING", "EDITING", "VALIDATING", "REVIEWING"}:
        return CYAN
    if value in {"PENDING", "CREATED", "RETRY_INFRA"}:
        return YELLOW
    return DIM


def _paint(text: str, color: str, enabled: bool) -> str:
    return f"{color}{text}{RESET}" if enabled else text


def _bar(value: int, maximum: int, width: int = 10) -> str:
    maximum = max(1, maximum)
    value = max(0, min(value, maximum))
    used = round(width * value / maximum)
    return "[" + "#" * used + "-" * (width - used) + "]"


def _section(title: str, width: int, color: bool) -> list[str]:
    label = f" {title} "
    remaining = max(0, width - len(label))
    return [_paint(label + "─" * remaining, BOLD + CYAN, color)]


def build_dashboard(
    store: SQLiteEngineeringStore,
    ledger: JsonContinuousLedger,
    *,
    env: dict[str, str],
    limit: int = 12,
    color: bool = False,
    width: int | None = None,
    now: float | None = None,
) -> str:
    width = max(72, min(width or shutil.get_terminal_size((110, 30)).columns, 160))
    now = time.time() if now is None else now
    profile = detect_hardware()

    configured = (env.get("ZEAZ_ENGINEERING_MODEL") or "auto").strip() or "auto"
    selected_alias = configured
    selected_model = ""
    selected_score = ""
    if configured.lower() == "auto":
        ranked = select_engineering_alias(
            env,
            hardware_profile=profile.profile,
            ram_available_gb=profile.ram_available_gb,
        )
        selected_alias = ranked.candidate.alias
        selected_model = ranked.candidate.id
        selected_score = str(ranked.score)

    records = ledger.records()
    tasks = {task.id: task for task in store.list_tasks()}
    states: dict[str, int] = {}
    for record in records:
        state = str(record.get("state", "UNKNOWN"))
        states[state] = states.get(state, 0) + 1

    lines: list[str] = []
    title = " zwslcore engineering control plane "
    lines.append(_paint(title.center(width, "═"), BOLD + MAGENTA, color))
    lines.append(
        f" hardware  {profile.profile:<10} cpu={profile.logical_cpus:<2} "
        f"ram={profile.ram_available_gb:.1f}/{profile.ram_total_gb:.1f}GiB "
        f"accelerator={profile.accelerator_backend}"
    )
    model_text = f" model     mode={configured} selected={selected_alias}"
    if selected_model:
        model_text += f" ({selected_model}) score={selected_score}"
    lines.append(model_text)
    lines.append(
        f" queue     total={len(records)} "
        + " ".join(f"{key.lower()}={value}" for key, value in sorted(states.items()))
    )

    lines.extend(_section("WORK QUEUE", width, color))
    if not records:
        lines.append(_paint(" no queued work", DIM, color))
    else:
        header = (
            f"{'FP':12} {'STATE':12} {'ATTEMPTS':12} {'PHASE':18} "
            f"{'KIND':18} TITLE"
        )
        lines.append(_paint(header, BOLD, color))
        lines.append("─" * width)
        for record in records[: max(1, limit)]:
            state = str(record.get("state", "UNKNOWN"))
            attempts = int(record.get("attempts", 0))
            maximum = int(record.get("max_attempts", 2))
            task_id = str(record.get("task_id") or "")
            task = tasks.get(task_id)
            phase = ""
            task_status = ""
            if task is not None:
                task_status = task.status.value
                phase = str(task.metadata.get("phase_cursor") or task_status)
            shown_state = task_status if state == "RUNNING" and task_status else state
            row = (
                f"{str(record.get('fingerprint', ''))[:12]:12} "
                f"{shown_state[:12]:12} "
                f"{_bar(attempts, maximum, 6)} {attempts}/{maximum:<3} "
                f"{_clip(phase, 18):18} "
                f"{_clip(record.get('kind', ''), 18):18} "
                f"{_clip(record.get('title', ''), max(8, width - 83))}"
            )
            lines.append(_paint(row, _state_color(shown_state), color))

    lines.extend(_section("RECENT TASKS", width, color))
    recent = sorted(tasks.values(), key=lambda task: task.updated_at, reverse=True)[:5]
    if not recent:
        lines.append(_paint(" no engineering tasks", DIM, color))
    for task in recent:
        age = max(0, int(now - task.updated_at))
        evidence = "yes" if task.metadata.get("evidence_sha256") else "no"
        row = (
            f"{task.id[:26]:26} "
            f"{task.status.value[:12]:12} "
            f"phase={_clip(task.metadata.get('phase_cursor', ''), 16):16} "
            f"attempt={task.attempts}/{task.max_attempts} "
            f"evidence={evidence:<3} age={age}s "
            f"{_clip(task.title, max(8, width - 93))}"
        )
        lines.append(_paint(row, _state_color(task.status.value), color))

    lines.extend(_section("RUNTIME POLICY", width, color))
    runtime = profile.recommended_runtime()
    lines.append(
        " ".join(
            [
                f"backend={runtime.get('backend')}",
                f"quant={runtime.get('quantization')}",
                f"ctx={runtime.get('context_length')}",
                f"flash={str(runtime.get('flash_attention')).lower()}",
                f"vllm_candidate={str(runtime.get('vllm_candidate')).lower()}",
            ]
        )
    )
    lines.append(
        _paint(
            " Ctrl+C exit · auto-refresh is read-only · run/resume/continuous stay separate commands ",
            DIM,
            color,
        )
    )
    return "\n".join(lines)


def run_tui(
    store: SQLiteEngineeringStore,
    ledger: JsonContinuousLedger,
    *,
    env: dict[str, str],
    interval: float = 2.0,
    once: bool = False,
    color: bool | None = None,
    limit: int = 12,
) -> int:
    use_color = sys.stdout.isatty() if color is None else color
    try:
        while True:
            if not once and sys.stdout.isatty():
                sys.stdout.write("\x1b[2J\x1b[H")
            sys.stdout.write(
                build_dashboard(
                    store,
                    ledger,
                    env=env,
                    limit=limit,
                    color=use_color,
                )
                + "\n"
            )
            sys.stdout.flush()
            if once:
                return 0
            time.sleep(max(0.25, interval))
    except KeyboardInterrupt:
        return 0
