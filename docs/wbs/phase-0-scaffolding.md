# Phase 0: Project Scaffolding

> **Tasks:** 16 · **Effort:** 32h (4 days)  
> **Dependencies:** None (starting point)

---

### P0-01: Poetry Project Initialization

**Description:** Initialize the Python project with Poetry, configure pyproject.toml with all dependencies from spec Section 12.1.

**Dependencies:** None

**Effort:** 2h

**Checklist:**
- [ ] Create `pyproject.toml` with `[tool.poetry]` section: name="mcp-fabric", version="0.1.0", description, authors, license="MIT", readme="README.md"
- [ ] Set repository + documentation URLs to github.com/deghosal-2026/mcp-fabric
- [ ] Set keywords: ["mcp", "agent", "governance", "platform", "tool-mesh", "ai"]
- [ ] Set classifiers: Development Status Alpha, Python 3.12, MIT License
- [ ] Configure `[tool.poetry.dependencies]`: python="^3.12", fastapi="^0.115", uvicorn[standard]="^0.32", sqlalchemy[asyncio]="^2.0", aiosqlite="^0.20", asyncpg="^0.29", alembic="^1.13", pydantic="^2.9", pydantic-settings="^2.6", redis="^5.2", celery[redis]="^5.4", httpx="^0.27", mcp="^1.0", opa-client="^0.5", prometheus-client="^0.21", opentelemetry-*, structlog="^24.4", python-jose[cryptography]="^3.3", passlib[bcrypt]="^1.7", pyotp="^2.9"
- [ ] Configure dev dependencies: pytest, pytest-asyncio, pytest-cov, httpx, ruff, mypy
- [ ] Configure `[tool.ruff]`: line-length=100, target-version="py312"
- [ ] Configure `[tool.pytest.ini_options]`: asyncio_mode="auto", testpaths=["tests"]
- [ ] Configure `[tool.poetry.scripts]`: fabric-admin = "api.cli:main"
- [ ] Run `poetry lock` — verify no dependency conflicts
- [ ] Run `poetry install` — verify all packages install
- [ ] Verify all imports: `poetry run python -c "import fastapi, sqlalchemy, redis, celery, mcp, prometheus_client, structlog, pyotp"`

**Success Criteria:**
- `poetry install` completes in < 60 seconds on fresh environment
- All 35+ dependencies resolve without version conflicts
- `poetry.lock` committed for deterministic builds
- Any developer can clone → `poetry install` → working environment

---

### P0-02: Ruff Linting Configuration

**Description:** Configure Ruff for Python linting and formatting per spec Section 12.1. Enforce consistent code style.

**Dependencies:** P0-01

**Effort:** 1h

**Checklist:**
- [ ] Verify line-length=100 in pyproject.toml
- [ ] Verify target-version=py312
- [ ] Verify lint rules: E, F, I, N, W, UP, B, C4, SIM
- [ ] Create `.ruff.toml` if needed (per-file ignores, exclude patterns)
- [ ] Exclude: `.venv/`, `__pycache__/`, `alembic/versions/`
- [ ] Run `poetry run ruff check .` — passes on empty project
- [ ] Run `poetry run ruff format --check .` — passes

**Success Criteria:**
- `make lint` passes on clean code
- `make format` auto-formats all Python files
- CI lint job fails on style violations

---

### P0-03: Makefile

**Description:** Create Makefile with all targets from spec Section 7. Single-command shortcuts for all dev workflows.

**Dependencies:** P0-01

**Effort:** 2h

