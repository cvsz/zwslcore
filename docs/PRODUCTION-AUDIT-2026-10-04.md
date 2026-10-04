# Production audit — 2026-10-04

## Scope

Deep review of the Windows 11 -> WSL2 -> Ubuntu 26.04 -> Docker -> Ollama/LiteLLM/Provider/Open WebUI path, including install lifecycle, configuration, runtime health, model selection, authentication boundaries, CI and dependency maintenance.

## Fixed

- WSL distro parsing accepts table/prose output and NUL-padded output.
- Existing WSL2 distributions skip redundant conversion.
- systemd is activated and verified before Docker bootstrap.
- Linux user, branch and repository installer inputs are validated.
- Docker Engine is installed from the official Docker Ubuntu repository.
- Runtime image defaults are pinned to stable tags rather than mutable latest/main tags.
- Existing known mutable defaults are migrated automatically without overwriting explicit custom image overrides.
- Cloud fallback remains disabled by default; LiteLLM no longer carries an always-declared OpenRouter route.
- RAM-aware model selection now updates Provider and LiteLLM model aliases so configured routes match models actually pulled into Ollama.
- Provider is built explicitly before the stack starts.
- Health checks use service readiness endpoints and expose diagnostics on failure.
- Open WebUI has a container healthcheck.
- Windows runtime checks execute inside the WSL checkout so they use the active runtime secrets and Docker daemon.
- Installer performs an authenticated inference smoke test after health becomes green.
- CI syntax-checks shell/PowerShell assets, renders Compose, rejects mutable default image tags and builds the provider image.
- Dependabot now covers provider Python dependencies and its Dockerfile.

## Security posture

- Host-published service ports bind to loopback.
- Open WebUI sign-up is disabled by default.
- Provider authentication remains mandatory by default.
- Generated runtime secrets are stored only in ignored `.env`, which is forced to mode 0600 in Linux.
- Cloud provider keys remain optional and cloud fallback is opt-in.
- Provider container runs as a non-root user with a read-only root filesystem, dropped capabilities and no-new-privileges.

## Verification gates

Repository readiness requires:

1. CI success.
2. CodeQL success.
3. Dependency Review success.
4. `scripts/doctor-wsl.ps1` success on Windows.
5. `scripts/doctor-wsl.ps1 -Smoke` success for end-to-end inference.
6. `docker compose ps` showing healthy runtime services.

## Residual controlled risks

- The in-repo Provider Python dependency graph still resolves transitive packages during image build. CI builds the image and Dependabot monitors direct dependencies, but a fully hashed transitive lockfile remains a future supply-chain improvement.
- Docker image release tags are stable version pins but not registry digests. For environments requiring immutable artifact identity, promote tested images by digest in `.env`.
- Ollama model tags identify upstream model artifacts but are not mirrored into a private immutable model registry.

These are controlled release-hardening opportunities rather than blockers for the loopback-only single-host runtime.
