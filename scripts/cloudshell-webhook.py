#!/usr/bin/env python3
"""Loopback-only signed webhook receiver; no arbitrary command execution."""
import hashlib
import hmac
import json
import os
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 65536
PORT = int(os.getenv("ZWSL_WEBHOOK_PORT", "8765"))
SECRET_FILE = Path(os.environ.get("ZWSL_WEBHOOK_SECRET_FILE", str(Path.home()/".config/zwslcore/webhook.key")))

def load_secret():
    if SECRET_FILE.is_symlink() or not SECRET_FILE.is_file() or SECRET_FILE.stat().st_mode & 0o077:
        raise RuntimeError("Webhook secret missing or permissions too broad")
    secret = SECRET_FILE.read_bytes().strip()
    if len(secret) < 32:
        raise RuntimeError("Webhook secret must be at least 32 bytes")
    return secret

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            return self.reply(404, {"error": "not_found"})
        return self.reply(200, {"status": "healthy"})
    def do_POST(self):
        if self.path != "/webhook":
            return self.reply(404, {"error": "not_found"})
        try:
            length = int(self.headers.get("Content-Length", "-1"))
        except ValueError:
            return self.reply(400, {"error": "invalid_length"})
        if length < 0 or length > MAX_BODY:
            return self.reply(413, {"error": "invalid_length"})
        timestamp = self.headers.get("X-ZWSL-Timestamp", "")
        event_id = self.headers.get("X-ZWSL-Event-ID", "")
        try:
            sent_at = int(timestamp)
        except ValueError:
            return self.reply(401, {"error": "invalid_timestamp"})
        if abs(time.time() - sent_at) > 300 or not (1 <= len(event_id) <= 128) or not all(c.isalnum() or c in "-_" for c in event_id):
            return self.reply(401, {"error": "invalid_timestamp_or_event"})
        body = self.rfile.read(length)
        supplied = self.headers.get("X-ZWSL-Signature", "")
        if not supplied.startswith("sha256="):
            return self.reply(401, {"error": "unauthorized"})
        expected = hmac.new(self.server.webhook_secret, (timestamp + '.' + event_id + '.').encode() + body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(supplied[7:], expected):
            return self.reply(401, {"error": "unauthorized"})
        try:
            payload = json.loads(body)
            if not isinstance(payload, dict):
                raise ValueError("not an object")
        except (ValueError, UnicodeDecodeError):
            return self.reply(400, {"error": "invalid_json"})
        with self.server.seen_lock:
            now = time.time()
            self.server.seen = {k: v for k, v in self.server.seen.items() if now - v < 600}
            if event_id in self.server.seen:
                return self.reply(409, {"error": "replay"})
            self.server.seen[event_id] = now
        # Intentionally no provider-specific dispatch until contracts are defined.
        return self.reply(202, {"accepted": True, "executed": False})
    def reply(self, status, payload):
        body = json.dumps(payload).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)
    def log_message(self, fmt, *args):
        pass

def main():
    if not (1 <= PORT <= 65535):
        raise ValueError("Invalid webhook port")
    secret = load_secret()
    with ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as server:
        server.webhook_secret = secret
        server.seen_lock = threading.Lock()
        server.seen = {}
        server.serve_forever()

if __name__ == "__main__":
    main()
