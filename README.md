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
6. detects CPU/NVIDIA/ROCm acceleration capability;
7. applies a hardware-aware Ollama runtime profile and quantization policy;
8. pulls local models appropriate to available RAM;
9. starts LiteLLM and Open WebUI;
10. runs runtime diagnostics.

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

### Cloudflare host profile

When zworkforce's Cloudflare Tunnel and Caddy proxy share this host, use the
optional profile to keep zwslcore clear of zworkforce's existing host ports:

```bash
make cloudflare-up
```

The command creates the ignored `.env.cloudflare` from its example when
missing, then starts Provider at `127.0.0.1:18086` and Open WebUI at
`127.0.0.1:18087`. Both remain loopback-only. The profile sets Open WebUI's
public URL and CORS allowlist to `https://zwsl.zeaz.dev`, enables secure
session cookies, and explicitly keeps signup disabled. Provider Bearer
authentication stays required, and Ollama/LiteLLM are not published through
the proxy.

The zworkforce Caddy route sends `/api/v1/models`,
`/api/v1/chat/completions`, `/api/v1/messages`, and `/api/v1/responses` to
Provider after removing the `/api` prefix. `/data/` maps to Open WebUI's
`/api/v1/files/` API and `/auth/` maps to `/api/v1/auths/`; other paths,
including `/oauth/`, go to Open WebUI's login and OAuth flows. Protected UI
and file operations remain behind Open WebUI authentication.

The normal `make up` command continues to use local defaults (`8080` and
`3000`). Recreating these containers with `make up` returns to those ports;
run `make cloudflare-up` again to restore the Cloudflare profile. Existing
Docker volumes are preserved when the containers are recreated.

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
- durable continuous-work ledger with restart-safe attempt budgets;
- secret-minimized evidence bundles with SHA-256 integrity verification;
- conservative task resume with HEAD-bound plan reuse and persisted phase cursors;
- strict-by-default validation with optional baseline-vs-delta regression gating.

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

### GPU acceleration and quantization

Run:

```powershell
.\scripts\engineer-wsl.ps1 profile
```

The profile reports the detected accelerator backend, GPU memory when available, recommended Ollama context size, Flash Attention setting, Q4_K_M quantization policy, and whether the host is a candidate for optional vLLM deployment.

Ollama remains the default backend. CPU-only hosts stay on the conservative 4096-context profile; supported NVIDIA/ROCm hosts receive larger context/Flash Attention recommendations without forcing GPU-only Compose settings.

See [Acceleration and quantization policy](docs/ACCELERATION.md).

### Engineering TUI

Open the read-only terminal dashboard from PowerShell:

```powershell
.\scripts\engineer-wsl.ps1 tui
```

Useful variants:

```powershell
.\scripts\engineer-wsl.ps1 tui --interval 1
.\scripts\engineer-wsl.ps1 tui --limit 20
.\scripts\engineer-wsl.ps1 tui --once --no-color
```

The TUI uses only the Python standard library and ANSI terminal control. It shows hardware profile, automatic model selection, queue state, attempt budgets, phase cursors, recent tasks, evidence availability and runtime policy. It is intentionally read-only; task mutation remains explicit through `run`, `resume`, `work-add` and `continuous`.

### Agent profiles and tool permissions

zwslcore now includes an OpenCode-inspired, independently implemented agent policy layer. Built-in profiles are `build`, `plan`, `review`, `explore`, and `general`.

```powershell
.\scripts\engineer-wsl.ps1 agents
.\scripts\engineer-wsl.ps1 tools
.\scripts\engineer-wsl.ps1 policy-check plan edit services/provider/main.py
```

Select a profile explicitly:

```powershell
.\scripts\engineer-wsl.ps1 run TASK_ID --agent build
.\scripts\engineer-wsl.ps1 run TASK_ID --agent plan
```

`plan`, `review`, and `explore` are read-only. `general` may edit and validate but cannot create a commit. Permission enforcement happens inside `EngineeringRuntime`; it is not only prompt text. See [OpenCode-inspired engineering patterns](docs/OPENCODE-PATTERNS.md).

### Custom agent profiles

Operator-defined profiles can be loaded from `~/.zwslcore/agents.json`. Custom profiles inherit from a built-in profile; omitting `extends` defaults to the read-only `plan` profile.

