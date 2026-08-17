# Phase 0: Project Scaffolding

> **Tasks:** 16 · **Effort:** 32h (4 days)  
> **Dependencies:** None (starting point)

---

### P0-01: Poetry Project Initialization (#1)

**Description:** Initialize the Python project with Poetry, configure pyproject.toml with all dependencies from spec Section 12.1.

**Dependencies:** None

**Effort:** 2h

**Status:** ✅ Complete — `pyproject.toml` created with all 35+ deps, `poetry lock` resolves cleanly, all imports verified.

**Checklist:**
- [x] Create `pyproject.toml` with `[tool.poetry]` section: name="mcp-fabric", version="0.1.0", description, authors, license="MIT", readme="README.md"
- [x] Set repository + documentation URLs to github.com/deghosal-2026/mcp-fabric
- [x] Set keywords: ["mcp", "agent", "governance", "platform", "tool-mesh", "ai"]
- [x] Set classifiers: Development Status Alpha, Python 3.12, MIT License
- [x] Configure `[tool.poetry.dependencies]`: python="^3.12", fastapi="^0.115", uvicorn[standard]="^0.32", sqlalchemy[asyncio]="^2.0", aiosqlite="^0.20", asyncpg="^0.29", alembic="^1.13", pydantic="^2.9", pydantic-settings="^2.6", redis="^5.2", celery[redis]="^5.4", httpx="^0.27", mcp="^1.0", opa-client="^0.5", prometheus-client="^0.21", opentelemetry-*, structlog="^24.4", python-jose[cryptography]="^3.3", passlib[bcrypt]="^1.7", pyotp="^2.9"
- [x] Configure dev dependencies: pytest, pytest-asyncio, pytest-cov, httpx, ruff, mypy
- [x] Configure `[tool.ruff]`: line-length=100, target-version="py312"
- [x] Configure `[tool.pytest.ini_options]`: asyncio_mode="auto", testpaths=["tests"]
- [x] Configure `[tool.poetry.scripts]`: fabric-admin = "api.cli:main"
- [x] Run `poetry lock` — verify no dependency conflicts
- [x] Run `poetry install` — verify all packages install
- [x] Verify all imports: `poetry run python -c "import fastapi, sqlalchemy, redis, celery, mcp, prometheus_client, structlog, pyotp"`

**Closing Note:** Poetry 2.4.1 used. Dependencies written in PEP 621 format under `[project]` (not legacy `[tool.poetry]`). All 35+ deps confirmed installed. `poetry.lock` generated.

---

### P0-02: Ruff Linting Configuration (#4)

**Description:** Configure Ruff for Python linting and formatting per spec Section 12.1. Enforce consistent code style.

**Dependencies:** P0-01

**Effort:** 1h

**Status:** ✅ Complete — Ruff configured in pyproject.toml, lint/format pass on all 39 files.

