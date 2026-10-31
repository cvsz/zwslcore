FROM cgr.dev/chainguard/python:latest-dev@sha256:01280a9ffd0c9c427d3127540203af6707ebf35cdb0481182aef303c03db239c AS build

USER 0:0
WORKDIR /app
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml requirements.lock ./
COPY zeaz_provider ./zeaz_provider
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: --no-binary pyyaml -r requirements.lock \
    && pip install --no-cache-dir --no-deps --no-build-isolation .

COPY config ./config

FROM cgr.dev/chainguard/python:latest@sha256:0f47468835f6c443553040eebccc20b0762d9608251be085786007e2e93b2285

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ZEAZ_CONFIG=/app/config/providers.yaml \
    ZEAZ_HOST=0.0.0.0 \
    ZEAZ_PORT=8080 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --from=build /app/config ./config

USER 65532:65532

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/opt/venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=3)"]

ENTRYPOINT ["zwslcore-provider"]