```powershell
Copy-Item .\config\agents.example.json $HOME\.zwslcore\agents.json
.\scripts\engineer-wsl.ps1 agents
.\scripts\engineer-wsl.ps1 policy-check architect edit services/provider/main.py
.\scripts\engineer-wsl.ps1 run TASK_ID --agent architect
```

Permission overrides retain ordered last-match semantics and are still subordinate to path scope, validators, static review and the security gate. Custom prompts are bounded and cannot bypass runtime permissions. See [Custom agent profiles](docs/CUSTOM-AGENTS.md).

### Durable subagent delegation

Subagent profiles can be queued as child tasks with their own attempt budget, evidence and lineage:

```powershell
.\scripts\engineer-wsl.ps1 delegate PARENT_TASK_ID "Inspect provider routing" --agent explore --allow-path services/provider
.\scripts\engineer-wsl.ps1 children PARENT_TASK_ID
.\scripts\engineer-wsl.ps1 lineage CHILD_TASK_ID
```

Delegation is bounded to depth 4. Only profiles marked `subagent` can be delegated. Child tasks never inherit remote-push capability, and their selected agent policy is enforced by `EngineeringRuntime`. Parent task metadata records each child's latest status, attempt count, error summary and evidence path.

### Local MCP registry

zwslcore now includes an operator-controlled local stdio MCP client. Configure servers in `~/.zwslcore/mcp/servers.json` and inspect/invoke them explicitly:

```powershell
.\scripts\engineer-wsl.ps1 mcp-status
.\scripts\engineer-wsl.ps1 mcp-tools
.\scripts\engineer-wsl.ps1 mcp-call local-tools.echo --json '{"value":"hello"}'
```

MCP processes start with `shell=False`, bounded request/message limits, and an environment allowlist. Autonomous agents do **not** receive MCP tool execution in this slice; remote HTTP/SSE/OAuth transports are also intentionally deferred. See [MCP integration](docs/MCP.md).

### Undo / redo engineering changes

Successful non-commit engineering runs capture a bounded local change snapshot under `~/.zwslcore/snapshots/<TASK_ID>/`. The snapshot stores a binary-capable Git patch plus SHA-256 metadata.

```powershell
.\scripts\engineer-wsl.ps1 snapshot-status TASK_ID
.\scripts\engineer-wsl.ps1 undo TASK_ID
.\scripts\engineer-wsl.ps1 redo TASK_ID
```

Undo is allowed only when the current managed worktree still matches the captured patch and HEAD. Redo is allowed only from the clean post-undo state. Any worktree or HEAD drift is fail-closed. Runs created with `--commit` rely on Git commit history instead and do not create this working-tree snapshot.

### Continuous engineering

Queue one bounded work item from PowerShell:

```powershell
.\scripts\engineer-wsl.ps1 work-add "Improve provider diagnostics" --kind REPAIR --description "Improve failure diagnostics without weakening tests" --repository . --risk medium --priority 80 --allow-path services --validate "python3 -m unittest discover -s tests -v"
```

Run queued work:

```powershell
.\scripts\engineer-wsl.ps1 continuous --max-iterations 4
```

Continuous runs emit live phase progress for baseline, worktree creation, scoped snapshot size, planning, editing, validation, security review, commit and final status. Autonomous engineering defaults to `ZEAZ_ENGINEERING_MODEL=auto`, which ranks only configured local Provider aliases against hardware fit, zero-cost policy, context and structured-output requirements. Explicit aliases such as `zeaz-fast`, `zeaz-coder` or `zeaz-local` still override automatic selection. From another PowerShell window, inspect a running item by fingerprint prefix:

```powershell
.\scripts\engineer-wsl.ps1 work-status 40780a4e4234
```

When `--allow-path` is supplied, repository context is built only from those paths. The default local-model snapshot is bounded to 32 KiB / 120 files / 64 KiB per file to avoid feeding multi-megabyte repositories into CPU-only models.

A blocked/failed task can be resumed without re-running planning when the managed worktree HEAD still matches the PLAN checkpoint baseline:

```powershell
.\scripts\engineer-wsl.ps1 resume TASK_ID
```