**Checklist:**
- [ ] `dev`: `docker-compose up`
- [ ] `test`: `poetry run pytest tests/ -v --cov=api --cov-report=term-missing`
- [ ] `test-unit`: `poetry run pytest tests/ -v -m "unit"`
- [ ] `test-integration`: `poetry run pytest tests/ -v -m "integration"`
- [ ] `test-e2e`: `poetry run pytest tests/ -v -m "e2e"`
- [ ] `lint`: `poetry run ruff check api/ tests/ && cd ui && npm run lint`
- [ ] `format`: `poetry run ruff format api/ tests/ && cd ui && npm run format`
- [ ] `typecheck`: `poetry run mypy api/`
- [ ] `db-up`: `docker-compose up -d postgres redis`
- [ ] `db-migrate`: `poetry run alembic upgrade head`
- [ ] `db-migrate-new`: `poetry run alembic revision --autogenerate -m "$(msg)"`
- [ ] `db-downgrade`: `poetry run alembic downgrade -1`
- [ ] `clean`: `docker-compose down -v && find . -name __pycache__ -delete && rm -rf .pytest_cache`
- [ ] `opa-test`: `opa test policies/ -v`
- [ ] All targets use `.PHONY` declaration
- [ ] Default target prints help

**Success Criteria:**
- `make help` lists all targets
- `make dev` starts 7 services
- `make test` runs suite + reports coverage
- `make clean` removes all containers/volumes

---

### P0-04: API Dockerfile

**Description:** Multi-stage Dockerfile per spec Section 30.1. Builder installs deps, runtime runs as non-root.

**Dependencies:** P0-01

**Effort:** 3h

**Checklist:**
- [ ] Stage 1 ("builder"): FROM python:3.12-slim-bookworm
- [ ] Install build deps: build-essential, curl
- [ ] Install Poetry, copy pyproject.toml + poetry.lock, `poetry install --only main`
- [ ] Stage 2 ("runtime"): FROM python:3.12-slim-bookworm
- [ ] Create non-root user: `fabric` (group + user)
- [ ] Install runtime deps: libpq5, curl
- [ ] Copy site-packages + binaries from builder
- [ ] `COPY --chown=fabric:fabric . .`
- [ ] `USER fabric`
- [ ] `EXPOSE 8000`
- [ ] `HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health/ready`
- [ ] `ENTRYPOINT ["uvicorn", "api.main:app"]`
- [ ] `CMD ["--host", "0.0.0.0", "--port", "8000", "--workers", "4"]`
- [ ] `.dockerignore`: .venv/, __pycache__/, .git/, tests/, docs/, ui/, *.pyc

**Success Criteria:**
- `docker build -t mcp-fabric .` succeeds
- Container starts + responds on `/health`
- `whoami` → `fabric` (non-root confirmed)
- Image < 300MB
- 0 critical/high CVEs

---

### P0-05: UI Dockerfile

**Description:** Multi-stage Dockerfile per spec Section 30.2. Node builds, nginx serves.

**Dependencies:** P9-01 (UI scaffold)

**Effort:** 2h

**Checklist:**
- [ ] Stage 1: FROM node:20-alpine, `npm ci`, `npm run build`
- [ ] Stage 2: FROM nginx:1.27-alpine
- [ ] COPY dist/ to /usr/share/nginx/html
- [ ] COPY nginx.conf (SPA routing, API proxy, gzip)
- [ ] EXPOSE 3000
- [ ] HEALTHCHECK: curl localhost:3000
- [ ] `ui/nginx.conf`: try_files $uri /index.html, proxy /v1 to api

