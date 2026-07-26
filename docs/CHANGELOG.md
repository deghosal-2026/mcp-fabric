# Changelog

All notable changes to MCP Fabric will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup: README, LICENSE, PRD, spec, architecture docs
- Repository scaffolding: CONTRIBUTING, SECURITY, CODEOWNERS, issue templates

## [Unreleased]

### Added
- Initial project setup: README, LICENSE, PRD, spec, architecture docs
- Repository scaffolding: CONTRIBUTING, SECURITY, CODEOWNERS, issue templates

## [0.3.0] — 2026-07-25

### Added

#### Schema-Digest Mappings — Detect Tool Schema Drift
- **Problem:** When a registered MCP server's tool schemas changed, existing capability mappings silently pointed to outdated schemas. Routing continued to use stale mappings.
- **Solution:** Each CapabilityMapping now stores a SHA-256 digest of (tool_name + input_schema + output_schema). On re-inspection, schema changes mark affected mappings as stale. Routing filters to active + digest-matched only.

#### Architecture
- New DB columns: `tool_schema_digest` (VARCHAR(64)), `status` (VARCHAR(20)) on `capability_mappings`
- New DB table: `mapping_reviews` with FK, previous/new digests, decision, reason, reviewer
- Alembic migration with backfill (SHA-256 via join on server_tools)
- `_compute_tool_digest()` in CapabilityService for deterministic JSON hashing
- RegistryService `inspect()` marks mappings stale on schema change/removal
- RoutingService `select_server()` filters by `status='active'` + digest match; `NoServerFoundError` on no match
- `ToolNotFoundError` for mapping to non-existent tools

#### OPA Policies
- `deny_stale_mapping` — denies if mapping_status != "active"
- `untrusted_write` — denies write tools on unreviewed servers
- `raw_context` — identity function for debug/audit
- `PolicyService.evaluate()` passes `mapping_status`, `tool_name`; returns new decision fields

#### API
- `GET /admin/mappings/stale` — list stale mappings
- `POST /admin/mappings/{id}/review` — approve or reject
- `GET /admin/capabilities/{id}/ambiguity` — mapping details

#### Admin UI
- Reviews page with Approve/Reject workflow, name resolution, toasts
- Sidebar Reviews link, Trust Posture "Pending Reviews" button
- 7 E2E spec files updated, 75 mock tests passing

#### Testing
- 5 new backend tests (schema-digest, mapping review)
- 10 new OPA Rego tests (31 total)
- Docker screenshots captured (13 total)

### Security
- Schema-digest routing prevents stale mapping use
- OPA deny_stale_mapping and untrusted_write as defense-in-depth
- MappingReview audit trail for every decision
- ToolNotFoundError prevents phantom mappings

## [0.2.0] — 2026-07-25

### Added

#### Resource-Aware Policy (Dynamic Resource Dimensions)
- **Problem:** The OPA policy engine evaluated `(agent_class, capability, trust_level)` — the verb only. It could answer "may agent:release-engineer use `deployment:promote`?" but not "may agent:release-engineer use `deployment:promote` on `env:prod`?"
- **Solution:** A dynamic resource dimension system lets platform engineers define per-capability which resource dimensions constrain it (e.g., `env`, `tenant`, `service`), bind allowed values to agent identities and capability packs, and let OPA evaluate `(capability, resource)` pairs at request time.
- **Key insight from community feedback (Alexey Spinov):** Verb-only policy passes 5/5 cases where the capability is correct but the object differs. Resource-binding closes that gap.

#### Architecture
- **4 new DB tables:** `resource_dimensions`, `dimension_value_map`, `identity_resource_bindings`, `pack_resource_bindings` with proper FKs, unique constraints, and cascade deletes
- **OPA Rego extension:** New `resource_allowed` gate in the `allow` rule, `dim_allowed` helper, `resource_violations` set for audit detail. Dimensions come from `input.declared_dimensions` (dynamic, not hardcoded)
- **Routing service:** `resolve_resources()` extracts dimension values from request params (via `dimension_value_map`) or explicit `resources` field. `merge_bindings()` computes identity ∩ pack intersection per dimension
- **Policy service:** `identity_resources` and `request_resources` passed to OPA. Cache key includes resource data with shorter TTL (60s vs 300s)
- **Audit:** `resource_check` field captured in audit event `details` JSONB, queryable via `resource_violation=true` filter
- **Design choice:** Dynamic dimension registry (Approach C) preferred over hardcoded dimensions — teams add dimensions at runtime without code changes

#### API (10 new endpoints)
- `POST/GET/DELETE /admin/capabilities/{id}/dimensions` — manage resource dimensions per capability
- `POST /admin/capabilities/{id}/dimensions/{dim_id}/value-map` — param-to-dimension extraction mapping
- `POST/GET/DELETE /admin/agents/{identity_id}/resources` — manage identity resource bindings
- `POST/GET/DELETE /admin/packs/{pack_id}/resources` — manage pack resource bindings

