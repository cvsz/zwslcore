# zwslcore Architecture

## Purpose and system boundary

`zwslcore` is a WSL2-first, local-first AI model-serving stack for Windows 11 and compatible Linux environments. It combines a local model runtime, an OpenAI-compatible Provider Gateway, optional UI and routing services, model catalog utilities, operator scripts, and a local engineering control plane.

The repository also carries ZEAZDEV's reusable governance and agent-execution baseline. That baseline supports repository safety; it is not a substitute for application-specific runtime design or operational evidence.

`zwslcore` serves LLM requests and local engineering workflows. It is **not** the video-generation runtime, media-processing worker pool, or publication service.

## Runtime layers

| Layer | Components | Responsibility |
|---|---|---|
| Client/UI | Open WebUI and compatible API clients | User interaction and client integration |
| API gateway | `services/provider/zeaz_provider` | Request validation, authentication, rate/concurrency limits, provider routing, compatibility conversion, audit events, and observability |
| Model routing | LiteLLM and the Provider's configured upstream adapters | Model aliasing and routing to explicitly configured targets |
| Local inference | Ollama and installed local models | Local-first LLM inference on qualified host resources |
| Model catalog | `services/model_catalog`, `scripts/models-dev.py`, and model-manifest tools | Inventory, metadata refresh, model selection, and resource-aware recommendations |
| Engineering runtime | `services/engineering` and `scripts/engineer.py` | Durable local tasks, isolated worktrees, bounded agent execution, validation, review, and evidence capture |
| Persistence | Docker volumes, local state, and operator-managed PostgreSQL for LiteLLM | Runtime state and application data; host PostgreSQL remains outside the Compose stack |
| Operations | `scripts/install.sh`, `scripts/doctor.sh`, `scripts/smoke.sh`, backup/restore, and capacity tools | Installation, diagnostics, recovery, and resource visibility |

## Request path

The normal local path is:

1. A user or compatible client submits an LLM request through Open WebUI or the Provider API.
2. The Provider Gateway validates the request and enforces authentication, rate/concurrency limits, cost policy, routing policy, and request auditing.
3. The configured route selects a permitted provider/model target. Local Ollama-backed inference is the default deployment path; any external provider must be explicitly configured and permitted by policy.
4. The gateway returns a normalized response and records bounded operational telemetry.

The exact available models and routes are determined by the active provider configuration, installed model inventory, and cost policy. A configured alias is not proof that a model is installed or that a remote provider is reachable.

## Deployment profiles

### WSL2 runtime

The full Compose profile runs the Provider, Ollama, LiteLLM, and Open WebUI. Published ports bind to loopback by default. The LiteLLM PostgreSQL database is operator-managed on the host and is not started by Compose.

Use the repository's installer, health checks, smoke tests, capacity report, and backup/restore runbooks. Do not replace the host's existing production services or overwrite an existing `.env` during setup.

### Cloud Shell CLI-only profile

`scripts/cloudshell.sh` and `scripts/ai.sh` provide a separate CLI-only profile. The default path intentionally does not install Docker, PostgreSQL, the full Compose stack, or local model weights. Cloud Shell is ephemeral and must not be treated as an always-on production host.

### Optional Cloudflare host profile

The optional Cloudflare profile maps the Provider and Open WebUI to loopback host ports for use behind the existing tunnel/proxy. It does not make Ollama or LiteLLM public. Follow [the Cloudflare tunnel runbook](CLOUDSHELL-CLOUDFLARE-TUNNEL.md) for the relevant deployment path.

## Security and reliability invariants

- Prefer local inference and keep automatic paid/external inference fallback disabled.
- External provider use requires explicit configuration, credentials, and a compatible cost policy; a missing local worker must not silently trigger a paid provider.
- Bind services to loopback by default. Public exposure requires an explicit, reviewed proxy/authentication configuration.
- Do not commit model weights, secrets, tokens, private keys, or production configuration.
- Pass user-controlled input as data, not shell code; enforce path, size, timeout, and resource limits at trust boundaries.
- Keep local engineering work isolated and bounded. The engineering runtime does not remotely push changes.
- Keep CI, dependency review, CodeQL, container scanning, and release gates blocking. Do not suppress findings merely to obtain a green build.
- A successful mock test or container build is not evidence of live provider inference or production readiness.

## ZEAZDEV integration boundaries

### ZCoder

ZCoder may use the Provider API for prompt planning, storyboards, code assistance, and other LLM tasks. It must not be treated as a video-generation runtime, and zwslcore must not be coupled to ZCoder's internal database or runtime implementation.

### ZWorkforce

ZWorkforce may orchestrate higher-level workflows through versioned HTTP APIs and authenticated webhooks. Keep job ownership and domain state in the owning service; use explicit service credentials, idempotency keys, and replay protection. Do not create circular runtime dependencies.

### CMe API

If CMe is approved for identity or shared metadata, integrate through a documented API contract. Do not couple zwslcore directly to CMe's internal database tables.

### ZEAZDEV Video Factory

The proposed Video Factory architecture (ZDVF-ARCH-001, v1.0) separates its control plane, inference workers, media pipeline, and artifact plane. Preserve that separation:

- zwslcore may provide LLM capabilities used for prompt refinement or planning through its supported API.
- Video generation, MiniMax H3 model weights/runtime, FFmpeg orchestration, media QA, artifact storage, and publication approval belong to the separate Video Factory system and qualified workers.
- Do not load H3 weights into Ollama/LiteLLM or represent an LLM endpoint as a video-generation engine.
- Connect systems only through an approved, versioned API or authenticated webhook. Never share internal database tables.
- Keep external inference disabled unless an administrator explicitly enables a reviewed provider path.

These are architecture boundaries, not a claim that ZCoder, ZWorkforce, CMe, or Video Factory integration has been implemented or end-to-end verified.

## Evidence and release posture

Architecture documentation describes intended boundaries. Production readiness still requires exact-head CI, security and dependency scans, provider/model compatibility evidence, live smoke tests on the target environment, backup/restore and rollback evidence, and independent review where required.

## Related documentation

- [README and operating commands](../README.md)
- [Engineering control plane](ENGINEERING-CONTROL-PLANE.md)
- [Production readiness](PRODUCTION-READINESS.md)
- [Backup and restore](BACKUP-RESTORE.md)
- [Cloud Shell / Cloudflare tunnel](CLOUDSHELL-CLOUDFLARE-TUNNEL.md)
- [Repository baseline rollout](repository-rollout.md)
- [ADR 0001: Runtime and Video Factory boundary](adr/0001-zwslcore-runtime-boundary.md)
