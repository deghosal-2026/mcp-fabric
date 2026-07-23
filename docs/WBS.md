# MCP Fabric — Work Breakdown Structure (v0.1.0)

> **Status:** Not started  
> **Total tasks:** 180  
> **Based on:** `docs/spec.md` v0.1.0 — 24 features

## Phase 0: Project Scaffolding (Week 1, Day 1-2)

### 0.1 Repository Setup
- [ ] P0-01 Initialize Poetry project (`pyproject.toml` with all dependencies)
- [ ] P0-02 Create `Makefile` with all targets (dev, test, lint, format, db-up, db-migrate, clean)
- [ ] P0-03 Create `Dockerfile` (multi-stage: builder + runtime, non-root user)
- [ ] P0-04 Create `ui/Dockerfile` (multi-stage: node build + nginx serve)
- [ ] P0-05 Verify `docker-compose.yml` works (API + UI + PostgreSQL + Redis + OPA + Celery)
- [ ] P0-06 Create `api/config.py` with all env var defaults (SQLite dev, PostgreSQL prod)
- [ ] P0-07 Create `api/main.py` with FastAPI app + middleware registration
- [ ] P0-08 Create `api/dependencies.py` (get_db, get_redis, get_opa, get_current_agent)
- [ ] P0-09 Create `alembic.ini` + initial Alembic migration (all 17 tables)
- [ ] P0-10 Create `.github/dependabot.yml` (pip, docker, github-actions, npm)
- [ ] P0-11 Create `CHANGELOG.md` structure
- [ ] P0-12 Create `CODE_OF_CONDUCT.md`
- [ ] P0-13 Create `.github/PULL_REQUEST_TEMPLATE.md`
- [ ] P0-14 Create `.gitattributes`
- [ ] P0-15 Update `README.md` with badges, Quick Start commands, links to docs
- [ ] P0-16 Create `policies/fabric/policy.rego` (default OPA policies)
- [ ] P0-17 Create `policies/fabric/policy_test.rego` (OPA policy tests)
- [ ] P0-18 Create `tests/conftest.py` (SQLite test DB, mock MCP server, agent token fixtures)

## Phase 1: Database & Models (Week 1, Day 2-3)

### 1.1 SQLAlchemy ORM Models
- [ ] P1-01 `api/models/server.py` — MCPServer, ServerTool, ToolVersion models
- [ ] P1-02 `api/models/capability.py` — Capability, CapabilityMapping, CapabilityAlias models
- [ ] P1-03 `api/models/policy.py` — AgentClass, TrustAssignment models
- [ ] P1-04 `api/models/agent.py` — AgentIdentity model
- [ ] P1-05 `api/models/audit.py` — AuditEvent model
- [ ] P1-06 `api/models/approval.py` — ApprovalRequest model
- [ ] P1-07 `api/models/pack.py` — CapabilityPack, PackAssignment, AgentClassPack models
- [ ] P1-08 `api/models/alert.py` — AlertRule, AlertEvent models
- [ ] P1-09 `api/models/user.py` — AdminUser model
- [ ] P1-10 `api/models/routing.py` — RoutingRule model
- [ ] P1-11 `api/models/opa.py` — OPAPolicyVersion model
- [ ] P1-12 `api/db/session.py` — SQLAlchemy async engine + session factory (SQLite + PostgreSQL)

### 1.2 Pydantic Schema Models
- [ ] P1-13 `api/models/schemas/server.py` — ServerCreate, ServerResponse, ServerInspectResponse
- [ ] P1-14 `api/models/schemas/capability.py` — CapabilityRequest, BatchRequest, CapabilityResponse, BatchResponse
- [ ] P1-15 `api/models/schemas/agent.py` — AgentIdentityCreate, AgentConnectResponse, CapabilitySurfaceItem
- [ ] P1-16 `api/models/schemas/audit.py` — AuditEventResponse, AuditExportRequest
- [ ] P1-17 `api/models/schemas/error.py` — FabricError
- [ ] P1-18 `api/models/schemas/auth.py` — LoginRequest, TokenResponse, MFASetupResponse

