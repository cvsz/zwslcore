# Windows + WSL2 full installation

This installer provisions a Windows host from PowerShell through a complete zwslcore runtime.

## Installed components

### Windows

- Windows Subsystem for Linux
- Virtual Machine Platform
- current WSL package/kernel
- WSL2 as the default engine
- Ubuntu 26.04 when it is present in `wsl --list --online`

### Ubuntu

- systemd
- ca-certificates
- curl
- Git
- GnuPG
- jq
- Make
- OpenSSL
- Python 3, pip and venv
- build-essential
- unzip / zip
- rsync
- procps / iproute2
- Docker Engine
- containerd
- Docker Buildx
- Docker Compose plugin
- zwslcore AI runtime

Docker is installed from Docker's official Ubuntu APT repository.

## Full install

Open **PowerShell as Administrator** from the zwslcore repository:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-wsl2.ps1
```

Default target:

```text
Distro     Ubuntu-26.04
Linux user cvsz
```

If Windows enables WSL/virtualization features and reports that a restart is required, restart Windows and run the same command again. The installer is designed to be rerunnable.

If Ubuntu 26.04 is unavailable in the host WSL catalog and Ubuntu 24.04 is acceptable:

```powershell
.\scripts\install-wsl2.ps1 -AllowFallback
```

Install WSL2, Ubuntu and host prerequisites only:

```powershell
.\scripts\install-wsl2.ps1 -SkipStackInstall
```

Override the Linux user:

```powershell
.\scripts\install-wsl2.ps1 -LinuxUser myuser
```

## New Linux user

When the requested Linux account does not already exist, the installer creates it, adds it to the `sudo` and `docker` groups, and invokes `passwd` interactively so its password is never placed in command arguments, environment variables, logs, or repository files.

## Verification

```powershell
wsl --status
wsl -l -v
wsl -d Ubuntu-26.04 -- bash -lc "ps -p 1 -o comm="
wsl -d Ubuntu-26.04 -- bash -lc "docker version"
wsl -d Ubuntu-26.04 -- bash -lc "docker compose version"
wsl -d Ubuntu-26.04 -- bash -lc "cd ~/zwslcore && make doctor"
```

Expected application endpoints:

```text
Open WebUI  http://localhost:3000
Provider    http://localhost:8080
LiteLLM     http://localhost:4000
Ollama      http://localhost:11434
```

## Safety and rollback

- The installer does not unregister or delete existing WSL distributions.
- It does not delete Docker images, containers, volumes, or model data.
- AI service ports remain loopback-only by default.
- Provider keys remain in the ignored local `.env`.
- Cloud fallback remains disabled unless explicitly configured.
- `wsl --unregister` is intentionally not part of automated recovery because it permanently deletes the selected distribution and its data.
