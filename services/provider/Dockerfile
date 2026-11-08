FROM cgr.dev/chainguard/python:latest-dev@sha256:898360ca56a2a65c3facdd36a4e6151133a580aa367195261554e82948921ff1 AS build

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

FROM cgr.dev/chainguard/python:latest@sha256:1a00964779bf570a8cb2ea4fa086614af19c35069029785c08fcec0c50b66ac0

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