#### Admin UI
- **Capabilities page** — "Dimensions" button opens modal to add/remove resource dimensions
- **Agent Classes page** — "Bindings" button opens modal to manage identity resource bindings
- **Packs page** — "Bindings" button opens modal to manage pack resource bindings
- **Approvals page** — Resource constraint section shown in review panel when present
- `CapabilityRequest` schema gains optional `resources` field for explicit dimension values

#### Testing (47 new tests)
- **13 backend integration tests** — dimension CRUD, value maps, identity/pack binding CRUD, `merge_bindings` intersection, `resolve_resources` extraction, cascade deletes
- **12 new OPA Rego tests** — resource_allowed pass/fail, empty identity, multi-value, missing dimensions, database query constraints, rollback constraints (21 total)
- **2 new merge_bindings tests** — pack-only and identity-only paths
- **3 new Playwright E2E tests** — dimensions modal, packs bindings modal, approval resource violation display
- **7 new UI test cases** (TC-PAGE-037 to 043) — detailed interaction specs for dimension/binding modals and resource violation display

#### Documentation
- PRD updated: Problem 5 (verb-only policy), Journey 30 (resource-constrained policy), Feature 10 (resource-aware policy), glossary terms
- Spec updated: DB schema (3.20-3.23), OPA policy (5.2), request lifecycle (Step 3.5), error catalog, Pydantic models, ERD, indexing, metrics, milestones, tech tradeoffs (Section 25)
- Design doc: `docs/resource-aware-policy-design.md`
- WBS: Phase 13 (12 tasks, 184h)
- 3 new E2E screenshots added

### Fixed
- `fetcher()` now handles 204 No Content responses (DELETE endpoints were crashing the UI)
- Audit `resource_violation` filter pagination — in-memory filter no longer applies offset/limit before filtering
- Param path resolution — `params.` prefix in `param_path` is now stripped correctly
- Hardcoded `capability_dimensions` map removed from Rego — dimensions now come from `input.declared_dimensions`
- `set_value_map` now deletes old value maps before inserting (no orphan rows)
- `create_dimension` validates capability exists before inserting (returns 404, not 500)
- `IntegrityError` on duplicate dimensions/bindings returns 409 (not 500)
- `ResourceConflictError` added for duplicate detection
- Source/param_path consistency validated in `set_value_map`
- Resource check in routing service now queries identity from auth context (was passing `None`)
- OPA evaluate called with proper `agent_class` (not empty string)
- Cache TTL reduced to 60s for resource-specific keys (was 300s)
- Explicit resources fallback fixed — now checked even when value_map exists
- Param value extraction uses `str(val)` instead of strict `isinstance(val, str)` check
- Approvals page no longer crashes when `request_params.resources` is `null`
- Audit failure logging added (was silently suppressed)
- N+1 query eliminated — `selectinload` used for dimension value_maps
- `DimensionValueMap` model now has `created_at` via `TimestampMixin`
- All existing OPA tests updated to include `declared_dimensions` in input

## [0.1.0] — 2026-07-22

### Added

#### Core Platform
- Server registry — register, inspect, list, get, decommission MCP servers with auto-inspected tool definitions (Journey 1, 11)
- Schema diff on re-inspect — breaking changes flagged, diff visible in UI, version history in tool_versions (Journey 10)
- Capability catalog — create, map, list, aliases, deprecate with normalized input/output schemas (Journey 12, 27)
- Conflict detection — flag when two servers map to the same capability, UI-driven resolution (Journey 9)
- Routing engine — single + batch capability request with policy-checked, audited responses (Journey 2, 23)
- Fallback chain — primary server timeout → fallback server → degradation logged → alert triggered (Journey 6)
- OPA policy engine — allow/deny/approval-gated Rego policy evaluation (Journey 2, 7)
- Approval-gated workflow — human-in-the-loop review for sensitive capabilities (Journey 7)

#### Authentication & Authorization
- Agent auth — token create, rotate, revoke, connect, capability surface discovery (Journey 5, 21, 29)
- Admin auth — login with password + MFA (TOTP), JWT session, role-based access (Journey 26, 29)
- RBAC roles — admin (full control), editor (team-scoped), viewer (read-only)
- Token lifecycle — bcrypt-hashed storage, grace period for rotation, immediate revocation
- Rate limiting — per-agent (100 req/min default) and per-IP (20 req/min)

#### Capability Discovery
- Agent capability surface returned on connect — scoped list of available capabilities (Journey 5)
- Full capability detail — input/output schemas, trust levels, deprecation status (Journey 22)
- Capability change webhooks — notify agents of added, deprecated, or schema-changed capabilities (Journey 22)

