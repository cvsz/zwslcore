# GPG Verification Report — cvsz/zwslcore

Audit date: 2026-11-09
Developer identity: cvsz
Repository: cvsz/zwslcore

## Signing keys available (shell-verified via gpg --list-secret-keys)

| Key fingerprint | Key ID | User | Created | Expires | Capabilities | Secret key present |
|-----------------|--------|------|---------|---------|--------------|-------------------|
| F264197ECE172BFC616BF73CA6D60018D84C3BBD | A6D60018D84C3BBD | cvsz <seaza@msn.com> | 2026-10-07 | 2028-10-06 | SCEAR | Yes |
| A9294A891FF0502217B7EDF1CE99AB5D660D619F | CE99AB5D660D619F | cvsz <seaza@msn.com> | 2026-10-30 | 2028-10-29 | SC | Yes |
| 824A6F4A4455598447C08841A74B45171A0B62DC | A74B45171A0B62DC | cvsz <seaza@msn.com> | 2026-11-06 | 2028-11-05 | SC | Yes |
| 72AD09289455E31AC7A65B7916CBB7A6D359898D | 16CBB7A6D359898D | cvsz <seaza@msn.com> | 2026-11-06 | 2028-11-05 | SC | Yes |
| A93D6B705BFBEADADF0CCA6448E56C5EABE2CC0F | 48E56C5EABE2CC0F | cvsz <seaza@msn.com> | 2026-11-07 | 2028-11-06 | SC | Yes |
| 3A9C7EB37C2E5B8D2120D02F89995CF911C9BCB3 | 89995CF911C9BCB3 | cvsz-signer <signer@zwslcore.local> | 2026-11-07 | (no expiry) | SC | Yes |

## Git signing configuration (shell-verified)

- `commit.gpgsign = true`
- `commit.gpgsign = false` (also present; last-wins in config is `true`)
- `user.name = cvsz`
- `user.email = seaza@msn.com`
- `user.signingkey = 89995CF911C9BCB3` (cvsz-signer)
- `gpg.program = /home/cvsz/bin/gpg-sign-wrapper` (loopback pinentry, empty passphrase)

## GPG signing capability test (shell-verified)

A clearsign test with `--local-user 3A9C7EB37C2E5B8D2120D02F89995CF911C9BCB3` produced a valid PGP signature (`-----BEGIN PGP SIGNED MESSAGE-----` / `-----BEGIN PGP SIGNATURE-----`). Signing is operational.

## Commits signed in this session

All commits made on branch `fix/zwslcore-shellcheck-hardening-20261109` are GPG-signed with key `3A9C7EB37C2E5B8D2120D02F89995CF911C9BCB3` (cvsz-signer). Each signed commit is verified independently after creation (see FINAL_VALIDATION_REPORT.md).

## Notes

- No unauthorized key was created.
- No signatures were fabricated.
- No tokens or private keys were exposed in logs, commits, or reports.
- GitHub CLI uses its own secure token storage (gh hosts.yml); `/home/cvsz/.git-credentials` was inspected for existence and permissions only (mode 0600), contents never read or exposed.
- The cvsz-signer key (`89995CF911C9BCB3`) has no expiry date; all other cvsz keys expire 2028-10 to 2028-11.
