from __future__ import annotations

import os
import signal
import sys
import tempfile
import textwrap
import time
import unittest
from pathlib import Path

from services.engineering.mcp import MCPError, MCPServerConfig, StdioMCPSession

PARTIAL_LINE_SERVER = textwrap.dedent(
    """
    import sys, time
    sys.stdin.readline()
    sys.stdout.write('{"jsonrpc"')  # partial line, never terminated
    sys.stdout.flush()
    time.sleep(30)
    """
)

NOISY_STDERR_SERVER = textwrap.dedent(
    """
    import json, sys
    request = json.loads(sys.stdin.readline())
    sys.stderr.write("x" * 400000)  # larger than any pipe buffer
    sys.stderr.flush()
    reply = {"jsonrpc": "2.0", "id": request["id"], "result": {}}
    sys.stdout.write(json.dumps(reply) + "\\n")
    sys.stdout.flush()
    sys.stdin.readline()
    """
)

CRASHING_SERVER = textwrap.dedent(
    """
    import sys
    sys.stdin.readline()
    sys.stderr.write("boom: configuration missing")
    sys.stderr.flush()
    """
)

CHILD_HOLDS_STDERR_SERVER = textwrap.dedent(
    """
    import json, pathlib, subprocess, sys
    child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    pathlib.Path(sys.argv[1]).write_text(str(child.pid), encoding="utf-8")
    request = json.loads(sys.stdin.readline())
    reply = {"jsonrpc": "2.0", "id": request["id"], "result": {}}
    sys.stdout.write(json.dumps(reply) + "\\n")
    sys.stdout.flush()
    sys.stdin.readline()
    """
)

STALLED_WRITER_SERVER = textwrap.dedent(
    """
    import json, sys, time
    request = json.loads(sys.stdin.readline())
    reply = {"jsonrpc": "2.0", "id": request["id"], "result": {}}
    sys.stdout.write(json.dumps(reply) + "\\n")
    sys.stdout.flush()
    time.sleep(30)  # never reads the next, deliberately oversized request
    """
)


class MCPSessionRobustnessTests(unittest.TestCase):
    def _config(self, directory: str, source: str, timeout: float = 2.0) -> MCPServerConfig:
        script = Path(directory) / "server.py"
        script.write_text(source, encoding="utf-8")
        return MCPServerConfig(
            name="fake",
            command=(sys.executable, str(script)),
            timeout_seconds=timeout,
        )

    @staticmethod
    def _pid_running(pid: int) -> bool:
        try:
            fields = Path(f"/proc/{pid}/stat").read_text(encoding="utf-8").rsplit(")", 1)[1].split()
        except FileNotFoundError:
            return False
        return fields[0] != "Z"

    def test_partial_line_cannot_outlive_the_configured_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, PARTIAL_LINE_SERVER, timeout=1.0)
            started = time.monotonic()
            with self.assertRaisesRegex(MCPError, "timed out"):
                with StdioMCPSession(config):
                    pass
            self.assertLess(time.monotonic() - started, 10.0)

    def test_request_write_cannot_outlive_the_configured_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, STALLED_WRITER_SERVER, timeout=0.5)
            with StdioMCPSession(config) as session:
                started = time.monotonic()
                with self.assertRaisesRegex(MCPError, "request timed out while writing"):
                    session.request("tools/call", {"payload": "x" * 1_000_000})
                self.assertLess(time.monotonic() - started, 2.0)

    def test_chatty_stderr_does_not_deadlock_the_server(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, NOISY_STDERR_SERVER, timeout=5.0)
            with StdioMCPSession(config) as session:
                self.assertIsNotNone(session.process)

    def test_stderr_tail_is_reported_when_server_exits(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, CRASHING_SERVER, timeout=5.0)
            with self.assertRaisesRegex(MCPError, "boom: configuration missing"):
                with StdioMCPSession(config):
                    pass

    def test_close_releases_pipe_descriptors(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, NOISY_STDERR_SERVER, timeout=5.0)
            session = StdioMCPSession(config)
            with session:
                process = session.process
            self.assertIsNotNone(process)
            self.assertTrue(process.stdin.closed)
            self.assertTrue(process.stdout.closed)
            self.assertTrue(process.stderr.closed)

    def test_close_stops_stderr_reader_when_descendant_keeps_pipe_open(self):
        with tempfile.TemporaryDirectory() as directory:
            pid_path = Path(directory) / "child.pid"
            script = Path(directory) / "server.py"
            script.write_text(CHILD_HOLDS_STDERR_SERVER, encoding="utf-8")
            config = MCPServerConfig(
                name="fake",
                command=(sys.executable, str(script), str(pid_path)),
                timeout_seconds=5.0,
            )
            session = StdioMCPSession(config)
            try:
                session.__enter__()
                reader = session._stderr_thread
                process = session.process
                session.close()
                self.assertIsNotNone(reader)
                self.assertFalse(reader.is_alive())
                self.assertIsNotNone(process)
                self.assertTrue(process.stderr.closed)
                child_pid = int(pid_path.read_text(encoding="utf-8"))
                for _ in range(40):
                    if not self._pid_running(child_pid):
                        break
                    time.sleep(0.05)
                self.assertFalse(self._pid_running(child_pid), "MCP session leaked its helper process")
            finally:
                if pid_path.exists():
                    try:
                        os.kill(int(pid_path.read_text(encoding="utf-8")), signal.SIGTERM)
                    except (ProcessLookupError, ValueError):
                        pass
                session.close()


if __name__ == "__main__":
    unittest.main()
