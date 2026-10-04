#!/usr/bin/env python3
from __future__ import annotations

import argparse
import dataclasses
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
from services.model_catalog.selector import (  # noqa: E402
    ModelRequirements,
    local_alias_candidates,
    models_dev_candidates,
    rank_models,
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

    rec = sub.add_parser("recommend")
    rec.add_argument("--refresh", action="store_true")
    rec.add_argument("--max-age", type=int, default=24 * 60 * 60)
    rec.add_argument("--structured-output", action="store_true")
    rec.add_argument("--tool-call", action="store_true")
    rec.add_argument("--reasoning", action="store_true")
    rec.add_argument("--min-context", type=int, default=0)
    rec.add_argument("--permit-paid", action="store_true")
    rec.add_argument("--include-remote", action="store_true")
    rec.add_argument("--top", type=int, default=10)
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

    if args.command == "recommend":
        env = {}
        env_path = ROOT / ".env"
        if env_path.exists():
            for raw in env_path.read_text(encoding="utf-8").splitlines():
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                env[key] = value

        profile = detect_hardware()
        candidates = local_alias_candidates(
            env,
            hardware_profile=profile.profile,
            ram_available_gb=profile.ram_available_gb,
        )
        if args.include_remote:
            cloud_enabled = env.get("FREE_CLOUD_FALLBACK_ENABLED", "false").lower() == "true"
            candidates.extend(
                models_dev_candidates(
                    catalog,
                    configured_providers={"openrouter", "gemini", "groq"},
                    enabled_providers={"openrouter", "gemini", "groq"} if cloud_enabled else set(),
                    cost_classes={
                        "openrouter": "FREE_REMOTE",
                        "gemini": "FREE_REMOTE",
                        "groq": "FREE_REMOTE",
                    },
                )
            )

        requirements = ModelRequirements(
            structured_output=args.structured_output,
            tool_call=args.tool_call,
            reasoning=args.reasoning,
            min_context=max(0, args.min_context),
            prefer_local=True,
            zero_cost_only=not args.permit_paid,
        )
        ranked = rank_models(candidates, requirements)[: max(1, args.top)]
        print(json.dumps({
            "source": source,
            "hardware": {
                "profile": profile.profile,
                "ram_available_gb": profile.ram_available_gb,
                "accelerator_backend": profile.accelerator_backend,
            },
            "requirements": dataclasses.asdict(requirements),
            "ranked": [
                {
                    "id": item.candidate.id,
                    "alias": item.candidate.alias,
                    "provider": item.candidate.provider,
                    "source": item.candidate.source,
                    "score": item.score,
                    "eligible": item.eligible,
                    "reasons": list(item.reasons),
                    "blockers": list(item.blockers),
                }
                for item in ranked
            ],
        }, indent=2))
        return 0

    if args.command == "lookup":
        result = lookup_model(catalog, args.model_id)
        if result is None:
            print("model not found", file=sys.stderr)
            return 2
        print(json.dumps({"source": source, "id": args.model_id, **result}, indent=2))
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())