**Success Criteria:**
- Image builds and serves UI at port 3000
- /v1/* proxied to API
- SPA routing works for deep links

---

### P0-06: docker-compose.yml Verification

**Description:** Verify all 7 services start and health checks pass per spec.

**Dependencies:** P0-04, P0-05

**Effort:** 2h

**Checklist:**
- [ ] API: build ., port 8000, depends_on postgres+redis, env vars
- [ ] UI: build ui/, port 3000, depends_on api
- [ ] PostgreSQL: 16-alpine, healthcheck pg_isready, volume pgdata
- [ ] Redis: 7-alpine, volume redisdata
- [ ] OPA: latest, port 8181, volume policies/
- [ ] Celery worker: same build, celery command
- [ ] Celery beat: same build, celery beat command

**Success Criteria:**
- All 7 services "healthy" within 60s
- API responds on :8000/health
- UI responds on :3000
- OPA responds on :8181
- `docker-compose down -v` cleans everything

---

### P0-07: api/config.py — Settings

**Description:** Settings class using pydantic-settings. SQLite default for zero-config dev.

**Dependencies:** P0-01

**Effort:** 2h

**Checklist:**
- [ ] Class `Settings(BaseSettings)` with model_config
- [ ] `database_url`: "sqlite+aiosqlite:///fabric.db" (default)
- [ ] `redis_url`, `opa_url`, `celery_broker_url`, `celery_result_backend`
- [ ] `secret_key`, `environment`, `log_level`
- [ ] `audit_retention_days`=90, `server_health_interval`=30, `default_rate_limit`=100
- [ ] `cors_origins`, `admin_session_ttl_hours`=8, `approval_expiry_hours`=1
- [ ] `max_batch_requests`=10
- [ ] Feature flags dict: enable_streaming=False etc
- [ ] Celery beat schedule dict
- [ ] Production secret_key validation (must not be "dev-*")
- [ ] `is_sqlite` boolean derived from database_url scheme

**Success Criteria:**
- `Settings()` works with zero config
- `Settings(database_url="postgresql+asyncpg://...")` switches
- Production mode rejects "dev-secret-change-me"
- All 18 settings have defaults + type validation

---

### P0-08: api/config.py — Celery Configuration

**Description:** Celery app instance with beat schedule.

**Dependencies:** P0-07

**Effort:** 1h

**Checklist:**
- [ ] Create `celery_app = Celery("fabric", broker=..., backend=...)`
- [ ] Configure: json serializer, UTC, acks_late, reject_on_worker_lost
- [ ] worker_prefetch_multiplier=1, worker_concurrency=4
- [ ] Beat schedule: health-check (30s), cleanup-audit (3am), check-alerts (60s), cleanup-tokens (2am), cleanup-approvals (5min), scheduled-exports (midnight)

**Success Criteria:**
- Worker picks up tasks from Redis
- Beat fires on schedule
- `redis-cli LLEN celery` shows task queue

---

### P0-09: api/main.py — FastAPI App

**Description:** FastAPI entry point with middleware, routers, lifespan, graceful shutdown per spec Sections 20.1 and 31.

**Dependencies:** P0-07

**Effort:** 3h

**Checklist:**
- [ ] Create FastAPI(title="MCP Fabric", version="0.1.0")
- [ ] Lifespan: startup (connect DB/Redis/OPA), shutdown (drain + close)
- [ ] Middleware order: CORS → RequestID → Tracing → Auth → Tenant → RateLimit → Audit
- [ ] API version middleware
- [ ] All router groups included
- [ ] Exception handlers: FabricError, RequestValidationError, unhandled
- [ ] SIGTERM/SIGINT → set readiness=shutting_down → wait 5s → close
- [ ] OpenAPI metadata: contact, license, tags

**Success Criteria:**
- `uvicorn api.main:app --reload` starts
- `/docs` shows Swagger with all endpoints
- `/openapi.json` is valid OpenAPI 3.1
- `kill -TERM` triggers graceful shutdown
- `/health/ready` returns 503 during shutdown

---

### P0-10: api/dependencies.py

**Description:** FastAPI dependency injection: DB, Redis, OPA, agent auth, admin auth, API version, tenant scope.

**Dependencies:** P0-07, P0-09

**Effort:** 3h

**Checklist:**
- [ ] `get_db()` → async SQLAlchemy session
- [ ] `get_redis()` → Redis client
- [ ] `get_opa()` → OPA client
- [ ] `get_current_agent(token)` → validates Bearer token → AgentIdentity or 401
- [ ] `get_current_admin(authorization)` → validates JWT session → AdminUser or 401
- [ ] `get_api_version(request)` → parses Accept header → "v1"
- [ ] `get_tenant_scope(request)` → extracts namespace from agent/admin
- [ ] `check_rate_limit(request, agent)` → Redis INCR → 429 if exceeded

**Success Criteria:**
- All injectable via `Depends()`
- `get_current_agent` returns identity for valid token, 401 for invalid
- `get_api_version` extracts "v1" from Accept header

---

### P0-11: Alembic Initialization

**Description:** Initialize Alembic for async SQLAlchemy with SQLite + PostgreSQL support.

**Dependencies:** P0-01

**Effort:** 2h

**Checklist:**
- [ ] `alembic init alembic`
- [ ] `alembic.ini` with placeholder URL
- [ ] `alembic/env.py`: async engine, import all models, target_metadata
- [ ] Test: `alembic revision --autogenerate` creates migration
- [ ] Test: `alembic upgrade head` on SQLite → all tables
- [ ] Test: `alembic downgrade -1` on SQLite → tables removed
- [ ] Test: `alembic upgrade head` on PostgreSQL → all tables
- [ ] Test: `alembic downgrade -1` on PostgreSQL → tables removed

**Success Criteria:**
- All 17 tables create + drop on both databases
- Auto-generation detects model changes
- Migrations committed to repo

---

### P0-12: OPA Policy Files

**Description:** Default OPA Rego policies + tests per spec Section 24.

**Dependencies:** None

**Effort:** 2h

**Checklist:**
- [ ] `policies/fabric/policy.rego`: trust_levels, class_min_trust, allow, approval_required, cross_team_allowed, result
- [ ] `policies/fabric/policy_test.rego`: 10 test cases
- [ ] `opa test policies/ -v` → 10/10 pass

**Success Criteria:**
- Tests pass, exit code 0
- Policy queryable at OPA endpoint
- Denies by default (secure)

---

### P0-13: GitHub CI Workflow

**Description:** CI pipeline per spec Section 22.

**Dependencies:** P0-01, P0-03

**Effort:** 2h

**Checklist:**
- [ ] `.github/workflows/ci.yml`: on push/PR to main
- [ ] lint, test-sqlite, test-postgres, opa-tests, typecheck, ui-lint, security-scan jobs
- [ ] All jobs run in parallel where possible
- [ ] Coverage upload to codecov

**Success Criteria:**
- CI green on main
- PR blocked if any job fails
- Coverage report visible on PR

---

### P0-14: GitHub Release Workflow

**Description:** Release pipeline per spec Section 22.2.

**Dependencies:** P0-04, P0-05

**Effort:** 2h

**Checklist:**
- [ ] `.github/workflows/release.yml`: on tag v*
- [ ] build-docker: push to ghcr.io with all tag variants
- [ ] publish-pypi: poetry build + publish
- [ ] create-release: GitHub Release with changelog

**Success Criteria:**
- Tag push triggers release
- Docker image at ghcr.io
- `pip install mcp-fabric` works

---

### P0-15: Dependabot Configuration

**Description:** Automated dependency updates per spec Section 27.1.

**Dependencies:** None

**Effort:** 1h

**Checklist:**
- [ ] `.github/dependabot.yml`
- [ ] pip: weekly Monday, groups (fastapi, sqlalchemy, telemetry, testing, linting), PR limit 5
- [ ] docker: weekly Monday
- [ ] github-actions: weekly Monday
- [ ] npm: weekly Monday, groups (react, tanstack, vite), PR limit 5

**Success Criteria:**
- Dependabot opens grouped PRs on schedule
- Security alerts trigger immediate PRs

---

### P0-16: Repository Documentation Files

**Description:** README badges, CHANGELOG, CODE_OF_CONDUCT, PR template, .gitattributes.

**Dependencies:** None

**Effort:** 2h

**Checklist:**
- [ ] README: badges (MIT, CI, Python 3.12)
- [ ] README: Quick Start with actual commands
- [ ] README: links to PRD, spec, design, architecture, WBS
- [ ] CHANGELOG: Keep a Changelog format
- [ ] CODE_OF_CONDUCT: Contributor Covenant 2.1
- [ ] PULL_REQUEST_TEMPLATE.md
- [ ] .gitattributes: linguist, line endings, diff

**Success Criteria:**
- README badges render on GitHub
- Quick Start produces working instance
- All .github/ files present
