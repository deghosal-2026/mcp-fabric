# Troubleshooting Guide

Common issues, diagnostic steps, and solutions for MCP Fabric.

## API Won't Start

### Port Conflicts

**Symptom:** `OSError: [Errno 48] Address already in use` or `port already allocated`

**Solution:**

```bash
# Find what's using the port
lsof -i :8000

# Kill the process
kill -9 <PID>

# Or start on a different port
poetry run uvicorn api.main:app --host 0.0.0.0 --port 8001
```

### Database Connection Failure

**Symptom:** `sqlalchemy.exc.OperationalError: unable to open database file` (SQLite) or `can't connect to server` (PostgreSQL)

**Solutions:**

**SQLite (development):**
```bash
# Ensure the parent directory is writable
touch fabric.db && chmod 644 fabric.db

# Try a clean database
rm -f fabric.db && alembic upgrade head
```

**PostgreSQL (production):**
```bash
# Verify PostgreSQL is running
pg_isready -h localhost -U fabric -d mcp_fabric

# Check the connection URL
echo $DATABASE_URL

# Test with psql
psql $DATABASE_URL -c "SELECT 1"

# Common fixes:
# 1. Wrong credentials → verify POSTGRES_USER/POSTGRES_PASSWORD
# 2. Docker service not running → docker compose up -d postgres
# 3. Network mismatch → host must match docker-compose service name
```

### Secret Key Not Set

**Symptom:** `ValueError: SECRET_KEY must be changed from default in production`

**Solution:** Set a strong random key:

```bash
# Generate a key
python -c "import secrets; print(secrets.token_hex(32))"

# Export it
export SECRET_KEY="<generated-value>"
```

## Health Check Failures

### `/health/ready` Returns 503

**Symptom:** Readiness probe consistently fails.

**Diagnostic steps:**

```bash
# Check full health
curl http://localhost:8000/health

# Check individual components
curl http://localhost:8000/health | python -m json.tool
```

**Common causes:**

| Component | Failure | Solution |
|-----------|---------|----------|
| `database` | `disconnected` | PostgreSQL is down or unreachable. Check `docker compose logs postgres`. |
| `database` | `not_initialized` | Migrations haven't run. Run `alembic upgrade head`. |
| `redis` | `disconnected` | Redis is down. Check `docker compose logs redis`. Verify `REDIS_URL`. |
| `opa` | `disconnected` | OPA server is down. Verify `OPA_URL` or disable OPA for development. |

## OPA Connection Errors

**Symptom:** Policy evaluation fails with connection refused or timeout.

```bash
# Check OPA is running
curl http://localhost:8181/v1/health

# If OPA is not running, start it
docker compose up -d opa

# Or disable OPA for development (not recommended for production)
opa_client = None  # in api/services/policy_service.py
```

**Common causes:**

| Cause | Symptom | Fix |
|-------|---------|-----|
| OPA not installed | `connection refused` | Install OPA or run via Docker: `docker run -p 8181:8181 openpolicyagent/opa` |
| Wrong OPA URL | `connection refused` | Verify `OPA_URL` environment variable |
| Policy not loaded | OPA returns 404 | Deploy policy bundle: `curl -X PUT --data-binary @policies/fabric.rego localhost:8181/v1/policies/fabric` |
| OPA version mismatch | Invalid response format | Use OPA v0.68+ |

## Redis Connection Errors

**Symptom:** `redis.exceptions.ConnectionError` or `Error 111 connecting to redis`.

```bash
# Verify Redis is running
redis-cli ping

# Or check Docker logs
docker compose logs redis

# Test connection
redis-cli -u $REDIS_URL PING
```

**Common fixes:**

1. Redis not running: `docker compose up -d redis`
2. Wrong host: In Docker Compose, use service name `redis`, not `localhost`
3. Auth required: Add password to `REDIS_URL`: `redis://:password@redis:6379/0`
4. Wrong database index: Default is DB 0 for cache, DB 1 for Celery broker, DB 2 for Celery backend

