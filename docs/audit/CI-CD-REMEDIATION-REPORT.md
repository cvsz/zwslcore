# CI/CD Remediation Report

**Repository**: `cvsz/zwslcore`  
**Workflows**: `ci.yml`, `codeql.yml`, `dependency-review.yml`, `provider-supply-chain.yml`  
**Date**: 2026-11-01  
**Actor**: cvsz (engineering operator)

---

## 1. Workflow Inventory

| Workflow | Triggers | Jobs | Required Checks |
|----------|----------|------|-----------------|
| CI (`ci.yml`) | push to main, pull_request | repository-baseline, windows-installer | repository-baseline, windows-installer |
| CodeQL (`codeql.yml`) | push to main, pull_request to main, schedule | Analyze GitHub Actions | CodeQL |
| Dependency Review (`dependency-review.yml`) | pull_request to main | dependency-review | dependency-review |
| Provider Supply Chain (`provider-supply-chain.yml`) | pull_request, push to main/tags | build-scan-sbom, attest-trusted-build | build-scan-sbom |

---

## 2. Required Check Status (PR #78 at SHA `6f9f45ceb862509b4e539c58c92b618d0db5fba2`)

| Check | Conclusion | Status | Required | Result |
|-------|------------|--------|----------|--------|
| repository-baseline | SUCCESS | COMPLETED | Yes | PASS |
| Analyze GitHub Actions | SUCCESS | COMPLETED | Yes | PASS |
| dependency-review | SUCCESS | COMPLETED | Yes | PASS |
| CodeQL | SUCCESS | COMPLETED | Yes | PASS |
| build-scan-sbom | FAILURE | COMPLETED | Yes | FAIL |
| windows-installer | SUCCESS | COMPLETED | Yes | PASS |
| attest-trusted-build | SKIPPED | COMPLETED | No | N/A |

**Result**: 5/6 required checks pass. `build-scan-sbom` fails due to CVE-2026-115557.

---

## 3. Workflow Issues Identified

### Issue 1: build-scan-sbom Failure

| Field | Value |
|-------|-------|
| Check | build-scan-sbom |
| Conclusion | FAILURE |
| Cause | CVE-2026-115557 Critical in Chainguard base image |
| Remediation | Base image fix (BLOCKED_EXTERNAL) or risk acceptance |

### Issue 2: CodeQL and Analyze Use Same SHA

Both `github/codeql-action/init` and `github/codeql-action/analyze` use `2892aa5e19bbd11bc0cff5427e3b750a04d9e3c2 # v4`. This was previously identified as a pairing issue (init and analyze must use the same version). Currently paired correctly.

### Issue 3: attest-trusted-build Only Runs on Main

The `attest-trusted-build` job only runs on `push` to `main` or tags `v*`, not on pull requests. This is expected behavior — attestations are for releases, not PRs.

### Issue 4: CodeQL Limited to Main Branch

The CodeQL workflow has `pull_request: branches: [main]`, meaning it only runs on PRs targeting `main`. PR #72 targets `feat/cloudshell-installer-20261017`, so CodeQL doesn't run on it. This causes 3 missing required checks for PR #72.

---

## 4. Remediation Plan

| Priority | Action | Owner | Status |
|----------|--------|-------|--------|
| Critical | Fix build-scan-sbom (CVE remediation) | policedbc (risk acceptance) | BLOCKED_EXTERNAL |
| High | Fix CodeQL branch filter for non-main PRs | cvsz | PENDING |
| Medium | Add attest-trusted-build to PR workflow (optional) | cvsz | PENDING |
| Low | Review workflow permissions for least privilege | cvsz | PENDING |

---
