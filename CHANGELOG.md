# Changelog

All notable changes to MCP Fabric will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Advanced routing engine (health/latency/fallback-aware)
- Multi-tenant scopes and namespace isolation
- Performance benchmarks and caching improvements

## [Unreleased]

### Planned
- Advanced routing engine (health/latency/fallback-aware)
- Multi-tenant scopes and namespace isolation
- Performance benchmarks and caching improvements

## [v0.3.0] — 2026-07-25

### Added

#### Schema-Digest Mappings — Detect Tool Schema Drift
- **Problem:** When a registered MCP server's tool schemas changed (e.g., a required parameter was added or a return type changed), existing capability mappings silently pointed to outdated schemas. Routing continued to use stale mappings, causing runtime failures or security bypasses.
- **Solution:** Each CapabilityMapping now stores a SHA-256 digest of `(tool_name + input_schema + output_schema)` at creation time. On server re-inspection, any schema change marks the affected mapping as `stale`. Routing only considers mappings with `status='active'` whose stored digest matches the current tool schema.

#### Architecture
- **New DB columns:** `capability_mappings.tool_schema_digest` (VARCHAR(64)), `capability_mappings.status` (VARCHAR(20), default `'active'`)
- **New DB table:** `mapping_reviews` with FK to `capability_mappings`, storing previous/new digests, decision, reason, reviewer
- **Alembic migration** with backfill: computes SHA-256 for existing mappings via join on `server_tools`
- **CapabilityService:** `_compute_tool_digest()` static method, `create_mapping()` stores digest, `review_mapping()` approve/reject with digest recomputation
- **RegistryService:** `inspect()` marks affected mappings stale when tools are removed or schemas change
- **RoutingService:** `select_server()` filters by `status='active'` and verifies `mapping.tool_schema_digest` matches current tool; raises `NoServerFoundError` when no valid candidate exists
- **New exception:** `ToolNotFoundError` for mapping attempts to non-existent tools

#### OPA Policy Extension (3 new rules)
- `deny_stale_mapping` — denies routing when `mapping_status != "active"`
- `untrusted_write` — denies write operations (non-read-only tools) on unreviewed servers
- `raw_context` — identity function returning raw input for debugging/audit
- `PolicyService.evaluate()` now passes `mapping_status` and `tool_name`; returns `deny_stale_mapping` and `untrusted_write` flags
- 10 new Rego tests (31 total)

#### API (3 new endpoints)
- `GET /admin/mappings/stale` — list stale mappings for admin review
- `POST /admin/mappings/{id}/review` — approve (updates digest, reactivates) or reject (disables permanently)
- `GET /admin/capabilities/{id}/ambiguity` — show all mappings with status/digest details

#### Admin UI
- **Reviews page** (`/reviews`) — table of stale mappings with server/capability name resolution, Approve/Reject buttons, toast notifications
- **Sidebar** — "Reviews" nav link (12th item)
- **Trust Posture** — "Pending Reviews" button linking to review page
- 2 new Playwright test sections, 7 E2E spec files updated

#### Testing (326 total tests, 31 OPA)
- 3 schema-digest service tests (creation, drift detection, routing selection)
- 2 mapping review tests (approve with digest update, reject with status change)
- 10 new OPA Rego tests (stale denial, untrusted write, raw context)
- 75 mock Playwright tests passing; Docker screenshots captured

### Fixed
- mypy error: `CapabilityService.list` shadowing built-in `list` — resolved with `from __future__ import annotations` + `typing.List`
- Ruff E501 line-length in capability service and test files
- Import sorting in admin.py, test files

### Security
- Schema-digest bound routing prevents use of stale mappings
- OPA `deny_stale_mapping` rule provides defense-in-depth even if routing layer is bypassed
- OPA `untrusted_write` rule blocks write operations on unreviewed servers
- `MappingReview` audit trail for every approve/reject decision
- `ToolNotFoundError` prevents mapping to non-existent tools

## [v0.2.0] — 2026-07-25

### Added

