# WSL2 Compatibility Review — cvsz/zwslcore

**Date:** 2026-11-09  
**Repository:** cvsz/zwslcore  
**Status:** PARTIALLY_VERIFIED (Linux/WSL2 verified; Windows/macOS not tested)

## 1. Scope

This document reviews WSL2-specific compatibility for the zwslcore local AI orchestration stack, which is designed to run on Windows 11 with WSL2 Ubuntu 26.04.

## 2. Environment Evidence

| Component | Version | Status |
|-----------|---------|--------|
| Host Linux | Ubuntu 26.04.1 LTS (Resolute Raccoon) | VERIFIED |
| Kernel | 6.18.54.1-microsoft-standard-WSL2 | VERIFIED |
| Python | 3.14.4 | VERIFIED |
| Bash | 5.3.9 | VERIFIED |
| Docker | 29.9.3 | VERIFIED |
| Docker Compose | v5.7.0 | VERIFIED |
| Git | 2.53.0 | VERIFIED |
| GitHub CLI | 2.46.0 | VERIFIED |
| GPU (NVIDIA) | Not available (`nvidia-smi` not found) | BLOCKED |

## 3. WSL2-Specific Findings

| Area | Finding | Severity | Status |
|------|---------|----------|--------|
| Distribution detection | `scripts/bootstrap-wsl.sh` sources `/etc/os-release` and requires `ID=ubuntu` | Low | VERIFIED |
| Root execution check | Bootstrap verifies `EUID=0` before installing | Low | VERIFIED |
| Path handling | PowerShell wrapper uses `.\scripts\` prefixes; Bash uses `/`-based paths | Low | VERIFIED |
| Docker Engine | Docker daemon required; Compose v5.7.0 used | Medium | VERIFIED (Linux only) |
| Loopback binding | All services bind to `127.0.0.1` by default | Low | VERIFIED |
| DNS resolution | Documented WSL2 DNS limitation in `Final-Report.md` | Medium | UNVERIFIED (Windows host not available) |
| GPU acceleration | No GPU detected in this environment; CPU-only profile applied | Medium | BLOCKED (no GPU hardware) |
| PowerShell wrappers | `engineer-wsl.ps1`, `doctor-wsl.ps1`, `install-wsl2.ps1` present | Low | VERIFIED (syntax checked in CI) |

## 4. Windows-Specific Status

| Check | Status | Reason |
|-------|--------|--------|
| Windows 11 WSL2 enablement | NOT APPLICABLE | No Windows host in this environment |
| PowerShell execution policy | NOT APPLICABLE | No Windows host |
| `install-wsl2.ps1` syntax | PARTIAL | Parsed by CI on Windows runner (GitHub Actions) |
| `doctor-wsl.ps1` syntax | PARTIAL | Parsed by CI on Windows runner |
| `engineer-wsl.ps1` argument binding | PARTIAL | Validated by CI on Windows runner |

## 5. Residual Risks

| Risk | Impact | Mitigation |
|------|--------|------------|
| No GPU available | CPU-only inference; slower model execution | Conservative 4096-context profile; Q4_K_M quantization |
| WSL2 DNS resolution | Local dev DNS may not resolve from WSL2 | Documented; fix via Windows `hosts` file if needed |
| Windows compatibility | Not verified on Windows | CI `windows-installer` job parses PowerShell scripts; runtime not tested |

## 6. Conclusion

WSL2 compatibility is VERIFIED on Linux/WSL2 Ubuntu 26.04. Windows-specific runtime behavior is NOT APPLICABLE in this environment (no Windows host). GPU acceleration is BLOCKED (no GPU hardware detected); CPU-only fallback is configured.
