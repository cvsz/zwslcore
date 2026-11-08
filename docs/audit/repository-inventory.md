# Repository Inventory — cvsz/zwslcore

**Generated:** 2026-11-08  
**Branch:** `main` at `bc1eb1c`  
**Working tree:** Clean (1 untracked operator-local file: `services/provider/config/s3.local.yaml`)

---

## Top-Level Structure

| Path | Type | Description |
|------|------|-------------|
| `AGENTS.md` | Doc | Repository agent contract (references SUPER ULTRA AI ORC v2.1) |
| `ZEAZ-INTRODUCTION.md` | Doc | ZEAZ engineering execution framework |
| `README.md` | Doc | Project overview and usage |
| `SECURITY.md` | Doc | Security policy and reporting |
| `GOVERNANCE.md` | Doc | Governance model |
| `ROADMAP.md` | Doc | Project roadmap |
| `IMPLEMENTATION-CHECKLIST.md` | Doc | Implementation/audit checklist |
| `AUDIT-REPORT.md` | Doc | Previous audit report |
| `FINAL-REPORT.md` | Doc | Final audit report |
| `Final-Report.md` | Doc | Duplicate final report (Thai language, non-compliant) |
| `final-report.md` | Doc | Duplicate final report |
| `CHANGELOG.md` | Doc | Change log |
| `CONTRIBUTING.md` | Doc | Contribution guidelines |
| `CODE_OF_CONDUCT.md` | Doc | Code of conduct |
| `ABOUT.md` | Doc | About |
| `LICENSE` | Doc | MIT license |
| `Makefile` | Build | Build and CI targets |
| `compose.yaml` | Config | Docker Compose stack |
| `Dockerfile` | Build | (Root placeholder) |
| `ecc-install.json` | Config | ECC installer config |
| `.editorconfig` | Config | Editor configuration |
| `.env.example` | Config | Environment variable template |
| `.env.cloudflare.example` | Config | Cloudflare profile template |
| `.env.production.example` | Config | Production template |
| `.gitattributes` | Config | Git attributes |
| `.gitignore` | Config | Git ignore rules |

---

## Directories

| Directory | Contents | Purpose |
|-----------|----------|---------|
| `.agents/skills/` | `scrutinize/SKILL.md` | Review skill definition |
| `.github/` | `workflows/`, `CODEOWNERS`, `scripts/` | CI/CD, governance, ownership |
| `.github/workflows/` | `ci.yml`, `codeql.yml`, `dependency-review.yml`, `provider-supply-chain.yml`, `auto-fix-open-prs.yml`, `automated-audit-review-approve.yml` | CI pipelines |
| `config/` | `agents.example.json`, `litellm.yaml`, `mcp.example.json` | Agent profiles, LiteLLM config, MCP config |
| `docs/` | 29 files + subdirs | Documentation (architecture, operations, security, audit) |
| `docs/audit/` | 4 files | Audit reports and matrices |
| `docs/adr/` | Architecture decision records | ADRs |
| `docs/ai/` | Reusable prompts and playbooks | AI agent playbooks |
| `docs/engineering/` | Engineering documentation | Control plane docs |
| `docs/evidence/` | Evidence bundles | Evidence storage |
| `docs/security/` | Security documents | CVE dispositions, risk acceptance |
| `scripts/` | 30+ scripts | Install, doctor, backup, restore, engineer, etc. |
| `services/provider/` | Provider gateway | Multi-provider AI gateway |
| `services/provider/zeaz_provider/` | 15 Python modules | Provider implementation |
| `services/provider/config/` | `providers.yaml` | Provider routing configuration |
| `services/engineering/` | 24 Python modules | Engineering control plane |
| `services/model_catalog/` | 5 Python modules | Model catalog and selection |
| `tests/` | 29 test files | Unit and integration tests |
| `templates/` | Templates | Project templates |
| `skills/` | Skills | Agent skills |
| `components.d/` | Components | Component definitions |
| `plugins.d/` | Plugins | Plugin definitions |
| `docker/postgres/` | Docker | PostgreSQL Docker config |

---

## Key Source Modules

### Provider Gateway (`services/provider/zeaz_provider/`)
| Module | Lines | Purpose |
|--------|-------|---------|
| `main.py` | 698 | FastAPI app, auth, routing, endpoints |
| `security.py` | 204 | Rate limiting, secret redaction, trusted proxy |
| `router.py` | ~90 | Provider routing logic |
| `providers.py` | ~110 | Provider client implementations |
| `config.py` | ~150 | Settings and configuration |
| `resilience.py` | ~60 | Circuit breakers, retries |
| `limits.py` | ~30 | Request/response size limits |
| `errors.py` | ~30 | Error types and handling |
| `normalize.py` | ~180 | Protocol normalization (OpenAI/Anthropic) |
| `streaming.py` | ~160 | SSE streaming |
| `observability.py` | ~60 | Metrics and observability |
| `structured.py` | ~30 | Structured output parsing |
| `capabilities.py` | ~60 | Model capability detection |
| `audit.py` | ~30 | Audit logging |

