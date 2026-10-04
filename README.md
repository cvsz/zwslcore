# zwslcore

WSL2-first local AI orchestration stack for Ubuntu 26.04. It contains its own integrated provider gateway, local-model runtime, model catalog, installer, diagnostics, and UI orchestration. Runtime operation does not require cloning or importing any other ZEAZ repository.

## Runtime

```text
Windows 11
└── WSL2 Ubuntu 26.04
    └── zwslcore
        ├── Ollama
        │   ├── qwen2.5-coder:3b
        │   ├── qwen2.5-coder:7b
        │   └── qwen3:8b
        ├── LiteLLM
        ├── zwslcore Provider Gateway
        │   ├── zeaz-fast
        │   ├── zeaz-coder
        │   ├── zeaz-reasoning
        │   ├── zeaz-local
        │   ├── zeaz-free
        │   └── zeaz-auto
        └── Open WebUI
```

All published ports bind to `127.0.0.1` by default.

## Windows one-command host bootstrap

For a new Windows 11 machine, open **PowerShell as Administrator** from this repository:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\scripts\install-wsl2.ps1
```

This installs/enables WSL2, Ubuntu 26.04, systemd, Git, Python, build tools, Docker Engine, Buildx, Docker Compose and then installs zwslcore. A Windows restart may be required after enabling virtualization features; rerun the same command afterward.

See [Windows + WSL2 full installation](docs/WINDOWS-WSL2-INSTALL.md).

## Install

Prerequisites:

- WSL2 Ubuntu 26.04 or compatible Linux
- Docker Engine
- Docker Compose plugin
- Python 3
- curl

From the repository:

```bash
cd ~/zwslcore
git pull
make install
```

The installer:

1. creates a private `.env` when missing;
2. generates Open WebUI and LiteLLM secrets locally;
3. validates Compose;
4. starts Ollama;
5. detects currently available memory;
6. pulls CPU-friendly models appropriate to available RAM;
7. starts LiteLLM and Open WebUI;
8. runs runtime diagnostics.

Open:

```text
Open WebUI  http://localhost:3000
Provider    http://localhost:8080
LiteLLM     http://localhost:4000
Ollama      http://localhost:11434
```

## Operations

```bash
make doctor
make smoke
make models
make logs
make restart
make down
make up
```

Validate configuration and repository checks:

```bash
make config
make ci
```

## Local engineering control plane

zwslcore now includes a self-contained local engineering runtime refactored from proven patterns in `cvsz/zcoder`. There is no runtime dependency on zcoder.

Capabilities:

- durable SQLite WAL task/checkpoint state;
- isolated Git worktrees under `~/.zwslcore/worktrees`;
- bounded secret-aware repository snapshots;
- planning/editing through the local zwslcore Provider;
- path traversal and secret-bearing file protection;
- operator-supplied validation commands;
- deterministic static review and fail-closed security gate;
- local commits only when explicitly requested;
- bounded UPGRADE / UPDATE / IMPLEMENT_FEATURE / REPAIR orchestration;
- hardware profiling with deterministic local-model recommendations;
- durable continuous-work ledger with restart-safe attempt budgets.

Example:

```bash
TASK_ID="$(python3 scripts/engineer.py create "Fix provider health" \
  --description "Repair readiness behavior without weakening tests" \
  --repository . \
  --risk medium)"

python3 scripts/engineer.py run "$TASK_ID" \
  --allow-path services \
  --validate "python3 -m unittest discover -s tests -v"

