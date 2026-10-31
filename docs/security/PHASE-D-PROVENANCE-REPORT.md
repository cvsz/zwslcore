# Phase D Provenance Report

**Repository**: `cvsz/zwslcore`
**GPG Key**: `8644B3973EA1743EF5D21EBA87A69650EB250939` (cvsz <seaza@msn.com>)
**GitHub GPG Key ID**: `A6D60018D84C3BBD`
**Date**: 2026-11-01

---

## 1. GPG Configuration Verification

| Setting | Value |
|---------|-------|
| `git config user.name` | `cvsz` |
| `git config user.email` | `seaza@msn.com` |
| `git config user.signingkey` | `A6D60018D84C3BBD` |
| `git config commit.gpgsign` | `true` |
| GPG key email match | `seaza@msn.com` (verified on GitHub) |
| `git verify-commit HEAD` | Good signature |

---

## 2. New Commits in Phase D

All commits were made with GPG signing enabled and verified locally.

| PR | Branch | Commit SHA | Message | GPG Signed | GitHub Verified |
|-----|---------|------------|---------|------------|-----------------|
| #71 | feat/cloudshell-installer-20261017 | `5921251d27013755eab8617716e3a76e8c70331b` | fix(cloudshell): address policedbc review feedback on PR #71 | Yes | Pending (email mismatch on existing commits only) |
| #82 | fix/postgres-docker-bridge-preflight-cvsz | `00b20d07f56161ef7c66fcc46f8589103d59b516` | fix: resolve merge conflicts in PR #82 | Yes | Pending |
| #79 | audit/robustness-fixes-20261018 | `62afa1cec74042cbd7297942c1f5d8ca72212c64` | fix: resolve merge conflicts in PR #79 | Yes | Pending |
| #76 | feat/cloudshell-ssh-access-mcp-diagnostics-20261017 | `f8b7c54f944b7d9c2a22617e467a7b5bf342d1fa` | fix: resolve merge conflict in PR #76 | Yes | Pending |
| #85 | dependabot/github_actions/github/codeql-action/analyze-4.39.1 | `800c407a60a0` | fix: pair CodeQL init and analyze on same v4.39.1 SHA | Yes | Pending |
| #84 | dependabot/github_actions/github/codeql-action/init-4.39.1 | `678987786e63` | fix: pair CodeQL init and analyze on same v4.39.1 SHA | Yes | Pending |
| Phase C report | feat/zwslcore-worktree-security-hardening | `ebb2851f5c5feecba7972e7a0448299d3d1c916a` | docs(security): Phase C execution report | Yes | Verified |

---

## 3. Commit Provenance Details

### Commit: `5921251d27013755eab8617716e3a76e8c70331b` (PR #71)

**Local verification**:
```
gpg: Signature made using RSA key 8644B3973EA1743EF5D21EBA87A69650EB250939
gpg: Good signature from "cvsz <seaza@msn.com>" [ultimate]
```

**Author/Committer**: cvsz <seaza@msn.com>
**GPG key**: 8644B3973EA1743EF5D21EBA87A69650EB250939
**Repository**: cvsz/zwslcore
**Branch**: feat/cloudshell-installer-20261017
**Files changed**: scripts/cloudshell.sh, tests/test_cloudshell_installer.py

### Commit: `00b20d07f56161ef7c66fcc46f8589103d59b516` (PR #82)

**Local verification**: GPG signed with key 8644B3973EA1743EF5D21EBA87A69650EB250939

**Author/Committer**: cvsz <seaza@msn.com>
**Repository**: cvsz/zwslcore
**Branch**: fix/postgres-docker-bridge-preflight-cvsz
**Files changed**: .env.example, Makefile, compose.yaml, services/provider/zeaz_provider/security.py

### Commit: `62afa1cec74042cbd7297942c1f5d8ca72212c64` (PR #79)

**Local verification**: GPG signed with key 8644B3973EA1743EF5D21EBA87A69650EB250939

**Author/Committer**: cvsz <seaza@msn.com>
**Repository**: cvsz/zwslcore
**Branch**: audit/robustness-fixes-20261018
**Files changed**: Makefile, services/provider/zeaz_provider/security.py

### Commit: `f8b7c54f944b7d9c2a22617e467a7b5bf342d1fa` (PR #76)

**Local verification**: GPG signed with key 8644B3973EA1743EF5D21EBA87A69650EB250939

**Author/Committer**: cvsz <seaza@msn.com>
**Repository**: cvsz/zwslcore
**Branch**: feat/cloudshell-ssh-access-mcp-diagnostics-20261017
**Files changed**: Makefile

### Commit: `800c407a60a0` (PR #85)

**Local verification**: GPG signed with key 8644B3973EA1743EF5D21EBA87A69650EB250939

**Author/Committer**: cvsz <seaza@msn.com>
**Repository**: cvsz/zwslcore
**Branch**: dependabot/github_actions/github/codeql-action/analyze-4.39.1
**Files changed**: .github/workflows/codeql.yml

### Commit: `678987786e63` (PR #84)

**Local verification**: GPG signed with key 8644B3973EA1743EF5D21EBA87A69650EB250939

**Author/Committer**: cvsz <seaza@msn.com>
**Repository**: cvsz/zwslcore
**Branch**: dependabot/github_actions/github/codeql-action/init-4.39.1
**Files changed**: .github/workflows/codeql.yml

---

## 4. GitHub Commit Verification Status

**Existing commits**: Show `bad_email` on GitHub due to author email (`cvsz@users.noreply.github.com`) not matching GPG key email (`seaza@msn.com`). Cannot be fixed without force-push (not authorized per Phase D governance).

**New commits**: Author email changed to `seaza@msn.com` to match GPG key email. GitHub will report `verified=true` for new commits once pushed with correct email configuration.

**Verification method**: `git verify-commit <SHA>` passes locally for all new commits.

---

## 5. Provenance Chain Integrity

| Check | Result |
|-------|--------|
| All new commits GPG signed | PASS |
| GPG key matches commit author email | PASS (new commits) |
| GitHub GPG key registered | PASS |
| No force-push performed | PASS |
| No published history rewritten | PASS |
| All commits on intended branches | PASS |
| Working tree clean | PASS |

---

## 6. Known Limitations

1. Existing commits (prior to email config change) cannot be fixed without force-push, which is not authorized per Phase D governance.
2. GitHub `verified=true` status for new commits depends on GitHub's verification of the author email against the registered GPG key email — configuration changed but GitHub-side verification not yet confirmed for each new commit SHA.
3. No commit was made to the main branch in Phase D — all work was on PR branches only.
