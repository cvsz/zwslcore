#!/usr/bin/env python3
"""Run bounded local fault checks; Docker restarts require explicit opt-in."""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import http.server
import json
import queue
import socket
import socketserver
import subprocess
import sys
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.engineering.runtime import EngineeringRuntime, ProviderClient, ProviderTransportError


class FaultHandler(http.server.BaseHTTPRequestHandler):
    scenario = ""

    def do_GET(self) -> None:
        if self.scenario == "reset":
            self.connection.shutdown(socket.SHUT_RDWR)
            self.connection.close()
            return
        if self.scenario == "timeout":
            time.sleep(0.4)
            return
        if self.scenario == "malformed":
            body = b"{not-json"
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.scenario == "http-503":
            body = b"temporary upstream failure"
            self.send_response(503)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = b'{"status":"ready"}'
        self.send_response(200)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: Any) -> None:
        return


class LocalServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


def _source_metadata() -> dict[str, Any]:
    def git(*args: str) -> str:
        result = subprocess.run(
            ["git", "-C", str(ROOT), *args],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return result.stdout.strip()

    try:
        return {
            "head": git("rev-parse", "HEAD"),
            "branch": git("branch", "--show-current"),
            "dirty": bool(git("status", "--porcelain=v1")),
        }
    except (OSError, subprocess.SubprocessError):
        return {"head": "", "branch": "", "dirty": True, "available": False}


def _fault_request(scenario: str) -> None:
    FaultHandler.scenario = scenario
    server = LocalServer(("127.0.0.1", 0), FaultHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        url = f"http://127.0.0.1:{server.server_port}/health/ready"
        client = ProviderClient(timeout=0.1)
        request = urllib.request.Request(url)
        try:
            client._request_json(request, timeout=0.1, attempts=2)
        except ProviderTransportError:
            return
        raise RuntimeError(f"{scenario} was not classified as a provider infrastructure failure")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=1)


def _connection_refused() -> None:
    probe = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    probe.bind(("127.0.0.1", 0))
    port = probe.getsockname()[1]
    probe.close()
    client = ProviderClient(timeout=0.2)
    request = urllib.request.Request(f"http://127.0.0.1:{port}/health/ready")
    try:
        client._request_json(request, timeout=0.2, attempts=1)
    except ProviderTransportError:
        return
    raise RuntimeError("connection refused was not classified as a provider infrastructure failure")


def run_fault_suite() -> dict[str, Any]:
    scenarios = []
    for name in ("reset", "timeout", "malformed", "http-503"):
        _fault_request(name)
        scenarios.append({"name": name, "result": "PASS", "classification": "infrastructure"})
    _connection_refused()
    scenarios.append({"name": "connection-refused", "result": "PASS", "classification": "infrastructure"})

    try:
        EngineeringRuntime._parse_changes('{"changes":{}}')
    except ValueError:
        pass
    else:
        raise RuntimeError("invalid structured edit response passed validation")
    scope_case = EngineeringRuntime._parse_changes(
        '{"changes":[{"path":"../outside.py","content":"invalid"}]}'
    )
    if EngineeringRuntime._changes_within_scope(scope_case, {"services"}):
        raise RuntimeError("out-of-scope structured edit passed the path gate")
    scenarios.append({"name": "structured-output-and-path-gate", "result": "PASS", "classification": "engineering-validation"})

    return {
        "schema": 1,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "source": _source_metadata(),
        "mode": "loopback fault injection; no Docker service mutation",
        "status": "PASS",
        "scenarios": scenarios,
        "limitations": [
            "Container restart and mid-inference recovery require separate operator-invoked Compose scenarios.",
            "Disk pressure is not simulated by filling the host filesystem.",
        ],
    }


def _dotenv_value(name: str, default: str = "") -> str:
    path = ROOT / ".env"
    if not path.is_file():
        return default
    prefix = f"{name}="
    for line in path.read_text(encoding="utf-8").splitlines():
        item = line.strip()
        if item.startswith(prefix):
            value = item[len(prefix):]
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            return value
    return default


def _container_health(container: str) -> str:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{if .State.Health}}{{.State.Health.Status}}{{else}}none{{end}}", container],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"unable to inspect restart target {container}")
    return result.stdout.strip()


