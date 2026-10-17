#!/usr/bin/env python3
"""Opt-in local-only Ollama pool and bounded parallel agent jobs.

Remote Ollama endpoints must be reachable through authenticated private tunnels.
Do not expose Ollama ports directly to the internet.
"""
import argparse
import concurrent.futures
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

def endpoints():
    raw = os.environ.get("ZWSL_OLLAMA_ENDPOINTS", "http://127.0.0.1:11434")
    values = [s.strip().rstrip("/") for s in raw.split(",") if s.strip()]
    if not values:
        raise ValueError("No endpoints configured")
    for value in values:
        parsed = urllib.parse.urlsplit(value)
        if parsed.scheme not in ("http", "https") or not parsed.hostname or parsed.username or parsed.password or parsed.path not in ("", "/") or parsed.query or parsed.fragment:
            raise ValueError("Invalid Ollama endpoint")
        if parsed.scheme == "http" and parsed.hostname not in ("localhost", "127.0.0.1", "::1"):
            raise ValueError("Remote Ollama must use HTTPS with authenticated private transport")
    return values

def request(base, path, payload=None, timeout=30):
    url = base + path
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST" if data is not None else "GET")
    class NoRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *args, **kwargs):
            return None
    opener = urllib.request.build_opener(NoRedirect())
    with opener.open(req, timeout=timeout) as response:
        if response.geturl() != url:
            raise ValueError("Redirect refused")
        return json.load(response)

def healthy(nodes):
    results = []
    for node in nodes:
        try:
            result = request(node, "/api/tags", timeout=3)
            if isinstance(result.get("models"), list):
                results.append(node)
        except (OSError, ValueError, KeyError, urllib.error.URLError):
            pass
    return results

def run_job(node, model, prompt, timeout):
    start = time.monotonic()
    result = request(node, "/api/generate", {"model": model, "prompt": prompt, "stream": False}, timeout=timeout)
    return {"node": node, "response": result.get("response", ""), "elapsed_seconds": round(time.monotonic() - start, 3), "eval_count": result.get("eval_count"), "eval_duration": result.get("eval_duration")}

def main(argv=None):
    p = argparse.ArgumentParser(description="Cloud Shell-friendly Ollama pool; no permanent daemon")
    p.add_argument("command", choices=["health", "ask", "agents", "benchmark"])
    p.add_argument("--model", default=os.environ.get("ZWSL_MODEL", "qwen2.5-coder:7b"))
    p.add_argument("--prompt", default="Reply only OK")
    p.add_argument("--jobs", type=int, default=2)
    p.add_argument("--timeout", type=int, default=120)
    args = p.parse_args(argv)
    if not 1 <= args.jobs <= 10 or not 1 <= args.timeout <= 600:
        p.error("jobs must be 1..10 and timeout 1..600")
    try:
        nodes = healthy(endpoints())
        if args.command == "health":
            print(json.dumps({"healthy": nodes, "count": len(nodes)}))
            return 0 if nodes else 1
        if not nodes:
            raise RuntimeError("No healthy Ollama workers")
        if args.command == "ask":
            print(json.dumps(run_job(nodes[0], args.model, args.prompt, args.timeout), ensure_ascii=False))
            return 0
        jobs = args.jobs
        with concurrent.futures.ThreadPoolExecutor(max_workers=min(jobs, len(nodes))) as pool:
            futures = [pool.submit(run_job, nodes[i % len(nodes)], args.model, args.prompt if args.command == "benchmark" else f"Task {i+1}: {args.prompt}", args.timeout) for i in range(jobs)]
            results = []
            failures = []
            for future in futures:
                try:
                    results.append(future.result())
                except Exception as exc:
                    failures.append(type(exc).__name__)
        print(json.dumps({"completed": len(results), "failed": len(failures), "results": results, "failure_types": failures}, ensure_ascii=False))
        return 1 if failures else 0
    except (OSError, ValueError, RuntimeError, urllib.error.URLError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())
