FROM python:3.14.7-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ZEAZ_CONFIG=/app/config/providers.yaml \
    ZEAZ_HOST=0.0.0.0 \
    ZEAZ_PORT=8080

WORKDIR /app

RUN groupadd --gid 10001 zwslcore \
    && useradd --uid 10001 --gid zwslcore --shell /usr/sbin/nologin --no-create-home zwslcore

COPY pyproject.toml ./
COPY zeaz_provider ./zeaz_provider
RUN pip install --no-cache-dir .

COPY config ./config

USER 10001:10001

EXPOSE 8080

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
  CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/health/live', timeout=3)"]

ENTRYPOINT ["zwslcore-provider"]
