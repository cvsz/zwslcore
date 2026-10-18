from __future__ import annotations

import sys
import tempfile
import textwrap
import threading
import time
import unittest
from pathlib import Path

from services.engineering.mcp import MCPError, MCPServerConfig, StdioMCPSession

DESCENDANT_STDERR_SERVER = textwrap.dedent(
    """
    import json, subprocess, sys
    # Spawn a child that inherits stderr and outlives the parent server, so
    # the stderr pipe never reaches EOF when the server is terminated.
    subprocess.Popen(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        stderr=None,
    )
    request = json.loads(sys.stdin.readline())
    reply = {"jsonrpc": "2.0", "id": request["id"], "result": {}}
    sys.stdout.write(json.dumps(reply) + "\\n")
    sys.stdout.flush()
    sys.stdin.readline()
    sys.exit(0)
    """
)

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


class MCPSessionRobustnessTests(unittest.TestCase):
    def _config(self, directory: str, source: str, timeout: float = 2.0) -> MCPServerConfig:
        script = Path(directory) / "server.py"
        script.write_text(source, encoding="utf-8")
        return MCPServerConfig(
            name="fake",
            command=(sys.executable, str(script)),
            timeout_seconds=timeout,
        )

    def test_partial_line_cannot_outlive_the_configured_timeout(self):
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, PARTIAL_LINE_SERVER, timeout=1.0)
            started = time.monotonic()
            with self.assertRaisesRegex(MCPError, "timed out"):
                with StdioMCPSession(config):
                    pass
            self.assertLess(time.monotonic() - started, 10.0)

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

    def test_stderr_drainer_exits_when_descendant_holds_the_pipe(self):
        # A descendant that inherits stderr (and outlives its parent) keeps
        # the pipe open, so shutdown must wake the drainer instead of waiting
        # for an EOF that never arrives.
        with tempfile.TemporaryDirectory() as directory:
            config = self._config(directory, DESCENDANT_STDERR_SERVER, timeout=5.0)
            first = time.monotonic()
            with StdioMCPSession(config):
                pass
            elapsed = time.monotonic() - first
            drainer = [t for t in threading.enumerate() if t.name.startswith("mcp-stderr-")]
            self.assertFalse(drainer)
            self.assertLess(elapsed, 8.0)


if __name__ == "__main__":
    unittest.main()
