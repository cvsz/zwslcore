#!/usr/bin/env python3
"""Discover current zero-price chat models from OpenRouter without storing secrets."""

from __future__ import annotations

import json
import os
import sys
import urllib.request

URL = "https://openrouter.ai/api/v1/models"


def is_zero(value: object) -> bool:
    try:
        return float(str(value)) == 0.0
    except (TypeError, ValueError):
        return False


def main() -> int:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    headers = {"User-Agent": "zwslcore-free-model-sync/1"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    req = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(req, timeout=20) as response:
        payload = json.load(response)

    selected = []
    for item in payload.get("data", []):
        pricing = item.get("pricing") or {}
        arch = item.get("architecture") or {}
        output_modalities = arch.get("output_modalities") or ["text"]
        if not (is_zero(pricing.get("prompt")) and is_zero(pricing.get("completion"))):
            continue
        if "text" not in output_modalities:
            continue
        selected.append(
            {
                "id": item.get("id"),
                "name": item.get("name"),
                "context_length": item.get("context_length"),
            }
        )

    selected.sort(key=lambda item: item["id"] or "")
    print(json.dumps({"provider": "openrouter", "models": selected}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