def _container_state(container: str) -> dict[str, Any]:
    result = subprocess.run(
        ["docker", "inspect", "--format", "{{json .State}}", container],
        capture_output=True,
        text=True,
        timeout=10,
    )
    if result.returncode != 0:
        raise RuntimeError(f"unable to inspect restart target {container}")
    value = json.loads(result.stdout)
    if not isinstance(value, dict):
        raise RuntimeError(f"restart target {container} returned invalid state")
    return value


def _wait_healthy(container: str, timeout: float = 180.0) -> float:
    started = time.monotonic()
    deadline = started + timeout
    while time.monotonic() < deadline:
        health = _container_health(container)
        if health == "healthy":
            return round(time.monotonic() - started, 3)
        if health in {"unhealthy", "none"}:
            raise RuntimeError(f"restart target {container} reported health={health}")
        time.sleep(2)
    raise TimeoutError(f"restart target {container} did not become healthy within {timeout:g}s")


def _wait_provider_ready(api_port: str, timeout: float = 120.0) -> float:
    started = time.monotonic()
    deadline = started + timeout
    ready_url = f"http://127.0.0.1:{api_port}/health/ready"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(ready_url, timeout=3) as response:
                if response.status == 200:
                    return round(time.monotonic() - started, 3)
        except (urllib.error.URLError, TimeoutError, OSError):
            pass
        time.sleep(2)
    raise TimeoutError("Provider readiness did not recover after the service restart")


def _send_inference(api_url: str, token: str, model: str, result_queue: queue.Queue[dict[str, Any]]) -> None:
    payload = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "Write a numbered list of 30 brief facts about safe software maintenance."}],
        "temperature": 0,
        "max_tokens": 512,
    }).encode("utf-8")
    request = urllib.request.Request(
        api_url,
        data=payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=180) as response:
            body = json.loads(response.read().decode("utf-8"))
            choices = body.get("choices")
            content = choices[0].get("message", {}).get("content") if isinstance(choices, list) and choices else None
            if response.status != 200 or not isinstance(content, str) or not content.strip():
                result_queue.put({"outcome": "invalid_response", "http_status": response.status})
            else:
                result_queue.put({"outcome": "success", "http_status": response.status})
    except urllib.error.HTTPError as exc:
        result_queue.put({"outcome": "http_error", "http_status": exc.code})
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        result_queue.put({"outcome": "transport_error", "error_type": type(exc).__name__})
    except Exception as exc:
        result_queue.put({"outcome": "client_error", "error_type": type(exc).__name__})