#### Error Handling
- 12 structured error types — consistent JSON envelope with error code, message, details, request_id, suggestion, retry_after (Journey 13)
- Error catalog — invalid_parameter, invalid_token, access_denied, capability_not_found, rate_limited, fabric_degraded, and more

#### Audit & Compliance
- Audit pipeline — capture every capability request, denial, policy change, approval decision (Journey 4, 18)
- Audit export — JSON and CSV format for compliance reporting (Journey 18)
- Append-only event log — immutable, no UPDATE or DELETE on audit rows
- Configurable retention — default 90 days via `AUDIT_RETENTION_DAYS`

#### Admin UI
- 12-page admin dashboard — dashboard, servers, capabilities, audit log, approvals, agent classes, alerts, users, trust posture, packs, policies, webhooks
- Every page handles loading, empty, error, and populated states
- All operations available via UI and API (UI is a consumer of the API)

#### Health & Telemetry
- Health endpoints — `/health` (detailed), `/health/ready` (readiness), `/health/live` (liveness)
- Prometheus metrics — 15 metric families: request count/duration, routing overhead, server health, policy decisions, approvals, audit events, DB/Redis connections, Celery tasks
- OpenTelemetry tracing — FastAPI, SQLAlchemy, Redis instrumentation
- Structured logging — structlog with JSON output
- Docker HEALTHCHECK — built-in container health monitoring

#### Background Workers (Celery)
- Server health checker — periodic ping of registered MCP servers (every 30s)
- Approval notification — email/Slack/webhook delivery for pending approvals
- Alert delivery — notification via configured channels
- Audit export generator — async CSV/JSON export for compliance
- Audit log retention cleanup — daily removal of expired entries (3 AM)

#### Infrastructure
- Dual database support — SQLite (local dev, zero-config) and PostgreSQL (production, concurrent access)
- Docker Compose — single command to run full stack (API, UI, PostgreSQL, Redis, Celery worker/beat)
- Dockerfile — multi-stage build, non-root user, health check
- Poetry — deterministic Python dependency management
- Makefile — 19 targets covering dev, test, lint, migrate, clean operations
- Alembic — database migration management

#### Capability Packs
- Create, assign, edit, clone capability packs (Journey 3)
- Pack-to-agent-class assignment — agents see only their assigned capabilities
- Self-documenting — packs show which capabilities are included and their trust levels

#### Routing Rules
- Priority-based ordering — explicit server preference without conditions (Journey 9)
- Parameter-based routing — route based on request parameters (e.g., `file_pattern` present)

#### Multi-Team Support
- Team namespaces — row-level filtering on all queries (Journey 20)
- Team-scoped admin roles — editors manage only their team's servers

#### Admin User Management
- Full admin lifecycle — invite, setup, login with MFA, session, deactivate, revoke (Journey 26)
- Password policy — 12-char minimum, complexity requirements, history (5), lockout (5 fails)
- MFA setup — QR code, TOTP verification, 8 backup codes

#### Tooling
- Test suite — 75% unit, 20% integration, 5% E2E (P0+P1 scenarios)
- OPA policy tests — Rego test coverage for all policy rules
- Ruff linting — E, F, I, N, W, UP, B, C4, SIM rules, line-length 100
- mypy strict mode — type checking on all public functions
- ESLint + Prettier — TypeScript code quality
- GitHub Actions CI — automated test and lint on push/PR

### Documentation
- PRD — 29 user journeys, 9 feature areas, success metrics, glossary (docs/PRD.md)
- Technical spec — architecture, schema, API contract, OPA integration, Celery tasks, test strategy (docs/spec.md)
- Architecture overview — component diagram, request lifecycle, state management, scaling boundaries (docs/ARCHITECTURE.md)
- Design document — auth design, state machines, sequence diagrams, caching strategy, concurrency model (docs/DESIGN.md)
- User guide — admin UI walkthrough with screenshots (docs/user-guide.md)
- Development guide — local setup, testing, migrations (docs/guides/development.md)
- Deployment guide — Docker Compose, health checks, backup/restore, blue-green upgrade (docs/guides/deployment.md)
- Configuration reference — all env vars, feature flags, example .env (docs/guides/configuration.md)
- Monitoring setup — 15 Prometheus metrics, Grafana dashboard, Alertmanager rules, OpenTelemetry (docs/guides/monitoring.md)
- Security guide — auth model, RBAC, token lifecycle, CORS, threat mitigations (docs/guides/security.md)
- Troubleshooting guide — common issues, diagnostic steps, solutions (docs/guides/troubleshooting.md)
- CONTRIBUTING.md — project structure, code style, how to contribute
- SECURITY.md — vulnerability reporting policy

[Unreleased]: https://github.com/deghosal-2026/mcp-fabric/compare/v0.2.0...HEAD
[0.3.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.3.0
[0.2.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.2.0
[0.1.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.1.0
