#!/usr/bin/env python3
"""Run the existing zwslcore Provider on Cloud Shell; never expose Ollama or read .env."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
PROVIDER = ROOT / "services" / "provider"
STATE = Path(os.getenv("XDG_STATE_HOME", str(Path.home() / ".local/state"))) / "zwslcore-public-provider"
KEY, CONFIG, PID, LOG = (STATE / x for x in ("provider.key", "providers-cloudshell.yaml", "provider.pid", "provider.log"))


class Blocked(RuntimeError):
    pass


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Blocked("Unexpected redirect from local origin")


def local_json(url: str, *, token: str = "", payload: dict | None = None, timeout: int = 5) -> dict:
    if not url.startswith("http://127.0.0.1:"):
        raise Blocked("Only loopback origins are supported")
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open(urllib.request.Request(url, data=data, headers=headers), timeout=timeout) as response:
            raw = response.read(131073)
        if len(raw) > 131072:
            raise Blocked("Origin response too large")
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise Blocked("Unexpected JSON response")
        return result
    except (urllib.error.HTTPError, urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        if isinstance(exc, Blocked):
            raise
        raise Blocked("Local origin check failed: " + type(exc).__name__) from exc


def model_name(preferred: str = "") -> str:
    payload = local_json("http://127.0.0.1:11434/api/tags")
    names = {item.get("name") for item in payload.get("models", []) if isinstance(item, dict)}
    names = {n for n in names if isinstance(n, str) and n and not any(c in n for c in "\r\n\x00")}
    if preferred:
        if preferred not in names:
            raise Blocked("Requested Ollama model is not installed")
        return preferred
    if not names:
        raise Blocked("No installed local Ollama models")
    return "qwen2.5-coder:7b" if "qwen2.5-coder:7b" in names else sorted(names)[0]


def private_file(path: Path) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise Blocked("Required private file missing or symlinked")
    metadata = path.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise Blocked("File must be owned by current user and mode 0600")
    return path.read_bytes().strip()


def prepare_state() -> None:
    if STATE.is_symlink():
        raise Blocked("State directory must not be a symlink")
    STATE.mkdir(parents=True, exist_ok=True, mode=0o700)
    metadata = STATE.stat()
    if metadata.st_uid != os.getuid() or metadata.st_mode & 0o077:
        raise Blocked("State directory must be owner-only")


def write_new(path: Path, content: bytes) -> None:
    fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(content)
        stream.flush()
        os.fsync(stream.fileno())


def token_file() -> str:
    prepare_state()
    if not KEY.exists() and not KEY.is_symlink():
        write_new(KEY, (secrets.token_urlsafe(48) + "\n").encode())
    token = private_file(KEY).decode("ascii")
    if len(token) < 32:
        raise Blocked("Provider token is too short")
    return token


def render_config(model: str) -> str:
    quoted = json.dumps(model)
    return ("default_model: zeaz-free\n"
            "providers:\n  ollama:\n    api: openai\n"
            "    base_url: http://127.0.0.1:11434/v1\n"
            "    api_key: ollama\n    cost_class: FREE_LOCAL\n"
            "    timeout_seconds: 600\n"
            "models:\n  zeaz-free:\n    provider: ollama\n"
            f"    model: {quoted}\n  {quoted}:\n"
            f"    provider: ollama\n    model: {quoted}\n")


def healthy(token: str) -> bool:
    try:
        ready = local_json("http://127.0.0.1:8080/health/ready")
        models = local_json("http://127.0.0.1:8080/v1/models", token=token)
        return ready.get("status") == "ready" and bool(models.get("data"))
    except Blocked:
        return False


def verify(model: str = "", infer: bool = False) -> None:
    token = private_file(KEY).decode("ascii")
    if not healthy(token):
        raise Blocked("Provider missing, unhealthy or authentication mismatch")
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    try:
        with opener.open("http://127.0.0.1:8080/v1/models", timeout=4) as response:
            raise Blocked("Unauthenticated models request was permitted")
    except urllib.error.HTTPError as exc:
        if exc.code not in (401, 403):
            raise Blocked("Unauthenticated models request was not rejected") from exc
    result = local_json("http://127.0.0.1:8080/v1/models", token=token)
    names = {row.get("id") for row in result["data"] if isinstance(row, dict)}
    if model and model not in names:
        raise Blocked("Requested model alias unavailable from Provider")
    if infer:
        output = local_json("http://127.0.0.1:8080/v1/chat/completions", token=token,
                            payload={"model": model or "zeaz-free", "stream": False,
                                     "messages": [{"role": "user", "content": "Reply OK."}], "max_tokens": 8},
                            timeout=90)
        choices = output.get("choices")
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            raise Blocked("Model inference did not return choices")
        message = choices[0].get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str) or not message["content"].strip():
            raise Blocked("Model inference returned empty assistant text")
        print("INFERENCE=PASS")
    print("PROVIDER=PASS (authenticated loopback only)")


def start(preferred: str) -> None:
    token = token_file()
    model = model_name(preferred)
    if healthy(token):
        verify(model)
        print("START=SKIPPED_ALREADY_HEALTHY")
        return
    if CONFIG.is_symlink():
        raise Blocked("Configuration symlinks are not permitted")
    desired = render_config(model).encode()
    if CONFIG.exists():
        if private_file(CONFIG) != desired.strip():
            raise Blocked("Existing provider profile differs: manual review required")
    else:
        write_new(CONFIG, desired)
    check = subprocess.run(
        [sys.executable, "-c", "import fastapi, httpx, yaml, uvicorn, redis; import zeaz_provider.main"],
        cwd=PROVIDER, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, check=False)
    if check.returncode:
        raise Blocked("Provider dependencies unavailable in current Python interpreter")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        if s.connect_ex(("127.0.0.1", 8080)) == 0:
            raise Blocked("Provider port 8080 already owned by an unverified service")
    env = os.environ.copy()
    env.update({"ZEAZ_CONFIG": str(CONFIG), "ZEAZ_CLIENT_KEY_HASHES": hashlib.sha256(token.encode()).hexdigest(),
                "ZEAZ_CLIENT_KEYS": "", "ZEAZ_ALLOW_UNAUTHENTICATED": "false",
                "ZEAZ_HOST": "127.0.0.1", "ZEAZ_PORT": "8080", "ZEAZ_WORKERS": "1",
                "ZEAZ_METRICS_ENABLED": "false"})
    if LOG.is_symlink() or PID.is_symlink():
        raise Blocked("Runtime log or PID file must not be a symlink")
    fd = os.open(LOG, os.O_WRONLY | os.O_CREAT | os.O_APPEND | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "ab") as log:
        process = subprocess.Popen([sys.executable, "-c", "from zeaz_provider.main import run; run()"],
                                   cwd=PROVIDER, env=env, stdin=subprocess.DEVNULL,
                                   stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    PID.write_text(str(process.pid) + "\n")
    PID.chmod(0o600)
    for _ in range(50):
        if process.poll() is not None:
            raise Blocked("Provider exited during startup")
        if healthy(token):
            verify(model)
            print("START=PASS")
            return
        time.sleep(0.2)
    raise Blocked("Provider did not reach readiness")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("inspect", "start", "verify"))
    parser.add_argument("--model", default="")
    parser.add_argument("--infer", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.action == "inspect":
            chosen = model_name(args.model)
            print("OLLAMA_MODEL=PASS model=" + chosen)
            print("PROVIDER_READY=" + ("PASS" if KEY.is_file() and healthy(private_file(KEY).decode()) else "NOT_READY"))
        elif args.action == "start":
            start(args.model)
        else:
            verify(args.model, args.infer)
        return 0
    except (Blocked, OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"BLOCKED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
