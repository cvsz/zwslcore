Enterprise Repository Baseline
=============================

Repository: cvsz/zwslcore
Date: 2026-11-08
Current HEAD: c591a35 (post-audit commit on pr-78-current)
Previous HEAD: c591a354a8d2ce29ad6cfc358fea1ff9fcca43ac
Current Branch: pr-78-current
Remote: origin/main (df7ef0eae393f44f39c5393533531fc4171c6156)

Repository Status
----------------
- Git status: Clean working tree with 1 untracked file (services/provider/config/s3.local.yaml)
- Branch: pr-78-current (feature branch for PR #78)
- Ahead of origin/main: Local branch is behind; main has merged many PRs
- All 102 PRs fetched from GitHub API and classified

Current HEAD Analysis
--------------------
The current HEAD at c591a35 is 21 commits ahead of the previously authorized SHA a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e.
Authorization status: The previously authorized SHA is INVALID for the current HEAD, as new commits were pushed after the approval.

SHA Timeline
-----------
- a72fc000284f0eb2d69b6f67ed6c2e3eb17ebe9e: Original PR #78 commit "fix(ai): route provider credentials by endpoint hostname and honor overrides"
  - Previously APPROVED by policedbc on 2026-10-18
  - DISMISSED when new commits pushed; authorization expired
- 95cc9ca565bcb3f18af57411a7e117f49a55a406: Exact head reviewed by policedbc on 2026-11-01
  - CHANGES_REQUESTED due to CVE-2026-115557 build-scan-sbom failure
  - Not an approval; comment-only status
- c591a354a8d2ce29ad6cfc358fea1ff9fcca43ac: Current local HEAD
  - 21 commits beyond a72fc00
  - Includes CVE allowlist updates and Dockerfile modifications

Open PR Summary (from GitHub API)
----------------------------------
Total open PRs: 23 (as of GitHub API fetch)
- PR #78: fix(ai): load provider credentials safely from repository .env — OPEN, mergeable; CVE-2026-115557 blocker
- PR #73: test(chat-ui): verify existing Open WebUI Provider Gateway security contract — OPEN, mergeable; **PRESERVATION RULE APPLIES — do not touch**
- PR #72: feat(cloudshell): opt-in multi-node Ollama pool and parallel agent jobs — OPEN, mergeable
- PR #71: feat: support optional Ollama installation on Google Cloud Shell — OPEN, mergeable; policedbc CHANGES_REQUESTED addressed
- PR #82: fix: move LiteLLM PostgreSQL into Docker and harden local runtime — OPEN, mergeable; merge conflicts resolved in latest commit
- PR #79: fix: harden MCP session, rate limiter, provider client and restore — OPEN, mergeable; merge conflicts resolved in latest commit
- PR #76: feat(cloudshell): Access, MCP diagnostics, and feature-aware installation — OPEN, mergeable
- 6 PRs blocked by Chainguard base image CVE-2026-115557 (PR #102, #101, #100, #88, #87, #80+)

Required Status Checks (from .github/workflows/ci.yml)
-------------------------------------------------------
- repository-baseline: Verifies current HEAD matches remote tracking
- Analyze GitHub Actions: CI workflow validation
- dependency-review: Checks pinned dependencies in requirements.lock
- build-scan-sbom: Scans provider image with Grype; FAILS due to CVE-2026-115557 (Critical) and CVE-2026-114613 (High)
- windows-installer: Windows installer build and validation
- CodeQL: Static code analysis

PR #73 Preservation Rule
------------------------
PR #73 (test(chat-ui): verify existing Open WebUI Provider Gateway security contract) must remain untouched, unmodified, and unmerged unless separately authorized by the user. This PR has no relationship to the CVE-2026-115557 blocker or PR #78 changes.

Governance Identities
--------------------
- cvsz: Engineering execution and authorized merge operator
- policedbc: Independent security review, audit, and approval
- Repository owner: Final authorization for exact commit SHA

Dependencies
------------
- services/provider/Dockerfile: Chainguard base image with CVE-2026-115557 (Critical blocker)
- services/provider/requirements.lock: Pinned dependencies with hashes
- scripts/ai.sh: Secure .env loading implementation (PR #78 feature)
- tests/test_ai_cli.py: Tests for provider credential loading (PR #78 tests)
- .github/workflows/provider-scan-allowlist.txt: CVE-2026-115557 allowlist entry