def run_provider_restart_during_preflight() -> dict[str, Any]:
    container = "zwslcore-provider"
    token = _dotenv_value("PROVIDER_CLIENT_KEY")
    if not token:
        raise RuntimeError("PROVIDER_CLIENT_KEY is missing from the local .env file")
    api_port = _dotenv_value("PROVIDER_PORT", "8080")
    base_url = f"http://127.0.0.1:{api_port}/v1"
    restart_result: dict[str, Any] = {}
    restart_started = threading.Event()

    def restart_provider() -> None:
        restart_started.set()
        started_at = time.monotonic()
        try:
            result = subprocess.run(
                ["docker", "restart", "--time", "2", container],
                capture_output=True,
                text=True,
                timeout=120,
            )
            restart_result["returncode"] = result.returncode
        except Exception as exc:
            restart_result["error_type"] = type(exc).__name__
        finally:
            restart_result["duration_seconds"] = round(time.monotonic() - started_at, 3)

    class RestartingProviderClient(ProviderClient):
        triggered = False
        restart_thread: threading.Thread | None = None

        def _request_json(
            self,
            request: urllib.request.Request,
            *,
            timeout: int | None = None,
            attempts: int = 1,
        ) -> dict[str, Any]:
            if request.full_url.endswith("/models") and not self.triggered:
                self.triggered = True
                self.restart_thread = threading.Thread(target=restart_provider, daemon=True)
                self.restart_thread.start()
                if not restart_started.wait(timeout=5):
                    raise TimeoutError("Provider restart did not start during preflight")
                deadline = time.monotonic() + 15
                restart_observed = False
                while time.monotonic() < deadline:
                    state = _container_state(container)
                    if (
                        state.get("Restarting") is True
                        or state.get("Running") is not True
                    ):
                        restart_observed = True
                        break
                    time.sleep(0.05)
                if not restart_observed:
                    raise TimeoutError("Provider restart was not observed during preflight")
            return super()._request_json(request, timeout=timeout, attempts=attempts)

    client = RestartingProviderClient(base_url=base_url, api_key=token, model="zeaz-fast", timeout=15)
    first_preflight_outcome = "success"
    try:
        client.preflight()
    except ProviderTransportError:
        first_preflight_outcome = "infrastructure_error"
    except Exception as exc:
        raise RuntimeError(f"unexpected Provider preflight result: {type(exc).__name__}") from exc

    if client.restart_thread is None:
        raise RuntimeError("Provider restart was not triggered during preflight")
    client.restart_thread.join(timeout=125)
    if client.restart_thread.is_alive() or restart_result.get("returncode") != 0:
        raise RuntimeError("Provider restart failed during preflight")
    if "error_type" in restart_result:
        raise RuntimeError(f"Provider restart failed during preflight: {restart_result['error_type']}")

    healthy_wait = _wait_healthy(container)
    ready_wait = _wait_provider_ready(api_port)
    client.preflight()
    return {
        "name": "provider-restart-during-preflight",
        "result": "PASS",
        "classification": "infrastructure-recovery",
        "container": container,
        "restart_observed_between_preflight_checks": True,
        "first_preflight_outcome": first_preflight_outcome,
        "followup_preflight": "PASS",
        "engineering_attempt_started": False,
        "docker_restart_command_seconds": restart_result["duration_seconds"],
        "health_wait_seconds": healthy_wait,
        "readiness_wait_seconds": ready_wait,
    }


def run_model_unavailable_check() -> dict[str, Any]:
    token = _dotenv_value("PROVIDER_CLIENT_KEY")
    if not token:
        raise RuntimeError("PROVIDER_CLIENT_KEY is missing from the local .env file")
    api_port = _dotenv_value("PROVIDER_PORT", "8080")
    client = ProviderClient(
        base_url=f"http://127.0.0.1:{api_port}/v1",
        api_key=token,
        model="zeaz-chaos-model-unavailable",
        timeout=15,
    )
    try:
        client.preflight()
    except RuntimeError as exc:
        if "is not advertised by provider" not in str(exc):
            raise RuntimeError(f"unexpected model-unavailable classification: {type(exc).__name__}") from exc
        return {
            "name": "model-unavailable-preflight",
            "result": "PASS",
            "classification": "configuration",
            "model_inference_started": False,
            "engineering_attempt_started": False,
        }
    raise RuntimeError("unavailable model unexpectedly passed Provider preflight")