### 1.3 Alembic Migrations
- [ ] P1-19 Initial migration: all 17 tables + all indexes
- [ ] P1-20 Migration tested: `alembic upgrade head` + `alembic downgrade -1` (SQLite + PostgreSQL)
- [ ] P1-21 Migration runs in CI (both SQLite and PostgreSQL jobs)

## Phase 2: MCP Client Layer (Week 1, Day 3-4)

### 2.1 MCP Protocol Client
- [ ] P2-01 `api/mcp/__init__.py` — package init
- [ ] P2-02 `api/mcp/client.py` — MCPClient class using official `mcp` SDK
- [ ] P2-03 `list_tools(endpoint)` — call `/tools/list`, return parsed ToolDefinition list
- [ ] P2-04 `call_tool(endpoint, tool_name, arguments)` — call `/tools/call`, return raw response
- [ ] P2-05 `diff_tools(endpoint, previous_tools)` — compare current vs previous tool lists
- [ ] P2-06 Connection timeout: 5s with 1 retry
- [ ] P2-07 Health check integration: update Redis health state after each call

## Phase 3: Core Services (Week 1-2, Day 4-8)

### 3.1 Registry Service
- [ ] P3-01 `api/services/registry_service.py` — RegistryService class
- [ ] P3-02 `register(name, endpoint, **meta)` — create server + inspect tools
- [ ] P3-03 `inspect(server_id)` — re-fetch tools, detect changes, store in tool_versions
- [ ] P3-04 `list_servers(team, trust, health)` — filtered listing with pagination
- [ ] P3-05 `get_server(server_id)` — full detail with tools, routing rules, trust assignments
- [ ] P3-06 `decommission(server_id, phase, replacement_id)` — phased decommission
- [ ] P3-07 Schema diff: detect added/removed/changed tools, flag breaking changes

### 3.2 Capability Service
- [ ] P3-08 `api/services/capability_service.py` — CapabilityService class
- [ ] P3-09 `create(name, domain, **schema)` — create capability with normalized schemas
- [ ] P3-10 `map_tool(capability_id, server_id, tool_name, **mapping)` — map tool to capability
- [ ] P3-11 `resolve(name)` — resolve capability by name or alias
- [ ] P3-12 `detect_conflicts(capability_id)` — find overlapping mappings
- [ ] P3-13 `deprecate(capability_id, grace_days, guidance)` — mark as deprecated
- [ ] P3-14 `add_alias(capability_id, alias)` — add alias for name resolution
- [ ] P3-15 `list_capabilities(domain, status)` — filtered listing with pagination

### 3.3 Policy Service
- [ ] P3-16 `api/services/policy_service.py` — PolicyService class
- [ ] P3-17 `evaluate(agent_class, server_id, capability, team)` — OPA evaluation
- [ ] P3-18 `deploy_bundle(rego_content, deployed_by)` — deploy OPA policy bundle
- [ ] P3-19 `create_agent_class(name, description, team)` — create agent class
- [ ] P3-20 `set_trust(class_id, server_id, trust_level, tool_scope)` — trust assignment
- [ ] P3-21 `list_agent_classes(team)` — filtered listing

### 3.4 Routing Service
- [ ] P3-22 `api/services/routing_service.py` — RoutingService class
- [ ] P3-23 `execute(capability_name, params, agent_identity)` — full routing pipeline
- [ ] P3-24 Step 1: Resolve capability (name + alias lookup)
- [ ] P3-25 Step 2: Get candidate servers (capability mappings + health filter)
- [ ] P3-26 Step 3: Apply routing rules (priority-based ordering)
- [ ] P3-27 Step 4: Evaluate policy (OPA — allow/deny/approval-gated)
- [ ] P3-28 Step 5: Rank candidates (match quality × policy × priority)
- [ ] P3-29 Step 6: Call MCP server (via MCPClient)
- [ ] P3-30 Step 7: Fallback if primary fails (mark degraded, try next candidate)
- [ ] P3-31 Step 8: Normalize response (apply output_mapping)
- [ ] P3-32 Step 9: Audit (log event)
- [ ] P3-33 `execute_batch(requests, agent_identity)` — parallel execution with asyncio.gather

