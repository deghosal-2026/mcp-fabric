# Changelog

All notable changes to MCP Fabric will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Initial project setup: README, LICENSE, PRD, spec, architecture docs
- Repository scaffolding: CONTRIBUTING, SECURITY, CODEOWNERS, issue templates

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

[Unreleased]: https://github.com/deghosal-2026/mcp-fabric/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.1.0
