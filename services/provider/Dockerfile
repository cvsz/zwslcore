FROM cgr.dev/chainguard/python:latest-dev@sha256:53b2fdfc1e01c96b0eb4ac9e3eaec16d702508c07e2b12cc5235fe5c97f3704d AS build

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

FROM cgr.dev/chainguard/python:latest@sha256:a3995e4d233c10dff34ebd5a9f86d60ca041fdc9ca6870482f222baa21e4e4fd

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
