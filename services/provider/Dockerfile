FROM cgr.dev/chainguard/python:latest-dev@sha256:ec39ad2cb02f38c50386430050ab993439336154cfd8e9d42e815e316a91a9d1 AS build

USER 0:0
WORKDIR /app
ENV VIRTUAL_ENV=/opt/venv
RUN python -m venv "$VIRTUAL_ENV"
RUN python -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' > /opt/python-build-version
ENV PATH="/opt/venv/bin:$PATH"

COPY pyproject.toml requirements.lock ./
COPY zeaz_provider ./zeaz_provider
RUN pip install --no-cache-dir --require-hashes --only-binary=:all: -r requirements.lock \
    && pip install --no-cache-dir --no-deps --no-build-isolation .

COPY config ./config

FROM cgr.dev/chainguard/python:latest@sha256:29ba28eeb37d00fba93ad2667fdae3ba6aa5b823c587be27ff481e20d1e95e2a

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ZEAZ_CONFIG=/app/config/providers.yaml \
    ZEAZ_HOST=0.0.0.0 \
    ZEAZ_PORT=8080 \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app
COPY --from=build /opt/venv /opt/venv
COPY --from=build /opt/python-build-version /opt/python-build-version
RUN ["/usr/bin/python", "-c", "from pathlib import Path; import sys; expected=Path('/opt/python-build-version').read_text().strip(); actual=f'{sys.version_info.major}.{sys.version_info.minor}'; assert actual == expected, f'Python minor mismatch: builder={expected}, runtime={actual}'"]
RUN ["/opt/venv/bin/python", "-c", "import zeaz_provider; from zeaz_provider.main import app; assert app.title == 'zwslcore Provider'"]
COPY --from=build /app/config ./config

USER 65532:65532

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["/opt/venv/bin/python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=3)"]

ENTRYPOINT ["zwslcore-provider"]
