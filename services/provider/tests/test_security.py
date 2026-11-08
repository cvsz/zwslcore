from __future__ import annotations

import hashlib
import unittest
from unittest import mock

from fastapi.testclient import TestClient

from zeaz_provider.config import (
    CostClass,
    CostPolicy,
    ModelRoute,
    ProviderConfig,
    RouteTarget,
    Settings,
)
from zeaz_provider.cost import cost_allowed
from zeaz_provider.errors import ErrorKind, ProviderError
from zeaz_provider.main import app
from zeaz_provider.router import ProviderRouter
from zeaz_provider.security import client_key_digest, verify_client_key

TEST_CLIENT_KEY = "test-client-key-12345-not-real"
TEST_CLIENT_KEY_HASH = client_key_digest(TEST_CLIENT_KEY)


def _provider(name: str, *, cost_class: str = CostClass.FREE_LOCAL.value) -> ProviderConfig:
    return ProviderConfig(
        name=name,
        api="openai",
        base_url=f"https://{name}.example/v1",
        cost_class=cost_class,
        max_attempts=1,
        retry_base_seconds=0,
        retry_max_seconds=0,
    )


def _settings(providers, models, client_key=TEST_CLIENT_KEY) -> Settings:
    return Settings(
        providers={provider.name: provider for provider in providers},
        models=models,
        client_key_hashes=frozenset({client_key_digest(client_key)}),
        default_model=next(iter(models)),
        cost_policy=CostPolicy.ZERO_COST_ONLY.value,
    )


class ClientKeyVerificationTests(unittest.TestCase):
    """verify_client_key must use constant-time comparison and fail closed."""

    def test_rejects_empty_candidate(self):
        self.assertFalse(verify_client_key("", frozenset({TEST_CLIENT_KEY_HASH})))

    def test_rejects_when_no_credentials_configured(self):
        self.assertFalse(verify_client_key(TEST_CLIENT_KEY, frozenset()))

    def test_rejects_wrong_key(self):
        self.assertFalse(verify_client_key("wrong-key", frozenset({TEST_CLIENT_KEY_HASH})))

    def test_accepts_configured_key(self):
        self.assertTrue(verify_client_key(TEST_CLIENT_KEY, frozenset({TEST_CLIENT_KEY_HASH})))

    def test_client_key_digest_is_deterministic(self):
        self.assertEqual(
            client_key_digest(TEST_CLIENT_KEY), hashlib.sha256(TEST_CLIENT_KEY.encode()).digest()
        )


class CostPolicyTests(unittest.TestCase):
    """ZERO_COST_ONLY must permit only free classes; paid classes remain blocked."""

    def test_zero_cost_only_allows_free_local_and_free_remote(self):
        self.assertTrue(cost_allowed(CostClass.FREE_LOCAL, CostPolicy.ZERO_COST_ONLY))
        self.assertTrue(cost_allowed(CostClass.FREE_REMOTE, CostPolicy.ZERO_COST_ONLY))

    def test_zero_cost_only_blocks_paid_and_customer_key(self):
        self.assertFalse(cost_allowed(CostClass.PAID_PLATFORM, CostPolicy.ZERO_COST_ONLY))
        self.assertFalse(cost_allowed(CostClass.CUSTOMER_KEY, CostPolicy.ZERO_COST_ONLY))
        self.assertFalse(cost_allowed(CostClass.UNKNOWN, CostPolicy.ZERO_COST_ONLY))

    def test_permit_paid_allows_every_class(self):
        self.assertTrue(cost_allowed(CostClass.PAID_PLATFORM, CostPolicy.PERMIT_PAID))
        self.assertTrue(cost_allowed(CostClass.CUSTOMER_KEY, CostPolicy.PERMIT_PAID))


