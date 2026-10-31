import unittest

import httpx
from zeaz_provider.config import (
    ModelRoute,
    ProviderConfig,
    RouteTarget,
    Settings,
)
from zeaz_provider.errors import ErrorKind, ProviderError
from zeaz_provider.router import ProviderRouter


def make_provider(name, cost_class):
    return ProviderConfig(
        name=name,
        api="openai",
        base_url=f"https://{name}.example/v1",
        cost_class=cost_class,
        max_attempts=1,
        retry_base_seconds=0,
        retry_max_seconds=0,
    )


def make_settings(route):
    providers = {
        "ollama": make_provider("ollama", "FREE_LOCAL"),
        "remote": make_provider("remote", "FREE_REMOTE"),
    }
    return Settings(
        providers=providers,
        models={route.alias: route},
        client_key_hashes=frozenset(),
        default_model=route.alias,
        cost_policy="PERMIT_PAID",
    )


class LocalOnlyRouterTests(unittest.IsolatedAsyncioTestCase):
    async def test_route_removes_remote_fallback(self):
        configured = ModelRoute(
            alias="claude",
            primary=RouteTarget("ollama", "qwen2.5-coder:3b"),
            fallbacks=(RouteTarget("remote", "remote-model"),),
            cost_policy="LOCAL_ONLY",
        )
        async with httpx.AsyncClient() as client:
            router = ProviderRouter(make_settings(configured), client)
            route = router.route("claude")

        self.assertEqual(route.primary.provider, "ollama")
        self.assertEqual(route.fallbacks, ())
        self.assertEqual(route.cost_policy, "LOCAL_ONLY")

    async def test_local_only_rejects_remote_primary_without_local_target(self):
        configured = ModelRoute(
            alias="claude",
            primary=RouteTarget("remote", "remote-model"),
            cost_policy="LOCAL_ONLY",
        )
        async with httpx.AsyncClient() as client:
            router = ProviderRouter(make_settings(configured), client)
            with self.assertRaises(ProviderError) as raised:
                router.route("claude")

        self.assertEqual(raised.exception.status_code, 410)
        self.assertFalse(raised.exception.fallback_allowed)

    async def test_execute_never_falls_back_to_remote(self):
        configured = ModelRoute(
            alias="claude",
            primary=RouteTarget("ollama", "qwen2.5-coder:3b"),
            fallbacks=(RouteTarget("remote", "remote-model"),),
            cost_policy="LOCAL_ONLY",
        )
        calls = []

        async with httpx.AsyncClient() as client:
            router = ProviderRouter(make_settings(configured), client)
            route = router.route("claude")

            async def operation(provider_client, model):
                calls.append(provider_client.config.name)
                raise ProviderError(
                    "temporary local failure",
                    kind=ErrorKind.NETWORK,
                    fallback_allowed=True,
                )

            with self.assertRaises(ProviderError):
                await router.execute(route, operation)

        self.assertEqual(calls, ["ollama"])

    async def test_stream_never_falls_back_to_remote(self):
        configured = ModelRoute(
            alias="claude",
            primary=RouteTarget("ollama", "qwen2.5-coder:3b"),
            fallbacks=(RouteTarget("remote", "remote-model"),),
            cost_policy="LOCAL_ONLY",
        )
        calls = []

        async with httpx.AsyncClient() as client:
            router = ProviderRouter(make_settings(configured), client)
            route = router.route("claude")

            async def operation(provider_client, model):
                calls.append(provider_client.config.name)
                raise ProviderError(
                    "temporary local failure",
                    kind=ErrorKind.NETWORK,
                    fallback_allowed=True,
                )
                yield b""

            with self.assertRaises(ProviderError):
                async for _ in router.stream(route, operation):
                    pass

        self.assertEqual(calls, ["ollama"])

    async def test_legacy_model_route_without_policy_remains_supported(self):
        route = ModelRoute(
            alias="legacy",
            primary=RouteTarget("ollama", "model"),
        )
        self.assertIsNone(route.cost_policy)


if __name__ == "__main__":
    unittest.main()
