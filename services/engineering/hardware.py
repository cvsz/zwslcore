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
    accelerator_backend: str = "cpu"
    gpu_memory_gb: float = 0.0

    def recommended_runtime(self) -> dict[str, object]:
        if self.accelerator_backend == "nvidia":
            if self.gpu_memory_gb >= 16:
                return {
                    "backend": "ollama",
                    "quantization": "Q4_K_M",
                    "context_length": 16384,
                    "flash_attention": True,
                    "vllm_candidate": True,
                }
            if self.gpu_memory_gb >= 8:
                return {
                    "backend": "ollama",
                    "quantization": "Q4_K_M",
                    "context_length": 8192,
                    "flash_attention": True,
                    "vllm_candidate": True,
                }
        if self.accelerator_backend == "rocm":
            return {
                "backend": "ollama",
                "quantization": "Q4_K_M",
                "context_length": 8192 if self.gpu_memory_gb >= 8 else 4096,
                "flash_attention": True,
                "vllm_candidate": self.gpu_memory_gb >= 8,
            }
        return {
            "backend": "ollama",
            "quantization": "Q4_K_M",
            "context_length": 4096,
            "flash_attention": False,
            "vllm_candidate": False,
        }

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
            "engineering": fast,
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


def _gpu_info() -> tuple[str, bool, str, float]:
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=3,
        )
        if result.returncode == 0:
            first = next((line.strip() for line in result.stdout.splitlines() if line.strip()), "")
            if first:
                name, _, memory = first.rpartition(",")
                memory_gb = float(memory.strip()) / 1024 if memory.strip() else 0.0
                return name.strip()[:240], True, "nvidia", round(memory_gb, 2)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        pass

    try:
        result = subprocess.run(["rocminfo"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            lines = [line.strip() for line in result.stdout.splitlines() if "name:" in line.lower()]
            if lines:
                return lines[0][:240], True, "rocm", 0.0
    except (OSError, subprocess.TimeoutExpired):
        pass

    try:
        result = subprocess.run(["lspci"], capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            lines = [
                line.strip()
                for line in result.stdout.splitlines()
                if "vga compatible controller" in line.lower() or "3d controller" in line.lower()
            ]
            if lines:
                return lines[0][:240], False, "detected-only", 0.0
    except (OSError, subprocess.TimeoutExpired):
        pass

    return "none-detected", False, "cpu", 0.0


def detect_hardware() -> HardwareProfile:
    total, available = _memory_gb()
    logical = os.cpu_count() or 1
    gpu, accelerator_ready, accelerator_backend, gpu_memory_gb = _gpu_info()
    if accelerator_ready:
        profile = "GPU_READY"
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
        accelerator_backend=accelerator_backend,
        gpu_memory_gb=gpu_memory_gb,
    )
