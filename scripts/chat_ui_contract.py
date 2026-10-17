#!/usr/bin/env python3
"""Read-only security and integration contract for the existing Chat UI stack."""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]

def inspect(compose: str, env: str):
    checks = {
        "open_webui_present": bool(re.search(r"(?m)^  open-webui:\s*$", compose)),
        "gateway_api_base": "OPENAI_API_BASE_URL: http://provider:8080/v1" in compose,
        "gateway_api_key": "OPENAI_API_KEY: ${PROVIDER_CLIENT_KEY}" in compose,
        "direct_ollama_disabled": 'ENABLE_OLLAMA_API: "false"' in compose,
        "signup_disabled_by_default": "OPENWEBUI_ENABLE_SIGNUP=false" in env,
        "ui_loopback_by_default": "OPENWEBUI_BIND_ADDRESS=127.0.0.1" in env,
        "provider_auth_enabled": 'ZEAZ_ALLOW_UNAUTHENTICATED: "false"' in compose,
        "provider_loopback": '"127.0.0.1:${PROVIDER_PORT:-8080}:8080"' in compose,
        "litellm_loopback": '"127.0.0.1:${LITELLM_PORT:-4000}:4000"' in compose,
        "ollama_loopback": '"127.0.0.1:${OLLAMA_PORT:-11434}:11434"' in compose,
        "conversation_volume": "open-webui-data:/app/backend/data" in compose,
        "secure_cookie_configurable": "OPENWEBUI_SESSION_COOKIE_SECURE:" in compose,
        "healthcheck": bool(re.search(r"(?s)^  open-webui:.*?healthcheck:", compose)),
    }
    return checks

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    checks = inspect((ROOT / "compose.yaml").read_text(), (ROOT / ".env.example").read_text())
    report = {"pass": all(checks.values()), "checks": checks, "scope": "static-only; not a runtime E2E or authorization audit"}
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        for name, passed in checks.items():
            print(f"{'PASS' if passed else 'FAIL'} {name}")
        print(report["scope"])
    return 0 if report["pass"] else 1

if __name__ == "__main__":
    sys.exit(main())
