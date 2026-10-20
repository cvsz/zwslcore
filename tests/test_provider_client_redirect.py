from __future__ import annotations

import http.server
import threading
import unittest

from services.engineering.runtime import ProviderClient, ProviderTransportError


class _Recorder:
    def __init__(self) -> None:
        self.target_authorization: list[str | None] = []


def _serve(handler_cls):
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


class ProviderClientRedirectTests(unittest.TestCase):
    def test_redirect_is_refused_and_bearer_token_is_not_forwarded(self):
        recorder = _Recorder()

        class Target(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                recorder.target_authorization.append(self.headers.get("Authorization"))
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"data": []}')

            def log_message(self, *args):
                return

        target, target_thread = _serve(Target)

        class Redirector(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{target.server_port}/models")
                self.end_headers()

            def log_message(self, *args):
                return

        redirector, redirector_thread = _serve(Redirector)
        try:
            client = ProviderClient(
                base_url=f"http://127.0.0.1:{redirector.server_port}/v1",
                api_key="secret-token",
                timeout=5,
            )
            with self.assertRaises(RuntimeError) as raised:
                client._request_json(
                    __import__("urllib.request").request.Request(
                        f"{client.base_url}/models",
                        headers={"Authorization": f"Bearer {client.api_key}"},
                    )
                )
            self.assertNotIsInstance(raised.exception, ProviderTransportError)
            self.assertIn("302", str(raised.exception))
            self.assertEqual(recorder.target_authorization, [])
        finally:
            for server, thread in ((redirector, redirector_thread), (target, target_thread)):
                server.shutdown()
                server.server_close()
                thread.join(timeout=2)


if __name__ == "__main__":
    unittest.main()
