#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.model_catalog.inventory import (
    ModelInventoryError,
    collect_inventory,
    compare_manifests,
    load_manifest,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Capture or compare immutable identities from the local Ollama inventory."
    )
    p.add_argument("--compare", metavar="MANIFEST", help="compare against a prior captured JSON manifest")
    p.add_argument("--fail-on-drift", action="store_true", help="return 1 when a comparison detects identity drift")
    return p


def main(argv: list[str] | None = None) -> int:
    p = parser()
    args = p.parse_args(argv)
    if args.fail_on_drift and not args.compare:
        p.error("--fail-on-drift requires --compare")
    try:
        current = collect_inventory()
        result = compare_manifests(current, load_manifest(args.compare)) if args.compare else current
    except ModelInventoryError as exc:
        print(f"model-manifest: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    if args.fail_on_drift and result["drift_detected"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
