#!/usr/bin/env python3
"""Benchmark zwslcore aliases without installing dependencies.

Only the local gateway is contacted; no remote API is contacted by this script
directly. Caller must explicitly allow remote routes and control quota externally.
"""
from __future__ import annotations

import argparse
import json
import os
import statistics
import sys
import time
import urllib.error
import urllib.request

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8080", help="Local provider URL")
    parser.add_argument("--model", action="append", default=[], help="Alias (repeatable)")
    parser.add_argument("--iterations", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=90)
    parser.add_argument("--allow-remote", action="store_true")
    parser.add_argument("--output", default="", help="JSON report path")
    args = parser.parse_args()
    if not 1 <= args.iterations <= 20 or not 1 <= args.timeout <= 600:
        parser.error("iterations must be 1..20 and timeout 1..600")
    models = args.model or ["zeaz-fast", "zeaz-coder"]
    if any(not model.startswith("zeaz-") for model in models):
        parser.error("only zwslcore model aliases are accepted")
    if not args.allow_remote and any("cloud" in model or model in {"zeaz-free", "zeaz-auto"} for model in models):
        parser.error("cloud-capable aliases require --allow-remote")
    from urllib.parse import urlsplit
    url = urlsplit(args.url)
    if url.scheme != "http" or url.hostname not in {"127.0.0.1", "localhost", "::1"} or url.username or url.password or url.query or url.fragment:
        parser.error("--url must be an HTTP loopback origin")
    key = os.getenv("PROVIDER_CLIENT_KEY", "")
    if not key:
        parser.error("PROVIDER_CLIENT_KEY must be set in the environment")
    endpoint = args.url.rstrip("/") + "/v1/chat/completions"
    records = []
    for model in models:
        for iteration in range(args.iterations):
            payload = {"model": model, "messages": [{"role": "user", "content": "Write a Python function to add two integers. Return code only."}], "max_tokens": 128, "stream": False}
            request = urllib.request.Request(endpoint, data=json.dumps(payload).encode(), headers={"Authorization": "Bearer " + key, "Content-Type": "application/json"}, method="POST")
            start = time.monotonic()
            try:
                with urllib.request.urlopen(request, timeout=args.timeout) as response:
                    result = json.load(response)
                elapsed = time.monotonic() - start
                usage = result.get("usage") or {}
                output_tokens = usage.get("completion_tokens")
                records.append({"model": model, "iteration": iteration + 1, "ok": True, "elapsed_s": round(elapsed, 3), "output_tokens": output_tokens if type(output_tokens) is int else None, "tokens_per_second": round(output_tokens / elapsed, 2) if type(output_tokens) is int and elapsed > 0 else None})
            except (urllib.error.URLError, TimeoutError, ValueError, KeyError) as exc:
                records.append({"model": model, "iteration": iteration + 1, "ok": False, "error_type": type(exc).__name__})
    summary = []
    for model in models:
        good = [r for r in records if r["model"] == model and r["ok"]]
        summary.append({"model": model, "successes": len(good), "attempts": args.iterations, "median_latency_s": round(statistics.median(r["elapsed_s"] for r in good), 3) if good else None, "median_tokens_per_second": round(statistics.median(r["tokens_per_second"] for r in good if r["tokens_per_second"] is not None), 2) if any(r["tokens_per_second"] is not None for r in good) else None})
    report = {"schema_version": 1, "summary": summary, "samples": records}
    output = json.dumps(report, indent=2)
    if args.output:
        from pathlib import Path
        Path(args.output).write_text(output + "\n", encoding="utf-8")
    print(output)
    return 0 if all(s["successes"] == args.iterations for s in summary) else 1

if __name__ == "__main__":
    sys.exit(main())