### 3.5 Audit Service
- [ ] P3-34 `api/services/audit_service.py` — AuditService class
- [ ] P3-35 `log_event(event_type, actor, target, details)` — write audit event
- [ ] P3-36 `query(event_type, actor, from_date, to_date, cursor)` — paginated query
- [ ] P3-37 `export(from_date, to_date, event_types, agent_classes, format)` — create export task

### 3.6 Approval Service
- [ ] P3-38 `api/services/approval_service.py` — ApprovalService class
- [ ] P3-39 `create_request(agent_id, capability_id, server_id, params)` — create pending approval
- [ ] P3-40 `list_pending(agent_class, capability)` — filtered listing
- [ ] P3-41 `approve(approval_id, approver_id, note)` — approve and route
- [ ] P3-42 `deny(approval_id, approver_id, note)` — deny with reason

### 3.7 Pack Service
- [ ] P3-43 `api/services/pack_service.py` — PackService class
- [ ] P3-44 `create(name, description, team)` — create pack
- [ ] P3-45 `assign_capabilities(pack_id, capability_ids)` — assign capabilities
- [ ] P3-46 `assign_to_class(pack_id, class_id)` — assign pack to agent class
- [ ] P3-47 `get_packs(team)` — filtered listing
- [ ] P3-48 `clone_pack(pack_id, new_name)` — clone for team variants

### 3.8 Alert Service
- [ ] P3-49 `api/services/alert_service.py` — AlertService class
- [ ] P3-50 `evaluate_thresholds()` — check all alert rules against recent metrics
- [ ] P3-51 `create_rule(name, alert_type, condition, channels)` — create alert rule
- [ ] P3-52 `fire_alert(rule_id, message, details)` — create alert event
- [ ] P3-53 `acknowledge(alert_id, user_id)` — acknowledge alert

### 3.9 Auth Service
- [ ] P3-54 `api/services/auth_service.py` — AuthService class
- [ ] P3-55 Agent: `validate_token(token_hash)` — validate agent token (bcrypt + Redis cache)
- [ ] P3-56 Agent: `create_identity(name, class_id, rate_limit, expires_days)` — create token
- [ ] P3-57 Agent: `rotate_token(identity_id, grace_hours)` — rotate with grace period
- [ ] P3-58 Agent: `revoke_token(identity_id, reason)` — immediate revocation
- [ ] P3-59 Agent: `get_capability_surface(identity_id)` — resolve agent's capability surface
- [ ] P3-60 Admin: `login(username, password)` — validate credentials
- [ ] P3-61 Admin: `verify_mfa(user_id, code)` — verify TOTP code
- [ ] P3-62 Admin: `setup_mfa(user_id)` — generate TOTP secret + QR code
- [ ] P3-63 Admin: `create_session(user_id)` — create JWT + Redis session
- [ ] P3-64 Admin: `validate_session(token)` — validate JWT + Redis presence
- [ ] P3-65 Admin: `logout(session_token)` — delete Redis session

## Phase 4: Middleware (Week 2, Day 5-6)

### 4.1 Middleware Stack
- [ ] P4-01 `api/middleware/__init__.py` — package init
- [ ] P4-02 `api/middleware/request_id.py` — assign UUID, set response header
- [ ] P4-03 `api/middleware/tracing.py` — OpenTelemetry span creation
- [ ] P4-04 `api/middleware/auth.py` — Agent token validation + admin session validation
- [ ] P4-05 `api/middleware/tenant.py` — namespace filtering based on agent class
- [ ] P4-06 `api/middleware/rate_limit.py` — Redis-based per-agent rate limiting
- [ ] P4-07 `api/middleware/audit.py` — async audit event logging (background task)
- [ ] P4-08 `api/middleware/cors.py` — CORS configuration
- [ ] P4-09 Middleware registration in `api/main.py` (correct order per Section 31)

## Phase 5: API Routes (Week 2, Day 6-8)