class RouterRouteTests(unittest.TestCase):
    """Model routing must reject unknown models and cost-blocked targets."""

    def test_unknown_model_raises_404(self):
        ollama = _provider("ollama")
        settings = _settings(
            [ollama],
            {"default-model": ModelRoute("default-model", RouteTarget("ollama", "qwen3:8b"))},
        )
        router = ProviderRouter(settings, None)
        with self.assertRaises(ProviderError) as ctx:
            router.route("does-not-exist")
        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.kind, ErrorKind.NOT_FOUND)

    def test_local_route_resolves_to_configured_provider(self):
        ollama = _provider("ollama")
        settings = _settings(
            [ollama],
            {"zeaz-free": ModelRoute("zeaz-free", RouteTarget("ollama", "qwen3:8b"))},
        )
        router = ProviderRouter(settings, None)
        route = router.route("zeaz-free")
        self.assertEqual(route.primary.provider, "ollama")
        self.assertEqual(route.primary.model, "qwen3:8b")

    def test_cost_blocked_provider_raises_410(self):
        paid = _provider("paid-provider", cost_class=CostClass.PAID_PLATFORM.value)
        settings = _settings(
            [paid],
            {"zeaz-paid": ModelRoute("zeaz-paid", RouteTarget("paid-provider", "gpt-5"))},
        )
        router = ProviderRouter(settings, None)
        with self.assertRaises(ProviderError) as ctx:
            router.route("zeaz-paid")
        self.assertEqual(ctx.exception.status_code, 410)
        self.assertFalse(ctx.exception.fallback_allowed)


class _PatchedClient:
    """Context manager that keeps load_settings patched across lifespan + request."""

    def __init__(self, test_settings):
        self.test_settings = test_settings

    def __enter__(self):
        self._patch = mock.patch(
            "zeaz_provider.main.load_settings", return_value=self.test_settings
        )
        self._patch.start()
        self.client = TestClient(app)
        self.client.__enter__()
        return self.client

    def __exit__(self, exc_type, exc, tb):
        try:
            self.client.__exit__(exc_type, exc, tb)
        finally:
            self._patch.stop()


class EndpointAuthenticationTests(unittest.TestCase):
    """All inference/model routes must require valid credentials."""

    def _models(self):
        return {
            "zeaz-free": ModelRoute("zeaz-free", RouteTarget("ollama", "qwen3:8b")),
            "zeaz-cloud": ModelRoute("zeaz-cloud", RouteTarget("openrouter", "openrouter/free")),
        }

    def _providers(self):
        return [
            _provider("ollama"),
            _provider("openrouter", cost_class=CostClass.FREE_REMOTE.value),
        ]

    def test_models_listing_rejected_without_credentials(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            response = client.get("/v1/models")
        self.assertEqual(response.status_code, 401)

    def test_models_listing_rejected_with_wrong_bearer(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            response = client.get(
                "/v1/models", headers={"Authorization": "Bearer wrong-key"}
            )
        self.assertEqual(response.status_code, 401)

    def test_models_listing_rejected_with_wrong_x_api_key(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            response = client.get("/v1/models", headers={"X-API-Key": "wrong-key"})
        self.assertEqual(response.status_code, 401)

    def test_models_listing_rejected_with_malformed_authorization_header(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            response = client.get(
                "/v1/models", headers={"Authorization": "Basic dXNlcjpwYXNz"}
            )
        self.assertEqual(response.status_code, 401)

    def test_models_listing_rejected_with_empty_authorization_header(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            response = client.get("/v1/models", headers={"Authorization": ""})
        self.assertEqual(response.status_code, 401)

    def test_models_listing_accepted_with_valid_bearer(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            response = client.get(
                "/v1/models", headers={"Authorization": f"Bearer {TEST_CLIENT_KEY}"}
            )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["object"], "list")
        ids = {item["id"] for item in data["data"]}
        self.assertIn("zeaz-free", ids)
        self.assertIn("zeaz-cloud", ids)

    def test_models_listing_accepted_with_valid_x_api_key(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            response = client.get("/v1/models", headers={"X-API-Key": TEST_CLIENT_KEY})
        self.assertEqual(response.status_code, 200)

    def test_health_endpoints_remain_unauthenticated(self):
        test_settings = _settings(self._providers(), self._models())
        with _PatchedClient(test_settings) as client:
            live = client.get("/health/live")
            ready = client.get("/health/ready")
        self.assertEqual(live.status_code, 200)
        self.assertEqual(ready.status_code, 200)


if __name__ == "__main__":
    unittest.main()
