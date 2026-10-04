from __future__ import annotations

import dataclasses
import os
import platform
import subprocess
from pathlib import Path


@dataclasses.dataclass(frozen=True)
class HardwareProfile:
    os: str
    architecture: str
    cpu: str
    logical_cpus: int
    ram_total_gb: float
    ram_available_gb: float
    gpu: str
    profile: str

    def recommended_models(self) -> dict[str, str]:
        fast = "qwen2.5-coder:3b"
        coder = fast
        reasoning = fast
        default = fast
        if self.ram_available_gb >= 10:
            coder = "qwen2.5-coder:7b"
            reasoning = coder
            default = coder
        if self.ram_available_gb >= 14:
            reasoning = "qwen3:8b"
            default = reasoning
        return {
            "fast": fast,
            "coder": coder,
            "reasoning": reasoning,
            "default": default,
        }


def _memory_gb() -> tuple[float, float]:
    info: dict[str, int] = {}
    path = Path("/proc/meminfo")
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if ":" not in line:
                continue
            key, raw = line.split(":", 1)
            value = raw.strip().split()[0]
            if value.isdigit():
                info[key] = int(value)
    total = info.get("MemTotal", 0) / 1024 / 1024
    available = info.get("MemAvailable", info.get("MemFree", 0)) / 1024 / 1024
    return total, available


def _cpu_name() -> str:
    cpu = platform.processor().strip()
    if cpu:
        return cpu
    path = Path("/proc/cpuinfo")
    if path.exists():
        for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            if line.lower().startswith("model name") and ":" in line:
                return line.split(":", 1)[1].strip()
    return "unknown"


def _gpu_name() -> str:
    commands = (
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
        ["lspci"],
    )
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if result.returncode != 0:
            continue
        lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
        if command[0] == "lspci":
            lines = [
                line for line in lines
                if "vga compatible controller" in line.lower() or "3d controller" in line.lower()
            ]
        if lines:
            return lines[0][:240]
    return "none-detected"


def detect_hardware() -> HardwareProfile:
    total, available = _memory_gb()
    logical = os.cpu_count() or 1
    gpu = _gpu_name()
    if gpu != "none-detected":
        profile = "GPU"
    elif available >= 14:
        profile = "CPU_LARGE"
    elif available >= 10:
        profile = "CPU_MEDIUM"
    else:
        profile = "CPU_SMALL"
    return HardwareProfile(
        os=platform.platform(),
        architecture=platform.machine(),
        cpu=_cpu_name(),
        logical_cpus=logical,
        ram_total_gb=round(total, 2),
        ram_available_gb=round(available, 2),
        gpu=gpu,
        profile=profile,
    )