### 5.1 Registry Routes
- [ ] P5-01 `POST /v1/servers` — register server + auto-inspect
- [ ] P5-02 `GET /v1/servers` — list with filters + pagination
- [ ] P5-03 `GET /v1/servers/{id}` — get server detail
- [ ] P5-04 `POST /v1/servers/{id}/inspect` — re-inspect + schema diff
- [ ] P5-05 `POST /v1/servers/{id}/decommission` — phased decommission

### 5.2 Capability Routes
- [ ] P5-06 `POST /v1/capabilities` — create capability
- [ ] P5-07 `GET /v1/capabilities` — list with filters + pagination
- [ ] P5-08 `POST /v1/capabilities/{id}/mappings` — map tool to capability
- [ ] P5-09 `POST /v1/capabilities/{id}/deprecate` — deprecate with grace period
- [ ] P5-10 `POST /v1/capabilities/{id}/aliases` — add alias
- [ ] P5-11 `GET /v1/capabilities/available` — agent's capability surface (full schemas)

### 5.3 Routing Routes
- [ ] P5-12 `POST /v1/capability/request` — single capability request
- [ ] P5-13 `POST /v1/capability/batch` — batch capability request

### 5.4 Policy Routes
- [ ] P5-14 `POST /v1/agent-classes` — create agent class
- [ ] P5-15 `GET /v1/agent-classes` — list with filters
- [ ] P5-16 `POST /v1/agent-classes/{id}/trust` — set trust assignment
- [ ] P5-17 `GET /v1/agent-classes/{id}` — get class detail with trust assignments

### 5.5 Approval Routes
- [ ] P5-18 `GET /v1/approvals` — list with filters + pagination
- [ ] P5-19 `POST /v1/approvals/{id}/approve` — approve
- [ ] P5-20 `POST /v1/approvals/{id}/deny` — deny
- [ ] P5-21 `GET /v1/approvals/{id}` — get approval detail

### 5.6 Audit Routes
- [ ] P5-22 `GET /v1/audit` — query with filters + pagination
- [ ] P5-23 `POST /v1/audit/export` — create export task (Celery)

### 5.7 Pack Routes
- [ ] P5-24 `POST /v1/packs` — create pack
- [ ] P5-25 `GET /v1/packs` — list with filters
- [ ] P5-26 `POST /v1/packs/{id}/capabilities` — assign capabilities
- [ ] P5-27 `POST /v1/packs/{id}/classes` — assign to agent class
- [ ] P5-28 `GET /v1/packs/{id}` — get pack detail

### 5.8 Auth Routes
- [ ] P5-29 `POST /v1/auth/connect` — agent connect (returns capability surface)
- [ ] P5-30 `POST /v1/auth/login` — admin login (returns JWT)
- [ ] P5-31 `POST /v1/auth/mfa/verify` — admin MFA verification
- [ ] P5-32 `POST /v1/auth/mfa/setup` — initiate MFA setup
- [ ] P5-33 `POST /v1/auth/logout` — admin logout

### 5.9 Admin Routes
- [ ] P5-34 `POST /v1/admin/users/invite` — invite admin user
- [ ] P5-35 `GET /v1/admin/users` — list admin users
- [ ] P5-36 `POST /v1/admin/users/{id}/deactivate` — deactivate user
- [ ] P5-37 `POST /v1/admin/agent-identities` — create agent identity
- [ ] P5-38 `POST /v1/admin/agent-identities/{id}/rotate` — rotate token
- [ ] P5-39 `POST /v1/admin/agent-identities/{id}/revoke` — revoke token
- [ ] P5-40 `POST /v1/admin/policies/bundle` — deploy OPA policy bundle

### 5.10 Health Routes
- [ ] P5-41 `GET /v1/health` — full health check (DB + Redis + OPA)
- [ ] P5-42 `GET /v1/health/ready` — readiness probe
- [ ] P5-43 `GET /v1/health/live` — liveness probe
- [ ] P5-44 `GET /v1/metrics` — Prometheus metrics endpoint

