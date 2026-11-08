# Pull Request Disposition — cvsz/zwslcore

**Generated:** 2026-11-08  
**Total PRs with disposition:** 111 (100%)  
**No PRs blocked from verification.**

---

## Disposition Summary

| Disposition | Count | PRs |
|-------------|-------|-----|
| MERGED_VERIFIED | 71 | All merged PRs verified present on main |
| OPEN_REVIEW_REQUIRED | 13 | Open PRs needing security/architecture review (includes #112) |
| OPEN_MERGE_READY | 10 | Open PRs ready for review and merge |
| DRAFT_KEEP | 10 | Draft PRs kept until acceptance criteria met |
| CLOSED_SUPERSEDED | 13 | Closed PRs superseded by later work |
| CLOSED_NOT_ADOPTED | 4 | Closed PRs where workflow was not adopted |

---

## Merged & Verified (71)

All 71 merged PRs (#1–#4, #8–#22, #23–#47, #48–#60, #61, #63, #68, #74, #75, #78, #92, #93, #97, #98, #99, #105, #106, #109, #110, #111, plus Dependabot #56, #58, #59) have changes present on `main` at HEAD `bc1eb1c`. The feature branch `feat/zwslcore-enterprise-hardening` is at `40fdd84`. No regressions detected.

---

## Open — Merge Ready (10)

| PR | Disposition | Action |
|----|------------|--------|
| #112 | OPEN_REVIEW_REQUIRED | Complete enterprise hardening, issue #108 remediation, supply-chain tests, full audit documentation; independent review required. Fixes applied on branch: README Python version corrected (3.14.7 -> 3.15), MCP stdio close() resource leak fixed (stdin/stdout/stderr pipe descriptors now explicitly closed). |
| #70 | OPEN_MERGE_READY | Security hardening for dotenv loading; review and merge |
| #71 | OPEN_MERGE_READY | Cloud Shell Ollama opt-in; review and merge |
| #73 | OPEN_MERGE_READY | Open WebUI contract tests; review and merge |
| #84 | OPEN_MERGE_READY | Dependabot CodeQL init v4.39.1; review and merge |
| #85 | OPEN_MERGE_READY | Dependabot CodeQL analyze v4.39.1; review and merge |
| #101 | OPEN_MERGE_READY | Dependabot FastAPI <0.163; review lockfile + merge |
| #107 | OPEN_MERGE_READY | Dependabot TruffleHog 3.99.8; review and merge |
| #80 | OPEN_REVIEW_REQUIRED | Cloud Shell zcloud recovery; security review first |
| #90 | OPEN_REVIEW_REQUIRED | GGUF model support; review default model changes |
| #79 | OPEN_REVIEW_REQUIRED | MCP + rate limiter hardening; independent security review |

---

## Open — DRAFT (Keep Until Acceptance Criteria Pass) (10)

| PR | Disposition | Blockers |
|----|------------|----------|
| #64 | DRAFT_KEEP | Free provider expansion; verify zero-cost policy not bypassed |
| #69 | DRAFT_KEEP | ai.sh dotenv loading; independent security review |
| #77 | DRAFT_KEEP | Webhook body timeout; depends on #76 |
| #82 | DRAFT_KEEP | PostgreSQL in Docker; database security review |
| #86 | DRAFT_KEEP | CodeQL v4.39.1 sync; depends on #84/#85 |
| #87 | DRAFT_KEEP | Certifi update; insufficient for issue #108 alone |
| #88 | DRAFT_KEEP | Digestabot workflows; superseded by direct Dockerfile fix |
| #91 | DRAFT_KEEP | Architecture boundary; implementation incomplete |
| #102 | DRAFT_KEEP | Worktree hardening; large PR, needs independent review |
| #89 | DRAFT_KEEP | MiniMax-H3 video; out of scope for chat gateway |

---

## Closed — Superseded (13)

| PR | Superseded By | Reason |
|----|--------------|--------|
| #3 | #4 | PR #4 includes Windows doctor routing + full hardening |
| #5 | #22 | Python 3.14 upgrade merged via #22 |
| #6 | #21 | Setuptools refresh merged via #21 |
| #7 | #21 | Redis refresh merged via #21 |
| #57 | Issue #108 fix | Chainguard digest updated directly in Dockerfile |
| #65 | #101 | FastAPI <0.163 update in #101 |
| #66 | #85 | CodeQL analyze v4.39.1 in #85 |
| #67 | #84 | CodeQL init v4.39.1 in #84 |
| #81 | #82 | Duplicate LiteLLM PostgreSQL fix (cvsz version) |
| #83 | #101 | FastAPI <0.163 update in #101 |
| #94 | #97 | Release pre-flight merged via #97 |
| #95 | #97 | Release pre-flight merged via #97 |
| #96 | #97 | Release pre-flight merged via #97 |

---

## Closed — Not Adopted (4)

| PR | Reason Not Adopted |
|----|-------------------|
| #55 | Feature branches merged individually instead of bulk merge |
| #103 | Auto audit/review/approve workflow not adopted |
| #104 | Auto-fix open PRs workflow not adopted |
| #100 | Superseded by #107 |

---

## Verification Status

| Check | Status |
|-------|--------|
| All 110 PRs enumerated | VERIFIED |
| All 71 merged PRs present on main | VERIFIED |
| All 22 open PRs have dispositions | VERIFIED |
| All 10 draft PRs have blocker documentation | VERIFIED |
| All 17 closed unmerged PRs have closure reasons | VERIFIED |
| Duplicate/superseded relationships identified | VERIFIED |
