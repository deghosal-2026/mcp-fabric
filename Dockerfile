FROM python:3.12-slim-bookworm AS builder

RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl && rm -rf /var/lib/apt/lists/*

RUN pip install poetry

WORKDIR /app
COPY pyproject.toml poetry.lock ./
COPY api/ api/

RUN poetry install --only main --no-root && poetry build

FROM python:3.12-slim-bookworm AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends libpq5 curl && rm -rf /var/lib/apt/lists/*

RUN groupadd -r fabric && useradd -r -g fabric -d /app -s /bin/false fabric

WORKDIR /app

COPY --from=builder /app .
COPY --from=builder /root/.cache/pypoetry /root/.cache/pypoetry

RUN pip install poetry && poetry install --only main --no-root && pip install dist/*.whl && rm -rf /root/.cache

RUN chown -R fabric:fabric /app

USER fabric

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

ENTRYPOINT ["uvicorn", "api.main:app"]
CMD ["--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
