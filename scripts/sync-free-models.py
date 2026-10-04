#!/usr/bin/env python3
"""Discover current OpenRouter zero-price chat models using zwslcore's in-repo catalog."""

from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.model_catalog.catalog import select_free_chat_models  # noqa: E402

URL = "https://openrouter.ai/api/v1/models"


def main() -> int:
    key = os.getenv("OPENROUTER_API_KEY", "").strip()
    headers = {"User-Agent": "zwslcore-free-model-sync/1"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    request = urllib.request.Request(URL, headers=headers)
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = json.load(response)

    selected = select_free_chat_models(payload.get("data", []))
    output = [
        {
            "id": item["id"],
            "name": item.get("name"),
            "context_length": item.get("context_length"),
        }
        for item in selected
    ]
    print(json.dumps({"provider": "openrouter", "models": output}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
