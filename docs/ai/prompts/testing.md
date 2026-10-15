# Reusable Testing Prompt

Focused slice of `master-think-drill.md` for validation design. Tests prove
behavior; ceremony never substitutes for execution.

## Design validation proportionate to risk

- unit: pure logic, parsers, policy functions, cost/rank decisions;
- integration: service wiring, migrations, queue/ledger round-trips;
- auth/authz: negative cases (missing/invalid credentials fail closed);
- isolation: tenant, path-scope, and secret-boundary enforcement;
- failure-mode: timeouts, resets, malformed responses, dependency outages;
- resilience: restarts, resume, stale-lease and worktree recovery;
- load/stress/soak and backup/restore/rollback where applicable.

## Execute and record

1. Run targeted tests before broad suites; stop expanding when acceptance
   criteria are satisfied.
2. Keep test fixtures hermetic: pin identity, disable signing/network side
   effects, and isolate temp state so suites pass on any compliant machine.
3. Record command, environment, result, and limitations for every run.

Classify unexecuted or incomplete tests with the canonical evidence-state
decision rule in `../../../ZEAZ-INTRODUCTION.md`: `BLOCKED` when a concrete
prerequisite prevents verification, otherwise `UNVERIFIED` when evidence has
simply not been obtained.