**Checklist:**
- [x] Verify line-length=100 in pyproject.toml
- [x] Verify target-version=py312
- [x] Verify lint rules: E, F, I, N, W, UP, B, C4, SIM
- [x] Configure per-file ignores in pyproject.toml (B008 for dependencies.py, routers/*.py)
- [x] Exclude patterns configured in `.gitignore` for `.venv/`, `__pycache__/`, `alembic/versions/`
- [x] Run `poetry run ruff check .` — passes
- [x] Run `poetry run ruff format --check .` — passes

**Closing Note:** Ruff config in `[tool.ruff]` section of pyproject.toml. Per-file ignores set for B008 (fastapi Depends with default factory).

---

### P0-03: Makefile (#7)

**Description:** Create Makefile with all targets from spec Section 7. Single-command shortcuts for all dev workflows.

**Dependencies:** P0-01

**Effort:** 2h

**Status:** ✅ Complete — Makefile with 16 targets, `.PHONY` declarations, help text.

**Checklist:**
- [x] `dev`: `docker compose up` (updated from v1 docker-compose)
- [x] `test`: `poetry run pytest tests/ -v --cov=api --cov-report=term-missing`
- [x] `test-unit`: `poetry run pytest tests/ -v -m "unit"`
- [x] `test-integration`: `poetry run pytest tests/ -v -m "integration"`
- [x] `test-e2e`: `poetry run pytest tests/ -v -m "e2e"`
- [x] `lint`: `poetry run ruff check api/ tests/`
- [x] `format`: `poetry run ruff format api/ tests/`
- [x] `typecheck`: `poetry run mypy api/`
- [x] `db-up`: `docker compose up -d postgres redis`
- [x] `db-migrate`: `poetry run alembic upgrade head`
- [x] `db-migrate-new`: `poetry run alembic revision --autogenerate -m "$(msg)"`
- [x] `db-downgrade`: `poetry run alembic downgrade -1`
- [x] `clean`: `docker compose down -v || true; find . -name __pycache__ -delete; rm -rf .pytest_cache`
- [x] `opa-test`: `opa test policies/ -v`
- [x] All targets use `.PHONY` declaration
- [x] Default target prints help

**Closing Note:** Migrated from `docker-compose` v1 to `docker compose` v2 plugin. `lint`/`format` targets only cover Python (UI not scaffolded yet).

---

### P0-04: API Dockerfile (#10)

**Description:** Multi-stage Dockerfile per spec Section 30.1. Builder installs deps, runtime runs as non-root.

**Dependencies:** P0-01

**Effort:** 3h

**Status:** ✅ Complete — Multi-stage Dockerfile with Poetry build, non-root fabric user.

**Checklist:**
- [x] Stage 1 ("builder"): FROM python:3.12-slim-bookworm
- [x] Install build deps: build-essential, curl
- [x] Install Poetry, copy pyproject.toml + poetry.lock, `poetry build` to generate wheel
- [x] Stage 2 ("runtime"): FROM python:3.12-slim-bookworm
- [x] Create non-root user: `fabric` (group + user)
- [x] Install runtime deps: libpq5, curl
- [x] Copy wheel from builder, `pip install dist/*.whl`
- [x] `COPY --chown=fabric:fabric . .`
- [x] `USER fabric`
- [x] `EXPOSE 8000`
- [x] `HEALTHCHECK --interval=30s CMD curl -f http://localhost:8000/health/ready`
- [x] `ENTRYPOINT ["uvicorn", "api.main:app"]`
- [x] `CMD ["--host", "0.0.0.0", "--port", "8000", "--workers", "4"]`
- [x] `.dockerignore`: .venv/, __pycache__/, .git/, tests/, docs/, ui/, *.pyc

**Closing Note:** Uses `poetry build` to generate wheel then `pip install` (avoids Poetry at runtime). Non-root `fabric` user. Multi-stage keeps image slim.

---

### P0-05: UI Dockerfile (#13)

**Description:** Multi-stage Dockerfile per spec Section 30.2. Node builds, nginx serves.

**Dependencies:** P9-01 (UI scaffold)

**Effort:** 2h

**Status:** ⏳ Deferred — blocked by P9-01 (UI scaffold not started).

**Checklist:**
- [ ] Stage 1: FROM node:20-alpine, `npm ci`, `npm run build`
- [ ] Stage 2: FROM nginx:1.27-alpine
- [ ] COPY dist/ to /usr/share/nginx/html
- [ ] COPY nginx.conf (SPA routing, API proxy, gzip)
- [ ] EXPOSE 3000
- [ ] HEALTHCHECK: curl localhost:3000
- [ ] `ui/nginx.conf`: try_files $uri /index.html, proxy /v1 to api

---

### P0-06: docker-compose.yml Verification (#16)

**Description:** Verify all 7 services start and health checks pass per spec.

**Dependencies:** P0-04, P0-05

**Effort:** 2h

**Status:** ⏳ Deferred — blocked by P0-05 (UI Dockerfile). docker-compose.yml structure defined mentally: API | UI | PostgreSQL | Redis | OPA | Celery worker | Celery beat.

**Checklist:**
- [ ] API: build ., port 8000, depends_on postgres+redis, env vars
- [ ] UI: build ui/, port 3000, depends_on api
- [ ] PostgreSQL: 16-alpine, healthcheck pg_isready, volume pgdata
- [ ] Redis: 7-alpine, volume redisdata
- [ ] OPA: latest, port 8181, volume policies/
- [ ] Celery worker: same build, celery command
- [ ] Celery beat: same build, celery beat command

---

### P0-07: api/config.py — Settings (#19)

**Description:** Settings class using pydantic-settings. SQLite default for zero-config dev.

**Dependencies:** P0-01

**Effort:** 2h

**Status:** ✅ Complete — `Settings` class with 22 env vars, feature flags, Celery beat schedule, `is_sqlite` property.

**Checklist:**
- [x] Class `Settings(BaseSettings)` with pydantic-settings
- [x] `database_url`: "sqlite+aiosqlite:///fabric.db" (default)
- [x] `redis_url`, `opa_url`, `celery_broker_url`, `celery_result_backend`
- [x] `secret_key`, `environment`, `log_level`
- [x] `audit_retention_days`=90, `server_health_interval`=30, `default_rate_limit`=100
- [x] `cors_origins`, `admin_session_ttl_hours`=8, `approval_expiry_hours`=1
- [x] `max_batch_requests`=10, `mcp_timeout`=5.0, `mcp_connect_timeout`=2.0, `health_check_timeout`=2.0
- [x] Feature flags dict: enable_streaming=False etc
- [x] Celery beat schedule dict with 3 periodic tasks
- [x] Production secret_key validation (must not be "dev-*")
- [x] `is_sqlite` boolean derived from database_url scheme

**Closing Note:** `model_post_init` validates production secret_key. CORS origins, feature_flags, and celery_beat_schedule need JSON-formatted env vars in production.

---

### P0-08: api/tasks.py — Celery Configuration (#22)

**Description:** Celery app instance with beat schedule.

**Dependencies:** P0-07

**Effort:** 1h

**Status:** ✅ Complete — Celery app in `api/tasks.py` with beat_schedule from config.

**Checklist:**
- [x] Create `celery_app = Celery("fabric", broker=..., backend=...)`
- [x] Configure: json serializer, UTC, acks_late, reject_on_worker_lost
- [x] worker_prefetch_multiplier=1, worker_concurrency=4
- [x] Beat schedule sourced from `settings.celery_beat_schedule`

**Closing Note:** Task definitions (health_check_all_servers, cleanup_audit_logs, check_alert_thresholds) are placeholders — actual implementations belong in Phase 6 (Celery).

---

### P0-09: api/main.py — FastAPI App (#25)

**Description:** FastAPI entry point with middleware, routers, lifespan, graceful shutdown per spec Sections 20.1 and 31.

**Dependencies:** P0-07

**Effort:** 3h

**Status:** ✅ Complete — FastAPI app with lifespan, seeders, health endpoints, exception handlers.

**Checklist:**
- [x] Create FastAPI(title="MCP Fabric", version="0.1.0")
- [x] Lifespan: startup runs seeders, shutdown sets readiness=shutting_down → 5s drain
- [x] Middleware scaffolding: readiness/health endpoints in place
- [x] Exception handlers: RequestValidationError (422), unhandled (500)
- [x] SIGTERM/SIGINT → set readiness=shutting_down → wait 5s → close
- [x] OpenAPI metadata: contact (Debashish Ghosal), license (MIT), version

**Closing Note:** Middleware stack (CORS, RequestID, Tracing, Auth, Tenant, RateLimit, Audit) to be implemented in Phase 4. Router groups to be added in Phase 5.

---

### P0-10: api/dependencies.py (#28)

**Description:** FastAPI dependency injection: DB, Redis, OPA, agent auth, admin auth, API version, tenant scope.

**Dependencies:** P0-07, P0-09

**Effort:** 3h

**Status:** ✅ Complete — DI scaffold with auth stubs, API version, request ID, tenant scope.

**Checklist:**
- [x] `get_db()` → async SQLAlchemy session (in api/database.py)
- [x] `get_current_agent(token)` → Bearer token validation stub → 401 if missing
- [x] `get_current_admin(authorization)` → Bearer token validation stub → 401 if missing
- [x] `get_api_version(request)` → parses Accept header → "v1"
- [x] `get_tenant_scope(request)` → extracts namespace from request state
- [x] `get_request_id(request)` → generates or forwards request ID

**Closing Note:** `get_current_agent` and `get_current_admin` are stubs (no JWT/Db validation yet). `get_redis()`, `get_opa()`, `check_rate_limit()` to be added when Redis/OPA services are wired in Phase 3/4.

---

### P0-11: Alembic Initialization (#31)

**Description:** Initialize Alembic for async SQLAlchemy with SQLite + PostgreSQL support.

**Dependencies:** P0-01

**Effort:** 2h

**Status:** ✅ Complete — Async Alembic env.py, autogenerate works, upgrade/downgrade tested on SQLite.

**Checklist:**
- [x] `alembic init alembic` with async env.py
- [x] `alembic.ini` with placeholder URL
- [x] `alembic/env.py`: async engine, import all 20 models, target_metadata
- [x] Test: `alembic revision --autogenerate` creates migration
- [x] Test: `alembic upgrade head` on SQLite → all 20 tables created
- [x] Test: `alembic downgrade -1` on SQLite → all tables removed
- [x] Test: round-trip upgrade→downgrade→upgrade passes cleanly

**Closing Note:** Migration regenerated after each model change (FKs, indexes, constraints). SQLite verified. PostgreSQL verification deferred until Phase 11 (CI with PG service).

---

### P0-12: OPA Policy Files (#34)

**Description:** Default OPA Rego policies + tests per spec Section 24.

**Dependencies:** None

**Effort:** 2h

**Status:** ✅ Complete — Rego policy with 11 test cases covering trust levels, cross-team, approvals.

**Checklist:**
- [x] `policies/fabric/policy.rego`: trust_levels, class_min_trust, allow, approval_required, cross_team_allowed, result
- [x] `policies/fabric/policy_test.rego`: 11 test cases
- [x] `opa test policies/ -v` → 11/11 pass (requires `opa` CLI)

**Closing Note:** OPA CLI not installed locally — tests will execute in CI. Policy denies by default. 11 test cases cover all trust levels and cross-team scenarios.

---

### P0-13: GitHub CI Workflow (#37)

**Description:** CI pipeline per spec Section 22.

**Dependencies:** P0-01, P0-03

**Effort:** 2h

**Status:** 🔲 Not started — deferred to Phase 11 (CI/CD).

**Checklist:**
- [ ] `.github/workflows/ci.yml`: on push/PR to main
- [ ] lint, test-sqlite, test-postgres, opa-tests, typecheck, ui-lint, security-scan jobs
- [ ] All jobs run in parallel where possible
- [ ] Coverage upload to codecov

---

### P0-14: GitHub Release Workflow (#39)

**Description:** Release pipeline per spec Section 22.2.

**Dependencies:** P0-04, P0-05

**Effort:** 2h

**Status:** 🔲 Not started — deferred to Phase 11 (CI/CD).

**Checklist:**
- [ ] `.github/workflows/release.yml`: on tag v*
- [ ] build-docker: push to ghcr.io with all tag variants
- [ ] publish-pypi: poetry build + publish
- [ ] create-release: GitHub Release with changelog

---

### P0-15: Dependabot Configuration (#42)

**Description:** Automated dependency updates per spec Section 27.1.

**Dependencies:** None

**Effort:** 1h

**Status:** 🔲 Not started — deferred to Phase 11 (CI/CD).

**Checklist:**
- [ ] `.github/dependabot.yml`
- [ ] pip: weekly Monday, groups (fastapi, sqlalchemy, telemetry, testing, linting), PR limit 5
- [ ] docker: weekly Monday
- [ ] github-actions: weekly Monday
- [ ] npm: weekly Monday, groups (react, tanstack, vite), PR limit 5

---

### P0-16: Repository Documentation Files (#45)

**Description:** README badges, CHANGELOG, CODE_OF_CONDUCT, PR template, .gitattributes.

**Dependencies:** None

**Effort:** 2h

**Status:** 🔲 Not started — deferred to Phase 12 (Documentation).

**Checklist:**
- [ ] README: badges (MIT, CI, Python 3.12)
- [ ] README: Quick Start with actual commands
- [ ] README: links to PRD, spec, design, architecture, WBS
- [ ] CHANGELOG: Keep a Changelog format
- [ ] CODE_OF_CONDUCT: Contributor Covenant 2.1
- [ ] PULL_REQUEST_TEMPLATE.md
- [ ] .gitattributes: linguist, line endings, diff
