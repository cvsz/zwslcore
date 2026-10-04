# Acceleration and quantization policy

zwslcore keeps Ollama as the default local inference backend and chooses a safe runtime profile from detected hardware.

## Current host behavior

On CPU-only or unsupported-GPU hosts:

- backend: Ollama
- quantization policy: Q4_K_M
- context length: 4096
- Flash Attention: disabled
- vLLM: not selected

This is the expected profile for the current Ryzen 5 3400G WSL host when no supported compute GPU is visible inside WSL.

## NVIDIA profile

When `nvidia-smi` is available:

- 8-15 GiB VRAM: context 8192, Flash Attention enabled
- 16+ GiB VRAM: context 16384, Flash Attention enabled
- vLLM becomes a candidate at 8+ GiB VRAM

Ollama remains the default backend unless the operator explicitly chooses another runtime.

## ROCm profile

When `rocminfo` succeeds:

- backend remains Ollama
- Flash Attention is enabled
- context defaults conservatively to 4096 unless reliable VRAM information is available
- vLLM is only considered when a suitable GPU memory budget is known

## Quantization

`ZEAZ_QUANTIZATION_PROFILE=Q4_K_M` is the default policy for local consumer hardware. It describes the preferred weight quantization class; the exact model artifact is still determined by the configured Ollama model tag.

To use another quantized artifact, override the model variables in the untracked `.env`, for example:

    ZEAZ_FAST_MODEL=<your-valid-ollama-model-tag>
    ZEAZ_CODER_MODEL=<your-valid-ollama-model-tag>

Do not invent model tags. Confirm that a tag exists in the model registry before changing it.

## Runtime settings

The installer manages:

    ZEAZ_ACCELERATOR_MODE=auto
    ZEAZ_QUANTIZATION_PROFILE=Q4_K_M
    ZEAZ_OLLAMA_CONTEXT_LENGTH=4096
    ZEAZ_OLLAMA_FLASH_ATTENTION=false

Ollama receives the context and Flash Attention values through Compose.

## vLLM

vLLM is intentionally not installed or started by default. It is best treated as an optional high-throughput backend for supported accelerators.

The hardware profile reports `vllm_candidate=true` only when the host has a sufficiently capable accelerator profile. This flag is advisory; it does not install packages, download models, or change the active backend.

## Operator verification

From Windows PowerShell:

    .\scripts\engineer-wsl.ps1 profile

Then confirm runtime health:

    .\scripts\doctor-wsl.ps1 -Smoke

The profile output includes:

- accelerator backend
- detected GPU and memory when available
- recommended quantization policy
- recommended context length
- Flash Attention recommendation
- whether vLLM is a candidate
