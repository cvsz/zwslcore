from __future__ import annotations

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest


class Observability:
    def __init__(self, *, otlp_enabled: bool = False):
        self.registry = CollectorRegistry()
        self.requests = Counter(
            "zeaz_http_requests_total",
            "Completed gateway HTTP requests.",
            ("method", "path", "status"),
            registry=self.registry,
        )
        self.duration = Histogram(
            "zeaz_http_request_duration_seconds",
            "Gateway HTTP request duration.",
            ("method", "path"),
            registry=self.registry,
        )
        self.in_flight = Gauge(
            "zeaz_http_requests_in_flight",
            "Gateway HTTP requests currently in flight.",
            registry=self.registry,
        )
        self.provider_requests = Counter(
            "zeaz_provider_requests",
            "Provider model requests by configured provider, model, and outcome.",
            ("provider", "model", "outcome"),
            registry=self.registry,
        )
        self.provider_errors = Counter(
            "zeaz_provider_errors",
            "Provider request failures by bounded error class.",
            ("provider", "model", "error_class"),
            registry=self.registry,
        )
        self.provider_latency = Histogram(
            "zeaz_provider_latency_seconds",
            "Provider model request latency, including local response adaptation.",
            ("provider", "model"),
            buckets=(0.1, 0.5, 1, 5, 15, 30, 60, 120, 300, 600),
            registry=self.registry,
        )
        self.inference_tokens = Counter(
            "zeaz_inference_tokens",
            "Provider-reported inference tokens, when response usage is available.",
            ("provider", "model", "direction"),
            registry=self.registry,
        )
        self.provider_retries = Counter(
            "zeaz_provider_retries",
            "Provider transport retries by bounded error class.",
            ("provider", "error_class"),
            registry=self.registry,
        )
        self.provider_fallbacks = Counter(
            "zeaz_provider_fallbacks",
            "Requests routed to a configured fallback provider.",
            ("provider", "model"),
            registry=self.registry,
        )
        self.circuit_breaker_state = Gauge(
            "zeaz_provider_circuit_breaker_state",
            "Provider circuit state: closed=0, half-open=0.5, open=1.",
            ("provider",),
            registry=self.registry,
        )
        self._meter_provider = None
        self._otel_requests = None
        self._otel_duration = None
        if otlp_enabled:
            self._configure_otlp()

    def _configure_otlp(self) -> None:
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        reader = PeriodicExportingMetricReader(OTLPMetricExporter())
        self._meter_provider = MeterProvider(metric_readers=[reader])
        meter = self._meter_provider.get_meter("zeaz_provider")
        self._otel_requests = meter.create_counter(
            "zeaz.http.requests",
            description="Completed gateway HTTP requests.",
        )
        self._otel_duration = meter.create_histogram(
            "zeaz.http.request.duration",
            unit="s",
            description="Gateway HTTP request duration.",
        )

    def start_request(self) -> None:
        self.in_flight.inc()

    def finish_request(
        self,
        *,
        method: str,
        path: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        duration = max(0.0, duration_seconds)
        status = str(status_code)
        self.in_flight.dec()
        self.requests.labels(method=method, path=path, status=status).inc()
        self.duration.labels(method=method, path=path).observe(duration)
        attributes = {
            "http.request.method": method,
            "http.route": path,
            "http.response.status_code": status_code,
        }
        if self._otel_requests is not None:
            self._otel_requests.add(1, attributes)
        if self._otel_duration is not None:
            self._otel_duration.record(duration, attributes)

    def prometheus(self) -> bytes:
        return generate_latest(self.registry)

    def record_provider_request(
        self,
        *,
        provider: str,
        model: str,
        outcome: str,
        duration_seconds: float,
        error_class: str | None = None,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
    ) -> None:
        self.provider_requests.labels(provider=provider, model=model, outcome=outcome).inc()
        self.provider_latency.labels(provider=provider, model=model).observe(
            max(0.0, duration_seconds)
        )
        if error_class is not None:
            self.provider_errors.labels(
                provider=provider,
                model=model,
                error_class=error_class,
            ).inc()
        if input_tokens is not None:
            self.inference_tokens.labels(
                provider=provider,
                model=model,
                direction="input",
            ).inc(input_tokens)
        if output_tokens is not None:
            self.inference_tokens.labels(
                provider=provider,
                model=model,
                direction="output",
            ).inc(output_tokens)

    def record_provider_retry(self, *, provider: str, error_class: str) -> None:
        self.provider_retries.labels(provider=provider, error_class=error_class).inc()

    def record_provider_fallback(self, *, provider: str, model: str) -> None:
        self.provider_fallbacks.labels(provider=provider, model=model).inc()

    def record_circuit_breaker_state(self, *, provider: str, state: str) -> None:
        value = {"closed": 0.0, "half_open": 0.5, "open": 1.0}.get(state)
        if value is not None:
            self.circuit_breaker_state.labels(provider=provider).set(value)

    def shutdown(self) -> None:
        if self._meter_provider is not None:
            self._meter_provider.shutdown()
