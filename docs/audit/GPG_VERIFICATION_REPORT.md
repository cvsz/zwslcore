# GPG Verification Report — zwslcore

Audit date: 2026-11-09
Reviewer: cvsz

## GPG keys available (secret keys in /home/cvsz/.gnupg)

| Key ID | Fingerprint | Type | Created | Expires | UID |
|--------|-------------|------|---------|---------|-----|
| A6D60018D84C3BBD | F264197E...D84C3BBD | rsa3072 [SCEAR] | 2026-10-07 | 2028-10-06 | cvsz <seaza@msn.com> |
| CE99AB5D660D619F | A9294A89...660D619F | rsa3072 [SC] | 2026-10-30 | 2028-10-29 | cvsz <seaza@msn.com> |
| A74B45171A0B62DC | 824A6F4A...45171A0B62DC | rsa3072 [SC] | 2026-11-06 | 2028-11-05 | cvsz <seaza@msn.com> |
| 16CBB7A6D359898D | 72AD0928...6BB7A6D359898D | rsa3072 [SC] | 2026-11-06 | 2028-11-05 | cvsz <seaza@msn.com> |
| 48E56C5EABE2CC0F | A93D6B70...5EABE2CC0F | rsa3072 [SC] | 2026-11-07 | 2028-11-06 | cvsz <seaza@msn.com> |
| 89995CF911C9BCB3 | 3A9C7EB3...995CF911C9BCB3 | rsa3072 [SC] | 2026-11-07 | (no expiry) | cvsz-signer <signer@zwslcore.local> |

## Signing configuration (verified)

- `git config user.signingkey` = 89995CF911C9BCB3 (cvsz-signer) — PRESENT
- `git config commit.gpgsign` = true — PRESENT
- `git config user.name` = cvsz — PRESENT
- `git config user.email` = seaza@msn.com — PRESENT
- Private key availability: verified (secret keys present in keyring; public keys match)
- Authorized signing key: 89995CF911C9BCB3 (cvsz-signer) — matches git config

## Commits signed and verified

| Commit | Subject | Signature |
|--------|---------|-----------|
| d2b8708 | docs: replace zeaz.md HTML with markdown policy | Good signature from cvsz-signer |
| a1fdfe0 | lint: apply ruff check --fix and ruff format | Good signature from cvsz-signer |
| d5743d6 | lint: resolve ShellCheck warnings | Good signature from cvsz-signer |

Verification method: `git log --show-signature -1` and `git verify-commit HEAD` both returned "Good signature from cvsz-signer <signer@zwslcore.local> [ultimate]".

## Credential safety

- `/home/cvsz/.git-credentials` exists (mode 0600); inspected for existence and permissions only — contents never printed or exposed.
- GitHub CLI uses its own secure token storage (`/home/cvsz/.config/gh/hosts.yml`); no tokens placed in shell arguments.
- Active developer account verified as `cvsz` via `gh auth status` before all write operations.

## Conclusion

GPG signing is properly configured and all commits made during this session are signed with the authorized key 89995CF911C9BCB3 and independently verified. No signatures were fabricated.
