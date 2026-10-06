from __future__ import annotations

import time
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any, TypeVar

import httpx

from .capabilities import CapabilityRegistry, ModelLifecycle
from .config import ModelRoute, Settings
from .cost import cost_allowed, cost_rank, parse_cost_class, parse_cost_policy
from .observability import Observability
from .providers import ProviderClient, ProviderError

T = TypeVar("T")


class ProviderRouter:
    def __init__(
        self,
        settings: Settings,
        client: httpx.AsyncClient,
        observability: Observability | None = None,
    ):
        self.settings = settings
        self.observability = observability
        self.clients = {
            name: ProviderClient(
                config,
                client,
                max_response_bytes=settings.max_response_bytes,
                on_retry=(
                    lambda error, provider=name: observability.record_provider_retry(
                        provider=provider,
                        error_class=error.kind.value,
                    )
                    if observability is not None
                    else None
                ),
            )
            for name, config in settings.providers.items()
        }
        self.capabilities = CapabilityRegistry(settings)
        if observability is not None:
            for name, provider_client in self.clients.items():
                observability.record_circuit_breaker_state(
                    provider=name,
                    state=provider_client.resilience.breaker.state,
                )

    def route(self, alias: str | None) -> ModelRoute:
        name = alias or self.settings.default_model
        try:
            configured = self.settings.models[name]
        except KeyError as exc:
            raise ProviderError(f"Unknown model: {name}", 404) from exc
        candidates = (configured.primary, *configured.fallbacks)
        policy = parse_cost_policy(self.settings.cost_policy)
        available = [
            target
            for target in candidates
            if (
                cost_allowed(parse_cost_class(self.settings.providers[target.provider].cost_class), policy)
                and (
                    (record := self.capabilities.get(target.provider, target.model)) is None
                    or record.lifecycle != ModelLifecycle.RETIRED
                )
            )
        ]
        if policy.value == "PREFER_ZERO_COST":
            available.sort(
                key=lambda target: cost_rank(
                    parse_cost_class(self.settings.providers[target.provider].cost_class)
                )
            )
        if not available:
            raise ProviderError(
                f"No configured targets for {name} are permitted and active under cost policy {policy.value}",
                410,
                fallback_allowed=False,
                circuit_failure=False,
            )
        return ModelRoute(
            alias=configured.alias,
            primary=available[0],
            fallbacks=tuple(available[1:]),
        )

    async def execute(
        self,
        route: ModelRoute,
        operation: Callable[[ProviderClient, str], Awaitable[T]],
    ) -> T:
        candidates = (route.primary, *route.fallbacks)
        errors: list[str] = []
        for index, target in enumerate(candidates):
            client = self.clients.get(target.provider)
            if not client:
                errors.append(f"{target.provider}: not configured")
                continue
            if index and self.observability is not None:
                self.observability.record_provider_fallback(
                    provider=target.provider,
                    model=target.model,
                )
            started = time.monotonic()
            try:
                result = await operation(client, target.model)
            except ProviderError as exc:
                self._record_attempt(
                    target.provider,
                    target.model,
                    started,
                    error_class=exc.kind.value,
                )
                errors.append(f"{target.provider}/{target.model}: {exc}")
                if not exc.fallback_allowed:
                    raise
            except Exception:
                self._record_attempt(
                    target.provider,
                    target.model,
                    started,
                    error_class="internal",
                )
                raise
            else:
                self._record_attempt(
                    target.provider,
                    target.model,
                    started,
                    result=result,
                )
                return result
        raise ProviderError("All providers failed: " + "; ".join(errors), 502)

    async def stream(
        self,
        route: ModelRoute,
        operation: Callable[[ProviderClient, str], AsyncIterator[bytes]],
    ) -> AsyncIterator[bytes]:
        errors: list[str] = []
        for index, target in enumerate((route.primary, *route.fallbacks)):
            client = self.clients.get(target.provider)
            if not client:
                errors.append(f"{target.provider}: not configured")
                continue
            if index and self.observability is not None:
                self.observability.record_provider_fallback(
                    provider=target.provider,
                    model=target.model,
                )
            emitted = False
            started = time.monotonic()
            try:
                async for chunk in operation(client, target.model):
                    emitted = True
                    yield chunk
            except ProviderError as exc:
                self._record_attempt(
                    target.provider,
                    target.model,
                    started,
                    error_class=exc.kind.value,
                )
                if emitted or not exc.fallback_allowed:
                    raise
                errors.append(f"{target.provider}/{target.model}: {exc}")
            except Exception:
                self._record_attempt(
                    target.provider,
                    target.model,
                    started,
                    error_class="internal",
                )
                raise
            else:
                self._record_attempt(target.provider, target.model, started)
                return
        raise ProviderError("All streaming providers failed: " + "; ".join(errors), 502)

    def _record_attempt(
        self,
        provider: str,
        model: str,
        started: float,
        *,
        error_class: str | None = None,
        result: Any = None,
    ) -> None:
        if self.observability is None:
            return
        input_tokens, output_tokens = _usage_tokens(result)
        self.observability.record_provider_request(
            provider=provider,
            model=model,
            outcome="error" if error_class is not None else "success",
            duration_seconds=time.monotonic() - started,
            error_class=error_class,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )
        client = self.clients.get(provider)
        if client is not None:
            self.observability.record_circuit_breaker_state(
                provider=provider,
                state=client.resilience.breaker.state,
            )

    def model_list(self) -> list[dict[str, Any]]:
        public_models: list[dict[str, Any]] = []
        for route in self.settings.models.values():
            try:
                self.route(route.alias)
            except ProviderError as exc:
                if exc.status_code == 410:
                    continue
                raise
            public_models.append({
                "id": route.alias,
                "object": "model",
                "owned_by": "zeaz",
            })
        return public_models


def _usage_tokens(result: Any) -> tuple[int | None, int | None]:
    if not isinstance(result, dict) or not isinstance(result.get("usage"), dict):
        return None, None
    usage = result["usage"]
    input_tokens = _first_nonnegative_int(usage, ("prompt_tokens", "input_tokens"))
    output_tokens = _first_nonnegative_int(usage, ("completion_tokens", "output_tokens"))
    return input_tokens, output_tokens


def _first_nonnegative_int(value: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for key in keys:
        count = value.get(key)
        if type(count) is int and count >= 0:
            return count
    return None
