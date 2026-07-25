FROM python:3.12-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml README.md ./
COPY api/ api/
COPY policies/ policies/
COPY alembic.ini ./
COPY alembic/ alembic/

RUN pip install --no-cache-dir --upgrade pip --quiet && \
    pip install --no-cache-dir . --quiet

RUN groupadd -r fabric && useradd -r -g fabric -d /app -s /bin/false fabric && \
    chown -R fabric:fabric /app

USER fabric

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
