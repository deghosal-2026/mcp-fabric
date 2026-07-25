# Configuration Reference

All configuration loads from environment variables via [pydantic-settings](https://docs.pydantic.dev/latest/concepts/pydantic_settings/). Override any value by setting the matching environment variable (case-insensitive).

## Environment Variables

### Database

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `DATABASE_URL` | `sqlite+aiosqlite:///fabric.db` | Database connection string | `postgresql+asyncpg://user:pass@host:5432/fabric` |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection string | `redis://:password@redis-cluster:6379/0` |
| `CELERY_BROKER_URL` | `redis://localhost:6379/1` | Celery message broker URL | Same as `REDIS_URL`, DB 1 |
| `CELERY_RESULT_BACKEND` | `redis://localhost:6379/2` | Celery result backend URL | Same as `REDIS_URL`, DB 2 |

### Auth / Security

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `SECRET_KEY` | `dev-secret-change-me` | HMAC key for JWT signing | `openssl rand -hex 32` output |
| `JWT_ISSUER` | `mcp-fabric` | Expected JWT `iss` claim | `mcp-fabric` |
| `JWT_AUDIENCE` | `mcp-fabric-api` | Expected JWT `aud` claim | `mcp-fabric-api` |
| `ADMIN_SESSION_TTL_HOURS` | `8` | Admin session duration | `8` |
| `APPROVAL_EXPIRY_HOURS` | `1` | Approval request TTL | `1` |

### Environment

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `ENVIRONMENT` | `development` | Deployment environment label | `production` |
| `LOG_LEVEL` | `INFO` | Logging verbosity | `WARNING` |

### Rate Limiting

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `DEFAULT_RATE_LIMIT` | `100` | Max requests/min per agent | `100` |

### Observability

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `OTEL_ENDPOINT` | `""` | OpenTelemetry collector endpoint | `http://otel-collector:4318` |

### CORS

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins | `["https://fabric.example.com"]` |

### Auditing

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `AUDIT_RETENTION_DAYS` | `90` | Audit log retention period | `90` (or as required by compliance) |

### Service Health

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `SERVER_HEALTH_INTERVAL` | `30` | Health check interval (seconds) | `30` |

### Request Handling

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `MAX_BATCH_REQUESTS` | `10` | Max tools per batch request | `10` |
| `MCP_TIMEOUT` | `5.0` | MCP tool execution timeout (s) | `5.0` |
| `MCP_CONNECT_TIMEOUT` | `2.0` | MCP connection timeout (s) | `2.0` |
| `HEALTH_CHECK_TIMEOUT` | `2.0` | Health probe timeout (s) | `2.0` |

### OPA

| Variable | Default | Description | Production Value |
|----------|---------|-------------|------------------|
| `OPA_URL` | `http://localhost:8181` | Open Policy Agent endpoint | `http://opa.fabric.svc:8181` |

## Feature Flags

Configured via the `FEATURE_FLAGS` environment variable as a JSON object.

| Flag | Default | Description | Target Version |
|------|---------|-------------|----------------|
| `enable_streaming` | `false` | Stream MCP tool responses via SSE | v0.3.0 |
| `enable_federation` | `false` | Cross-Fabric capability sharing | Future |
| `require_mfa_for_admins` | `false` | Enforce MFA for admin role | v0.2.0 |
| `enable_fuzzy_capability_match` | `false` | Semantic (fuzzy) capability matching | v0.2.0 |

Setting feature flags:

```bash
export FEATURE_FLAGS='{"enable_streaming": true, "enable_fuzzy_capability_match": true}'
```

## Example `.env` File

```bash
# ── Database ──────────────────────────────────────────────
# Development: SQLite (zero config)
# DATABASE_URL=sqlite+aiosqlite:///fabric.db

# Production: PostgreSQL
DATABASE_URL=postgresql+asyncpg://fabric:fabric@postgres:5432/mcp_fabric

# Redis
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2

# ── Auth / Security ───────────────────────────────────────
# Generate with: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=change-me-to-a-random-256-bit-hex-string
ENVIRONMENT=production

# ── Observability ─────────────────────────────────────────
LOG_LEVEL=INFO
OTEL_ENDPOINT=http://otel-collector:4318

# ── CORS ──────────────────────────────────────────────────
CORS_ORIGINS=["https://fabric.example.com"]

# ── OPA ───────────────────────────────────────────────────
OPA_URL=http://opa:8181

# ── Feature Flags ─────────────────────────────────────────
FEATURE_FLAGS={"require_mfa_for_admins": true, "enable_streaming": false}
```

## Production Checklist

Before deploying to production, verify:

- [ ] `DATABASE_URL` points to PostgreSQL (not SQLite)
- [ ] `SECRET_KEY` is a strong random value (not `dev-secret-change-me`)
- [ ] `REDIS_URL` uses a password-authenticated Redis instance
- [ ] `CORS_ORIGINS` set to the actual frontend domain(s)
- [ ] `ENVIRONMENT` set to `production`
- [ ] `LOG_LEVEL` set to `WARNING` or `INFO`
- [ ] `OTEL_ENDPOINT` configured if using tracing
- [ ] `FEATURE_FLAGS` reviewed for your deployment
- [ ] Rate limits reviewed for expected traffic patterns
- [ ] PostgreSQL connection pool size reviewed (default 20 per worker)
