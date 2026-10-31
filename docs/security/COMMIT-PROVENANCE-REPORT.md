# Commit Provenance Report — cvsz/zwslcore

**Repository**: `cvsz/zwslcore`
**Document Date**: 2026-10-31
**Related PR**: #102 (`feat/zwslcore-worktree-security-hardening`)
**Head SHA**: `b19ff81e746ff37f254b76b18189f8748b289f1f`

---

## 1. Problem Statement

GitHub commit verification reports `verified=false / reason=bad_email` for commits on PR #102. All commits are GPG signed locally with `Good signature`, but GitHub does not recognize them as verified because the commit author email does not match any email on the GPG signing key.

---

## 2. Investigation Findings

### Git Configuration (Before Fix)

| Setting | Value |
|---------|-------|
| `git config user.name` | `cvsz` |
| `git config user.email` | `cvsz@users.noreply.github.com` |

### GPG Key on GitHub Account `cvsz`

| Key ID | Key Type | Email | Verified |
|--------|----------|-------|----------|
| `8644B3973EA1743EF5D21EBA87A69650EB250939` (A6D60018D84C3BBD) | RSA | `seaza@msn.com` | Verified |
| `0C54E869DE49D872` | RSA | `seaza@msn.com` | Verified |
| `14E1E0BC08F632B0` | RSA | `seaza@msn.com` | Verified |
| `220A4C8CCC7D2D50` | RSA | `seaza@msn.com` | Verified |
| `AA759FAAD97197D5` | RSA | `seaza@msn.com` | Verified |
| `C3CDE65F606F7BF0` | RSA | `seaza@msn.com` | Verified |
| `C5D34CD8F440CF63` | RSA | `seaza@msn.com` | Verified |

### Commit Verification

| Check | Result |
|-------|--------|
| `git verify-commit HEAD` | `Good signature from "cvsz <seaza@msn.com>" [ultimate]` |
| GitHub commit verification | `verified=false`, `reason=unknown_key` (previously) / `bad_email` (current) |
| GPG signing key | `8644B3973EA1743EF5D21EBA87A69650EB250939` |
| Commit author email | `cvsz@users.noreply.github.com` |
| GPG key email | `seaza@msn.com` |

### Root Cause

Git commit author email (`cvsz@users.noreply.github.com`) does not match any email on the GPG signing key (`seaza@msn.com`). GitHub verifies that the commit author email is a verified email on the signing GPG key. Since `cvsz@users.noreply.github.com` is not on the GPG key, GitHub reports `bad_email`.

GitHub account `cvsz` has three verified emails:
1. `seaza@msn.com` (primary, verified)
2. `4076926+cvsz@users.noreply.github.com` (verified)
3. `sea@zeaz.dev` (not verified)

The GPG keys on the account all have `seaza@msn.com` as their email. The git config uses `cvsz@users.noreply.github.com` which is verified on GitHub but NOT on the GPG key.

---

## 3. Fix Applied

### Change Made

Changed git config to match GPG key email:

```bash
git config user.email seaza@msn.com
git config user.name cvsz
```

**Verification**:
```bash
$ git config user.name
cvsz
$ git config user.email
seaza@msn.com
```

### Effect

- **Future commits**: Will use author email `seaza@msn.com`, which matches the GPG key email and is verified on GitHub. `git verify-commit` will show `verified=true` on GitHub.
- **Existing commits**: Already signed with `cvsz@users.noreply.github.com` author email but `seaza@msn.com` GPG key. These commits will continue to show `bad_email` on GitHub until rewritten with authorization.

### Why Not Rewrite Existing Commits?

Per repository policy (PROMPT §14): "Do not rewrite protected branch history without authorization." The commits on `feat/zwslcore-worktree-security-hardening` are already pushed to GitHub. Rewriting them would require force-push, which is not authorized without explicit repository owner consent.

---

## 4. Impact on PR #102

| Item | Status |
|------|--------|
| New commits (after fix) | Will have verified GPG signatures on GitHub |
| Existing commits (b19ff81 and earlier) | Will show `bad_email` on GitHub |
| policedbc review decision | CHANGES_REQUESTED (due to scope + CI failure, not GPG) |
| Merge eligibility | Blocked by CI failure (build-scan-sbom), not GPG |

The GPG provenance issue is a secondary concern. The primary blocker is the `build-scan-sbom` failure due to Chainguard base image CVEs.

---

## 5. Recommendations

### Immediate (Already Done)
1. ✅ Changed `git config user.email` to `seaza@msn.com` (matches GPG key)
2. ✅ Changed `git config user.name` to `cvsz` (consistent)

### Future Commits
- All new commits on `feat/zwslcore-worktree-security-hardening` will have verified GPG signatures on GitHub
- No further action needed for provenance on new commits

### Existing Commits (Optional, Requires Authorization)
- If the repository owner wants existing commits to show `verified=true` on GitHub, the commits would need to be amended with `git commit --amend --reset-author` (which changes committer email) and force-pushed.
- This requires explicit authorization from the repository owner and would invalidate any existing PR reviews based on the old commit SHAs.

---

## 7. Evidence

| Evidence | Value |
|----------|-------|
| `git config user.email` | `seaza@msn.com` |
| `git config user.name` | `cvsz` |
| GPG key fingerprint | `8644B3973EA1743EF5D21EBA87A69650EB250939` |
| GPG key email | `seaza@msn.com` (verified on GitHub) |
| `git verify-commit HEAD` | `Good signature from "cvsz <seaza@msn.com>"` |
| GitHub GPG keys API | 7 keys found, all with `seaza@msn.com` email |
| GitHub user emails API | `seaza@msn.com` (primary, verified), `4076926+cvsz@users.noreply.github.com` (verified) |
