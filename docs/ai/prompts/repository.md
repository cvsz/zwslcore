# Reusable Repository Execution Prompt

Focused slice of `master-think-drill.md` for single-objective repository tasks.
Follow the master workflow (THINK, DRILL, DIVE DEEPER, IMPLEMENT, VERIFY,
DELIVER) at reduced ceremony, and keep this file subordinate to
`../../../ZEAZ-INTRODUCTION.md` for all evidence semantics.

## Execute

1. Read repository instructions and inspect exact Git state: branch, HEAD,
   dirty and untracked files. Exclude operator-local bulk (caches, downloaded
   catalogs, ignored secrets) from conclusions.
2. Establish baseline behavior with a concrete command, test, or log before
   changing anything.
3. Identify objective, current implementation, root cause with file/line
   evidence, dependencies, and security/deployment impact.
4. Prioritize `P0`/`P1`/`P2`/`P3`. Implement the smallest safe root-cause fix,
   preserve unrelated work, and add regression coverage first when practical.
5. Validate proportionally to risk: targeted tests first, then the broader
   suite, then exact-head CI. Record command, environment, result, and
   limitations for each check.
6. Report baseline, files changed, evidence, failures, unresolved risks, and
   the next safest action.

## Classify honestly

Use the canonical evidence-state decision rule in
`../../../ZEAZ-INTRODUCTION.md`: `BLOCKED` when a concrete prerequisite
prevents verification, `PARTIALLY VERIFIED` when direct evidence covers only
part of the exact claim, and `UNVERIFIED` when sufficient evidence has simply
not been obtained. Never claim done, fixed, or production ready without
evidence for that exact claim.