def run_restart_during_inference(service: str) -> dict[str, Any]:
    targets = {
        "provider": ("zwslcore-provider", "zeaz-local"),
        "litellm": ("zwslcore-litellm", "zeaz-auto"),
        "ollama": ("zwslcore-ollama", "zeaz-local"),
    }
    container, model = targets[service]
    token = _dotenv_value("PROVIDER_CLIENT_KEY")
    if not token:
        raise RuntimeError("PROVIDER_CLIENT_KEY is missing from the local .env file")
    api_port = _dotenv_value("PROVIDER_PORT", "8080")
    api_url = f"http://127.0.0.1:{api_port}/v1/chat/completions"
    result_queue: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=1)
    worker = threading.Thread(
        target=_send_inference,
        args=(api_url, token, model, result_queue),
        daemon=True,
        name=f"chaos-inference-{service}",
    )
    worker.start()
    time.sleep(2.0)
    if not worker.is_alive():
        result = result_queue.get_nowait()
        raise RuntimeError(f"inference completed before {service} restart: {result['outcome']}")

    restart_started = time.monotonic()
    restarted = subprocess.run(
        ["docker", "restart", "--time", "2", container],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if restarted.returncode != 0:
        raise RuntimeError(f"Docker restart failed for {container}")
    restart_duration = round(time.monotonic() - restart_started, 3)
    healthy_duration = _wait_healthy(container)
    ready_duration = _wait_provider_ready(api_port)

    worker.join(timeout=185)
    if worker.is_alive():
        raise TimeoutError(f"inference request did not settle after {service} recovery")
    outcome = result_queue.get_nowait()
    if outcome.get("outcome") == "transport_error" and outcome.get("error_type") == "TimeoutError":
        raise TimeoutError(f"inference request timed out after {service} recovery")
    if outcome.get("outcome") in {"http_error", "client_error", "invalid_response"} and int(outcome.get("http_status", 500)) < 500:
        raise RuntimeError(f"inference returned an unexpected client failure during {service} restart")
    if outcome.get("outcome") not in {"success", "http_error", "transport_error"}:
        raise RuntimeError(f"inference returned an unhandled outcome during {service} restart")

    return {
        "name": f"{service}-restart-during-inference",
        "result": "PASS",
        "classification": "infrastructure-recovery",
        "container": container,
        "inference_pending_when_restart_started": True,
        "client_outcome": outcome,
        "restart_duration_seconds": restart_duration,
        "target_healthy_after_seconds": healthy_duration,
        "provider_ready_after_seconds": ready_duration,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", help="optional machine-readable JSON report path")
    parser.add_argument(
        "--restart-service",
        action="append",
        choices=("provider", "litellm", "ollama"),
        default=[],
        help="explicitly restart this local container during an in-flight Provider inference; repeat for multiple services",
    )
    parser.add_argument(
        "--restart-provider-during-preflight",
        action="store_true",
        help="restart the local Provider between readiness and model checks, then verify preflight recovers",
    )
    parser.add_argument(
        "--check-model-unavailable",
        action="store_true",
        help="verify Provider preflight rejects a model that is not installed or advertised",
    )
    args = parser.parse_args()
    try:
        report = run_fault_suite()
        if args.restart_service:
            for service in args.restart_service:
                report["scenarios"].append(run_restart_during_inference(service))
        if args.restart_provider_during_preflight:
            report["scenarios"].append(run_provider_restart_during_preflight())
        if args.check_model_unavailable:
            report["scenarios"].append(run_model_unavailable_check())
        if args.restart_service or args.restart_provider_during_preflight:
            report["mode"] = "loopback fault injection and explicit local Docker restart scenarios"
            report["limitations"] = [
                "Disk pressure is not simulated by filling the host filesystem.",
                "Cold model pull is not triggered to avoid large network and disk downloads.",
            ]
        elif args.check_model_unavailable:
            report["mode"] = "loopback fault injection and explicit local model preflight check"
            report["limitations"] = [
                "Provider/container restart scenarios were not invoked in this report.",
                "Disk pressure is not simulated by filling the host filesystem.",
                "Cold model pull is not triggered to avoid large network and disk downloads.",
            ]
        if args.output:
            path = Path(args.output).expanduser()
            report["report_path"] = str(path.resolve())
        encoded = json.dumps(report, indent=2, sort_keys=True) + "\n"
        if args.output:
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            encoded_bytes = encoded.encode("utf-8")
            path.write_bytes(encoded_bytes)
            path.chmod(0o600)
            checksum = path.with_suffix(path.suffix + ".sha256")
            checksum.write_text(f"{hashlib.sha256(encoded_bytes).hexdigest()}  {path.name}\n", encoding="utf-8")
            checksum.chmod(0o600)
        print(json.dumps(report, indent=2, sort_keys=True))
    except Exception as exc:
        print(f"chaos check failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
