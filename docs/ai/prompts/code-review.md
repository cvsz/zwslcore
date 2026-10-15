# Reusable Code Review Prompt

Focused slice of `master-think-drill.md` for second-opinion review. Question
whether the change is necessary or can be smaller before tracing real code
paths. Cite concrete file/line evidence and distinguish verified behavior
from unverified claims.

## Review dimensions

Correctness, regressions, security, data integrity, concurrency, error
handling, compatibility, maintainability, performance, observability, and
test adequacy. Prioritize concrete defects over style preferences.

## Report each material issue with

- severity (`P0`/`P1`/`P2`/`P3`);
- file and location;
- defect and root cause;
- impact and blast radius;
- evidence (command output, test, or trace);
- recommended fix and its rollback.

Do not invent issues unsupported by evidence. Do not approve changes that
weaken CI, security scanning, branch protection, or release controls, commit
secrets, or claim readiness without exact-head verification. Classify the
review itself per `../../../ZEAZ-INTRODUCTION.md` when validation is partial
or blocked.
