#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from services.engineering.hardware import detect_hardware  # noqa: E402
from services.model_catalog.models_dev import (  # noqa: E402
    DEFAULT_CACHE,
    DEFAULT_URL,
    ModelsDevError,
    get_catalog,
    lookup_model,
)


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Sync and inspect models.dev metadata.")
    p.add_argument("--cache", default=str(DEFAULT_CACHE))
    p.add_argument("--url", default=DEFAULT_URL)
    sub = p.add_subparsers(dest="command", required=True)

    sync = sub.add_parser("sync")
    sync.add_argument("--max-age", type=int, default=24 * 60 * 60)
    sync.add_argument("--no-stale", action="store_true")

    stats = sub.add_parser("stats")
    stats.add_argument("--refresh", action="store_true")
    stats.add_argument("--max-age", type=int, default=24 * 60 * 60)

    lookup = sub.add_parser("lookup")
    lookup.add_argument("model_id")
    lookup.add_argument("--refresh", action="store_true")
    lookup.add_argument("--max-age", type=int, default=24 * 60 * 60)

    providers = sub.add_parser("providers")
    providers.add_argument("--refresh", action="store_true")
    providers.add_argument("--max-age", type=int, default=24 * 60 * 60)

    rank = sub.add_parser("rank")
    rank.add_argument("--refresh", action="store_true")
    rank.add_argument("--max-age", type=int, default=24 * 60 * 60)
    rank.add_argument("--limit", type=int, default=20)
    rank.add_argument("--include-ineligible", action="store_true")
    _selection_args(rank)

    select = sub.add_parser("select")
    select.add_argument("--refresh", action="store_true")
    select.add_argument("--max-age", type=int, default=24 * 60 * 60)
    _selection_args(select)
    return p


def load(args):
    return get_catalog(
        cache_path=args.cache,
        refresh=getattr(args, "refresh", args.command == "sync"),
        max_age_seconds=max(0, getattr(args, "max_age", 24 * 60 * 60)),
        allow_stale=not getattr(args, "no_stale", False),
        url=args.url,
    )


def main() -> int:
    args = parser().parse_args()
    try:
        catalog, source = load(args)
    except ModelsDevError as exc:
        print(f"models.dev: {exc}", file=sys.stderr)
        return 1

    if args.command == "sync":
        print(json.dumps({
            "source": source,
            "cache": str(Path(args.cache).expanduser()),
            "stats": catalog["stats"],
        }, indent=2))
        return 0

    if args.command == "stats":
        print(json.dumps({"source": source, **catalog["stats"]}, indent=2))
        return 0

    if args.command == "providers":
        output = [
            {
                "id": provider_id,
                "name": provider.get("name"),
                "api": provider.get("api"),
                "models": len(provider.get("models", {})),
            }
            for provider_id, provider in sorted(catalog["providers"].items())
        ]
        print(json.dumps({"source": source, "providers": output}, indent=2))
        return 0

    if args.command == "lookup":
        result = lookup_model(catalog, args.model_id)
        if result is None:
            print("model not found", file=sys.stderr)
            return 2
        print(json.dumps({"source": source, "id": args.model_id, **result}, indent=2))
        return 0

    if args.command in {"rank", "select"}:
        profile = detect_hardware()
        runtime = profile.recommended_runtime()
        recommended = profile.recommended_models()
        candidates = catalog_candidates(catalog)
        if not args.no_local:
            candidates = local_candidates(
                recommended,
                context_length=int(runtime["context_length"]),
            ) + candidates

        requirements = SelectionRequirements(
            structured_output=args.structured_output,
            tool_call=args.tool_call,
            reasoning=args.reasoning,
            min_context=max(0, args.min_context),
            cost_policy=args.cost_policy,
        )

        if args.command == "rank":
            ranked = rank_models(
                candidates,
                requirements,
                hardware_models=recommended.values(),
                include_ineligible=args.include_ineligible,
            )
            print(json.dumps({
                "source": source,
                "hardware_profile": profile.profile,
                "requirements": {
                    "structured_output": requirements.structured_output,
                    "tool_call": requirements.tool_call,
                    "reasoning": requirements.reasoning,
                    "min_context": requirements.min_context,
                    "cost_policy": requirements.cost_policy,
                },
                "models": [item.as_dict() for item in ranked[:max(1, args.limit)]],
            }, indent=2))
            return 0

        selected = select_model(
            candidates,
            requirements,
            hardware_models=recommended.values(),
        )
        if selected is None:
            print("no eligible model found", file=sys.stderr)
            return 2
        print(json.dumps({
            "source": source,
            "hardware_profile": profile.profile,
            "selected": selected.as_dict(),
        }, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
