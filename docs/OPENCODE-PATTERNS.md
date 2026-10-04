# OpenCode-inspired engineering patterns

zwslcore borrows architectural ideas from the MIT-licensed [anomalyco/opencode](https://github.com/anomalyco/opencode) project while keeping an independent Python implementation and no runtime dependency on OpenCode.

OpenCode concepts reviewed for this integration include:

- named primary/subagent profiles such as build, plan and general;
- ordered tool permission rules with allow/ask/deny decisions;
- declarative tool registration;
- read-only planning/review modes;
- explicit agent selection carried with durable session/task state.

zwslcore deliberately does **not** embed OpenCode, Bun, Electron, its TUI, or its provider/runtime packages. The local stack remains Python + Ollama + LiteLLM + zwslcore Provider.

## Built-in profiles

- `build`: full bounded engineering path (snapshot, plan, edit, validate, review, local commit).
- `plan`: read-only planning; completes after PLAN without changing files.
- `review`: read-only review-oriented profile.
- `explore`: read-only repository exploration profile.
- `general`: delegated implementation profile that may edit and validate but may not commit.

All profiles are fail-closed. The default rule denies everything, followed by explicit allows.

## Permission model

Rules are evaluated in order and the **last matching rule wins**. A rule has:

- permission name, such as `edit`, `validate` or `commit`;
- glob-style resource pattern;
- action: `allow`, `ask`, or `deny`.

The autonomous runtime only proceeds on an explicit `allow`. `ask` is not silently promoted to allow.

## Tool capability registry

The current registry exposes the engineering capabilities:

- snapshot
- plan
- edit
- validate
- review
- commit
- delegate

The registry is metadata; runtime checks the selected agent policy before each mutating or sensitive phase.

## CLI

Inspect profiles:

    python3 scripts/engineer.py agents

Inspect tool capabilities:

    python3 scripts/engineer.py tools

Check one decision:

    python3 scripts/engineer.py policy-check plan edit services/provider/main.py

Run with an agent:

    python3 scripts/engineer.py run TASK_ID --agent build
    python3 scripts/engineer.py run TASK_ID --agent plan

Continuous work persists the selected agent in the work item payload and task run_config.

## Provenance

OpenCode is licensed under the MIT License. This zwslcore feature is a clean reimplementation of the reviewed architectural patterns rather than a vendored copy of OpenCode source files. zwslcore is not affiliated with or maintained by the OpenCode project.