## UI Not Loading

### Proxy Issues

**Symptom:** UI loads but API calls fail with CORS errors or 404.

**Solutions:**

```bash
# Verify the UI proxy configuration
# ui/vite.config.ts should proxy /api to the API server
cat ui/vite.config.ts

# Common fixes:
# 1. API server is not running on the expected port
# 2. CORS_ORIGINS doesn't include the UI dev server URL (http://localhost:3000)
# 3. Wrong proxy path — check 'proxy' configuration in vite.config.ts
```

### CORS Errors

**Symptom:** Browser console shows `Access-Control-Allow-Origin` errors.

**Solutions:**

```bash
# Verify CORS configuration
# The API must include the UI's origin in CORS_ORIGINS
export CORS_ORIGINS='["http://localhost:3000", "http://localhost:5173"]'

# If using Docker Compose UI (port 3005):
export CORS_ORIGINS='["http://localhost:3005"]'
```

### Blank Page

**Symptom:** UI loads but shows a blank white page.

**Solutions:**

```bash
# Check browser console for JavaScript errors
# Common causes:
# 1. Missing dependencies — run `cd ui && npm install`
# 2. TypeScript compilation errors — run `cd ui && npm run build` and check output
# 3. React Router configuration — verify routes match expected paths
```

## Agent Cannot Connect

**Symptom:** Agent receives 401 when trying to authenticate.

**Diagnostic steps:**

```bash
# Verify the agent token
curl -H "Authorization: Bearer <token>" http://localhost:8000/health

# Check token status (as admin)
GET /admin/tokens/{id}
```

**Common causes:**

| Error | Cause | Solution |
|-------|-------|----------|
| `invalid_token` | Token is malformed or doesn't exist | Regenerate the token |
| `token_expired` | Token past `expires_at` | Rotate the token |
| `access_denied` | Agent class not authorized for capability | Adjust trust levels or agent class mapping |
| `namespace_restricted` | Cross-team access attempt | Verify agent's team namespace matches server's team |

## Database Migration Issues

**Symptom:** `alembic.util.exc.CommandError` or migration fails.

```bash
# Check current migration state
alembic current

# View migration history
alembic history

# If stuck on a failed migration:
alembic downgrade -1   # Rollback
# Fix the issue, then:
alembic upgrade head    # Re-apply
```

**If migrations are out of sync:**

```bash
# Stamp the database at a specific revision (recovery only)
alembic stamp <revision_id>

# Then upgrade fresh
alembic upgrade head
```

## Celery Worker Issues

**Symptom:** Background tasks (health checks, alerts, approval notifications) never execute.

```bash
# Check worker logs
docker compose logs worker

# Verify Celery can connect to Redis
docker compose exec worker celery -A api.tasks inspect ping

# Restart workers
docker compose restart worker beat
```

**Common causes:**

| Cause | Symptom | Fix |
|-------|---------|-----|
| Redis broker down | Worker cannot connect | Ensure Redis is running |
| Wrong broker URL | Connection refused | Verify `CELERY_BROKER_URL` |
| Task import error | Worker crashes on startup | Check `api/tasks.py` for import errors |
| Beat not running | Scheduled tasks never fire | Ensure `beat` service is running: `docker compose up -d beat` |

## General Debugging

### Enable Debug Logging

```bash
export LOG_LEVEL=DEBUG
# Restart the API to see verbose logs
```

### Check API Logs

```bash
# Docker Compose
docker compose logs -f api

# Direct Uvicorn (stdout)
poetry run uvicorn api.main:app --reload --log-level debug
```

### Verify All Services

```bash
# Full health check
curl http://localhost:8000/health

# Prometheus metrics
curl http://localhost:8000/v1/metrics

# OpenAPI docs (for endpoint reference)
open http://localhost:8000/docs
```

### Reset Development Environment

```bash
# Stop everything and remove volumes
docker compose down -v

# Clean cache files
make clean

# Start fresh
docker compose up
```