### 5.11 Webhook Routes
- [ ] P5-45 `POST /v1/agents/{id}/webhooks` — register webhook
- [ ] P5-46 `GET /v1/agents/{id}/webhooks` — list webhooks

## Phase 6: Celery Tasks (Week 2, Day 8-9)

### 6.1 Task Definitions
- [ ] P6-01 `api/tasks.py` — Celery app initialization
- [ ] P6-02 `health_check_server(server_id)` — ping /tools/list, update health state
- [ ] P6-03 `health_check_all_servers()` — iterate all servers, call health_check_server
- [ ] P6-04 `notify_approval_request(approval_id)` — send email/Slack/webhook
- [ ] P6-05 `deliver_alert(alert_event_id)` — deliver alert via configured channels
- [ ] P6-06 `generate_audit_export(export_id)` — generate CSV/JSON file
- [ ] P6-07 `cleanup_audit_logs()` — remove events older than retention window
- [ ] P6-08 `check_alert_thresholds()` — evaluate alert rules against metrics
- [ ] P6-09 Celery Beat schedule: health checks every 30s, cleanup daily, thresholds every 60s

## Phase 7: Telemetry (Week 2, Day 9-10)

### 7.1 Observability
- [ ] P7-01 `api/telemetry/__init__.py` — package init
- [ ] P7-02 `api/telemetry/metrics.py` — all 15 Prometheus metric definitions
- [ ] P7-03 `api/telemetry/tracing.py` — OpenTelemetry SDK setup + FastAPI instrumentation
- [ ] P7-04 structlog configuration: JSON format in production, console in dev
- [ ] P7-05 Middleware integration: request_id in all logs, span in all traces
- [ ] P7-06 Grafana dashboard JSON (exported to `monitoring/grafana-dashboard.json`)

## Phase 8: Error Handling (Week 2, Day 10)

### 8.1 Error Infrastructure
- [ ] P8-01 `api/errors.py` — FabricError exception class
- [ ] P8-02 FastAPI exception handlers for all 12 error types
- [ ] P8-03 Error response format: `{error, message, details, request_id, suggestion?, retry_after?}`
- [ ] P8-04 Pydantic validation error → 422 with field-level details
- [ ] P8-05 Graceful degradation: DB down → 503, Redis down → 503 (rate limit + sessions degraded)

## Phase 9: Admin UI (Week 3-4, Day 1-10)

### 9.1 UI Scaffolding
- [ ] P9-01 `ui/package.json` — React 18 + TypeScript + Vite + Tailwind
- [ ] P9-02 `ui/tsconfig.json` + `ui/vite.config.ts`
- [ ] P9-03 `ui/tailwind.config.js` — Tailwind configuration
- [ ] P9-04 `ui/src/api/client.ts` — TanStack Query API client with auth headers
- [ ] P9-05 `ui/src/App.tsx` — React Router with all page routes
- [ ] P9-06 `ui/src/components/Layout.tsx` — sidebar navigation + header
- [ ] P9-07 Shared page state pattern: loading / error / empty / populated

### 9.2 Dashboard Page
- [ ] P9-08 `ui/src/pages/Dashboard.tsx`
- [ ] P9-09 Server count widget + health breakdown
- [ ] P9-10 Recent audit events (last 10)
- [ ] P9-11 Pending approvals count
- [ ] P9-12 Degraded servers list
- [ ] P9-13 Auto-refresh every 30s

### 9.3 Servers Page
- [ ] P9-14 `ui/src/pages/Servers.tsx` — server list table
- [ ] P9-15 `ui/src/pages/ServerDetail.tsx` — server detail view
- [ ] P9-16 `ui/src/components/ServerCard.tsx`
- [ ] P9-17 `ui/src/components/ToolTable.tsx`
- [ ] P9-18 Register modal: name, endpoint, owner, description, labels, team
- [ ] P9-19 Inspect action: loading → diff view (added/removed/changed tools)
- [ ] P9-20 Decommission modal: phase selection + replacement server
- [ ] P9-21 Filters: team namespace, trust level, health status, search

