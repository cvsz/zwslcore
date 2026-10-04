# MCP integration

zwslcore includes an operator-controlled local MCP client inspired by the MCP registry/tool patterns reviewed in the MIT-licensed anomalyco/opencode project.

## Scope of this implementation

Current support is deliberately narrow:

- local stdio MCP servers only;
- JSON-RPC 2.0 initialize, notifications/initialized, tools/list and tools/call;
- namespaced tool identifiers in `server.tool` form;
- bounded request timeouts and 2 MiB message limits;
- `shell=False` process launch;
- environment allowlisting;
- operator-only discovery and execution through the engineering CLI.

The autonomous model/tool loop does **not** call MCP tools automatically in this slice.

Remote Streamable HTTP, SSE and OAuth are intentionally deferred until zwslcore has a dedicated authentication/token store and per-tool permission workflow.

## Configuration

The default config lives outside the repository:

    ~/.zwslcore/mcp/servers.json

Start from the repository example:

    mkdir -p ~/.zwslcore/mcp
    cp config/mcp.example.json ~/.zwslcore/mcp/servers.json

A server entry:

    {
      "servers": {
        "local-tools": {
          "enabled": true,
          "command": ["python3", "/home/user/mcp/server.py"],
          "cwd": "/home/user/project",
          "inherit_env": ["SAFE_EXISTING_VARIABLE"],
          "environment": {
            "NON_SECRET_FLAG": "1"
          },
          "timeout_seconds": 30,
          "protocol_version": "2025-06-18"
        }
      }
    }

`inherit_env` copies only the named environment variables. zwslcore does not forward the complete parent environment to the MCP process.

## Commands

Inspect configured servers without launching them:

    python3 scripts/engineer.py mcp-status

Discover tools:

    python3 scripts/engineer.py mcp-tools
    python3 scripts/engineer.py mcp-tools local-tools

Invoke one tool explicitly:

    python3 scripts/engineer.py mcp-call local-tools.echo --json '{"value":"hello"}'

The PowerShell wrapper supports the same arguments:

    .\scripts\engineer-wsl.ps1 mcp-status
    .\scripts\engineer-wsl.ps1 mcp-tools local-tools
    .\scripts\engineer-wsl.ps1 mcp-call local-tools.echo --json '{"value":"hello"}'

## Security boundary

- Config is local and untracked by default.
- Commands are passed as argv arrays and started with `shell=False`.
- Disabled servers are never started.
- Server stdout is treated only as bounded JSON-RPC messages.
- Tool arguments must be a JSON object.
- External tools are not exposed to autonomous engineering agents yet.
- Enabling an MCP server means its executable is trusted to run locally with only the explicitly supplied/inherited environment.

Future autonomous MCP execution must integrate the existing `PermissionRule` engine and require explicit per-server/tool allows before the model can invoke a tool.
