# MCP Fabric — Work Breakdown Structure (v0.1.0)

> **Status:** Approved
> **Total tasks:** 285
> **Based on:** `docs/PRD.md`, `docs/spec.md`, `docs/DESIGN.md`, `docs/ARCHITECTURE.md`
> **Milestone:** [v0.1.0 - Core Platform](https://github.com/deghosal-2026/mcp-fabric/milestone/1)

---

## Phase 0: Project Scaffolding

### P0-01: Poetry + pyproject.toml

**Checklist:**
- [ ] Create `pyproject.toml` with all dependencies from spec Section 12.1
- [ ] Configure `[tool.poetry]` — name, version, description, authors, license, readme, repository, keywords, classifiers
- [ ] Configure `[tool.poetry.dependencies]` — python ^3.12, fastapi, uvicorn, sqlalchemy[asyncio], aiosqlite, asyncpg, alembic, pydantic, pydantic-settings, redis, celery[redis], httpx, mcp, opa-client, prometheus-client, opentelemetry-*
- [ ] Configure `[tool.poetry.group.dev.dependencies]` — pytest, pytest-asyncio, pytest-cov, httpx, ruff
- [ ] Configure `[tool.ruff]` — line-length=100, target-version=py312, select lint rules
- [ ] Configure `[tool.pytest.ini_options]` — asyncio_mode=auto, testpaths=tests
- [ ] Configure `[tool.poetry.scripts]` — fabric-admin = "api.cli:main"
- [ ] Run `poetry lock` and verify no dependency conflicts
- [ ] Verify `poetry install` succeeds

**Success Criteria:**
- `poetry install` completes without errors
- `poetry run python -c "import fastapi, sqlalchemy, redis, celery, mcp, opa_client, prometheus_client, structlog"` succeeds
- All dependency versions match spec Section 2

---

### P0-02: Makefile

**Checklist:**
- [ ] `make dev` — runs `docker-compose up`
- [ ] `make test` — runs `pytest tests/ -v --cov=api --cov-report=term-missing`
- [ ] `make lint` — runs `ruff check api/ tests/` + `cd ui && npm run lint`
- [ ] `make format` — runs `ruff format api/ tests/` + `cd ui && npm run format`
- [ ] `make db-up` — runs `docker-compose up -d postgres redis`
- [ ] `make db-migrate` — runs `alembic upgrade head`
- [ ] `make db-migrate-new msg="..."` — runs `alembic revision --autogenerate -m "$msg"`
- [ ] `make clean` — runs `docker-compose down -v` + `find __pycache__ -delete`
- [ ] All targets work from a fresh clone

**Success Criteria:**
- `make dev` starts all services without errors
- `make lint` passes on scaffolded code
- `make clean` removes all containers and generated files

---

### P0-03: Dockerfile (API)

**Checklist:**
- [ ] Multi-stage build: `builder` stage installs Poetry + dependencies
- [ ] `runtime` stage copies site-packages from builder, uses non-root `fabric` user
- [ ] Healthcheck: `curl -f http://localhost:8000/health/ready || exit 1`
- [ ] Base image: `python:3.12-slim-bookworm`
- [ ] Expose port 8000
- [ ] ENTRYPOINT: `uvicorn api.main:app --host 0.0.0.0 --port 8000 --workers 4`
- [ ] Docker scan passes (no critical/high CVEs)
- [ ] Image builds and runs successfully

**Success Criteria:**
- `docker build -t mcp-fabric .` succeeds
- `docker run -p 8000:8000 mcp-fabric` responds on `/health`
- Image size < 300MB
- Non-root user confirmed via `docker exec whoami` → `fabric`

---

### P0-04: Dockerfile (UI)

**Checklist:**
- [ ] Multi-stage: `builder` (node:20-alpine) builds React app, `runtime` (nginx:1.27-alpine) serves
- [ ] `npm ci` + `npm run build` in builder stage
- [ ] Copy `dist/` to nginx `html/` in runtime stage
- [ ] Copy `ui/nginx.conf` for API proxy + SPA routing
- [ ] Healthcheck: `curl -f http://localhost:3000/`
- [ ] Expose port 3000

**Success Criteria:**
- `docker build -f ui/Dockerfile -t mcp-fabric-ui .` succeeds
- Admin UI serves at `http://localhost:3000`

---

### P0-05: docker-compose.yml Verification

**Checklist:**
- [ ] API service: builds from `Dockerfile`, port 8000, env vars set, depends on postgres + redis
- [ ] UI service: builds from `ui/Dockerfile`, port 3000, proxy to API
- [ ] PostgreSQL service: postgres:16-alpine, healthcheck, persistent volume
- [ ] Redis service: redis:7-alpine, persistent volume
- [ ] OPA service: openpolicyagent/opa:latest, port 8181, mounted policies/
- [ ] Celery worker: same image as API, different command
- [ ] Celery beat: same image as API, different command
- [ ] All services start: `docker-compose up` → all healthy within 60s
- [ ] `docker-compose down -v` cleans all volumes

**Success Criteria:**
- `docker-compose up` → `docker-compose ps` shows all 7 services as "healthy"
- API responds on `http://localhost:8000/health`
- UI responds on `http://localhost:3000`
- OPA responds on `http://localhost:8181/v1/data`

---

### P0-06: api/config.py

**Checklist:**
- [ ] Settings class using pydantic-settings BaseSettings
- [ ] All env vars with defaults from spec Section 10.1
- [ ] DATABASE_URL default: `sqlite+aiosqlite:///fabric.db`
- [ ] REDIS_URL, OPA_URL, CELERY_BROKER_URL, CELERY_RESULT_BACKEND
- [ ] SECRET_KEY, ENVIRONMENT, LOG_LEVEL
- [ ] AUDIT_RETENTION_DAYS, SERVER_HEALTH_INTERVAL, DEFAULT_RATE_LIMIT
- [ ] Feature flags dict from spec Section 10.2
- [ ] Celery beat schedule from spec Section 6.2
- [ ] Validation: DATABASE_URL scheme check (sqlite vs postgresql)

**Success Criteria:**
- `Settings()` loads with all defaults in dev mode
- `Settings(DATABASE_URL="postgresql+asyncpg://...")` switches to PostgreSQL
- Missing required env var in production raises clear error

---

### P0-07: api/main.py

**Checklist:**
- [ ] FastAPI app initialization with title, version, docs_url
- [ ] Middleware registration in correct order: CORS → RequestID → Tracing → Auth → Tenant → RateLimit → Audit
- [ ] Router includes: all route modules
- [ ] Lifespan: startup (connect DB/Redis/OPA) and shutdown (drain requests, close connections)
- [ ] Signal handlers for SIGTERM/SIGINT (graceful shutdown per spec Section 20.1)
- [ ] Exception handlers registered for all 12 error types
- [ ] OpenAPI metadata: title, version, description, contact

**Success Criteria:**
- `uvicorn api.main:app` starts without errors
- `GET /docs` shows Swagger UI with all endpoints
- `GET /openapi.json` returns valid OpenAPI 3.1 spec
- `kill -TERM` triggers graceful shutdown (logs "shutting down", closes connections)

---

### P0-08: api/dependencies.py

**Checklist:**
- [ ] `get_db()` — async SQLAlchemy session, yields per-request session
- [ ] `get_redis()` — async Redis client from connection pool
- [ ] `get_opa()` — OPA client instance
- [ ] `get_current_agent()` — FastAPI Depends that validates Bearer token, returns AgentIdentity
- [ ] `get_current_admin()` — FastAPI Depends that validates admin JWT session
- [ ] `get_api_version()` — FastAPI Depends that parses Accept header for version
- [ ] `get_tenant_scope()` — FastAPI Depends that sets namespace filter from agent class

**Success Criteria:**
- All dependencies injectable via FastAPI Depends()
- `get_current_agent` returns 401 for invalid/missing token
- `get_current_admin` returns 401 for expired session
- `get_api_version` extracts v1 from `Accept: application/vnd.fabric.v1+json`

---

### P0-09: Alembic Setup + Initial Migration

**Checklist:**
- [ ] `alembic init` → `alembic.ini` configured with DATABASE_URL placeholder
- [ ] `env.py` configured for async SQLAlchemy, imports all models
- [ ] Initial migration: `alembic revision --autogenerate -m "initial schema"`
- [ ] Migration creates all 17 tables from spec Section 3
- [ ] Migration creates all indexes from spec Section 19.1
- [ ] Test: `alembic upgrade head` + `alembic downgrade -1` on SQLite
- [ ] Test: `alembic upgrade head` + `alembic downgrade -1` on PostgreSQL
- [ ] Auto-generation works: add a model field → `alembic revision --autogenerate` detects it

**Success Criteria:**
- Initial migration creates all tables and indexes
- Upgrade and downgrade work without errors on both SQLite and PostgreSQL
- `alembic history` shows clean linear history

---

### P0-10: OPA Policy Files

**Checklist:**
- [ ] `policies/fabric/policy.rego` — default policies from spec Section 24.1
- [ ] Package `fabric.policy`, default allow=false
- [ ] trust_levels map, class_min_trust map
- [ ] Main `allow` rule, `approval_required` rule, `cross_team_allowed` rule
- [ ] `result` output rule
- [ ] `policies/fabric/policy_test.rego` — all 10 tests from spec Section 24.2
- [ ] `opa test policies/ -v` passes all tests
- [ ] Policy bundle loaded into OPA at startup

**Success Criteria:**
- `opa test policies/ -v` → 10/10 tests pass
- `opa run --server policies/` → policy queryable at `/v1/data/fabric/policy`

---

### P0-11: CI/CD Files

**Checklist:**
- [ ] `.github/workflows/ci.yml` — lint, test-sqlite, test-postgres, opa-tests, typecheck, ui-lint
- [ ] `.github/workflows/release.yml` — build Docker + push ghcr.io + publish PyPI
- [ ] `.github/dependabot.yml` — pip (weekly, groups), docker, github-actions, npm
- [ ] CI passes on push to main

**Success Criteria:**
- All CI checks green on main branch
- Dependabot opens PRs for outdated dependencies

---

### P0-12: Repository Documentation Files

**Checklist:**
- [ ] `CONTRIBUTING.md` — quick start, project structure, dev workflow, PR process, code style
- [ ] `SECURITY.md` — reporting, response timeline, supported versions, design principles
- [ ] `CODE_OF_CONDUCT.md` — standard Contributor Covenant
- [ ] `.github/CODEOWNERS` — @deghosal-2026 as default owner
- [ ] `.github/PULL_REQUEST_TEMPLATE.md` — description, checklist, testing notes
- [ ] `.github/ISSUE_TEMPLATE/bug_report.md` — steps to reproduce, expected/actual, environment
- [ ] `.github/ISSUE_TEMPLATE/feature_request.md` — problem, solution, user journey, alternatives
- [ ] `.gitattributes` — linguist, line endings, diff for poetry.lock
- [ ] `CHANGELOG.md` — Keep a Changelog format, [Unreleased] section
- [ ] `README.md` — badges (license, CI status, Python version), Quick Start with actual commands, links to PRD/spec/design

**Success Criteria:**
- All `.github/` files present and valid
- README Quick Start produces a working Fabric instance when followed

---

### P0-13: Test Fixtures (conftest.py)

**Checklist:**
- [ ] Pytest fixtures for SQLite in-memory test database
- [ ] Pytest fixtures for TestClient (FastAPI TestClient with async support)
- [ ] Pytest fixtures for mock Redis (fakeredis or similar)
- [ ] Pytest fixtures for mock OPA (mock responses for allow/deny/gated)
- [ ] Pytest fixtures for agent tokens (pre-created test identities per agent class)
- [ ] Pytest fixtures for admin user + session
- [ ] `tests/fixtures/mock_mcp_server.py` — in-process FastAPI app implementing MCP `/tools/list` + `/tools/call`
- [ ] Mock MCP server supports configurable latency and failure injection
- [ ] Fixture scope: `function` for test isolation, `session` for expensive fixtures

**Success Criteria:**
- `pytest tests/ --collect-only` collects all test files
- Mock MCP server responds to `/tools/list` with test tool definitions
- Mock MCP server responds to `/tools/call` with test responses
- Agent token fixture returns valid Bearer token for test requests

---

## Phase 1: Database & Models

### P1-01: MCPServer + ServerTool + ToolVersion Models

**Checklist:**
- [ ] `MCPServer` model: id (UUID PK), name, endpoint, owner_team, description, labels (JSONB), trust_level, health_status, last_health_check, registered_at, updated_at, decommissioned_at, decommission_phase, version, team_namespace
- [ ] `ServerTool` model: id (UUID PK), server_id (FK → MCPServer), tool_name, description, input_schema (JSONB), output_schema (JSONB), UNIQUE(server_id, tool_name)
- [ ] `ToolVersion` model: id (UUID PK), server_id (FK), tool_name, input_schema (JSONB), output_schema (JSONB), detected_at, is_breaking
- [ ] Relationships: MCPServer.tools → list[ServerTool], MCPServer.tool_versions → list[ToolVersion]
- [ ] Indexes: idx_servers_team, idx_servers_trust, idx_servers_health, idx_tools_server, idx_tool_versions_server
- [ ] Cascade delete: deleting a server deletes its tools and versions

**Success Criteria:**
- Models create tables in SQLite + PostgreSQL
- JSONB fields accept and query nested JSON correctly on both databases
- Relationship queries work: `server.tools` returns tool list

---

### P1-02: Capability + CapabilityMapping + CapabilityAlias Models

**Checklist:**
- [ ] `Capability` model: id (UUID PK), name (UNIQUE VARCHAR 255), domain, normalized_input_schema (JSONB), normalized_output_schema (JSONB), description, status (active/deprecated), deprecated_at, grace_period_days, created_at, created_by
- [ ] `CapabilityMapping` model: id (UUID PK), capability_id (FK), server_id (FK), tool_name, input_mapping (JSONB), output_mapping (JSONB), is_primary, routing_weight, created_at
- [ ] `CapabilityAlias` model: id (UUID PK), capability_id (FK), alias (UNIQUE VARCHAR 255), created_at
- [ ] Indexes: idx_capabilities_domain, idx_capabilities_status, idx_capabilities_name, idx_mappings_capability, idx_mappings_server, idx_aliases_alias, idx_aliases_capability

**Success Criteria:**
- `capability.mappings` returns all tool mappings
- `capability.aliases` returns all aliases
- Alias lookup: `CapabilityAlias.alias == "repo:search"` resolves to capability `code:search`

---

### P1-03: AgentClass + TrustAssignment + AgentIdentity Models

**Checklist:**
- [ ] `AgentClass` model: id (UUID PK), name (UNIQUE VARCHAR 255), description, team_namespace, created_at
- [ ] `TrustAssignment` model: id (UUID PK), agent_class_id (FK), server_id (FK), trust_level, tool_scope (JSONB, nullable), created_at, UNIQUE(agent_class_id, server_id)
- [ ] `AgentIdentity` model: id (UUID PK), name (UNIQUE), agent_class_id (FK), token_hash, token_prefix, status (active/rotating/revoked/expired), rate_limit_per_min, expires_at, grace_period_end, rotated_from_id (self-referential FK), created_at, revoked_at
- [ ] Indexes: idx_trust_class, idx_trust_unique, idx_identities_token, idx_identities_class, idx_identities_status

**Success Criteria:**
- `agent_class.trust_assignments` returns all server trust levels
- `agent_class.agent_identities` returns all tokens for this class
- Token hash stored as bcrypt, prefix as first 4 chars

---

### P1-04: AuditEvent Model

**Checklist:**
- [ ] `AuditEvent` model: id (UUID PK), event_type, actor_type, actor_id, target_type, target_id, details (JSONB), created_at
- [ ] Event types span all from spec Section 3.14: capability_request, capability_denied, server_registered, policy_change, trust_change, approval_*, server_degraded, capability_deprecated, token_*, admin_login, admin_logout, schema_change_detected, conflict_resolved
- [ ] Indexes: idx_audit_type, idx_audit_actor, idx_audit_time, idx_audit_type_time
- [ ] Audit events are append-only (no UPDATE or DELETE on audit rows)

**Success Criteria:**
- Audit event creation < 5ms
- Query by event_type + actor_id returns correct events
- JSONB details field stores and queries nested data

---

### P1-05: ApprovalRequest Model

**Checklist:**
- [ ] `ApprovalRequest` model: id (UUID PK), agent_identity_id (FK), capability_id (FK), server_id (FK), request_params (JSONB), status (pending/approved/denied/expired), approver_id (FK → AdminUser, nullable), approver_note, requested_at, resolved_at, expires_at
- [ ] Indexes: idx_approvals_status, idx_approvals_agent
- [ ] Status state machine enforced at model/service level

**Success Criteria:**
- Only pending approvals can transition to approved/denied/expired
- Expired approvals auto-deny after TTL

---

### P1-06: CapabilityPack + PackAssignment + AgentClassPack Models

**Checklist:**
- [ ] `CapabilityPack` model: id (UUID PK), name (UNIQUE), description, team_namespace, created_at
- [ ] `PackAssignment` model: id (UUID PK), pack_id (FK), capability_id (FK), UNIQUE(pack_id, capability_id)
- [ ] `AgentClassPack` model: id (UUID PK), agent_class_id (FK), pack_id (FK), UNIQUE(agent_class_id, pack_id)
- [ ] Relationships: pack.capabilities (through PackAssignment), pack.agent_classes (through AgentClassPack)

**Success Criteria:**
- `pack.capabilities` returns capability list
- `pack.agent_classes` returns class list
- Removing a pack cascades to PackAssignment + AgentClassPack

---

### P1-07: AlertRule + AlertEvent + OPAPolicyVersion + RoutingRule Models

**Checklist:**
- [ ] `AlertRule` model: id, name, alert_type, condition (JSONB), channels (JSONB), enabled
- [ ] `AlertEvent` model: id, rule_id (FK), message, details (JSONB), fired_at, acknowledged_at, acknowledged_by (FK → AdminUser)
- [ ] `OPAPolicyVersion` model: id, version, bundle_hash, deployed_at, deployed_by, rego_content
- [ ] `RoutingRule` model: id, capability_id (FK), server_id (FK), priority, condition (JSONB, nullable), created_at, created_by
- [ ] Indexes: idx_alerts_fired, idx_alerts_rule, idx_routing_rules_cap

**Success Criteria:**
- Alert rule creates alert event when condition matches
- Routing rules ordered by priority on capability queries

---

### P1-08: AdminUser Model

**Checklist:**
- [ ] `AdminUser` model: id (UUID PK), username (UNIQUE), email (UNIQUE), password_hash, role (admin/editor/viewer), team_namespace (nullable), mfa_enabled, mfa_secret (encrypted), status (active/invited/deactivated), last_login_at, created_at
- [ ] Indexes: on username, email, status
- [ ] `mfa_secret` stored encrypted at rest (Fernet or similar)

**Success Criteria:**
- Password hashed with bcrypt (salt=12)
- MFA secret encryption/decryption works
- `editor` role with team_namespace scopes queries via TenantMiddleware

---

### P1-09: Pydantic Request/Response Schemas

**Checklist:**
- [ ] Server schemas: `ServerCreate`, `ServerResponse`, `ServerInspectResponse`, `ToolResponse`, `ToolChange`
- [ ] Capability schemas: `CapabilityCreate`, `CapabilityRequest`, `BatchCapabilityRequest`, `BatchRequestItem`, `CapabilityResponse`, `BatchResponse`, `BatchResultItem`
- [ ] Agent schemas: `AgentIdentityCreate`, `AgentIdentityResponse`, `AgentConnectResponse`, `CapabilitySurfaceItem`
- [ ] Auth schemas: `LoginRequest`, `TokenResponse`, `MFASetupResponse`, `MFAVerifyRequest`, `MFARecoveryRequest`, `PasswordResetRequest`, `SetupCompleteRequest`
- [ ] Audit schemas: `AuditEventResponse`, `AuditExportRequest`
- [ ] Pack schemas: `PackCreate`, `PackResponse`, `PackAssignmentRequest`
- [ ] Policy schemas: `PolicyDecision`, `TrustAssignmentCreate`
- [ ] Error schema: `FabricError`
- [ ] Pagination schema: `PaginationMeta` (next_cursor, has_more, per_page, total)
- [ ] Webhook schemas: `WebhookRegistrationRequest`, `WebhookRegistrationResponse`, `WebhookEvent`
- [ ] All schemas include Field validators, examples, and regex patterns per spec Section 32
- [ ] Custom validators: capability name pattern `^[a-z]+:[a-z][a-z-]*$`, endpoint URL pattern, per_page max limits

**Success Criteria:**
- All schemas validate correctly with test data
- Invalid input returns 422 with field-level error details
- OpenAPI spec auto-generated from schemas is accurate

---

### P1-10: Alembic Migration Validation

**Checklist:**
- [ ] Initial migration creates all tables + indexes
- [ ] Test: `alembic upgrade head` on fresh SQLite → all 17 tables exist
- [ ] Test: `alembic upgrade head` on fresh PostgreSQL → all 17 tables exist
- [ ] Test: `alembic downgrade -1` on SQLite → tables removed cleanly
- [ ] Test: `alembic downgrade -1` on PostgreSQL → tables removed cleanly
- [ ] Test: auto-generation detects a new model field → creates migration
- [ ] Migration runs in CI (both SQLite and PostgreSQL jobs)

**Success Criteria:**
- Zero errors on upgrade/downgrade cycle
- Both database backends produce identical schema (PostgreSQL uses JSONB, SQLite uses JSON strings)

---

## Phase 2: MCP Client Layer

### P2-01: MCPClient — Server Inspection

**Checklist:**
- [ ] `api/mcp/client.py` — MCPClient class using official `mcp` Python SDK
- [ ] `async list_tools(endpoint: str, timeout: float = 5.0) -> list[ToolDefinition]`
- [ ] Calls `/tools/list` on target MCP server
- [ ] Parses response into ToolDefinition dataclass (name, description, input_schema, output_schema)
- [ ] Connection timeout: 5s with 1 retry
- [ ] Error handling: timeout → raise MCPTimeoutError, non-200 → raise MCPServerError
- [ ] Health: updates Redis server health state after each call (healthy/degraded)

**Success Criteria:**
- `list_tools("http://mock-mcp:3001")` returns tool list from mock server
- Timeout after 5s raises MCPTimeoutError
- Failed call marks server as degraded in Redis

---

### P2-02: MCPClient — Tool Execution

**Checklist:**
- [ ] `async call_tool(endpoint: str, tool_name: str, arguments: dict, timeout: float = 5.0) -> ToolResponse`
- [ ] Calls `/tools/call` on target MCP server with tool name and arguments
- [ ] Returns raw ToolResponse (result, metadata, server info)
- [ ] Connection timeout: 5s with 1 retry
- [ ] Error handling: invalid tool → MCPToolError, timeout → MCPTimeoutError

**Success Criteria:**
- `call_tool("http://mock-mcp:3001", "search_code", {"query": "test"})` returns mock response
- Invalid tool name raises MCPToolError with clear message

---

### P2-03: MCPClient — Schema Diff

**Checklist:**
- [ ] `async diff_tools(endpoint: str, previous_tools: list[ToolDefinition]) -> ToolDiff`
- [ ] Calls `/tools/list`, compares against previous tool list
- [ ] Returns: `tools_added`, `tools_removed`, `tools_changed` (with change details)
- [ ] Detects: added/removed params, changed param types, changed output schema
- [ ] Flags `is_breaking` when: required param added, param removed, output schema structure changed
- [ ] Stores results in tool_versions table

**Success Criteria:**
- Same tool list → empty diff (no changes)
- New tool added → `tools_added: ["new_tool"]`
- Param changed → `tools_changed: [{tool_name, changes: {added_params, removed_params}}]`
- Required param added → `is_breaking: true`

---

## Phase 3: Core Services

### P3-01: RegistryService — Register Server

**Checklist:**
- [ ] `async register(name, endpoint, owner_team, description, labels, team_namespace) -> MCPServer`
- [ ] Creates MCPServer record with trust_level="unreviewed", health_status="unknown"
- [ ] Calls `mcp_client.list_tools(endpoint)` to auto-inspect
- [ ] Creates ServerTool records for each discovered tool
- [ ] Auto-suggests trust level: if all tools are read-only via input schema analysis → "trusted", otherwise "unreviewed"
- [ ] Returns full server with tools
- [ ] Logs `audit_event(server_registered)`
- [ ] Invalid endpoint → raises ServerUnreachableError
- [ ] Duplicate endpoint → raises DuplicateServerError

**Success Criteria:**
- Registered server appears in GET /servers with tools
- Auto-suggested trust level is "trusted" for read-only servers
- Duplicate endpoint returns 409
- Unreachable endpoint returns 400 with clear error

---

### P3-02: RegistryService — Inspect Server

**Checklist:**
- [ ] `async inspect(server_id: UUID) -> ServerInspectResponse`
- [ ] Calls `mcp_client.diff_tools(endpoint, previous_tools)`
- [ ] Stores new tools in server_tools, new versions in tool_versions
- [ ] Returns: server with tools_added, tools_removed, tools_changed lists
- [ ] Updates `server.updated_at` and health status
- [ ] Logs `audit_event(schema_change_detected)` if changes found
- [ ] Breaking changes trigger alert (Celery task: health_check_server discovered breaking change)

**Success Criteria:**
- Re-inspect unchanged server → empty added/removed/changed
- Re-inspect server with new tool → tools_added = [new_tool]
- Breaking change → is_breaking=true on ToolVersion, alert fired

---

### P3-03: RegistryService — List + Get Servers

**Checklist:**
- [ ] `async list_servers(team, trust, health, cursor, per_page) -> PaginatedServers`
- [ ] Filter by team_namespace, trust_level, health_status
- [ ] Cursor-based pagination (by created_at)
- [ ] Order by created_at DESC
- [ ] `async get_server(server_id: UUID) -> ServerDetail`
- [ ] Returns server with tools, routing_rules, trust_assignments, decommission timeline

**Success Criteria:**
- Empty filter returns all servers
- Team filter returns only servers in that namespace
- Cursor pagination: next_cursor present when more pages exist
- Decommissioned servers included by default (filterable)

---

### P3-04: RegistryService — Decommission Server

**Checklist:**
- [ ] `async decommission(server_id, phase, replacement_server_id) -> DecommissionResult`
- [ ] Phase validation: grace_period → migration → sunset (must proceed in order)
- [ ] Returns dependency report: which capabilities this server provides, which agent classes depend on it, request volume stats
- [ ] Phase "grace_period": sets decommissioned_at, adds deprecation header to responses from this server
- [ ] Phase "migration": if replacement_server_id provided, redirects capability mappings to replacement
- [ ] Phase "sunset": removes server from capability mappings, marks as fully decommissioned
- [ ] Logs `audit_event(server_decommissioned)` with phase details
- [ ] Row-level lock (SELECT FOR UPDATE) to prevent double decommission

**Success Criteria:**
- Grace period: server still routes but returns deprecation header
- Migration: capability requests redirected to replacement server
- Sunset: server removed from routing candidates
- Double decommission prevented (second call returns 409)

---

### P3-05: CapabilityService — Create + Map

**Checklist:**
- [ ] `async create(name, domain, normalized_input_schema, normalized_output_schema, description) -> Capability`
- [ ] Validates name follows `domain:action` convention
- [ ] `async map_tool(capability_id, server_id, tool_name, input_mapping, output_mapping, is_primary) -> CapabilityMapping`
- [ ] Validates server_id + tool_name exist
- [ ] Creates mapping with input/output parameter translation config
- [ ] After mapping: runs `detect_conflicts` — if same capability mapped to >1 server, flags conflict
- [ ] Logs `audit_event(capability_created)` or `audit_event(capability_mapped)`

**Success Criteria:**
- Create capability with valid name → success
- Create with invalid name pattern → 422
- Map tool → mapping appears in capability.mappings
- Map second server to same capability → conflict flag raised

---

### P3-06: CapabilityService — Resolve + Conflicts + List

**Checklist:**
- [ ] `async resolve(name: str) -> Capability`
- [ ] Exact match on name → return capability
- [ ] No exact match → try aliases → return capability with alias info
- [ ] Neither → raise CapabilityNotFoundError with suggestion (closest match)
- [ ] `async detect_conflicts(capability_id) -> list[Conflict]`
- [ ] Find all mappings for this capability, group by server
- [ ] Return Conflict objects: server A vs server B, tool differences
- [ ] `async list_capabilities(domain, status, offset, per_page) -> PaginatedCapabilities`

**Success Criteria:**
- `resolve("code:search")` returns capability
- `resolve("repo:find")` returns capability if alias exists
- `resolve("nonexistent")` raises error with suggestion "Did you mean 'code:search'?"
- Conflict detection returns side-by-side tool comparison

---

### P3-07: CapabilityService — Deprecate + Aliases

**Checklist:**
- [ ] `async deprecate(capability_id, grace_period_days, migration_guidance) -> Capability`
- [ ] Sets status="deprecated", deprecated_at=now, grace_period_days, stores guidance
- [ ] Auto-removes capability from all packs (with audit log)
- [ ] During grace period: capability still routes, but returns deprecation warning in response
- [ ] After grace period: capability returns `{status: "deprecated", error: "capability_deprecated", retired_on: ..., guidance: "..."}`
- [ ] `async add_alias(capability_id, alias) -> CapabilityAlias`
- [ ] Validates alias follows naming convention
- [ ] Validates alias is unique (no capability or other alias uses it)

**Success Criteria:**
- Deprecated capability still works during grace period (returns warning)
- Deprecated capability returns 410 Gone after grace period
- Auto-removal from packs verified
- Alias resolves to parent capability

---

### P3-08: PolicyService — OPA Evaluation

**Checklist:**
- [ ] `async evaluate(agent_class, server_id, capability, team_namespace) -> PolicyDecision`
- [ ] Sends input to OPA: `{agent_class, server_trust_level, capability, agent_namespace, server_namespace}`
- [ ] OPA returns: `{allow, approval_required, cross_team_allowed, trust_level}`
- [ ] Caches result in Redis (key: `fcp:opa:{agent_class}:{server_id}:{capability}`, TTL: 60s)
- [ ] Cache hit → skip OPA call
- [ ] OPA unreachable → deny by default (secure fail-closed)
- [ ] Returns PolicyDecision dataclass
- [ ] `async deploy_bundle(rego_content, deployed_by) -> PolicyBundleVersion`
- [ ] Pushes to OPA bundle API
- [ ] Stores version in opa_policy_versions table
- [ ] Invalidates all OPA cache keys (Redis SCAN + DELETE `fcp:opa:*`)

**Success Criteria:**
- Agent with trusted server → `allow=true, approval_required=false`
- Agent with approval-gated server → `allow=true, approval_required=true`
- Agent with restricted server (lower class) → `allow=false`
- OPA down → all requests denied with 503
- Policy deploy invalidates cache

---

### P3-09: PolicyService — Agent Classes + Trust

**Checklist:**
- [ ] `async create_agent_class(name, description, team_namespace) -> AgentClass`
- [ ] `async set_trust(class_id, server_id, trust_level, tool_scope) -> TrustAssignment`
- [ ] Validates trust_level: one of trusted/restricted/approval-gated
- [ ] tool_scope: null = all tools, ["tool_a"] = specific tools
- [ ] `async list_agent_classes(team) -> list[AgentClass]`
- [ ] `async get_agent_class(class_id) -> AgentClassDetail`
- [ ] Returns class with trust_assignments, assigned packs, agent count

**Success Criteria:**
- Create class → appears in list
- Set trust → trust assignment visible in class detail
- tool_scope: only listed tools are accessible at that trust level

---

### P3-10: RoutingService — Execute Single Request

**Checklist:**
- [ ] `async execute(capability_name, params, agent_identity) -> RouteResult`
- [ ] Step 1: Resolve capability → CapabilityService.resolve(capability_name)
- [ ] Step 2: Get candidate servers → query capability_mappings + filter by health_status != unhealthy + decommissioned_at IS NULL
- [ ] Step 3: Apply routing rules → ORDER BY priority, apply condition match if provided
- [ ] Step 4: Evaluate policy → PolicyService.evaluate() for each candidate, filter to allowed only
- [ ] Step 5: Handle denial → if all denied, return 403 with `access_denied` error
- [ ] Step 6: Handle approval-gated → if all gated, return 202 with `approval_pending` + create approval request
- [ ] Step 7: Rank candidates → score = match_quality × routing_weight, tiebreaker = latency (Redis health state)
- [ ] Step 8: Call MCP server → mcp_client.call_tool(selected_server, tool_name, translated_params)
- [ ] Step 9: Fallback on failure → mark server degraded, try next candidate, log fallback
- [ ] Step 10: Normalize response → apply output_mapping from capability_mapping entry
- [ ] Step 11: Audit → log capability_request event with routing detail
- [ ] Step 12: Return RouteResult with data, server, routing_reason, latency, fallback_used

**Success Criteria:**
- Valid request routes to correct server and returns normalized response
- All candidates denied → 403 with clear reason
- All gated → 202 with approval_id
- Server timeout → fallback to next candidate → response with fallback_used=true
- Audit event captured with full routing detail

---

### P3-11: RoutingService — Execute Batch Request

**Checklist:**
- [ ] `async execute_batch(requests: list[BatchRequestItem], agent_identity) -> BatchResult`
- [ ] Validates requests: min 1, max 10 items
- [ ] Executes all requests in parallel via `asyncio.gather()`
- [ ] Each request goes through the full single-request pipeline independently
- [ ] Mixed results handled: some success, some failure, some fallback
- [ ] Returns BatchResult with per-item status, data, server, error, latency
- [ ] Batch timeout: 30s total (configurable)

**Success Criteria:**
- 3 valid requests → 3 parallel responses in ~max(individual_latencies)
- Mixed results: success + failure + fallback all returned correctly
- Exceeding batch limit (11 items) → 422

---

### P3-12: AuditService — Log + Query + Export

**Checklist:**
- [ ] `async log_event(event_type, actor_type, actor_id, target_type, target_id, details) -> AuditEvent`
- [ ] Append-only: INSERT only, no UPDATE or DELETE on audit_events
- [ ] `async query(event_type, actor_type, actor_id, target_type, from_date, to_date, cursor, per_page) -> PaginatedAuditEvents`
- [ ] Cursor-based pagination (by created_at DESC)
- [ ] `async create_export(from_date, to_date, event_types, agent_classes, format) -> ExportTask`
- [ ] Dispatches Celery task `generate_audit_export`
- [ ] Returns export_id for status polling

**Success Criteria:**
- Log event → queryable by event_type + actor_id
- Cursor pagination works for large datasets
- Export task created, Celery worker picks it up

---

### P3-13: ApprovalService — Create + List + Approve/Deny

**Checklist:**
- [ ] `async create_request(agent_identity_id, capability_id, server_id, params) -> ApprovalRequest`
- [ ] Sets status="pending", expires_at = now + 1 hour, requested_at = now
- [ ] Dispatches Celery task `notify_approval_request` (email/Slack/webhook)
- [ ] `async list_pending(agent_class, capability, cursor, per_page) -> PaginatedApprovals`
- [ ] `async approve(approval_id, approver_id, note) -> ApprovalRequest`
- [ ] Validates status is "pending" → sets status="approved", resolved_at=now, approver info
- [ ] Routes the original capability request (re-executes RoutingService with original params)
- [ ] Returns routing result to the agent
- [ ] `async deny(approval_id, approver_id, note) -> ApprovalRequest`
- [ ] Sets status="denied", resolved_at=now, returns 403 to agent with reason
- [ ] `async get_status(approval_id) -> ApprovalRequest` — for agent polling
- [ ] Expired approvals: Celery task or query filter excludes expired from list

**Success Criteria:**
- Create → approval appears in pending list
- Approve → capability request routed, agent gets result
- Deny → agent gets 403 with approver note
- Poll status → agent sees pending/approved/denied
- Expired approvals → auto-deny after TTL

---

### P3-14: PackService — Create + Manage

**Checklist:**
- [ ] `async create(name, description, team_namespace) -> CapabilityPack`
- [ ] `async assign_capabilities(pack_id, capability_ids) -> PackAssignment`
- [ ] Bulk assignment: add all capability_ids to pack
- [ ] Validates all capability_ids exist
- [ ] `async remove_capability(pack_id, capability_id)` — remove single capability
- [ ] `async assign_to_class(pack_id, class_id)` — assign pack to agent class
- [ ] Validates class exists, pack exists
- [ ] `async get_packs(team, offset, per_page) -> PaginatedPacks`
- [ ] `async get_pack(pack_id) -> PackDetail` — with capabilities list + assigned classes
- [ ] `async clone_pack(pack_id, new_name) -> CapabilityPack`
- [ ] Copies all capability assignments to new pack

**Success Criteria:**
- Create pack → appears in list
- Assign capabilities → pack.capabilities returns correct list
- Assign to class → class sees pack's capabilities in capability surface
- Clone → new pack has identical capabilities

---

### P3-15: AlertService — Rules + Fire + Acknowledge

**Checklist:**
- [ ] `async create_rule(name, alert_type, condition, channels) -> AlertRule`
- [ ] `async evaluate_thresholds() -> list[AlertEvent]`
- [ ] Called by Celery beat every 60s
- [ ] Checks all enabled rules against current metrics (Redis counters, DB queries)
- [ ] Condition examples: `{"metric": "fabric_requests_total{status='error'}", "threshold": 0.01, "window": 300}`
- [ ] `async fire_alert(rule_id, message, details) -> AlertEvent`
- [ ] Dispatches Celery task `deliver_alert` for each configured channel
- [ ] `async acknowledge(alert_id, user_id)` — sets acknowledged_at, acknowledged_by
- [ ] `async list_alerts(alert_type, from_date, to_date, acknowledged, cursor) -> PaginatedAlerts`

**Success Criteria:**
- Rule with error rate >1% fires when threshold crossed
- Alert delivered to configured channels
- Acknowledge marks alert, visible in history

---

### P3-16: AuthService — Agent Token Lifecycle

**Checklist:**
- [ ] `async create_identity(name, class_id, rate_limit_per_min, expires_in_days) -> AgentIdentity + token`
- [ ] Generates random token: `fcp_` + 48 random chars
- [ ] Stores bcrypt(token, salt=12) hash + first 4 chars as prefix
- [ ] Returns FULL token ONCE in response (never stored, never logged)
- [ ] Warning message: "Save this token. It will not be shown again."
- [ ] `async validate_token(token: str) -> AgentIdentity`
- [ ] Hashes incoming token, looks up by hash in DB (hot path)
- [ ] Redis cache: key `fcp:auth:{token_hash}`, TTL 5 min
- [ ] Cache hit → skip DB query
- [ ] Checks: status=active, not expired, not revoked
- [ ] Returns AgentIdentity with agent_class, team_namespace
- [ ] `async rotate_token(identity_id, grace_period_hours) -> AgentIdentity + new_token`
- [ ] Generates new token, sets old token to status="rotating", grace_period_end
- [ ] Both old and new tokens valid during grace period
- [ ] `async revoke_token(identity_id, reason) -> AgentIdentity`
- [ ] Sets status="revoked", revoked_at=now
- [ ] Deletes Redis auth cache entry
- [ ] Logs `audit_event(token_revoked)`
- [ ] `async get_capability_surface(identity_id) -> CapabilitySurface`
- [ ] Resolves: agent class → trust assignments + capability packs → merged capability list
- [ ] Each capability: name, trust_level, requires_approval, deprecated status
- [ ] Redis cache: key `fcp:surface:{identity_id}`, TTL 5 min
- [ ] Invalidate on: token rotation, trust change, pack change, capability deprecation

**Success Criteria:**
- Create token → full token returned once, hash stored
- Validate valid token → returns identity
- Validate revoked token → 401
- Validate expired token → 401 with token_expired
- Rotate → both tokens work during grace, old token rejected after
- Capability surface reflects all trust assignments and pack memberships

---

### P3-17: AuthService — Admin Authentication

**Checklist:**
- [ ] `async login(username, password) -> LoginResult`
- [ ] Looks up user by username → validate bcrypt password
- [ ] Check: status=active, not deactivated
- [ ] Check: not locked out (5 failed attempts → 15 min lockout)
- [ ] If MFA enabled: return `requires_mfa=True, mfa_token=<temporary token>`
- [ ] If MFA disabled: create session, return JWT
- [ ] Failed login: increment failed_attempts counter (Redis, TTL 15 min). At 5 → lock account.
- [ ] `async verify_mfa(mfa_token, totp_code) -> LoginResult`
- [ ] Validates TOTP code against stored secret
- [ ] Creates session, returns JWT
- [ ] `async create_session(user_id) -> Session`
- [ ] Generates JWT: claims {user_id, role, team_namespace, exp=8h, iat=now}
- [ ] Stores in Redis: key `fcp:session:{jti}`, TTL 8h
- [ ] Sliding expiration: TTL resets on activity (update Redis TTL on each validated request)
- [ ] Max 3 concurrent sessions per user (enforced at session creation)
- [ ] `async validate_session(token) -> AdminUser`
- [ ] Validates JWT signature + expiry
- [ ] Checks Redis: key must exist (handles logout/invalidation)
- [ ] `async logout(session_token)` — deletes Redis key

**Success Criteria:**
- Valid credentials → JWT returned
- MFA enabled → requires MFA step
- Wrong password 5x → account locked for 15 min
- Logout → session immediately invalid
- Expired JWT → 401
- Session limit: 4th login fails

---

### P3-18: AuthService — MFA + Password + Invite

**Checklist:**
- [ ] `async setup_mfa(user_id) -> MFASetupResponse`
- [ ] Generates TOTP secret (pyotp.random_base32())
- [ ] Stores encrypted secret (Fernet with app secret key)
- [ ] Returns: secret, QR code URI (otpauth://), manual entry key
- [ ] `async verify_mfa_setup(user_id, totp_code) -> MFASetupResult`
- [ ] Validates TOTP against unconfirmed secret
- [ ] On success: enables MFA, generates 8 backup codes
- [ ] Backup codes: 8 random 8-char codes, stored as bcrypt(code) hashes
- [ ] Returns backup codes ONCE with warning
- [ ] `async recover_mfa(backup_code) -> MFARecoveryResult`
- [ ] Looks up by backup code hash → bcrypt verify
- [ ] On success: marks code as used, disables MFA, returns temporary session
- [ ] After all 8 used: MFA disabled, user must re-enable
- [ ] `async reset_mfa_by_admin(admin_id, target_user_id)`
- [ ] Admin action: disables target user's MFA, invalidates backup codes
- [ ] Logs `audit_event(admin_mfa_reset)` with both admin and target IDs
- [ ] `async reset_password(email) -> PasswordResetResult`
- [ ] Generates reset token (JWT, 1h expiry), dispatches email via Celery
- [ ] `async complete_password_reset(reset_token, new_password)`
- [ ] Validates token, validates password complexity (12 chars, upper, lower, digit, special)
- [ ] Checks password history (last 5 cannot be reused)
- [ ] `async invite_user(email, role, team_namespace) -> AdminUser`
- [ ] Creates user with status="invited", generates setup token (JWT, 24h expiry)
- [ ] Dispatches email with setup link via Celery
- [ ] `async complete_setup(setup_token, username, password) -> AdminUser`
- [ ] Validates token, sets username + password, status → "active"

**Success Criteria:**
- MFA setup → QR code displayed, verify with TOTP app
- MFA recovery → backup code works, MFA disabled
- All 8 backup codes used → MFA disabled, must re-enable
- Admin resets another user's MFA → audit logged
- Password reset email delivered
- Password history enforced (reuse rejected)
- Invite → setup → active user lifecycle complete

---

### P3-19: AuthService — Password + MFA Edge Cases

**Checklist:**
- [ ] Password complexity: min 12 chars, 1 uppercase, 1 lowercase, 1 digit, 1 special
- [ ] Account lockout: 5 failed attempts → 15 min lock (Redis key `fcp:lockout:{user_id}`, TTL 15 min)
- [ ] Lockout counter: Redis INCR `fcp:failed:{user_id}`, TTL 15 min
- [ ] Successful login clears failed counter
- [ ] Admin can unlock account (delete Redis lockout key)
- [ ] Password history: store last 5 bcrypt hashes per user, PREVENT reuse
- [ ] Password expiry: advisory warning at 90 days (not enforced in v0.1.0)
- [ ] Concurrent session enforcement: count Redis keys matching `fcp:session:{user_id}:*`, max 3
- [ ] First admin auto-creation: if no admin users exist, first user created via env var `FABRIC_ADMIN_EMAIL` + `FABRIC_ADMIN_PASSWORD` gets admin role

**Success Criteria:**
- Weak password rejected with specific feedback
- 5 wrong attempts → locked for 15 min
- Lockout auto-expires after 15 min
- Previous password reuse rejected
- First admin auto-created on fresh install

---

## Phase 4: Middleware

### P4-01: RequestID Middleware

**Checklist:**
- [ ] Generates UUID for every request
- [ ] Sets `request.state.request_id`
- [ ] Sets `Fabric-Request-Id` response header
- [ ] Binds to structlog context for all log entries in this request

**Success Criteria:**
- Every response includes `Fabric-Request-Id: uuid` header
- All log entries for a request share the same request_id

---

### P4-02: Tracing Middleware

**Checklist:**
- [ ] Creates OpenTelemetry span "http_request" for every request
- [ ] Span attributes: http.method, http.url, http.status_code, request_id, agent_id (if authenticated)
- [ ] Propagates trace context to downstream calls (MCP server calls)
- [ ] Span ends after response is sent

**Success Criteria:**
- Every request creates a trace span
- Span includes method + url + status + duration
- Traces exported to configured backend (Tempo/Jaeger)

---

### P4-03: Auth Middleware

**Checklist:**
- [ ] Extracts token from `Authorization: Bearer <token>` header
- [ ] Agent endpoints (`/v1/capability/*`, `/v1/auth/connect`, `/v1/capabilities/available`): validates agent token
- [ ] Admin endpoints (`/v1/admin/*`): validates admin JWT session
- [ ] Public endpoints (`/v1/health`, `/v1/health/ready`, `/v1/health/live`, `/v1/metrics`, `/docs`, `/openapi.json`): no auth required
- [ ] Sets `request.state.agent_identity` or `request.state.admin_user`
- [ ] Invalid token → 401 with `invalid_token` error
- [ ] Expired token → 401 with `token_expired` error
- [ ] Rate limited token → 429 (RateLimit middleware handles this — auth just passes through)

**Success Criteria:**
- Valid agent token passes through to route handler
- Invalid token returns 401
- Admin session valid returns admin user
- Health endpoints accessible without auth

---

### P4-04: Tenant Middleware

**Checklist:**
- [ ] Runs after Auth middleware
- [ ] Reads `request.state.agent_identity.agent_class.team_namespace`
- [ ] Sets `request.state.tenant_namespace` as filter for all DB queries
- [ ] Admin users with `editor` role: scoped to their `team_namespace`
- [ ] Admin users with `admin` role: no scope (all teams)
- [ ] All service layer queries apply `WHERE team_namespace = request.state.tenant_namespace` filter
- [ ] Cross-team access: OPA policy controls whether agents can access servers in other namespaces

**Success Criteria:**
- Platform team agent cannot see security team servers
- Editor admin cannot modify servers outside their team
- Global admin sees all servers

---

### P4-05: RateLimit Middleware

**Checklist:**
- [ ] Runs after Auth middleware
- [ ] Key: `fcp:ratelimit:{agent_identity_id}:{minute_window}`
- [ ] Redis INCR on each request, EXPIRE after window
- [ ] If count > agent_identity.rate_limit_per_min → 429
- [ ] Response headers: `Retry-After: <seconds>`, `X-RateLimit-Limit: <limit>`, `X-RateLimit-Remaining: <remaining>`
- [ ] Redis unavailable: fail-open (allow request, log warning)
- [ ] Rate limit bypass for admin users (configurable)

**Success Criteria:**
- Agent at limit → 429 with Retry-After
- Headers present on all capability requests
- Redis down → requests still allowed through

---

### P4-06: Audit Middleware

**Checklist:**
- [ ] Runs as FastAPI background task (after response sent — zero latency impact)
- [ ] Captures: method, path, status_code, agent_id, request_id, latency_ms
- [ ] Does NOT capture: request bodies (contain params), response bodies (contain data)
- [ ] Only logs for authenticated requests (agent + admin)
- [ ] Does not log health/metric endpoints (noise)

**Success Criteria:**
- Audit event created for every capability request (async, non-blocking)
- Health endpoint calls NOT logged
- Audit middleware failure does not affect response (fail-open)

---

### P4-07: CORS Middleware

**Checklist:**
- [ ] Allow origins: configurable via `CORS_ORIGINS` env var (default: `http://localhost:3000`)
- [ ] Allow methods: GET, POST, PUT, PATCH, DELETE, OPTIONS
- [ ] Allow headers: Authorization, Content-Type, Accept
- [ ] Expose headers: Fabric-Request-Id, Fabric-Routing-Server, Fabric-API-Version
- [ ] Max age: 3600 seconds

**Success Criteria:**
- Admin UI can call API from different origin
- Preflight OPTIONS returns correct headers
- Invalid origin rejected

---

### P4-08: API Version Middleware

**Checklist:**
- [ ] Parses `Accept: application/vnd.fabric.v1+json` header
- [ ] Extracts version: `v1`, `v2`, etc.
- [ ] Sets `request.state.api_version`
- [ ] No version header → defaults to latest stable (v1) + adds warning header
- [ ] Response: includes `Fabric-API-Version: v1` header
- [ ] Response: includes `Content-Type: application/vnd.fabric.v1+json`
- [ ] Unknown version → 406 Not Acceptable with supported versions list

**Success Criteria:**
- Request with version header → response confirms version
- No version → defaults to v1 with warning header
- Unknown version → 406

---

## Phase 5: API Routes

### P5-01: Registry Routes — Server CRUD

**Checklist:**
- [ ] `POST /v1/servers` — create server, auto-inspect tools, return ServerResponse
- [ ] `GET /v1/servers` — list with filters (team, trust, health, search), cursor pagination
- [ ] `GET /v1/servers/{id}` — get server detail with tools + trust + routing rules
- [ ] `POST /v1/servers/{id}/inspect` — re-inspect + schema diff
- [ ] `POST /v1/servers/{id}/decommission` — phased decommission with body `{phase, replacement_server_id}`
- [ ] Auth: admin or editor (team-scoped)
- [ ] Request validation via Pydantic schemas

**Success Criteria:**
- Create → 201 with auto-discovered tools
- List → paginated with filters working
- Get → full detail with all relationships
- Inspect → diff response
- Decommission → phase validation + dependency report

---

### P5-02: Capability Routes

**Checklist:**
- [ ] `POST /v1/capabilities` — create capability
- [ ] `GET /v1/capabilities` — list with filters (domain, status, search), offset pagination
- [ ] `GET /v1/capabilities/{id}` — capability detail with mappings + aliases
- [ ] `POST /v1/capabilities/{id}/mappings` — map tool to capability
- [ ] `POST /v1/capabilities/{id}/deprecate` — deprecate with grace period
- [ ] `POST /v1/capabilities/{id}/aliases` — add alias
- [ ] `GET /v1/capabilities/available` — agent's capability surface (full schemas, requires agent auth)
- [ ] Auth: admin or editor for write, agent token for `available` endpoint

**Success Criteria:**
- Create capability with valid name → 201
- Map tool → mapping visible in capability detail
- Deprecate → status changes, auto-remove from packs
- `available` endpoint returns agent's scoped capabilities with full schemas

---

### P5-03: Routing Routes

**Checklist:**
- [ ] `POST /v1/capability/request` — single capability request
- [ ] `POST /v1/capability/batch` — batch capability request (1-10 items)
- [ ] `GET /v1/capability/status/{request_id}` — poll approval status (for approval-gated requests)
- [ ] Auth: agent token required
- [ ] Response includes routing metadata: server, routing_reason, fallback_used, latency_ms

**Success Criteria:**
- Single request → 200 with normalized response + routing metadata
- Batch request → parallel execution, mixed results supported
- Status poll → returns pending/approved/denied
- Denied request → 403 with policy reason
- Approval-gated → 202 with approval_id

---

### P5-04: Policy Routes

**Checklist:**
- [ ] `POST /v1/agent-classes` — create agent class
- [ ] `GET /v1/agent-classes` — list with team filter
- [ ] `GET /v1/agent-classes/{id}` — class detail with trust assignments + packs + agent count
- [ ] `POST /v1/agent-classes/{id}/trust` — set trust assignment
- [ ] `POST /v1/admin/policies/bundle` — deploy OPA policy bundle
- [ ] `POST /v1/routing-rules` — create routing rule (priority-based)
- [ ] `GET /v1/routing-rules?capability_id=X` — list routing rules
- [ ] `DELETE /v1/routing-rules/{id}` — delete routing rule
- [ ] Auth: admin or editor (team-scoped)

**Success Criteria:**
- Create class → 201
- Set trust → trust assignment visible in class detail
- Deploy bundle → OPA loads new policies, cache invalidated
- Routing rule → appears in capability detail

---

### P5-05: Approval Routes

**Checklist:**
- [ ] `GET /v1/approvals` — list with filters (status, agent_class, capability), cursor pagination
- [ ] `GET /v1/approvals/{id}` — approval detail with full context
- [ ] `POST /v1/approvals/{id}/approve` — approve with body `{note}`
- [ ] `POST /v1/approvals/{id}/deny` — deny with body `{note}`
- [ ] Auth: admin or editor for approve/deny, agent for status poll

**Success Criteria:**
- Approve → request routed, agent gets result
- Deny → agent gets 403 with reason
- Bulk approval supported (select multiple → approve all)

---

### P5-06: Audit Routes

**Checklist:**
- [ ] `GET /v1/audit` — query with filters (event_type, actor_type, actor_id, target_type, from_date, to_date), cursor pagination
- [ ] `POST /v1/audit/export` — create export task with body `{from_date, to_date, event_types, agent_classes, format}`
- [ ] `GET /v1/audit/export/{export_id}` — poll export status
- [ ] `GET /v1/audit/export/{export_id}/download` — download exported file
- [ ] Auth: admin or editor for export, viewer for read-only query

**Success Criteria:**
- Query returns filtered events with pagination
- Export creates Celery task, returns export_id
- Poll returns progress (pending/generating/complete/failed)
- Download returns JSON or CSV file

---

### P5-07: Pack Routes

**Checklist:**
- [ ] `POST /v1/packs` — create pack
- [ ] `GET /v1/packs` — list with team filter
- [ ] `GET /v1/packs/{id}` — pack detail with capabilities + assigned classes + usage stats
- [ ] `POST /v1/packs/{id}/capabilities` — bulk assign capabilities (body: `{capability_ids: [...]}`)
- [ ] `DELETE /v1/packs/{id}/capabilities/{capability_id}` — remove capability from pack
- [ ] `POST /v1/packs/{id}/classes` — assign to agent class (body: `{class_id}`)
- [ ] `DELETE /v1/packs/{id}/classes/{class_id}` — unassign from class
- [ ] `POST /v1/packs/{id}/clone` — clone with body `{new_name}`
- [ ] `DELETE /v1/packs/{id}` — delete pack (cascades to assignments)
- [ ] Auth: admin or editor (team-scoped)

**Success Criteria:**
- Create pack → 201
- Assign capabilities → pack detail shows capabilities
- Assign to class → agent's capability surface includes pack capabilities
- Clone → new pack with identical capabilities
- Usage stats: shows which agents/classes use this pack

---

### P5-08: Auth Routes

**Checklist:**
- [ ] `POST /v1/auth/connect` — agent connect (returns agent_id, agent_class, capability_surface)
- [ ] `POST /v1/auth/login` — admin login (returns JWT or requires_mfa flag)
- [ ] `POST /v1/auth/mfa/verify` — verify MFA code + create session
- [ ] `POST /v1/auth/mfa/setup` — initiate MFA setup (returns QR code + secret)
- [ ] `POST /v1/auth/mfa/verify-setup` — verify setup with TOTP code (returns backup codes)
- [ ] `POST /v1/auth/mfa/recover` — recover MFA with backup code
- [ ] `POST /v1/auth/password-reset` — request password reset (body: `{email}`)
- [ ] `POST /v1/auth/password-reset/complete` — complete reset (body: `{token, new_password}`)
- [ ] `POST /v1/auth/setup` — complete account setup from invite (body: `{token, username, password}`)
- [ ] `POST /v1/auth/logout` — admin logout

**Success Criteria:**
- Agent connect → returns capability surface scoped to agent class
- Admin login → returns JWT for non-MFA, requires_mfa flag for MFA
- MFA verify → creates session, returns JWT
- MFA setup → QR code scannable by authenticator app
- Password reset → email delivered (via Celery)
- Account setup → user activated after invite link

---

### P5-09: Admin Routes

**Checklist:**
- [ ] `POST /v1/admin/users/invite` — invite admin user (body: `{email, role, team_namespace}`)
- [ ] `GET /v1/admin/users` — list admin users
- [ ] `GET /v1/admin/users/{id}` — user detail
- [ ] `PATCH /v1/admin/users/{id}` — update role or team scope
- [ ] `POST /v1/admin/users/{id}/deactivate` — deactivate user (revokes sessions)
- [ ] `POST /v1/admin/users/{id}/unlock` — unlock account (clear lockout)
- [ ] `POST /v1/admin/users/{id}/reset-mfa` — admin resets another user's MFA
- [ ] `POST /v1/admin/agent-identities` — create agent identity (returns token ONCE)
- [ ] `GET /v1/admin/agent-identities` — list agent identities
- [ ] `POST /v1/admin/agent-identities/{id}/rotate` — rotate token with grace period
- [ ] `POST /v1/admin/agent-identities/{id}/revoke` — revoke token
- [ ] `GET /v1/admin/migration/status` — migration tracking (always returns empty for v0.1.0, full in v0.2.0)
- [ ] Auth: admin role required for user management, admin or editor for agent identity management

**Success Criteria:**
- Invite user → user gets email, completes setup
- Deactivate → sessions revoked, user cannot log in
- Create agent identity → token returned once, hash stored
- Rotate → both tokens work during grace period
- Revoke → token immediately invalid

---

### P5-10: Health + Metrics Routes

**Checklist:**
- [ ] `GET /v1/health` — full health check: status (healthy/degraded/shutting_down), version, uptime, checks (database, redis, opa)
- [ ] `GET /v1/health/ready` — readiness probe: returns 200 or 503 (shutting_down). Kubernetes readinessProbe
- [ ] `GET /v1/health/live` — liveness probe: returns 200 if process alive. Kubernetes livenessProbe
- [ ] `GET /v1/metrics` — Prometheus metrics endpoint (text format)
- [ ] Auth: none (public endpoints)
- [ ] Health check logic: DB ping (SELECT 1), Redis ping (PING), OPA ping (/v1/data)

**Success Criteria:**
- All healthy → `/health` returns status=healthy with all checks "connected"
- DB down → status=degraded, database=disconnected
- `/ready` returns 503 during graceful shutdown
- `/live` returns 200 as long as process is running
- `/metrics` returns all 15 Prometheus metric families

---

### P5-11: Webhook Routes

**Checklist:**
- [ ] `POST /v1/agents/{agent_id}/webhooks` — register webhook (body: `{url, events}`)
- [ ] `GET /v1/agents/{agent_id}/webhooks` — list webhooks
- [ ] `DELETE /v1/agents/{agent_id}/webhooks/{webhook_id}` — remove webhook
- [ ] `POST /v1/agents/{agent_id}/webhooks/{webhook_id}/reactivate` — reactivate degraded webhook
- [ ] Generates webhook_secret (whsec_xxx) on registration — returned once
- [ ] HMAC-SHA256 signature on delivery: `Fabric-Webhook-Signature: sha256=<hmac>`
- [ ] Auth: agent token for own webhooks, admin for management

**Success Criteria:**
- Register → returns webhook_secret + events
- Delivery: POST to webhook URL with signature header
- Retry: 3 attempts with exponential backoff (1s, 5s, 25s)
- After 3 failures → webhook marked degraded
- Reactivate → webhook active again

---

## Phase 6: Celery Tasks

### P6-01: Celery App + Worker Configuration

**Checklist:**
- [ ] `api/tasks.py` — Celery app with Redis broker + result backend
- [ ] Task base class with auto-retry on connection errors
- [ ] Task result serializer: JSON
- [ ] Worker concurrency: 4 per worker process
- [ ] Celery Beat schedule defined in config per spec Section 6.2
- [ ] Worker runs: `celery -A api.tasks worker --loglevel=info`
- [ ] Beat runs: `celery -A api.tasks beat --loglevel=info`

**Success Criteria:**
- Worker picks up tasks from Redis queue
- Beat scheduler fires on configured intervals
- Failed tasks retry with exponential backoff

---

### P6-02: Health Check Tasks

**Checklist:**
- [ ] `health_check_server(server_id)` — pings /tools/list, updates health state in Redis
- [ ] On success: sets `fcp:health:{server_id}` = "healthy", TTL 60s
- [ ] On timeout: sets to "degraded" or increments degradation counter
- [ ] On repeated failure (>3 consecutive): sets to "unhealthy", fires alert
- [ ] `health_check_all_servers()` — iterates all non-decommissioned servers, calls health_check_server
- [ ] Scheduled: every 30 seconds (Celery beat)
- [ ] Rate limited: max 10 concurrent health checks

**Success Criteria:**
- Healthy server → health status "healthy" in Redis
- Timeout → "degraded" after 1 failure, "unhealthy" after 3
- Alert fires on unhealthy transition

---

### P6-03: Notification + Alert Tasks

**Checklist:**
- [ ] `notify_approval_request(approval_id)` — sends notification via configured channels
- [ ] Email: SMTP via config, Slack: webhook URL, generic: webhook POST
- [ ] Retry: 3 attempts with 60s delay
- [ ] `deliver_alert(alert_event_id)` — delivers alert via configured channels
- [ ] Same channel support as notification
- [ ] `cleanup_audit_logs()` — deletes audit events older than AUDIT_RETENTION_DAYS
- [ ] Scheduled: daily at 3 AM
- [ ] Batch delete: 1000 rows at a time to avoid long locks

**Success Criteria:**
- Approval created → admin gets notification
- Alert fired → alert delivered to configured channels
- Audit logs older than retention → deleted in daily cleanup

---

### P6-04: Export + Threshold Tasks

**Checklist:**
- [ ] `generate_audit_export(export_id)` — generates CSV/JSON export file
- [ ] Queries audit events matching export params
- [ ] Writes file to storage (local or S3-compatible)
- [ ] Updates export record with status + download URL
- [ ] `check_alert_thresholds()` — evaluates all enabled alert rules
- [ ] Retrieves current metric values from Redis/DB
- [ ] Compares against rule conditions
- [ ] Fires alerts when threshold crossed
- [ ] Scheduled: every 60 seconds
- [ ] `deliver_webhook(webhook_id, event_payload)` — delivers webhook with retry
- [ ] HMAC signature on every delivery
- [ ] Retry: 3 attempts with exponential backoff (1s, 5s, 25s)
- [ ] After 3 failures → mark webhook as degraded

**Success Criteria:**
- Export generates file, status updates, download URL works
- Threshold crossed → alert fires only once (deduplication)
- Webhook delivery retries on failure, degrades after 3 failures

---

### P6-05: Recurring Export + Token Cleanup Tasks

**Checklist:**
- [ ] `run_scheduled_exports()` — executes any recurring export jobs
- [ ] Scheduled: daily at midnight (configurable per export)
- [ ] `cleanup_expired_tokens()` — marks tokens past expires_at as "expired"
- [ ] Scheduled: daily at 2 AM
- [ ] `cleanup_expired_approvals()` — marks approvals past expires_at as "expired"
- [ ] Scheduled: every 5 minutes (approvals expire after 1 hour)
- [ ] `cleanup_expired_sessions()` — no-op (Redis TTL handles expiry automatically)

**Success Criteria:**
- Expired tokens → status = "expired", rejected on next validation
- Expired approvals → status = "expired", agent gets "expired" on status poll

---

## Phase 7: Telemetry

### P7-01: Prometheus Metrics

**Checklist:**
- [ ] `api/telemetry/metrics.py` — all 15 metric definitions from spec Section 21.1
- [ ] `fabric_requests_total` — Counter with labels: agent_class, capability, status
- [ ] `fabric_request_duration_seconds` — Histogram with labels: agent_class, capability, server
- [ ] `fabric_routing_overhead_seconds` — Histogram with labels: agent_class, capability
- [ ] `fabric_server_health` — Gauge per server (1=healthy, 0.5=degraded, 0=unhealthy)
- [ ] `fabric_server_tool_count` — Gauge per server
- [ ] `fabric_policy_decisions_total` — Counter with labels: agent_class, decision
- [ ] `fabric_policy_evaluation_duration` — Histogram
- [ ] `fabric_approvals_pending` — Gauge
- [ ] `fabric_approval_duration_minutes` — Histogram
- [ ] `fabric_audit_events_total` — Counter with label: event_type
- [ ] `fabric_db_connections` — Gauge
- [ ] `fabric_redis_connections` — Gauge
- [ ] `fabric_celery_tasks_total` — Counter with labels: task_type, status
- [ ] `fabric_info` — Info with version, environment
- [ ] Metrics endpoint: `GET /v1/metrics` returns Prometheus text format
- [ ] Metrics updated in middleware + service layer at appropriate points

**Success Criteria:**
- `curl http://localhost:8000/v1/metrics` returns all metric families
- Counter increments on capability request
- Histogram captures latency distribution
- Gauge updates on server health changes

---

### P7-02: OpenTelemetry Tracing

**Checklist:**
- [ ] `api/telemetry/tracing.py` — OpenTelemetry SDK setup
- [ ] Tracer provider with OTLP exporter (configurable endpoint)
- [ ] FastAPI auto-instrumentation
- [ ] SQLAlchemy auto-instrumentation
- [ ] Redis auto-instrumentation
- [ ] Celery auto-instrumentation
- [ ] Custom spans for: capability_resolution, policy_evaluation, server_selection, mcp_call, response_normalization
- [ ] Span events for key decisions (routing_reason, fallback_used, approval_required)
- [ ] Trace context propagation to MCP server calls (via HTTP headers)

**Success Criteria:**
- Traces exported to configured backend
- Full request lifecycle visible as trace with nested spans
- Each span has meaningful attributes and events

---

### P7-03: Structured Logging

**Checklist:**
- [ ] structlog configuration: JSON format in production, console (colored) in dev
- [ ] Context binding: request_id, agent_id, agent_class bound at middleware level
- [ ] Log levels per spec Section 20.3
- [ ] DEBUG: full request/response bodies, SQL queries (dev only)
- [ ] INFO: method + path + status + latency, server registrations, policy changes
- [ ] WARN: degraded servers, fallback events, rate limit hits
- [ ] ERROR: server failures, DB/Redis connection errors, OPA unreachable
- [ ] Never logged: agent tokens, MCP response bodies, admin passwords, capability request param values
- [ ] Log redaction: sanitize param values in audit events and debug logs

**Success Criteria:**
- Production logs are valid JSON, one line per event
- Dev logs are human-readable with colors
- Token/sensitive data never appears in logs

---

### P7-04: Grafana Dashboard

**Checklist:**
- [ ] `monitoring/grafana-dashboard.json` — pre-built dashboard JSON
- [ ] All panels from spec Section 21.3
- [ ] Request rate graph, latency (p50/p95/p99) graph, routing overhead graph
- [ ] Requests by agent class bar chart, by capability bar chart
- [ ] Error rate, denial rate, fallback rate graphs
- [ ] Server health status grid
- [ ] Pending approvals stat, approval resolution time
- [ ] OPA evaluation latency
- [ ] DB connections, Celery task status
- [ ] Dashboard importable via Grafana UI → Import → Paste JSON

**Success Criteria:**
- Import dashboard JSON into Grafana → all panels render
- Dashboard updates with live metrics from Prometheus
- Time range picker works for all panels

---

### P7-05: Prometheus Alertmanager Rules

**Checklist:**
- [ ] `monitoring/alerts.yml` — Prometheus alert rules
- [ ] Alert: Error budget burn rate > 5x → P0, page on-call
- [ ] Alert: p95 latency > 1s for 10 min → P1, page on-call
- [ ] Alert: Availability below 99% for 30 min → P0
- [ ] Alert: Server health degradation (3+ servers unhealthy) → P1
- [ ] Alert: Denial rate spike > 10% for any agent class → P1
- [ ] Alert: Unreviewed server > 0 for > 48h → P2
- [ ] Alert: Fabric API error rate > 1% for 5 min → P1
- [ ] Alert labels: severity=P0/P1/P2, component=fabric

**Success Criteria:**
- `promtool check rules monitoring/alerts.yml` passes
- Alerts fire in Prometheus when thresholds crossed
- Alertmanager routes to configured channels

---

## Phase 8: Error Handling

### P8-01: Error Infrastructure

**Checklist:**
- [ ] `api/errors.py` — FabricError exception class
- [ ] Constructor: `FabricError(status_code, error_code, message, details, suggestion, retry_after)`
- [ ] FastAPI exception handler: catches FabricError → returns structured JSON response
- [ ] Error response format: `{error, message, details, request_id, suggestion?, retry_after?}`
- [ ] All 12 error codes from spec Section 8.2 implemented
- [ ] Pydantic ValidationError handler → 422 with field-level details
- [ ] Unhandled exceptions → 500 with generic message (no stack traces in production)
- [ ] Exception logging: ERROR level with request_id, traceback (dev only)
- [ ] `capability_deprecated` response: 410 Gone with `{status: "deprecated", retired_on, guidance}`

**Success Criteria:**
- All errors return consistent JSON format with request_id
- Validation errors include field-level messages
- 500 errors never leak stack traces in production
- Deprecated capability returns 410 with guidance

---

### P8-02: Error Catalog Implementation

**Checklist:**
- [ ] 400 `invalid_parameter` — malformed capability request params with expected/received
- [ ] 401 `invalid_token` — missing/expired/revoked agent token
- [ ] 401 `token_expired` — token past expiration with no grace period
- [ ] 403 `access_denied` — agent class not authorized for capability
- [ ] 403 `namespace_restricted` — agent outside allowed team namespace
- [ ] 404 `capability_not_found` — requested capability doesn't exist + suggestion
- [ ] 404 `server_not_found` — referenced server doesn't exist
- [ ] 409 `capability_conflict` — two servers claim same capability
- [ ] 409 `schema_breaking_change` — server upgrade contains breaking changes
- [ ] 410 `capability_deprecated` — capability retired after grace period
- [ ] 422 `validation_error` — request body fails Pydantic validation
- [ ] 429 `rate_limited` — agent exceeded request limit
- [ ] 503 `fabric_degraded` — Fabric internal error (DB/Redis down)
- [ ] 503 `no_healthy_server` — all candidate servers unhealthy

**Success Criteria:**
- Each error code returns correct HTTP status + structured body
- Suggestions present where applicable (404 capability_not_found)
- Retry-After header present on 429 and 503

---

## Phase 9: Admin UI

### P9-01: UI Scaffolding

**Checklist:**
- [ ] `ui/package.json` — React 18, TypeScript, Vite, Tailwind CSS, TanStack Query, React Router
- [ ] `ui/tsconfig.json` — strict mode, path aliases
- [ ] `ui/vite.config.ts` — proxy `/v1` to API, dev server on port 3000
- [ ] `ui/tailwind.config.js` — content paths, theme extensions
- [ ] `ui/index.html` — mount point
- [ ] `ui/src/main.tsx` — React root with QueryClientProvider + RouterProvider
- [ ] `ui/src/api/client.ts` — TanStack Query API client
- [ ] Base URL from env: `VITE_API_URL=http://localhost:8000`
- [ ] Request interceptor: attach `Authorization: Bearer <token>` from auth store
- [ ] Response interceptor: 401 → redirect to login
- [ ] `ui/src/App.tsx` — React Router routes for all 12 pages + login
- [ ] `ui/src/components/Layout.tsx` — sidebar (nav links for all pages) + top bar (user info, logout)
- [ ] Protected routes: redirect to login if no auth token
- [ ] Role-based route visibility: admin-only routes hidden for editor/viewer

**Success Criteria:**
- `npm run dev` starts on port 3000
- API calls proxied to backend
- Auth token attached to all requests
- 401 response → redirect to login
- Sidebar shows nav links corresponding to user role

---

### P9-02: Shared Components

**Checklist:**
- [ ] `PageState<T>` pattern: loading / error / empty / populated
- [ ] Loading state: skeleton loaders (pulsing gray blocks matching layout)
- [ ] Error state: error message + retry button
- [ ] Empty state: message + optional CTA button
- [ ] `PaginatedTable` component: cursor-based or offset-based pagination, sortable headers, row click → detail
- [ ] `FilterBar` component: dropdown filters + search input + clear all
- [ ] `Modal` component: overlay, close on Esc/outside click, form submission
- [ ] `ConfirmDialog` component: destructive action confirmation
- [ ] `Badge` component: colored badges for status/trust levels
- [ ] `Toast` component: success/error/info notifications
- [ ] `ErrorBoundary` component: catches React render errors, shows fallback UI

**Success Criteria:**
- All pages use consistent loading/error/empty/populated states
- Pagination works for cursor and offset modes
- Modals close on Esc and outside click
- Error boundary catches render errors gracefully

---

### P9-03: Login Page

**Checklist:**
- [ ] `ui/src/pages/Login.tsx`
- [ ] Username + password form with validation
- [ ] Submit → POST /v1/auth/login
- [ ] If `requires_mfa`: show MFA code input
- [ ] MFA code input: 6-digit TOTP, auto-submit on 6th digit
- [ ] "Lost MFA device?" link → MFA recovery flow (backup code input)
- [ ] On success: store JWT in auth store, redirect to dashboard
- [ ] On failure: show error message (invalid credentials / account locked / etc.)
- [ ] "Forgot password?" link → password reset flow

**Success Criteria:**
- Valid credentials → redirect to dashboard
- MFA required → MFA code prompt
- Invalid credentials → error message without revealing which field failed
- Account locked → clear lockout message with time remaining

---

### P9-04: Dashboard Page

**Checklist:**
- [ ] `ui/src/pages/Dashboard.tsx`
- [ ] Server count widget: total + health breakdown (healthy/degraded/unhealthy)
- [ ] Trust posture widget: servers by trust level (trusted/restricted/approval-gated/unreviewed)
- [ ] Recent audit events: last 10 events, scrollable, click → expand details
- [ ] Pending approvals: count badge, click → navigate to approvals page
- [ ] Degraded servers: list with quick health check trigger
- [ ] Auto-refresh: TanStack Query `refetchInterval: 30000`
- [ ] Empty state (first run): "Welcome to MCP Fabric. Register your first server to get started." with CTA

**Success Criteria:**
- Dashboard loads within 2 seconds
- Widgets display current data
- Auto-refresh updates every 30 seconds
- Clicking widgets navigates to detail pages

---

### P9-05: Servers Page — List

**Checklist:**
- [ ] `ui/src/pages/Servers.tsx`
- [ ] Table: name, endpoint (truncated), trust level (Badge), health (icon + color), tool count, team namespace, last inspected, actions
- [ ] Filters: team namespace (dropdown), trust level (multi-select), health status (multi-select), search (name + endpoint)
- [ ] Sort: by name, created_at, health_status, trust_level
- [ ] "Register Server" button → opens modal
- [ ] Register modal: name, endpoint URL, owner team, description, labels (tag input), team namespace
- [ ] On submit: POST /v1/servers → show success toast → navigate to detail or refresh list
- [ ] Row click → navigate to server detail

**Success Criteria:**
- List loads with correct server data
- Filters narrow results
- Register creates server + navigates to detail
- Empty state: "No servers registered yet."

---

### P9-06: Servers Page — Detail + Inspect + Decommission

**Checklist:**
- [ ] `ui/src/pages/ServerDetail.tsx`
- [ ] Server metadata panel: name, endpoint, owner, labels, trust level, health, team, registered date
- [ ] Tools table: tool_name, description, input_schema (expandable JSON), output_schema (expandable JSON)
- [ ] Trust assignments panel: agent class, trust level (Badge), tool scope
- [ ] Routing rules panel: capability, priority, condition
- [ ] Decommission timeline: show phases if decommissioned
- [ ] "Inspect" button → POST /v1/servers/{id}/inspect → loading → show diff modal (added/removed/changed tools)
- [ ] "Decommission" button → decommission modal: select phase, optional replacement server, confirm
- [ ] "Quick trust change" dropdown: change trust level inline

**Success Criteria:**
- Detail shows all server metadata + tools + trust + routing
- Inspect shows diff with breaking change warnings
- Decommission shows dependency report before confirming

---

### P9-07: Capability Catalog Page — List + Create

**Checklist:**
- [ ] `ui/src/pages/Capabilities.tsx`
- [ ] Table: name, domain (Badge), status (active/deprecated Badge), mapped tools count, aliases
- [ ] Filters: domain (dropdown), status (active/deprecated), search (name + alias)
- [ ] "Create Capability" button → modal: name (with domain:action helper), domain, description, normalized input/output schema editors (JSON textarea with validation)
- [ ] On submit: POST /v1/capabilities → success toast → refresh list

**Success Criteria:**
- List loads with correct capability data
- Create with valid name → 201
- Name validation shows domain:action format hint

---

### P9-08: Capability Catalog Page — Detail + Map + Deprecate + Aliases

**Checklist:**
- [ ] Capability detail view: metadata, mapped servers table (server name, tool name, is_primary, routing weight)
- [ ] "Map Tool" button → modal: select server → select tool → configure input/output mapping → save
- [ ] Conflict warning banner: "2 servers claim this capability. Review routing." with link to routing rules
- [ ] `ui/src/components/CapabilityMapper.tsx` — handles mapping creation + editing
- [ ] Deprecate flow: button → modal: grace period days, migration guidance text → confirm
- [ ] Alias management: add alias input, list of existing aliases with delete
- [ ] After deprecation: status badge changes to "deprecated"

**Success Criteria:**
- Map tool → appears in mapped servers table
- Conflict detected → warning banner visible
- Deprecate → status changes, auto-remove from packs
- Add alias → alias resolves in capability search

---

### P9-09: Agent Classes Page — List + Detail + Token Management

**Checklist:**
- [ ] `ui/src/pages/AgentClasses.tsx`
- [ ] Table: name, team namespace, trust count, agent count, packs count
- [ ] "Create Class" button → modal: name, description, team namespace
- [ ] Class detail view: metadata, trust assignments table, assigned packs, agent identities sub-list
- [ ] Trust assignment table: server name, trust level (Badge), tool scope, add/remove
- [ ] Agent identities sub-list: name, status (Badge), token prefix, rate limit, expires, actions (rotate, revoke)
- [ ] "Create Token" button → modal: agent name, rate limit → generate → show token ONCE with copy button
- [ ] Warning banner on token creation: "Save this token now. It cannot be retrieved later."
- [ ] Rotate token: modal → grace period hours → generate → show new token + "old token valid for X hours"
- [ ] Revoke token: confirm dialog → "This will immediately invalidate the token. All active sessions will be rejected."

**Success Criteria:**
- Create class → appears in list
- Create token → token shown once, not retrievable
- Rotate → both tokens work during grace period
- Revoke → token immediately invalid

---

### P9-10: Policy Editor Page

**Checklist:**
- [ ] `ui/src/pages/PolicyEditor.tsx`
- [ ] Rego editor: Monaco editor (or CodeMirror) with rego syntax highlighting
- [ ] Shows current deployed policy version + timestamp
- [ ] "Deploy" button → POST /v1/admin/policies/bundle → success toast or error with OPA validation message
- [ ] "Test" button → runs `opa test` (or evaluates sample input against policy) → shows results
- [ ] Policy history: list of past versions with deploy timestamps
- [ ] Editor read-only for non-admin users

**Success Criteria:**
- Editor loads with syntax highlighting
- Deploy updates OPA policies
- Invalid rego → error message from OPA
- Deploy feedback: success/failure toast

---

### P9-11: Audit Log Page

**Checklist:**
- [ ] `ui/src/pages/AuditLog.tsx`
- [ ] Table: timestamp, event type (Badge), actor type + ID, target type + ID, summary (truncated details)
- [ ] Expandable row: full details JSON (formatted, scrollable)
- [ ] `ui/src/components/AuditFilter.tsx`
- [ ] Filters: event type (multi-select), actor type (agent/admin/system), actor ID (search), target type, date range (date picker), capability (search)
- [ ] Cursor pagination: "Load More" or infinite scroll
- [ ] "Export" button → modal: event types (multi-select), agent classes (multi-select), date range, format (JSON/CSV) → "Generate Export"
- [ ] Export progress: polling status until download available
- [ ] Read-only for viewers: no export button (viewer cannot export)

**Success Criteria:**
- Events load with correct data and pagination
- Filters narrow results
- Expandable row shows full details
- Export generates file, download link appears when ready

---

### P9-12: Approvals Page

**Checklist:**
- [ ] `ui/src/pages/Approvals.tsx`
- [ ] Table: agent name, capability, server, params summary (truncated), requested at, status (Badge)
- [ ] Filters: status (pending/approved/denied/expired), agent class, capability
- [ ] "Review" button → side panel: full request context
- [ ] Side panel: agent (name + class), capability, params (formatted JSON), server, trust level, requested timestamp
- [ ] Approve: textarea for optional note → "Approve" button → POST /v1/approvals/{id}/approve
- [ ] Deny: textarea for required reason → "Deny" button → POST /v1/approvals/{id}/deny
- [ ] Bulk actions: checkbox selection → "Approve Selected" / "Deny Selected"
- [ ] After action: row removed from pending list, audit logged

**Success Criteria:**
- Pending approvals listed correctly
- Review side panel shows full context
- Approve → request routed, agent gets result
- Deny → agent gets 403 with reason
- Bulk approve works for multiple selections

---

### P9-13: Capability Packs Page

**Checklist:**
- [ ] `ui/src/pages/Packs.tsx`
- [ ] Cards view: pack name, description, capability count, assigned classes count
- [ ] "Create Pack" button → modal: name, description, team namespace → save
- [ ] Pack detail: assigned capabilities list (with search + add), assigned classes list (with add)
- [ ] "Add Capability" → capability picker modal: search/filter from catalog + multi-select → "Add"
- [ ] "Assign to Class" → class picker modal: select agent class → "Assign"
- [ ] Clone pack: modal → new name → creates duplicate with same capabilities
- [ ] Usage stats: shows which agent classes + how many agents use this pack
- [ ] Delete pack: confirm dialog → cascades to assignments

**Success Criteria:**
- Create pack → appears in cards
- Add capabilities → pack detail shows capabilities
- Assign to class → agent's capability surface includes pack
- Clone → new pack with identical capabilities
- Usage stats show correct numbers

---

### P9-14: Alerts Page

**Checklist:**
- [ ] `ui/src/pages/Alerts.tsx`
- [ ] Table: fired at (relative time + absolute), rule name, message, acknowledged (icon)
- [ ] Filters: alert type (server_degradation/unreviewed_server/denial_spike/schema_change), acknowledged status, time range
- [ ] Acknowledge: click "Acknowledge" → POST (implicit) → icon changes to checkmark
- [ ] Expandable row: full alert details JSON

**Success Criteria:**
- Alerts load with correct data
- Acknowledge marks alert
- Filters narrow results

---

### P9-15: Admin Users Page

**Checklist:**
- [ ] `ui/src/pages/AdminUsers.tsx`
- [ ] Table: username, email, role (Badge), team scope, MFA (icon), last login, status (Badge)
- [ ] "Invite User" button → modal: email, role (admin/editor/viewer), team namespace
- [ ] User detail: edit role, edit team scope, deactivate, unlock, reset MFA
- [ ] Deactivate: confirm dialog → POST /v1/admin/users/{id}/deactivate → user status "deactivated", sessions revoked
- [ ] Unlock: confirm dialog → POST /v1/admin/users/{id}/unlock → clears lockout
- [ ] Reset MFA: confirm dialog → POST /v1/admin/users/{id}/reset-mfa → user's MFA disabled

**Success Criteria:**
- Invite → user receives email with setup link
- Deactivate → user cannot log in
- Unlock → locked user can log in again
- Reset MFA → user's MFA disabled

---

### P9-16: Trust Posture Page

**Checklist:**
- [ ] `ui/src/pages/TrustPosture.tsx`
- [ ] Grid: server cards colored by trust level
- [ ] Trusted (green), Restricted (yellow), Approval-Gated (orange), Unreviewed (red)
- [ ] Unreviewed banner: "N servers unreviewed (oldest: X hours)" — prominent, red background
- [ ] Quick actions on card: change trust level dropdown
- [ ] Click card → navigate to server detail
- [ ] Filter: team namespace, trust level

**Success Criteria:**
- Cards display correct trust level colors
- Unreviewed banner visible when servers need review
- Quick trust change updates server immediately

---

## Phase 10: Testing

### P10-01: Unit Tests — Services

**Checklist:**
- [ ] `tests/test_registry.py` — register (success, duplicate, unreachable), inspect (no change, change, breaking), list (filtered, paginated, empty), get (found, not_found), decommission (phases, dependencies)
- [ ] `tests/test_catalog.py` — create (valid, invalid name), map (valid, invalid server, invalid tool), resolve (name, alias, not_found with suggestion), conflict detect (single server, two servers, three+ servers), deprecate (during grace, after grace, auto-remove from packs), alias (create, duplicate, resolve via alias)
- [ ] `tests/test_routing.py` — single request (success, denied, gated, timeout+fallback), batch (success, mixed, all_failure), status poll (pending, approved, denied, expired)
- [ ] `tests/test_policy.py` — evaluate (allow trusted, deny restricted, approval-gated for developer), deploy bundle (valid, invalid rego), cache invalidation
- [ ] `tests/test_audit.py` — log (all event types), query (filtered, paginated, empty), export (create, status poll, download)
- [ ] `tests/test_approval.py` — create (pending, expiry set), approve (routes request, status update), deny (status update, 403 to agent), expire (auto-deny)
- [ ] `tests/test_packs.py` — create, assign capabilities, assign to class, clone, delete (cascade), usage stats
- [ ] `tests/test_alerts.py` — create rule, evaluate thresholds (fires, does_not_fire), fire alert (delivered to channels), acknowledge
- [ ] `tests/test_auth.py` — agent token lifecycle (create, validate, rotate, revoke, expire), admin (login, MFA setup/verify/recover, session, logout), password (complexity, history, lockout, reset), invite + setup
- [ ] `tests/test_batch.py` — 3 parallel successes, 3 with mixed results, max batch size validation
- [ ] `tests/test_fallback.py` — timeout primary → fallback → degradation logged → alert threshold
- [ ] `tests/test_tenant.py` — namespace filtering (platform sees platform, security sees security, admin sees all), cross-team access
- [ ] `tests/test_schema_diff.py` — identical (no change), new tool, removed tool, changed param (non-breaking), changed param (breaking), output schema change
- [ ] `tests/test_errors.py` — all 14 error types return correct status + format
- [ ] `tests/test_pagination.py` — cursor pagination, offset pagination, max per_page, empty results

**Success Criteria:**
- All P0 scenarios tested (critical path)
- Test coverage > 80%
- Tests pass on SQLite (fast, local) and PostgreSQL (CI)

---

### P10-02: Integration Tests

**Checklist:**
- [ ] Registration flow: POST /servers → inspect → tools imported → GET /servers/{id} → verify tools
- [ ] Capability request: register server → create capability → map tool → create class + token → POST /capability/request → verify response + audit event
- [ ] Approval flow: create approval-gated capability → POST request → verify 202 → POST approve → verify routing → verify audit
- [ ] Fallback flow: mock primary server timeout → POST request → verify fallback → verify degradation → verify alert created
- [ ] Batch flow: 3 parallel requests with mock servers → verify all responses → verify 3 audit events
- [ ] Auth flow: create token → POST /auth/connect → verify capability surface → revoke token → verify 401
- [ ] Pack flow: create pack → add capabilities → assign to class → create agent in class → POST /auth/connect → verify surface includes pack capabilities
- [ ] Deprecation flow: create capability → deprecate → POST request during grace → verify warning → after grace → verify 410

**Success Criteria:**
- All flows complete end-to-end with correct results
- Mock MCP server returns controlled responses
- Audit events captured at each step

---

### P10-03: OPA Policy Tests

**Checklist:**
- [ ] All 10 default policy tests from spec Section 24.2 pass
- [ ] `opa test policies/ -v` → 10/10
- [ ] Additional tests: cross-team deny by default, cross-team allow when explicitly shared
- [ ] Policy bundle deploy → `/v1/data/fabric/policy/allow` returns updated results
- [ ] Policy deploy invalidates OPA cache in Redis

**Success Criteria:**
- All policy tests pass in CI (`opa-tests` job)
- Policy changes reflected within 1 second of deploy

---

### P10-04: E2E Tests

**Checklist:**
- [ ] Docker compose: `docker-compose up` → all 7 services healthy within 60s
- [ ] Full happy path: register server → create capability → map tool → create agent class → create token → capability request → audit event visible → server decommission → sunset
- [ ] Admin UI: login → dashboard loads → navigate to servers → register server → verify in list
- [ ] Batch: register 3 servers → create 3 capabilities → map all → batch request → verify all responses

**Success Criteria:**
- E2E tests pass in Docker Compose environment
- Full lifecycle from registration to decommission works

---

### P10-05: Test Infrastructure

**Checklist:**
- [ ] `tests/fixtures/mock_mcp_server.py` — in-process FastAPI app
- [ ] Implements `/tools/list` → returns configurable tool definitions
- [ ] Implements `/tools/call` → returns configurable responses
- [ ] Configurable latency (simulate slow servers)
- [ ] Configurable failure (simulate timeouts, errors)
- [ ] Multiple mock servers: code-search, git-history, kb-server, deployment-server
- [ ] Test fixtures create test database + mock servers + agent tokens automatically
- [ ] Test coverage reporting: pytest-cov with XML output

**Success Criteria:**
- Tests use mock MCP server, no external dependencies
- Test suite runs < 60 seconds (SQLite mode)
- Coverage report generated

---

## Phase 11: CI/CD

### P11-01: CI Pipeline

**Checklist:**
- [ ] `.github/workflows/ci.yml` — triggers on push/PR to main
- [ ] `lint` job: ruff check + ruff format --check (Python) + eslint + prettier (UI)
- [ ] `test-sqlite` job: pytest with SQLite in-memory DB, Redis service container
- [ ] `test-postgres` job: pytest with PostgreSQL + Redis + OPA service containers
- [ ] `opa-tests` job: `opa test policies/ -v`
- [ ] `typecheck` job: `mypy api/`
- [ ] `ui-lint` job: `cd ui && npm ci && npm run lint && npm run typecheck`
- [ ] `security-scan` job: `pip-audit` + `npm audit --audit-level=high`
- [ ] All jobs must pass before PR merge

**Success Criteria:**
- CI runs on every push and PR
- All checks green on main branch
- Security scan fails CI on high/critical vulnerabilities

---

### P11-02: Release Pipeline

**Checklist:**
- [ ] `.github/workflows/release.yml` — triggers on tag push `v*`
- [ ] `build-docker` job: builds API Docker image + UI Docker image, pushes to ghcr.io
- [ ] `publish-pypi` job: `poetry build` + `poetry publish` (requires PYPI_TOKEN secret)
- [ ] Tags: `v0.1.0`, `v0.1`, `v0`, `latest`
- [ ] Smoke test: after deploy, run capability request against deployed instance

**Success Criteria:**
- `git tag v0.1.0 && git push --tags` triggers release
- Docker image available at `ghcr.io/deghosal-2026/mcp-fabric:v0.1.0`
- PyPI package installable via `pip install mcp-fabric`

---

### P11-03: Release Checklist Automation

**Checklist:**
- [ ] CI must pass before release tag can be created
- [ ] Migrations tested: `alembic upgrade head && alembic downgrade -1` on PostgreSQL
- [ ] OPA tests pass
- [ ] Security scan passes
- [ ] API diff: compare OpenAPI specs between versions, flag breaking changes
- [ ] CHANGELOG updated
- [ ] GitHub Release created with changelog notes

**Success Criteria:**
- Release fails if any check fails
- OpenAPI diff catches accidental breaking changes
- Release notes auto-generated from CHANGELOG

---

## Phase 12: Documentation

### P12-01: Code Documentation

**Checklist:**
- [ ] All public functions have docstrings (Google style: Args, Returns, Raises)
- [ ] All service classes have class-level docstrings explaining responsibility
- [ ] All API route handlers have docstrings describing endpoint behavior
- [ ] OpenAPI spec at `/docs` is accurate: all endpoints, schemas, examples present
- [ ] `README.md` Quick Start validated: clone → docker-compose up → first request works (as per spec Section 14.1)
- [ ] `README.md` badges: license, CI status (from GitHub Actions), Python version, Docker pulls

**Success Criteria:**
- `pydocstyle api/` passes
- OpenAPI spec at `/docs` matches actual API behavior
- README Quick Start produces a working instance in < 10 minutes

---

### P12-02: Operator Documentation

**Checklist:**
- [ ] Deployment guide: Docker Compose (dev) + Kubernetes (prod, basic manifest)
- [ ] Configuration reference: all env vars documented
- [ ] Backup/restore guide: pg_dump + pg_restore (simple until v0.2.0 fabric-admin CLI)
- [ ] Upgrade guide: blue-green procedure from spec Section 17
- [ ] Monitoring guide: Prometheus setup + Grafana dashboard import
- [ ] Troubleshooting: common errors + solutions

**Success Criteria:**
- Deployment guide enables a new operator to deploy Fabric in < 30 minutes
- Configuration reference matches all env vars in config.py

---

## Summary

| Phase | Tasks | Key Deliverables |
|---|---|---|
| P0: Scaffolding | 13 | Poetry, Makefile, Dockerfiles, Compose, Config, Main, Dependencies, Alembic, OPA, CI/CD, Docs, Tests |
| P1: Database | 10 | 17 ORM models, 11 Pydantic schema groups, migrations for SQLite + PostgreSQL |
| P2: MCP Client | 3 | list_tools, call_tool, diff_tools with timeout + retry |
| P3: Services | 19 | Registry, Capability, Policy, Routing, Audit, Approval, Pack, Alert, Auth (19 services covered) |
| P4: Middleware | 8 | RequestID, Tracing, Auth, Tenant, RateLimit, Audit, CORS, API Version |
| P5: Routes | 11 | Registry, Capability, Routing, Policy, Approval, Audit, Pack, Auth, Admin, Health, Webhooks |
| P6: Celery | 5 | Health checks, notifications, exports, thresholds, cleanup |
| P7: Telemetry | 5 | Prometheus metrics, OpenTelemetry traces, structlog, Grafana dashboard, Alertmanager rules |
| P8: Errors | 2 | Error infrastructure + 14 error catalog entries |
| P9: Admin UI | 16 | Scaffolding, Shared, Login, Dashboard, Servers (2), Capability (2), Agent Classes, Policy, Audit, Approvals, Packs, Alerts, Users, Trust |
| P10: Testing | 5 | Unit (15 files), Integration (8 flows), OPA, E2E, Infrastructure |
| P11: CI/CD | 3 | CI pipeline, Release pipeline, Release checklist |
| P12: Docs | 2 | Code docs + Operator docs |
| **Total** | **102** | **~285 sub-items across all checklists** |