Resume always resets the managed worktree to clean HEAD and reruns EDITING, VALIDATING and REVIEWING. If HEAD changed, planning is performed again automatically. The previous run configuration is reused unless new `--validate`, `--allow-path`, `--commit` or `--no-commit` options are supplied.

Every completed or failed engineering task writes an evidence bundle under `~/.zwslcore/evidence/<TASK_ID>/`. Inspect or verify it with:

```powershell
.\scripts\engineer-wsl.ps1 evidence TASK_ID
.\scripts\engineer-wsl.ps1 evidence-show TASK_ID
.\scripts\engineer-wsl.ps1 evidence-verify TASK_ID
```

Evidence includes task state, checkpoint chronology, validation commands/return codes, review findings, Git HEAD/branch/changed paths, and hashes of diff/checkpoint payloads. Raw diff and validator stdout/stderr are not persisted by default.

Validation remains strict by default. For repositories with known pre-existing failures, opt in to baseline-vs-delta mode:

```powershell
.\scripts\engineer-wsl.ps1 work-add "Repair provider" --kind REPAIR --validation-mode delta --allow-path services --validate "python3 -m unittest discover -s tests -v"
```

Delta mode runs the validators on the clean worktree before editing and blocks only validators that regress from pass to fail. Existing failures are recorded as residual failures; improvements are recorded separately. Security/path/review gates are unchanged.

### Adaptive blocked-work recovery

For blocked autonomous work, use the bounded recovery command:

```powershell
.\scripts\engineer-wsl.ps1 recover --max-iterations 4
```

Recovery keeps the existing safety gates but adapts inference to the local machine:

- snapshot budget is derived from `ZEAZ_OLLAMA_CONTEXT_LENGTH` (4096 context -> 8192-byte repository snapshot);
- task/title terms prioritize relevant paths before the snapshot byte budget is exhausted;
- CPU_MEDIUM uses a quality ladder beginning with `zeaz-fast` and falling back to `zeaz-coder` when a real model-quality failure occurs;
- CPU_SMALL does not force a 7B fallback;
- transport, validator and security-gate failures do not trigger model escalation;
- selected model, fallback ladder and snapshot budget are written to task metadata/evidence.

The TUI shows the active ladder and the recovery command whenever blocked queue items exist.

Orphan tasks are never auto-cancelled. Reconciliation reports an explicit remediation choice:

```powershell
.\scripts\engineer-wsl.ps1 enqueue-task TASK_ID --kind REPAIR
.\scripts\engineer-wsl.ps1 cancel TASK_ID --reason "no longer required"
```

Cancellation is audited: the task moves to `CANCELLED`, a cancellation checkpoint is written, linked queue records are reconciled, and an evidence bundle is generated. Cancelling a `SUCCEEDED` task is refused.

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


## Models.dev catalog

zwslcore can optionally sync provider-agnostic model metadata and provider-specific offerings from [Models.dev](https://models.dev/) without making runtime startup depend on the public service.

```bash
make models-dev-sync
make models-dev-stats
python3 scripts/models-dev.py providers
python3 scripts/models-dev.py lookup openai/gpt-5.4
python3 scripts/models-dev.py recommend --structured-output --min-context 4096
```

The combined `catalog.json?type=all` endpoint is cached atomically under `~/.zwslcore/cache/models.dev.catalog.json`. Fresh cache is preferred; network refresh falls back to a stale cache when the service is unavailable. The cache retains canonical model metadata separately from provider offerings, including published capabilities, token limits and provider pricing. No provider API keys are sent to Models.dev.

This catalog is advisory metadata. Local Ollama availability and zwslcore Provider routing remain authoritative for what this machine can actually execute. The recommendation engine is explainable: every result includes its score, eligibility, reasons and blockers. Remote candidates are excluded unless `--include-remote` is requested, and remain ineligible when cloud fallback is disabled.

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

Default service images are pinned to tested stable release tags instead of mutable `latest` or `main` tags. The in-repo Provider runtime is pinned to Python 3.14.7 after package-install/import compatibility and built-image smoke validation in CI. The installer migrates the old known mutable defaults while preserving explicit custom image overrides. Upgrade image versions deliberately through `.env` and rerun `make install`.

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

See the [production-readiness matrix](docs/PRODUCTION-READINESS.md) for current gate states and evidence.

## License

MIT. See `LICENSE`.