### 9.4 Capability Catalog Page
- [ ] P9-22 `ui/src/pages/Capabilities.tsx` — capability list
- [ ] P9-23 `ui/src/components/CapabilityMapper.tsx`
- [ ] P9-24 Create modal: name (domain:action), domain, schema editors
- [ ] P9-25 Map tool modal: select server → select tool → configure mapping
- [ ] P9-26 Conflict warning banner + link to conflict resolver
- [ ] P9-27 Deprecate modal: grace period + migration guidance
- [ ] P9-28 Alias management: add/remove aliases
- [ ] P9-29 Filters: domain, status, search

### 9.5 Agent Classes Page
- [ ] P9-30 `ui/src/pages/AgentClasses.tsx`
- [ ] P9-31 Create class: name, description, team namespace
- [ ] P9-32 Trust assignment table: server, trust level badge, tool scope
- [ ] P9-33 Create agent token modal: name, rate limit → show token ONCE with copy
- [ ] P9-34 Rotate token modal: grace period hours → new token
- [ ] P9-35 Revoke token: confirm dialog

### 9.6 Policy Editor Page
- [ ] P9-36 `ui/src/pages/PolicyEditor.tsx`
- [ ] P9-37 Rego editor (textarea with syntax highlighting)
- [ ] P9-38 Deploy button + last deployed version info

### 9.7 Audit Log Page
- [ ] P9-39 `ui/src/pages/AuditLog.tsx`
- [ ] P9-40 `ui/src/components/AuditFilter.tsx`
- [ ] P9-41 Filter: event type, actor type, actor ID, date range, capability
- [ ] P9-42 Expandable row for full details JSON
- [ ] P9-43 Export modal: event types, agent classes, date range, format → generate

### 9.8 Approvals Page
- [ ] P9-44 `ui/src/pages/Approvals.tsx`
- [ ] P9-45 Review side panel: full request context + approve/deny
- [ ] P9-46 Bulk approve/deny for low-risk patterns
- [ ] P9-47 Filter: status, agent class, capability

### 9.9 Capability Packs Page
- [ ] P9-48 `ui/src/pages/Packs.tsx`
- [ ] P9-49 Pack cards: name, description, capability count, assigned classes
- [ ] P9-50 Create/edit modal: name, description, team → capability picker
- [ ] P9-51 Assign to agent class modal
- [ ] P9-52 Clone pack action

### 9.10 Alerts Page
- [ ] P9-53 `ui/src/pages/Alerts.tsx`
- [ ] P9-54 Alert history table: fired at, rule name, message, acknowledged status
- [ ] P9-55 Filter: alert type, time range, acknowledged status

### 9.11 Admin Users Page
- [ ] P9-56 `ui/src/pages/AdminUsers.tsx`
- [ ] P9-57 User table: username, email, role badge, team scope, MFA, last login, status
- [ ] P9-58 Invite modal: email, role, team namespace
- [ ] P9-59 Deactivate: confirm dialog

### 9.12 Trust Posture Page
- [ ] P9-60 `ui/src/pages/TrustPosture.tsx`
- [ ] P9-61 Server cards colored by trust level: green/yellow/orange/red
- [ ] P9-62 Unreviewed count banner
- [ ] P9-63 Quick trust change dropdown on cards

### 9.13 Login Page
- [ ] P9-64 `ui/src/pages/Login.tsx` — username + password form
- [ ] P9-65 MFA code prompt (if enabled)
- [ ] P9-66 Lost MFA recovery flow (backup code entry)
- [ ] P9-67 Session auto-refresh (check JWT expiry, re-login if expired)

## Phase 10: Testing (Week 1-4, ongoing)

