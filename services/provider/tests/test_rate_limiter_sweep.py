from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace

from starlette.requests import Request
from starlette.responses import JSONResponse

from zeaz_provider.limits import RequestConcurrencyLimiter
from zeaz_provider.main import request_boundary
from zeaz_provider.observability import Observability
from zeaz_provider.security import (
    InMemoryRateLimiter,
    TrustedProxyPolicy,
    allow_rate_limit_buckets,
    request_rate_buckets,
)


class InMemoryRateLimiterSweepTests(unittest.TestCase):
    def test_expired_buckets_are_released(self):
        async def scenario() -> tuple[int, bool, bool]:
            now = [0.0]
            limiter = InMemoryRateLimiter(2, 60.0, clock=lambda: now[0], max_buckets=32)
            for index in range(1000):
                now[0] += 0.001
                await limiter.allow(f"rotating-credential-{index}")
            self.assertEqual(len(limiter._events), 32)
            now[0] += 3600.0
            allowed, _ = await limiter.allow("fresh-client")
            return len(limiter._events), allowed, "fresh-client" in limiter._events

        retained, allowed, present = asyncio.run(scenario())
        self.assertEqual(retained, 1)
        self.assertTrue(allowed)
        self.assertTrue(present)

    def test_rotating_credentials_still_share_the_peer_limit(self):
        async def scenario() -> tuple[bool, bool, bool]:
            limiter = InMemoryRateLimiter(2, 60.0)
            first = request_rate_buckets("Bearer first", None, "192.0.2.10")
            second = request_rate_buckets("Bearer second", None, "192.0.2.10")
            return (
                (await allow_rate_limit_buckets(limiter, first))[0],
                (await allow_rate_limit_buckets(limiter, second))[0],
                (await allow_rate_limit_buckets(
                    limiter,
                    request_rate_buckets("Bearer third", None, "192.0.2.10"),
                ))[0],
            )

        self.assertEqual(asyncio.run(scenario()), (True, True, False))

    def test_http_boundary_limits_rotating_credentials_by_resolved_peer(self):
        async def scenario() -> tuple[list[int], int]:
            app = SimpleNamespace(
                state=SimpleNamespace(
                    observability=Observability(),
                    concurrency_limiter=RequestConcurrencyLimiter(8),
                    trusted_proxy_policy=TrustedProxyPolicy.from_cidrs(()),
                    rate_limiter=InMemoryRateLimiter(2),
                    settings=SimpleNamespace(max_response_bytes=1024),
                )
            )
            reached = 0

            async def call_next(_request):
                nonlocal reached
                reached += 1
                return JSONResponse({"ok": True})

            statuses = []
            for token in ("first-token", "second-token", "third-token"):
                scope = {
                    "type": "http",
                    "asgi": {"version": "3.0", "spec_version": "2.3"},
                    "http_version": "1.1",
                    "method": "GET",
                    "scheme": "http",
                    "path": "/health/live",
                    "raw_path": b"/health/live",
                    "query_string": b"",
                    "root_path": "",
                    "headers": [(b"authorization", f"Bearer {token}".encode())],
                    "client": ("192.0.2.10", 50000),
                    "server": ("127.0.0.1", 8080),
                    "app": app,
                }
                response = await request_boundary(Request(scope), call_next)
                statuses.append(response.status_code)
            return statuses, reached

        self.assertEqual(asyncio.run(scenario()), ([200, 200, 429], 2))

    def test_bucket_table_stays_bounded_when_credentials_rotate(self):
        async def scenario() -> tuple[int, bool]:
            now = [0.0]
            limiter = InMemoryRateLimiter(1000, 60.0, clock=lambda: now[0], max_buckets=16)
            for index in range(100):
                await limiter.allow(f"credential-{index}")
            return len(limiter._events), (await limiter.allow("overflow"))[0]

        self.assertEqual(asyncio.run(scenario()), (16, False))

    def test_limits_still_enforced_inside_the_window(self):
        async def scenario() -> list[bool]:
            now = [0.0]
            limiter = InMemoryRateLimiter(2, 60.0, clock=lambda: now[0])
            results = []
            for _ in range(3):
                now[0] += 1.0
                results.append((await limiter.allow("client"))[0])
            return results

        self.assertEqual(asyncio.run(scenario()), [True, True, False])

    def test_active_bucket_survives_a_sweep(self):
        async def scenario() -> bool:
            now = [0.0]
            limiter = InMemoryRateLimiter(1, 60.0, clock=lambda: now[0])
            await limiter.allow("busy")
            now[0] += 61.0  # first sweep point; "busy" event is now expired too
            await limiter.allow("busy")
            now[0] += 1.0
            return (await limiter.allow("busy"))[0]

        self.assertFalse(asyncio.run(scenario()))


if __name__ == "__main__":
    unittest.main()
