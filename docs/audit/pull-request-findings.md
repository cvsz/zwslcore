# Pull Request Findings — cvsz/zwslcore

**Generated:** 2026-11-08  
**Total PRs reviewed:** 110  
**PRs with verified defects:** 3 (see below)  
**PRs requiring independent review:** 12 (open, security-sensitive or architectural)

---

## Findings by PR

### PR #87 — fix(security): patch critical certifi in hashed provider lock (DRAFT, OPEN)

**Finding:** The certifi update alone (2026.7.22 → 2026.10.19) does not resolve the image-level Critical vulnerability (CVE-2026-115557 in Chainguard `python:latest` base image). Independent review confirmed this PR is insufficient as a standalone fix for issue #108.

**Severity:** Medium  
**Status:** OPEN — DRAFT, stale base (f031984954d1), non-mergeable  
**Recommendation:** Close as superseded by the direct Dockerfile base image digest fix (issue #108 remediation, committed on feat/zwslcore-enterprise-hardening).

---

### PR #88 — ci(security): automate reviewed Provider base-image digest refresh (DRAFT, OPEN)

**Finding:** Creates two new workflow files (digestabot + lock refresh) but does not directly fix the current image. The lock refresh workflow uses `python:3.14.7-slim-bookworm` which cannot resolve a compatible PyYAML 6.0.3 wheel under hash-only binary install policy. The image build fails on this candidate.

**Severity:** Medium  
**Status:** OPEN — DRAFT, stale base (f031984954d1), non-mergeable  
**Recommendation:** Close as superseded by the direct Dockerfile base image digest fix. The digestabot automation concept is valid and could be re-proposed as a separate enhancement after the base image fix is merged.

---

### PR #89 — feat: add MiniMax-H3 GGUF video generation model support (OPEN)

**Finding:** Adds video generation model support (MiniMax-H3, 20B parameters) via stable-diffusion.cpp. This is out of scope for zwslcore, which is a chat/AI gateway, not a video generation platform. The PR adds ~330 lines of documentation and Modelfile templates but no runtime integration with the Provider chat API.

**Severity:** Low (scope creep)  
**Status:** OPEN  
**Recommendation:** Close or move to a separate repository. The MiniMax-H3 model is not related to the Provider's chat/completion routing and introduces unrelated dependencies (stable-diffusion.cpp, Comfy-Org VAEs).

---

### PR #90 — feat: add GGUF model support via Ollama Modelfile import (OPEN)

**Finding:** Changes default Ollama models from `qwen2.5-coder:3b/7b` and `qwen3:8b` to GGUF-imported `zwslcore-qwen-1.5b-q4km` and `zwslcore-qwen-7b-q4km`. Requires model files from an external server (`ssh -p 2223 cvsz@192.168.1.85:/home/cvsz/zcoder/models/`). This changes runtime behavior and defaults.

**Severity:** Medium  
**Status:** OPEN  
**Recommendation:** Review carefully before merge. The GGUF import feature is useful but changes default model aliases. The external model source (192.168.1.85) is not reproducible in CI. Consider keeping existing Ollama registry pulls as defaults and making GGUF import opt-in.

---

### PR #91 — refactor(architecture): define zwslcore runtime and Video Factory (DRAFT, OPEN)

**Finding:** Defines a runtime architecture boundary and references a "Video Factory" concept. 131 additions, 39 deletions across 5 files. DRAFT with no implementation completeness evidence.

**Severity:** Low  
**Status:** OPEN — DRAFT  
**Recommendation:** Keep DRAFT until implementation is complete and test coverage is added.

---

### PR #101 — build(deps): update fastapi requirement from <0.143 to <0.163 (OPEN)

**Finding:** Widens the FastAPI version constraint from `<0.143` to `<0.163`. Current lock has `fastapi==0.142.4`. This allows newer FastAPI versions but requires lockfile regeneration and testing.

**Severity:** Low  
**Status:** OPEN  
**Recommendation:** Review and merge after regenerating `requirements.lock` with `--upgrade-package fastapi` and running tests.

---

### PR #102 — fix(engineering): harden worktree ownership rollback (DRAFT, OPEN, 9676 additions)

**Finding:** Large security hardening PR (75 files, 9676 additions). Adds `.env.protection.backup*`, `.env.local`, `*.pem`, `*.key`, `services/provider/config/s3.local.yaml` to `.gitignore`. Adds `ORC_MASTER_PROMPT.md` (1238 lines). Various hardening changes to backup/restore, MCP, and engineering scripts.

**Severity:** High (large surface area)  
**Status:** OPEN — DRAFT, stale base (df7ef0eae393)  
**Recommendation:** Keep DRAFT until: (1) base is refreshed to current main, (2) changes are split into reviewable units, (3) independent security review is completed, (4) tests are added for all new security controls.

---

### PR #107 — build(deps): bump trufflesecurity/trufflehog from 3.99.7 to 3.99.8 (OPEN)

**Finding:** Minor Dependabot update. Low risk.

**Severity:** Low  
**Status:** OPEN  
**Recommendation:** Review and merge.

---

### Dependabot PRs #84, #85 — CodeQL v4.39.1 (OPEN)

**Finding:** Bump CodeQL actions from v4 to v4.39.1. Two separate PRs (init and analyze). Low risk security tooling update.

**Severity:** Low  
**Status:** OPEN  
**Recommendation:** Review and merge together.

---

### Closed Without Merge — Notable

| # | Title | Reason |
|---|-------|--------|
| #55 | Merge all feature branches into main | Not merged — individual feature branches were merged directly instead |
| #81 | fix: move LiteLLM PostgreSQL into Docker | Duplicate of #82 (policedbc vs cvsz author) |
| #94, #95, #96 | build: add make release pre-flight target | Duplicate PRs; #97 (cvsz) was merged |
| #100 | bump trufflehog 3.86.1→3.99.7 | Superseded by #107 |
| #103 | auto audit/review/approve workflow | Not adopted — workflow not merged |
| #104 | auto-fix open PRs workflow | Not adopted — workflow not merged |

---

## Security-Sensitive PRs Requiring Independent Review

The following open PRs touch security boundaries and require independent review before merge:

1. **#69** — dotenv loading in ai.sh (symlink rejection, permission checks, key allowlisting)
2. **#70** — dotenv provider config loading (credential chaining via ${VAR})
3. **#76** — MCP diagnostics + cloudflare SSH access (network boundary)
4. **#77** — webhook request body timeout (DoS protection)
5. **#79** — MCP session hardening, rate limiter, restore (multiple security controls)
6. **#80** — zcloud recovery script (path traversal, credential handling)
7. **#82** — PostgreSQL in Docker (database security, credential isolation)
8. **#87** — certifi lock update (supply chain, insufficient alone)
9. **#102** — worktree ownership rollback (path isolation, permission bypass)

---

## Duplicate / Overlapping PRs

| Group | PRs | Recommendation |
|-------|-----|----------------|
| Release pre-flight | #94, #95, #96, #97 | #97 merged; close others as superseded |
| FastAPI update | #65, #83, #101 | #101 open; close #65, #83 as superseded |
| CodeQL init | #67, #84 | #84 open; close #67 as superseded |
| CodeQL analyze | #66, #85 | #85 open; close #66 as superseded |
| TruffleHog | #100, #107 | #107 open; close #100 as superseded |
| LiteLLM PostgreSQL | #81, #82 | #82 open (cvsz); close #81 (policedbc) as duplicate |
| Python bump | #5, #22 | #22 merged; close #5 as superseded |
