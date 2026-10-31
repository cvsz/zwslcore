# PR Dependency Graph

**Repository**: `cvsz/zwslcore`  
**Date**: 2026-11-01

---

## 1. Dependency Relationships

| PR | Depends On | Reason |
|-----|------------|--------|
| #78 | None | Standalone provider credentials change |
| #73 | None | Standalone Chat UI contract tests |
| #72 | #71 | Stacked on `feat/cloudshell-installer-20261017` branch (PR #71) |
| #71 | None | Standalone Cloud Shell installer |
| #82 | None | Standalone LiteLLM PostgreSQL change |
| #79 | None | Standalone MCP session hardening |
| #76 | None | Standalone CloudShell Access change |
| #85 | None | Standalone CodeQL Dependabot update |
| #84 | None | Standalone CodeQL Dependabot update |

No circular dependencies detected.

---

## 2. Shared Blockers

| Blocker | Affected PRs | Root Cause |
|---------|-------------|------------|
| CVE-2026-115557 (Critical, no fix) | #102, #101, #100, #91, #90, #89, #88, #87, #86, #85, #84, #82, #80, #79, #78, #76, #71 | Chainguard `python:latest` base image contains unpatched Critical CVE; `build-scan-sbom` fails with `severity-cutoff: high` |
| No independent review | #101, #100, #86, #82, #79, #76, #70, #69, #64 | policedbc review not yet requested |
| Review feedback pending | #102, #88, #87, #85, #84, #80, #71 | policedbc CHANGES_REQUESTED |
| Draft status | #91, #88, #87, #86, #82, #77, #69, #64 | PRs in draft state |
| Merge conflicts | #88, #87, #77 | Conflicting with base branch |
| No CI checks | #77 | No workflows triggered; unknown base branch |

---

## 3. Recovery Order (When CVE Blocker Resolved)

1. **#73** — READY_FOR_AUTHORIZATION (all checks pass, APPROVED)
2. **#72** — VERIFICATION_REQUIRED (3 checks not triggered due to non-main base; needs investigation)
3. **#78** — BLOCKED_BY_SECURITY (build-scan-sbom failure; needs CVE resolution + new authorization)
4. **#70, #69, #64** — BLOCKED_BY_REVIEW (need policedbc review)
5. **#77** — BLOCKED_BY_CONFLICT (needs conflict resolution + CI setup)
6. All others — BLOCKED_BY_SECURITY (need CVE resolution)

---
