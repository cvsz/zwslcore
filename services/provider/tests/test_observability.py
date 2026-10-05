from __future__ import annotations

import unittest

import httpx

from zeaz_provider.config import ModelRoute, ProviderConfig, RouteTarget, Settings
from zeaz_provider.errors import ErrorKind, ProviderError
from zeaz_provider.observability import Observability
from zeaz_provider.router import ProviderRouter


def _provider(name: str, *, max_attempts: int = 2) -> ProviderConfig:
    return ProviderConfig(
        name=name,
        api="openai",
        base_url="https://provider.example/v1",
        max_attempts=max_attempts,
        retry_base_seconds=0,
        retry_max_seconds=0,
    )


def _settings(*providers: ProviderConfig) -> Settings:
    return Settings(
        providers={provider.name: provider for provider in providers},
        models={},
        client_key_hashes=frozenset(),
        default_model="example-model",
    )


class ProviderObservabilityTests(unittest.IsolatedAsyncioTestCase):
    async def test_records_provider_failure_fallback_latency_and_usage(self):
        metrics = Observability()
        async with httpx.AsyncClient(transport=httpx.MockTransport(lambda _: None)) as client:
            router = ProviderRouter(
                _settings(_provider("primary"), _provider("backup")),
                client,
                metrics,
            )
            route = ModelRoute(
                alias="example-model",
                primary=RouteTarget("primary", "model-a"),
                fallbacks=(RouteTarget("backup", "model-b"),),
            )

            async def operation(provider_client, model):
                if provider_client.config.name == "primary":
                    raise ProviderError(
                        "temporary failure",
                        kind=ErrorKind.NETWORK,
                        fallback_allowed=True,
                    )
                return {
                    "model": model,
                    "usage": {"prompt_tokens": 7, "completion_tokens": 4},
                }

            result = await router.execute(route, operation)

        self.assertEqual(result["model"], "model-b")
        exposition = metrics.prometheus().decode()
        self.assertIn(
            'zeaz_provider_requests_total{model="model-a",outcome="error",provider="primary"} 1.0',
            exposition,
        )
        self.assertIn(
            'zeaz_provider_errors_total{error_class="network",model="model-a",provider="primary"} 1.0',
            exposition,
        )
        self.assertIn(
            'zeaz_provider_fallbacks_total{model="model-b",provider="backup"} 1.0',
            exposition,
        )
        self.assertIn(
            'zeaz_inference_tokens_total{direction="input",model="model-b",provider="backup"} 7.0',
            exposition,
        )
        self.assertIn("zeaz_provider_latency_seconds_count", exposition)
        self.assertIn('zeaz_provider_circuit_breaker_state{provider="primary"} 0.0', exposition)

    async def test_records_internal_transport_retry(self):
        metrics = Observability()
        attempts = 0

        def respond(request: httpx.Request) -> httpx.Response:
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                return httpx.Response(503, json={"error": "retry"}, request=request)
            return httpx.Response(
                200,
                json={"choices": [], "usage": {"prompt_tokens": 2, "completion_tokens": 3}},
                request=request,
            )

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            router = ProviderRouter(_settings(_provider("primary")), client, metrics)
            route = ModelRoute(
                alias="example-model",
                primary=RouteTarget("primary", "model-a"),
            )
            result = await router.execute(
                route,
                lambda provider_client, model: provider_client.chat({"model": model}),
            )

        self.assertEqual(attempts, 2)
        self.assertEqual(result["usage"]["completion_tokens"], 3)
        exposition = metrics.prometheus().decode()
        self.assertIn(
            'zeaz_provider_retries_total{error_class="upstream",provider="primary"} 1.0',
            exposition,
        )
        self.assertIn(
            'zeaz_provider_requests_total{model="model-a",outcome="success",provider="primary"} 1.0',
            exposition,
        )


if __name__ == "__main__":
    unittest.main()
