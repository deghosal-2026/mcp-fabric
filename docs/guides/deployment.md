# Deployment Guide

Deploying MCP Fabric to production.

## Docker Compose Deployment (Single Node)

The recommended production deployment uses Docker Compose with the provided `docker-compose.yml`.

### Prerequisites

- Docker 24+ with Docker Compose v2
- At least 2 GB RAM allocated to Docker
- Ports 8000 (API), 3000 (UI), 5432 (PostgreSQL), 6379 (Redis) available

### Production Configuration

Create a `docker-compose.override.yml` or use environment files:

```bash
cp .env.example .env
# Edit .env with production values
```

### Deploy

```bash
# Pull images and start
docker compose up -d

# Verify
curl http://localhost:8000/health
curl http://localhost:8000/health/ready
```

### Database Migrations

```bash
# Run migrations against the production database
docker compose exec api alembic upgrade head
```

### Scaling Workers

```bash
# Increase Celery worker concurrency
docker compose exec worker celery -A api.tasks worker -l info --concurrency=8
```

## Environment Variables Reference

See `docs/guides/configuration.md` for the complete reference.

### Required in Production

| Variable | Required | Default | Production Value |
|----------|----------|---------|------------------|
| `DATABASE_URL` | Yes | `sqlite+aiosqlite:///fabric.db` | `postgresql+asyncpg://user:pass@host:5432/fabric` |
| `SECRET_KEY` | Yes | `dev-secret-change-me` | `openssl rand -hex 32` output |
| `REDIS_URL` | No | `redis://localhost:6379/0` | `redis://:password@redis-cluster:6379/0` |
| `CORS_ORIGINS` | Yes | `["http://localhost:3000"]` | `["https://fabric.example.com"]` |
| `ENVIRONMENT` | No | `development` | `production` |
| `LOG_LEVEL` | No | `INFO` | `WARNING` |

### Secret Key Generation

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

## Health Checks and Readiness Probes

The API exposes three health check endpoints:

### `/health` — Detailed Health

Returns the status of all core dependencies (database, Redis, OPA).

```json
{
  "status": "healthy",
  "version": "0.4.0",
  "checks": {
    "database": "connected",
    "redis": "connected",
    "opa": "connected"
  }
}
```

### `/health/ready` — Readiness Probe

Returns 503 if the database is unreachable or the service is shutting down.

```json
{"status": "ready"}
```

### `/health/live` — Liveness Probe

Returns 200 immediately with no dependency checks.

```json
{"status": "alive"}
```

### Docker HEALTHCHECK

The Dockerfile includes a built-in health check:

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health/ready || exit 1
```

### Kubernetes Probes

```yaml
livenessProbe:
  httpGet:
    path: /health/live
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 30

readinessProbe:
  httpGet:
    path: /health/ready
    port: 8000
  initialDelaySeconds: 10
  periodSeconds: 15
  failureThreshold: 3

startupProbe:
  httpGet:
    path: /health/ready
    port: 8000
  failureThreshold: 30
  periodSeconds: 10
```

## Backup and Restore

### Automatic Backups

Fabric does not include built-in backup tooling. Use standard PostgreSQL backup procedures:

```bash
# pg_dump (daily)
pg_dump -h localhost -U fabric -d mcp_fabric > fabric_backup_$(date +%Y%m%d).sql

# Point-in-time recovery — enable WAL archiving in postgresql.conf
archive_mode = on
archive_command = 'cp %p /backups/%f'
```

### Restore

```bash
# Restore from SQL dump
psql -h localhost -U fabric -d mcp_fabric < fabric_backup_20260723.sql

# Run migrations to bring schema up to date
alembic upgrade head
```

## Logging and Monitoring

### Logging

Fabric uses [structlog](https://www.structlog.org/) for structured JSON logging.

Configure log level via `LOG_LEVEL`:

| Level | Use Case |
|-------|----------|
| `DEBUG` | Development — verbose request details |
| `INFO` | Production — key events (startup, registration, denials) |
| `WARNING` | Production — degradation events, rate limit warnings |
| `ERROR` | Production — failures requiring investigation |

### Production Log Configuration

```yaml
# docker-compose.override.yml
services:
  api:
    environment:
      - LOG_LEVEL=WARNING
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

### Monitoring

- Prometheus metrics at `GET /v1/metrics`
- OpenTelemetry traces (configure `OTEL_ENDPOINT`)
- Pre-built Grafana dashboard at `monitoring/grafana-dashboard.json`
- Alert rules at `monitoring/alerts.yml`

See `docs/guides/monitoring.md` for detailed setup.

## Upgrade Procedure

### Blue-Green Deployment

1. Deploy a second API instance behind the load balancer
2. Remove one instance from rotation
3. Upgrade the removed instance (new image, run migrations)
4. Verify health on the upgraded instance
5. Return it to rotation, remove the other instance
6. Upgrade the second instance
7. Both instances are now on the new version with zero downtime

### Database Migrations

Migrations are backward-compatible. Run them before deploying new code:

```bash
# 1. Run migrations while old code still runs
docker compose exec api alembic upgrade head

# 2. Deploy new code (rolling update)
docker compose up -d --no-deps --build api
```
