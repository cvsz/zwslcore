from __future__ import annotations

import json
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

from services.engineering.mcp import (
    MCPError,
    MCPServerConfig,
    StdioMCPSession,
    call_server_tool,
    list_server_tools,
    load_config,
    split_qualified_tool,
)


FAKE_SERVER = r"""
import json
import sys

for line in sys.stdin:
    try:
        msg = json.loads(line)
    except Exception:
        continue
    method = msg.get("method")
    ident = msg.get("id")
    if method == "initialize":
        out = {
            "jsonrpc": "2.0",
            "id": ident,
            "result": {
                "protocolVersion": msg.get("params", {}).get("protocolVersion"),
                "capabilities": {"tools": {}},
                "serverInfo": {"name": "fake", "version": "1"},
            },
        }
    elif method == "notifications/initialized":
        continue
    elif method == "tools/list":
        out = {
            "jsonrpc": "2.0",
            "id": ident,
            "result": {
                "tools": [{
                    "name": "echo",
                    "description": "Echo one value",
                    "inputSchema": {
                        "type": "object",
                        "properties": {"value": {"type": "string"}},
                        "required": ["value"],
                    },
                }]
            },
        }
    elif method == "tools/call":
        args = msg.get("params", {}).get("arguments", {})
        out = {
            "jsonrpc": "2.0",
            "id": ident,
            "result": {
                "content": [{"type": "text", "text": str(args.get("value", ""))}],
                "structuredContent": {"echo": args.get("value")},
                "isError": False,
            },
        }
    else:
        out = {
            "jsonrpc": "2.0",
            "id": ident,
            "error": {"code": -32601, "message": "method not found"},
        }
    sys.stdout.write(json.dumps(out) + "\n")
    sys.stdout.flush()
"""


class MCPConfigTests(unittest.TestCase):
    def test_missing_config_is_empty(self):
        with tempfile.TemporaryDirectory() as td:
            self.assertEqual(load_config(Path(td) / "missing.json"), {})

    def test_config_parses_without_shell(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "servers.json"
            path.write_text(
                json.dumps({
                    "servers": {
                        "fake": {
                            "command": [sys.executable, "-u", "-c", FAKE_SERVER],
                            "enabled": True,
                            "inherit_env": ["TEST_TOKEN"],
                            "environment": {"SAFE_FLAG": "1"},
                            "timeout_seconds": 5,
                        }
                    }
                }),
                encoding="utf-8",
            )
            value = load_config(path)["fake"]
            self.assertEqual(value.name, "fake")
            self.assertEqual(value.command[0], sys.executable)
            self.assertEqual(value.timeout_seconds, 5.0)

    def test_invalid_server_name_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "servers.json"
            path.write_text(
                json.dumps({"servers": {"bad name": {"command": ["x"]}}}),
                encoding="utf-8",
            )
            with self.assertRaisesRegex(MCPError, "invalid MCP server name"):
                load_config(path)

    def test_qualified_name_requires_server_dot_tool(self):
        self.assertEqual(split_qualified_tool("alpha.echo"), ("alpha", "echo"))
        with self.assertRaisesRegex(MCPError, "server.tool"):
            split_qualified_tool("echo")


class MCPStdioTests(unittest.TestCase):
    def config(self) -> MCPServerConfig:
        return MCPServerConfig(
            name="fake",
            command=(sys.executable, "-u", "-c", textwrap.dedent(FAKE_SERVER)),
            timeout_seconds=5,
        )

    def test_initialize_and_list_tools(self):
        tools = list_server_tools(self.config())
        self.assertEqual(len(tools), 1)
        self.assertEqual(tools[0].qualified_name, "fake.echo")
        self.assertEqual(tools[0].input_schema["type"], "object")

    def test_call_tool(self):
        result = call_server_tool(self.config(), "echo", {"value": "hello"})
        self.assertEqual(result["structuredContent"], {"echo": "hello"})
        self.assertFalse(result["isError"])

    def test_unknown_method_is_reported(self):
        with StdioMCPSession(self.config()) as session:
            with self.assertRaisesRegex(MCPError, "method not found"):
                session.request("unknown/method", {})


if __name__ == "__main__":
    unittest.main()
