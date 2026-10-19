from __future__ import annotations

import asyncio
import unittest

from zeaz_provider.security import InMemoryRateLimiter


class InMemoryRateLimiterSweepTests(unittest.TestCase):
    def test_expired_buckets_are_released(self):
        async def scenario() -> tuple[int, bool, bool]:
            now = [0.0]
            limiter = InMemoryRateLimiter(2, 60.0, clock=lambda: now[0])
            for index in range(1000):
                now[0] += 0.001
                await limiter.allow(f"rotating-credential-{index}")
            self.assertGreaterEqual(len(limiter._events), 1000)
            now[0] += 3600.0
            allowed, _ = await limiter.allow("fresh-client")
            return len(limiter._events), allowed, "fresh-client" in limiter._events

        retained, allowed, present = asyncio.run(scenario())
        self.assertEqual(retained, 1)
        self.assertTrue(allowed)
        self.assertTrue(present)

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