python3 scripts/engineer.py show "$TASK_ID"
```

Add `--commit` only when you want a local commit in the isolated worktree. The engineering runtime never performs a remote push.

From Windows PowerShell, use the WSL wrapper instead of calling Windows Python:

```powershell
.\scripts\engineer-wsl.ps1 list
.\scripts\engineer-wsl.ps1 create "Fix provider health" --description "Repair health handling" --repository . --risk medium
.\scripts\engineer-wsl.ps1 run TASK_ID --allow-path services --validate "python3 -m unittest discover -s tests -v"
```

PowerShell does not use Bash's trailing `\` for line continuation. Keep each wrapper command on one line, or use PowerShell's backtick when splitting a command.

See [Engineering Control Plane](docs/ENGINEERING-CONTROL-PLANE.md).

### Continuous engineering

Queue one bounded work item from PowerShell:

```powershell
.\scripts\engineer-wsl.ps1 work-add "Improve provider diagnostics" --kind REPAIR --description "Improve failure diagnostics without weakening tests" --repository . --risk medium --priority 80 --allow-path services --validate "python3 -m unittest discover -s tests -v"
```

Run queued work:

```powershell
.\scripts\engineer-wsl.ps1 continuous --max-iterations 4
```

Blocked/exhausted work does not silently reset its attempt budget across process restarts. To explicitly retry blocked work:

```powershell
.\scripts\engineer-wsl.ps1 continuous --max-iterations 4 --retry-blocked
```

### Cost policy

The Provider enforces `ZEAZ_COST_POLICY` at routing time:

- `ZERO_COST_ONLY` (default): permits only `FREE_LOCAL` and `FREE_REMOTE`.
- `PREFER_ZERO_COST`: ranks free routes before customer-key/paid routes.
- `PERMIT_PAID`: permits every configured cost class.

Cloud providers remain disabled unless `FREE_CLOUD_FALLBACK_ENABLED=true`, so the default installation remains local-only.


## Free model discovery

Local Ollama models are the default and require no provider API key.

To inspect currently declared zero-price OpenRouter text models:

```bash
python3 scripts/sync-free-models.py
```

Optionally export `OPENROUTER_API_KEY` before discovery or configure it only in the untracked `.env`. External free tiers and quotas can change and are not treated as permanently free.

## Windows runtime verification

The production runtime lives inside WSL. From PowerShell, use the wrapper instead of running Linux `make` targets from the Windows checkout:

```powershell
.\scripts\doctor-wsl.ps1
.\scripts\doctor-wsl.ps1 -Smoke
```

`-Smoke` performs an authenticated end-to-end inference test after the health checks.

## Runtime version policy

Default service images are pinned to tested stable release tags instead of mutable `latest` or `main` tags. The installer migrates the old known mutable defaults while preserving explicit custom image overrides. Upgrade image versions deliberately through `.env` and rerun `make install`.

## Security defaults

- Open WebUI, LiteLLM, and Ollama publish only to loopback.
- Open WebUI sign-up is disabled by default.
- Provider credentials are not committed.
- `.env` remains ignored.
- Cloud provider fallback is opt-in.
- Ollama is not intended to be exposed directly through Cloudflare or the public Internet.
- Existing repository governance, CodeQL, dependency review, and branch-protection tooling remain in place.

## Self-contained implementation

The runtime implementation required by this stack is stored inside this repository:

```text
services/
  provider/
    Dockerfile
    pyproject.toml
    config/providers.yaml
    zeaz_provider/
  model_catalog/
    catalog.py
  engineering/
    models.py
    store.py
    snapshot.py
    worktree.py
    review.py
    loop.py
    runtime.py
    hardware.py
    ledger.py
    continuous.py
config/
  litellm.yaml
scripts/
  install-wsl2.ps1
  bootstrap-wsl.sh
  install.sh
  doctor.sh
  create-local-models.sh
  sync-free-models.py
  engineer.py
```

No other ZEAZ repository is required at runtime. Historical component provenance and refactoring notes are documented in [Integrated components](docs/STACK-SOURCES.md), but those repositories are not runtime dependencies.

## Repository engineering controls

The repository retains its ZEAZ engineering baseline including:

- CI repository validation
- CodeQL
- Dependency Review
- Dependabot
- CODEOWNERS and PR governance
- secret-file checks
- repository administration verification tooling

A green repository CI run validates only the checks that ran. Production readiness still requires runtime, recovery, security, observability, and deployment evidence for the target environment.

## License

MIT. See `LICENSE`.