### Engineering Control Plane (`services/engineering/`)
| Module | Lines | Purpose |
|--------|-------|---------|
| `runtime.py` | ~4200 | EngineeringRuntime state machine |
| `store.py` | ~12700 | SQLite WAL task store |
| `ledger.py` | ~23000 | Durable continuous-work ledger |
| `worktree.py` | ~4500 | Git worktree management |
| `snapshot.py` | ~4700 | Change snapshots |
| `review.py` | ~2700 | Static review and security gate |
| `mcp.py` | ~11900 | Local stdio MCP client |
| `continuous.py` | ~12400 | Continuous work loop |
| `evidence.py` | ~8800 | Evidence bundles |
| `reconcile.py` | ~7600 | Orphan/task reconciliation |
| `validation.py` | ~2400 | Validation profiles |
| `hardware.py` | ~5600 | Hardware profiling |
| `agents.py` | ~7000 | Agent profiles and permissions |
| `delegation.py` | ~4400 | Subagent delegation |
| `loop.py` | ~7700 | Work loop |
| `models.py` | ~1800 | Data models |
| `tools.py` | ~1000 | Tool definitions |
| `observability.py` | ~5000 | Prometheus metrics |
| `tui.py` | ~9700 | Terminal UI |
| `lease.py` | ~5600 | Runner leases |
| `change_snapshot.py` | ~8200 | Change snapshots |

### Model Catalog (`services/model_catalog/`)
| Module | Lines | Purpose |
|--------|-------|---------|
| `catalog.py` | ~3700 | Model catalog |
| `inventory.py` | ~9200 | Ollama model inventory |
| `models_dev.py` | ~7400 | Models.dev integration |
| `selector.py` | ~10000 | Model selection and ranking |

---

## Configuration Files

| File | Status | Notes |
|------|--------|-------|
| `compose.yaml` | VERIFIED | All services loopback-only, digest-pinned images |
| `services/provider/Dockerfile` | UPDATED | Base image digests updated for issue #108 |
| `services/provider/pyproject.toml` | VERIFIED | Python 3.14+, hashed dependencies |
| `services/provider/requirements.lock` | VERIFIED | Hash-pinned dependencies |
| `services/provider/config/providers.yaml` | VERIFIED | Zero-cost policy, local-only default |
| `config/litellm.yaml` | VERIFIED | LiteLLM routing |
| `.env.example` | VERIFIED | Placeholders only, no real secrets |

---

## CI/CD Workflows

| Workflow | Status | Key Controls |
|----------|--------|-------------|
| `ci.yml` | VERIFIED | Repository validation, tests, shell syntax, Python compile, secret scanning (TruffleHog v3.99.7), Compose validation, Docker build |
| `codeql.yml` | VERIFIED | CodeQL v4 (Python) — outdated, PRs #84/#85 to v4.39.1 |
| `dependency-review.yml` | VERIFIED | Dependency review on PRs |
| `provider-supply-chain.yml` | VERIFIED | Image build, grype scan (fail on high), SBOM generation, attestation |
| `auto-fix-open-prs.yml` | PRESENT | Auto-fix workflow (not merged — PR #104) |
| `automated-audit-review-approve.yml` | PRESENT | Auto audit workflow (not merged — PR #103) |

---

## Dependencies

### Provider Python Dependencies (hash-pinned)
- fastapi==0.142.4, httpx==0.28.1, pydantic==2.14.1, prometheus-client==0.26.0
- PyYAML==6.0.3, redis==8.1.0, uvicorn[standard]==0.54.0
- opentelemetry-* ==1.45.1, python-dotenv==1.2.4
- Plus transitive dependencies (see `requirements.lock`)

### Docker Images (digest-pinned)
- `cgr.dev/chainguard/python:latest-dev@sha256:898360ca...` (build, UPDATED)
- `cgr.dev/chainguard/python:latest@sha256:1a009647...` (runtime, UPDATED)
- `ollama/ollama:0.40.2@sha256:b86366bb...`
- `ghcr.io/berriai/litellm:v1.104.2@sha256:3d88bd75...`
- `ghcr.io/open-webui/open-webui:v0.11.4@sha256:9591b13f...`

---

## Test Suite (29 test files)

| Test File | Purpose |
|-----------|---------|
| `test_ai_cli.py` | AI CLI secure dotenv loading |
| `test_backup_restore.py` | Backup/restore integrity |
| `test_bootstrap.py` | Bootstrap validation |
| `test_capacity.py` | Capacity reporting |
| `test_cloudshell_tunnel.py` | Cloud Shell tunnel |
| `test_engineering_agents.py` | Agent profiles |
| `test_engineering_change_snapshot.py` | Change snapshots |
| `test_engineering_control_plane.py` | Control plane state machine |
| `test_engineering_custom_agents.py` | Custom agent profiles |
| `test_engineering_delegation.py` | Subagent delegation |
| `test_engineering_evidence.py` | Evidence bundles |
| `test_engineering_mcp.py` | MCP client |
| `test_engineering_metrics.py` | Observability metrics |
| `test_engineering_observability.py` | Observability |
| `test_engineering_queue_lifecycle.py` | Queue state machine |
| `test_engineering_reconcile.py` | Reconciliation |
| `test_engineering_resume.py` | Resume/checkpoints |
| `test_engineering_runner_lease.py` | Runner leases |
| `test_engineering_transport_retry.py` | Transport retry |
| `test_engineering_tui.py` | Terminal UI |
| `test_engineering_validation.py` | Validation profiles |
| `test_env_loader.sh` | Dotenv loader shell test |
| `test_github_admin.py` | GitHub admin verification |
| `test_model_catalog.py` | Model catalog |
| `test_model_inventory.py` | Ollama inventory |
| `test_model_selector.py` | Model selection |
| `test_models_dev_catalog.py` | Models.dev catalog |
| `test_provider_structured_output.py` | Structured output |
| `test_structured_edit_parser.py` | Structured edit parsing |
| `test_supply_chain_dockerfile.py` | **NEW** Supply-chain regression |

**Total: 200 tests, all passing.**
