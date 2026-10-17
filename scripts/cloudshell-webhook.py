#!/usr/bin/env python3
"""Loopback-only signed webhook receiver; no arbitrary command execution."""
import hashlib
import hmac
import json
import os
import time
import sqlite3
import stat
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

MAX_BODY = 65536
PORT = int(os.getenv("ZWSL_WEBHOOK_PORT", "8765"))
SECRET_FILE = Path(os.environ.get("ZWSL_WEBHOOK_SECRET_FILE", str(Path.home()/".config/zwslcore/webhook.key")))
REPLAY_DB = Path(os.environ.get("ZWSL_WEBHOOK_REPLAY_DB", str(Path.home()/".local/state/zwslcore-webhook/replay.sqlite3")))
REPLAY_TTL_SECONDS = 600

def load_secret():
    if SECRET_FILE.is_symlink() or not SECRET_FILE.is_file() or SECRET_FILE.stat().st_mode & 0o077:
        raise RuntimeError("Webhook secret missing or permissions too broad")
    secret = SECRET_FILE.read_bytes().strip()
    if len(secret) < 32:
        raise RuntimeError("Webhook secret must be at least 32 bytes")
    return secret


class ReplayStore:
    """Durable atomic replay defense; event identifiers are stored as keyed hashes."""

    def __init__(self, path: Path, secret: bytes):
        self.path = path
        self.secret = secret
        parent = path.parent
        if parent.is_symlink():
            raise RuntimeError("Replay state directory must not be a symlink")
        parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        info = parent.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise RuntimeError("Replay state directory must be owner-only")
        if path.is_symlink() or (path.exists() and not path.is_file()):
            raise RuntimeError("Replay database must be a private regular file")
        if path.exists():
            self._check_file()
        with self._connect() as database:
            # Set journal mode during startup only; doing this on every
            # concurrent request can cause avoidable SQLITE_BUSY errors.
            database.execute("PRAGMA journal_mode=DELETE")
            database.execute("CREATE TABLE IF NOT EXISTS events (event_hash TEXT PRIMARY KEY, seen_at INTEGER NOT NULL)")
        self._check_file()

    def _check_file(self):
        if self.path.is_symlink() or not self.path.is_file():
            raise RuntimeError("Replay database missing or replaced")
        info = self.path.stat()
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o077:
            raise RuntimeError("Replay database permissions must be private")

    def _connect(self):
        database = sqlite3.connect(self.path, timeout=5.0)
        if not self.path.is_symlink():
            os.chmod(self.path, 0o600)
        database.execute("PRAGMA synchronous=FULL")
        return database

    def accept(self, event_id: str, now: int) -> bool:
        self._check_file()
        digest = hmac.new(self.secret, b"event-id:" + event_id.encode("ascii"), hashlib.sha256).hexdigest()
        with self._connect() as database:
            database.execute("BEGIN IMMEDIATE")
            database.execute("DELETE FROM events WHERE seen_at < ?", (now - REPLAY_TTL_SECONDS,))
            inserted = database.execute("INSERT OR IGNORE INTO events(event_hash, seen_at) VALUES (?, ?)", (digest, now))
            return inserted.rowcount == 1

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/health":
            return self.reply(404, {"error": "not_found"})
        return self.reply(200, {"status": "healthy"})
    def do_POST(self):
        if self.path not in ("/webhook", "/webhook/"):
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
        if abs(time.time() - sent_at) > 300 or not (1 <= len(event_id) <= 128) or not all(c.isascii() and (c.isalnum() or c in "-_") for c in event_id):
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
        try:
            if not self.server.replay_store.accept(event_id, int(time.time())):
                return self.reply(409, {"error": "replay"})
        except (OSError, RuntimeError, sqlite3.Error):
            return self.reply(503, {"error": "replay_store_unavailable"})
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
    os.umask(0o077)
    secret = load_secret()
    store = ReplayStore(REPLAY_DB, secret)
    with ThreadingHTTPServer(("127.0.0.1", PORT), Handler) as server:
        server.webhook_secret = secret
        server.replay_store = store
        server.serve_forever()

if __name__ == "__main__":
    main()