#### Resource-Aware Policy (Dynamic Resource Dimensions)
- **Problem:** The OPA policy engine evaluated `(agent_class, capability, trust_level)` — the verb only. It could not answer resource-scoped queries like "may agent use `deployment:promote` on `env:prod`?"
- **Solution:** A dynamic resource dimension system lets platform engineers define per-capability which resource dimensions constrain it (e.g., `env`, `tenant`, `service`), bind allowed values to agent identities and capability packs, and let OPA evaluate `(capability, resource)` pairs at request time.
- **Key insight:** Verb-only policy passes 5/5 cases where the capability is correct but the object differs. Resource-binding closes that gap.

#### Architecture
- **4 new DB tables:** `resource_dimensions`, `dimension_value_map`, `identity_resource_bindings`, `pack_resource_bindings` with proper FKs, unique constraints, and cascade deletes
- **OPA Rego extension:** New `resource_allowed` gate, `resource_violations` set, 12 new Rego tests (21 total)
- **Routing service:** `resolve_resources()` extracts dimension values from params; `merge_bindings()` computes identity ∩ pack intersection per dimension
- **Policy service:** `identity_resources` and `request_resources` passed to OPA; cache key includes resource data with shorter TTL (60s)
- **Audit:** `resource_check` field in audit event `details` JSONB, queryable via `resource_violation=true` filter

#### API (10 new endpoints)
- `POST/GET/DELETE /admin/capabilities/{id}/dimensions` — manage resource dimensions per capability
- `POST /admin/capabilities/{id}/dimensions/{dim_id}/value-map` — param-to-dimension mapping
- `POST/GET/DELETE /admin/agents/{identity_id}/resources` — manage identity resource bindings
- `POST/GET/DELETE /admin/packs/{pack_id}/resources` — manage pack resource bindings

#### Admin UI
- Capabilities page — "Dimensions" button/modal for resource dimensions
- Agent Classes page — "Bindings" button/modal for identity resource bindings
- Packs page — "Bindings" button/modal for pack resource bindings
- Approvals page — Resource constraint section in review panel
- `CapabilityRequest` schema gains optional `resources` field

#### Testing (47 new tests)
- 13 backend integration tests — dimension CRUD, value maps, binding CRUD, merge/resolve, cascades
- 12 new OPA Rego tests (21 total)
- 3 new Playwright E2E tests — dimensions, bindings, approval resource display
- 2 new merge_bindings tests

### Fixed
- `fetcher()` handling of 204 No Content responses
- Audit `resource_violation` filter pagination (in-memory filter no longer applies offset/limit before filtering)
- Param path resolution — `params.` prefix stripped correctly
- Hardcoded `capability_dimensions` map removed from Rego (dynamic via `input.declared_dimensions`)
- `IntegrityError` on duplicate dimensions/bindings returns 409 (not 500)
- Resource check passes identity from auth context (was `None`)
- OPA evaluate passes proper `agent_class` (not empty string)
- Cache TTL reduced to 60s for resource-specific keys
- Approvals page no longer crashes when `request_params.resources` is `null`
- N+1 query eliminated — `selectinload` for dimension value_maps
- Param value extraction uses `str(val)` instead of strict `isinstance` check

## [v0.1.0] — 2026-07-25

### Added
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

### Fixed
- 170 mypy type errors across 41 files (strict mode)
- 32 ruff lint errors (unused imports, line length, import sorting)
- Webhook routes now enforce agent_id ownership
- Admin self-deactivation guard
- MFA verify/recover moved into service layer
- Capability mapping creation moved into service layer
- CI pipeline with 6 parallel jobs (lint, typecheck, tests, OPA, UI)

### Security
- Auth middleware skips health/metrics endpoints
- Webhook routes enforce agent_id match via request.state.agent_id
- Self-deactivation prohibited for admin accounts

[Unreleased]: https://github.com/deghosal-2026/mcp-fabric/compare/v0.3.0...HEAD
[v0.3.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.3.0
[v0.2.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.2.0
[v0.1.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.1.0
