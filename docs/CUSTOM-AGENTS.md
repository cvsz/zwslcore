# Custom agent profiles

zwslcore can load operator-defined agent profiles from:

    ~/.zwslcore/agents.json

The file is optional. Built-in profiles remain available when it is absent.

Start from:

    mkdir -p ~/.zwslcore
    cp config/agents.example.json ~/.zwslcore/agents.json

## Inheritance

Every custom profile must inherit from a built-in profile:

- build
- plan
- review
- explore
- general

If `extends` is omitted, the custom profile inherits from `plan`, which is read-only and therefore fail-closed.

Custom profile names may not replace built-ins.

## Permissions

Permission entries are appended after inherited rules. The existing last-matching-rule-wins behavior therefore applies.

Example:

    {
      "agents": {
        "safe-implementer": {
          "extends": "general",
          "permissions": [
            {"permission":"edit","pattern":"*","action":"deny"},
            {"permission":"edit","pattern":"services/safe/*","action":"allow"}
          ]
        }
      }
    }

This profile inherits `general`, then removes broad edit access and allows only `services/safe/*`.

The runtime still enforces path scope, validators, static review and the security gate independently from agent permissions.

## Custom prompt

A profile may add a bounded `prompt` (maximum 16 KiB). It is appended to the trusted base system instruction for planning and editing. A prompt cannot bypass permission checks.

## CLI

The default config path is loaded by engineering execution:

    python3 scripts/engineer.py agents
    python3 scripts/engineer.py policy-check architect edit services/provider/main.py
    python3 scripts/engineer.py run TASK_ID --agent architect

To use another config file, provide the global option before the command:

    python3 scripts/engineer.py --agent-config /path/to/agents.json agents

Custom profiles with `mode=subagent` can be used by `delegate`.

## Validation

Configuration is rejected when:

- a custom name collides with a built-in;
- `extends` is not a built-in profile;
- mode is not `primary` or `subagent`;
- permission fields/actions are invalid;
- prompt exceeds 16 KiB;
- type validation fails.

Disabled custom profiles are not registered.