### 10.1 Unit Tests
- [ ] P10-01 `tests/test_registry.py` — register, inspect, list, get, decommission
- [ ] P10-02 `tests/test_catalog.py` — create, map, resolve, conflict detect, deprecate, alias
- [ ] P10-03 `tests/test_routing.py` — single request, batch request, routing logic
- [ ] P10-04 `tests/test_policy.py` — OPA evaluation: allow, deny, approval-gated
- [ ] P10-05 `tests/test_audit.py` — log, query, export
- [ ] P10-06 `tests/test_approval.py` — create, approve, deny, expire
- [ ] P10-07 `tests/test_packs.py` — create, assign, clone
- [ ] P10-08 `tests/test_alerts.py` — create rule, fire, acknowledge
- [ ] P10-09 `tests/test_auth.py` — agent token lifecycle, admin login/MFA/session
- [ ] P10-10 `tests/test_batch.py` — mixed success/failure, parallel execution
- [ ] P10-11 `tests/test_fallback.py` — timeout → fallback → degradation → alert
- [ ] P10-12 `tests/test_tenant.py` — namespace filtering, cross-team access
- [ ] P10-13 `tests/test_schema_diff.py` — tool changes, breaking flags

### 10.2 Integration Tests
- [ ] P10-14 Registration flow: register → inspect → tools imported (SQLite + PostgreSQL)
- [ ] P10-15 Capability request: resolve → policy → route → normalize → audit (with mock MCP server)
- [ ] P10-16 Approval flow: request → approve → route (end-to-end with Celery)
- [ ] P10-17 Fallback flow: primary timeout → fallback → alert (mock MCP with failure injection)
- [ ] P10-18 Batch flow: 3 parallel requests with mixed results

### 10.3 OPA Policy Tests
- [ ] P10-19 All 10 default policy tests pass (`opa test policies/ -v`)
- [ ] P10-20 Custom policy: cross-team access denied by default
- [ ] P10-21 Custom policy: admin bypasses approval-gated

### 10.4 E2E Tests
- [ ] P10-22 Docker compose: all services start + health checks pass
- [ ] P10-23 Register server → create capability → map tool → create agent → capability request → audit

### 10.5 Test Infrastructure
- [ ] P10-24 `tests/fixtures/mock_mcp_server.py` — in-process mock MCP server
- [ ] P10-25 Test fixtures: SQLite in-memory DB, mock Redis, mock OPA
- [ ] P10-26 Test coverage > 80%

## Phase 11: CI/CD (Week 1, Day 2 + ongoing)

### 11.1 GitHub Actions
- [ ] P11-01 `.github/workflows/ci.yml` — lint + test-sqlite + test-postgres + opa-tests + typecheck + ui-lint
- [ ] P11-02 `.github/workflows/release.yml` — build Docker image + push to ghcr.io + publish to PyPI
- [ ] P11-03 All CI checks green on main branch

### 11.2 Release Readiness
- [ ] P11-04 CHANGELOG.md updated with v0.1.0 entries
- [ ] P11-05 Git tag: `v0.1.0`
- [ ] P11-06 Docker image: `ghcr.io/deghosal-2026/mcp-fabric:v0.1.0`
- [ ] P11-07 PyPI package: `mcp-fabric==0.1.0`
- [ ] P11-08 GitHub Release created with changelog notes

## Phase 12: Documentation (Week 4, final days)

### 12.1 Code Documentation
- [ ] P12-01 All public functions have docstrings
- [ ] P12-02 API reference: OpenAPI spec at `/docs` is accurate + complete
- [ ] P12-03 README Quick Start validated (clone → docker-compose up → first request works)

---

## Summary

| Phase | Tasks | Est. Duration |
|---|---|---|
| P0: Scaffolding | 18 | Day 1-2 |
| P1: Database & Models | 21 | Day 2-3 |
| P2: MCP Client | 7 | Day 3-4 |
| P3: Core Services | 65 | Day 4-8 |
| P4: Middleware | 9 | Day 5-6 |
| P5: API Routes | 46 | Day 6-8 |
| P6: Celery Tasks | 9 | Day 8-9 |
| P7: Telemetry | 6 | Day 9-10 |
| P8: Error Handling | 5 | Day 10 |
| P9: Admin UI | 67 | Day 11-20 |
| P10: Testing | 26 | Ongoing (W1-4) |
| P11: CI/CD | 8 | Day 2 + final |
| P12: Documentation | 3 | Final days |
| **Total** | **180** | **4 weeks** |
