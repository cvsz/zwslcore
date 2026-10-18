"""Regression tests for bounded webhook request-body reads."""
import importlib.util
import io
from pathlib import Path
import socket
import time
import unittest
from unittest.mock import Mock


MODULE = Path(__file__).resolve().parents[1] / "scripts" / "cloudshell-webhook.py"
spec = importlib.util.spec_from_file_location("cloudshell_webhook_body_limits", MODULE)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class WebhookBodyTests(unittest.TestCase):
    def make_handler(self, stream):
        handler = object.__new__(module.Handler)
        handler.path = "/webhook"
        handler.headers = {
            "Content-Length": "20",
            "X-ZWSL-Timestamp": str(int(time.time())),
            "X-ZWSL-Event-ID": "body-limits-regression",
        }
        handler.rfile = stream
        handler.reply = Mock()
        return handler

    def test_partial_body_rejected_before_signature(self):
        handler = self.make_handler(io.BytesIO(b'{"partial":true}'))
        handler.do_POST()
        handler.reply.assert_called_once_with(400, {"error": "incomplete_body"})

    def test_timed_out_body_rejected_before_signature(self):
        class StalledStream:
            def read(self, size):
                raise socket.timeout("request body stalled")

        handler = self.make_handler(StalledStream())
        handler.do_POST()
        handler.reply.assert_called_once_with(408, {"error": "body_read_timeout"})

    def test_connection_setup_sets_timeout(self):
        handler = object.__new__(module.Handler)
        handler.request = Mock()
        handler.client_address = ("127.0.0.1", 12345)
        handler.server = Mock()
        handler.request.makefile = Mock(return_value=io.BytesIO())
        handler.setup()
        handler.connection.settimeout.assert_called_once_with(10.0)


if __name__ == "__main__":
    unittest.main()
