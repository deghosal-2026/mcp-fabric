# Roadmap

## v0.1.0 — Current

- MCP server registry with auto-discovery of tools
- Normalized capability catalog with deprecation lifecycle
- OPA Rego policy engine for access decisions
- Agent classes with identity token management
- Capability packs — bundle and assign to agent classes
- Human-in-the-loop approvals for gated capabilities
- Audit log with event filtering and JSON export
- Trust posture dashboard with per-class trust levels
- Operational alerts for server health and security issues
- Admin user management with RBAC (Admin/Editor/Viewer) and MFA
- Dashboard with stat cards and recent activity panels
- 474 automated tests (backend, UI, OPA, E2E)

## v0.2.0 — Planned (Q3 2026)

- Advanced routing engine (health/latency/fallback-aware)
- Conflict detection across similar tools
- Capability-to-tool mapping UI from the catalog
- Persistent webhook storage (DB-backed, not in-memory)
- Webhook auth middleware enforcement

## v0.3.0 — Planned (Q4 2026)

- Multi-tenant scopes and namespace isolation
- Analytics and usage heatmaps
- Webhook integrations for external tooling
- Performance benchmarks and caching improvements

## v0.4.0 — Planned (Q1 2027)

- Reference integrations with popular OSS MCP servers
- API versioning and SDK
- OpenAPI-generated client libraries
- Helm chart for Kubernetes deployment

## GA (v1.0.0)

Stabilization, security audit, production hardening, and enterprise features.
