# Roadmap

## v0.1.0 — Shipped

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

## v0.3.0 — Shipped

- Schema-digest mappings — detect tool schema drift
- OPA deny_stale_mapping + untrusted_write rules
- Mapping review workflow (stale/approve/reject)
- Reviews admin UI page
- PackBreadthWarning for over-broad packs
- 326 Python tests, 31 OPA tests, 75 E2E tests

## v0.4.0 — Current (shipped)

- Trust Posture: pack cohesion score + semantic-band detection (#439)
- Nightly λ-clustered adversarial resource-confusion fuzz harness (#440)
- Agent-level permissions — read-only vs destructive tool classification (#445)
- Structured policy-denial feedback to agents (#443)
- Many-to-one capability-mapping collision detection + review gate (#441)
- Fail-closed re-inspection + stale-review age alerts (#444)
- External staleness watchdog with heartbeat + dead-man switch (#446)
- Review queue prioritization — unreachable vs genuinely changed (#447)
- Approval fatigue mitigation — reversibility split + bulk approve + expiring envelopes (#442)

## v0.5.0 — Planned (Q2 2027)

- Advanced routing engine (health/latency/fallback-aware)
- Conflict detection across similar tools
- Capability-to-tool mapping UI
- Persistent webhook storage

## Gap — Planned

- Multi-tenant scopes and namespace isolation
- Analytics and usage heatmaps
- Performance benchmarks and caching improvements

## GA (v1.0.0)

Stabilization, security audit, production hardening, and enterprise features.
