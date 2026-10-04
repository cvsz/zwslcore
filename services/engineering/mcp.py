from __future__ import annotations

import dataclasses
import json
import os
import selectors
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DEFAULT_CONFIG = Path.home() / ".zwslcore" / "mcp" / "servers.json"
DEFAULT_PROTOCOL_VERSION = "2025-06-18"
MAX_MESSAGE_BYTES = 2 * 1024 * 1024


class MCPError(RuntimeError):
    pass


@dataclasses.dataclass(frozen=True)
class MCPServerConfig:
    name: str
    command: tuple[str, ...]
    enabled: bool = True
    cwd: str | None = None
    inherit_env: tuple[str, ...] = ()
    environment: dict[str, str] = dataclasses.field(default_factory=dict)
    timeout_seconds: float = 30.0
    protocol_version: str = DEFAULT_PROTOCOL_VERSION


@dataclasses.dataclass(frozen=True)
class MCPTool:
    server: str
    name: str
    description: str
    input_schema: dict[str, Any]

    @property
    def qualified_name(self) -> str:
        return f"{self.server}.{self.name}"


def _validate_server_name(value: str) -> str:
    name = value.strip()
    if not name or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-." for ch in name):
        raise MCPError(f"invalid MCP server name: {value!r}")
    return name


def load_config(path: str | Path = DEFAULT_CONFIG) -> dict[str, MCPServerConfig]:
    target = Path(path).expanduser()
    try:
        payload = json.loads(target.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise MCPError(f"unable to read MCP config {target}: {exc}") from exc

    if not isinstance(payload, dict):
        raise MCPError("MCP config root must be an object")
    raw_servers = payload.get("servers", {})
    if not isinstance(raw_servers, dict):
        raise MCPError("MCP config servers must be an object")

    result: dict[str, MCPServerConfig] = {}
    for raw_name, raw in raw_servers.items():
        if not isinstance(raw_name, str) or not isinstance(raw, dict):
            raise MCPError("MCP server entries must be named objects")
        name = _validate_server_name(raw_name)
        raw_command = raw.get("command")
        if not isinstance(raw_command, list) or not raw_command or not all(
            isinstance(item, str) and item for item in raw_command
        ):
            raise MCPError(f"MCP server {name!r} command must be a non-empty string array")

        raw_inherit = raw.get("inherit_env", [])
        if not isinstance(raw_inherit, list) or not all(isinstance(item, str) and item for item in raw_inherit):
            raise MCPError(f"MCP server {name!r} inherit_env must be a string array")

        raw_env = raw.get("environment", {})
        if not isinstance(raw_env, dict) or not all(
            isinstance(key, str) and isinstance(value, str)
            for key, value in raw_env.items()
        ):
            raise MCPError(f"MCP server {name!r} environment must be a string map")

        timeout = raw.get("timeout_seconds", 30)
        if not isinstance(timeout, (int, float)) or timeout <= 0 or timeout > 300:
            raise MCPError(f"MCP server {name!r} timeout_seconds must be within (0, 300]")

        protocol = raw.get("protocol_version", DEFAULT_PROTOCOL_VERSION)
        if not isinstance(protocol, str) or not protocol.strip():
            raise MCPError(f"MCP server {name!r} protocol_version must be a string")

        cwd = raw.get("cwd")
        if cwd is not None and not isinstance(cwd, str):
            raise MCPError(f"MCP server {name!r} cwd must be a string")

        enabled = raw.get("enabled", True)
        if type(enabled) is not bool:
            raise MCPError(f"MCP server {name!r} enabled must be boolean")

        result[name] = MCPServerConfig(
            name=name,
            command=tuple(raw_command),
            enabled=enabled,
            cwd=cwd,
            inherit_env=tuple(raw_inherit),
            environment=dict(raw_env),
            timeout_seconds=float(timeout),
            protocol_version=protocol,
        )
    return result


class StdioMCPSession:
    def __init__(self, config: MCPServerConfig) -> None:
        self.config = config
        self.process: subprocess.Popen[bytes] | None = None
        self._next_id = 1
        self._selector: selectors.BaseSelector | None = None

    def __enter__(self) -> "StdioMCPSession":
        if not self.config.enabled:
            raise MCPError(f"MCP server {self.config.name!r} is disabled")

        env: dict[str, str] = {}
        for key in self.config.inherit_env:
            if key in os.environ:
                env[key] = os.environ[key]
        env.update(self.config.environment)

        base_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": os.environ.get("HOME", ""),
            "LANG": os.environ.get("LANG", "C.UTF-8"),
        }
        base_env.update(env)

        cwd = Path(self.config.cwd).expanduser().resolve() if self.config.cwd else None
        try:
            self.process = subprocess.Popen(
                list(self.config.command),
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=str(cwd) if cwd else None,
                env=base_env,
                shell=False,
                bufsize=0,
            )
        except OSError as exc:
            raise MCPError(f"unable to start MCP server {self.config.name!r}: {exc}") from exc

        assert self.process.stdout is not None
        self._selector = selectors.DefaultSelector()
        self._selector.register(self.process.stdout, selectors.EVENT_READ)

        try:
            initialized = self.request(
                "initialize",
                {
                    "protocolVersion": self.config.protocol_version,
                    "capabilities": {},
                    "clientInfo": {"name": "zwslcore", "version": "1"},
                },
            )
            if not isinstance(initialized, dict):
                raise MCPError("MCP initialize result must be an object")
            self.notify("notifications/initialized", {})
        except Exception:
            self.close()
            raise
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        process = self.process
        self.process = None
        selector = self._selector
        self._selector = None
        if selector is not None:
            selector.close()
        if process is None:
            return
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def _send(self, payload: dict[str, Any]) -> None:
        if self.process is None or self.process.stdin is None:
            raise MCPError("MCP session is not connected")
        raw = json.dumps(payload, separators=(",", ":")).encode("utf-8") + b"\n"
        if len(raw) > MAX_MESSAGE_BYTES:
            raise MCPError("MCP request exceeds message size limit")
        try:
            self.process.stdin.write(raw)
            self.process.stdin.flush()
        except (BrokenPipeError, OSError) as exc:
            raise MCPError(f"MCP server {self.config.name!r} stdin failed: {exc}") from exc

    def _read_message(self, deadline: float) -> dict[str, Any]:
        if self.process is None or self.process.stdout is None or self._selector is None:
            raise MCPError("MCP session is not connected")

        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise MCPError(f"MCP server {self.config.name!r} response timed out")
            events = self._selector.select(timeout=remaining)
            if not events:
                raise MCPError(f"MCP server {self.config.name!r} response timed out")

            raw = self.process.stdout.readline(MAX_MESSAGE_BYTES + 1)
            if not raw:
                stderr = b""
                if self.process.stderr is not None:
                    try:
                        stderr = self.process.stderr.read(4096)
                    except OSError:
                        pass
                detail = stderr.decode("utf-8", errors="replace").strip()
                raise MCPError(
                    f"MCP server {self.config.name!r} closed stdout"
                    + (f": {detail[:1000]}" if detail else "")
                )
            if len(raw) > MAX_MESSAGE_BYTES:
                raise MCPError("MCP response exceeds message size limit")
            try:
                value = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(value, dict):
                return value

    def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        request_id = self._next_id
        self._next_id += 1
        self._send(
            {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": method,
                "params": params or {},
            }
        )
        deadline = time.monotonic() + self.config.timeout_seconds
        while True:
            message = self._read_message(deadline)
            if message.get("id") != request_id:
                continue
            error = message.get("error")
            if isinstance(error, dict):
                code = error.get("code")
                text = error.get("message", "unknown error")
                raise MCPError(f"MCP {method} failed ({code}): {text}")
            if "result" not in message:
                raise MCPError(f"MCP {method} response missing result")
            return message["result"]

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        self._send(
            {
                "jsonrpc": "2.0",
                "method": method,
                "params": params or {},
            }
        )

    def list_tools(self) -> tuple[MCPTool, ...]:
        result = self.request("tools/list", {})
        if not isinstance(result, dict) or not isinstance(result.get("tools"), list):
            raise MCPError("MCP tools/list response missing tools[]")
        tools: list[MCPTool] = []
        for raw in result["tools"]:
            if not isinstance(raw, dict):
                continue
            name = raw.get("name")
            if not isinstance(name, str) or not name:
                continue
            description = raw.get("description")
            schema = raw.get("inputSchema", {})
            if not isinstance(schema, dict):
                schema = {}
            tools.append(
                MCPTool(
                    server=self.config.name,
                    name=name,
                    description=description if isinstance(description, str) else "",
                    input_schema=schema,
                )
            )
        return tuple(sorted(tools, key=lambda item: item.name))

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return self.request("tools/call", {"name": name, "arguments": arguments})


def list_server_tools(config: MCPServerConfig) -> tuple[MCPTool, ...]:
    with StdioMCPSession(config) as session:
        return session.list_tools()


def call_server_tool(
    config: MCPServerConfig,
    tool_name: str,
    arguments: dict[str, Any],
) -> Any:
    with StdioMCPSession(config) as session:
        return session.call_tool(tool_name, arguments)


def split_qualified_tool(value: str) -> tuple[str, str]:
    server, dot, tool = value.partition(".")
    if not dot or not server or not tool:
        raise MCPError("qualified MCP tool must use server.tool syntax")
    return server, tool
