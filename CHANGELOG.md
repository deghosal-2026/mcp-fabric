# Changelog

All notable changes to MCP Fabric will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Planned
- Advanced routing engine (health/latency/fallback-aware)
- Multi-tenant scopes and namespace isolation
- Performance benchmarks and caching improvements

## [v0.4.0] — 2026

### Added

#### Trust Posture — Pack Cohesion & Semantic-Band Detection (#439)
- **Problem:** A tightly-clustered pack (a "semantic band") is far more exposed to adversarial resource confusion than a scattered pack of the same size — catch falls to ~0.02 vs ~0.88.
- **Solution:** An independent **cohesion axis** on the Trust Posture dashboard computes similarity dispersion of resources within each pack via the stored resource embedding. Packs that form a tight semantic cluster are flagged, with guidance recommending per-resource identity (pack=1) for the most sensitive bands.
- `compute_pack_cohesion()` — similarity dispersion (variance/std-dev of pairwise embedding similarity) within a pack, independent of breadth
- `GET /admin/trust-posture/cohesion` returns `{ pack_id, pack_name, resource_count, cohesion_score, is_semantic_band }`
- `PackCohesionCard` UI component with risk coloring + tooltip linking to the pack-granularity guide
- Fixture test: two packs of size 64 (scattered vs tight semantic band) → cohesion clearly separates, band flagged

#### Nightly Adversarial Resource-Confusion Fuzz Harness (λ-clustered) (#440)
- **Problem:** Uniform-random redirect fuzzing (λ=∞) missed the semantically targeted attacker who collapses catch on a semantic band.
- **Solution:** A nightly λ-clustered fuzz harness models similarity-targeted redirects across the λ spectrum (∞→1). λ=∞ matches the closed-form `catch = 1 − (P−1)/(R−1)` baseline; λ=1 reproduces near-zero catch on semantic bands.
- Emits expected-vs-actual catch rate as structured JSON, independent of PR-gate CI, deterministic seeds
- Alerts when pack cohesion drives catch below the configured threshold
- `docs/guides/security-testing.md` documents λ semantics and how to run/read results

#### Agent-Level Permissions — Read-Only vs Destructive Tool Classification (#445)
- **Problem:** Tool trust was described in docs only; mutating tools were not distinguished at the permission layer.
- **Solution:** A per‑tool `tool_class` (read_only/mutating) model enforced at the request boundary and surfaced in the audit trail. Read-scoped agents can call read-only tools; mutating calls are denied (403/denial) unless trusted under approval policy.
- OPA Rego rules + tests (read-only pass, write blocked, trusted write allowed)
- `docs/guides/security.md` boundary contract for autonomous agents

#### Structured Policy-Denial Feedback to Agents (#443)
- **Problem:** Policy denials surfaced as opaque failures, so agents blind-retried the same verb.
- **Solution:** Denials are now returned over the MCP tool-result channel as a structured **`DenialResult`** with an explicit `"denied"` type — `{ impact: "none", reason: <rule id>, suggestion: <next allowed step> }` — so agents can branch instead of retrying.
- Denial recorded in the audit trail; blind-retry count measurably reduced vs opaque-error control

#### Many-to-One Capability-Mapping Collision Detection + Review Gate (#441)
- **Problem:** Multiple distinct tools normalized to the same capability could route ambiguously, enabling confused-deputy confusion.
- **Solution:** Detect ≥2 distinct tools mapping to the same capability at mapping time and require explicit review/approval before the colliding mapping becomes routable.
- Immutable raw call context (server identity + tool + args) passed to OPA alongside the normalized capability, enabling origin-aware denial
- Admin UI surfaces collision list on the Reviews page with distinct visual treatment; confused-deputy fuzz case added

#### Fail-Closed Re-Inspection + Stale-Review Age Alerts (#444)
- **Problem:** A failed/timeout re-inspection could be recorded as `unchanged`, failing open.
- **Solution:** Re-inspection failure/timeout now marks mappings `stale-unverified` (excluded from routing) with retry/backoff — never `unchanged`. Every pending review carries `pending_since`/deadline; un-cleared items trigger deadline alerts (email/dashboard). A third state — **limbo** — is tracked explicitly (visible and time-boxed).

#### External Staleness Watchdog — Independent of the Review Queue (#446)
- **Problem:** The staleness monitor shared liveness with the queue it watches; a queue failure silenced the alarm.
- **Solution:** A standalone watchdog process/service architected as a sidecar or separate cron context with read-only access to item timestamps — it never writes to the queue, exposes its own **heartbeat**, and a **dead-man switch** raises a human-visible alert if the watchdog stops checking in.
- Test: killing the review-queue service entirely does NOT silence staleness alerts

#### Review Queue Prioritization — Unreachable vs Genuinely Changed (#447)
- **Problem:** Unreachable servers buried real schema changes in the review queue.
- **Solution:** Every review item carries a `failure_class` (`unreachable` / `drifted` / `schema_mismatch` / `timeout`), written at re-inspection. UI separates unreachable items with a distinct section/filter; bulk "retire all unreachable" without per-item review; grouped notifications (`unreachable ≠ drift`) and unreachable items excluded from the reviewer critical tally.
- Backend: `GET /mappings/stale?failure_class=`, `GET /mappings/summary`, `POST /mappings/retire`
- Queue of 50 unreachable + 2 changes → real changes rise to top

#### HITL Approval Fatigue Mitigation — Reversibility + Bulk Approve + Expiring Envelopes (#442)
- **Problem:** Reviewers were prompted on safe, reversible actions, causing approval fatigue and real anomalies getting buried.
- **Solution:** Reversibility-based auto-approval (reads/undo-able actions auto-approved; writes/leaving-the-system prompted), **bulk-approve** grouping with explicit anomaly markers, and **scoped expiring approval envelopes** (human grants a budget, e.g., 10 promotes to staging within the hour; deterministic validator burns it down; only out-of-envelope actions escalate).
- Tests: 50-action workload → prompt count is a small subset; over-budget/new-env/schema-change always escalates

### Fixed
- `ApprovalEnvelope` model/migration drift — missing `TimestampMixin` mapped `created_at` in the migration but not the ORM (production `AttributeError`); tests masked via `metadata.create_all`
- Unreachable 409 path in `bulk_approve` — `contextlib.suppress` swallowed `InsufficientEnvelopeError`, so exhausted envelopes returned 200 instead of escalating
- Playwright docker E2E harness — image bumped to `v1.62.1-jammy` to match `@playwright/test ^1.62.1`; `test-e2e` command paths/reporter fixed
- IP rate limiter now bypassed when `ENVIRONMENT=testing` (test-stack 429s during E2E)
- `TrustPosture.test.tsx` mock missing `fetchPackBreadth` export

### Security
- Pack cohesion flag — tight semantic bands surfaced for per-resource identity recommendation
- Tool-class enforcement at request/protocol level, not docs-only
- Fail-closed re-inspection (never fails open), deadline alerting, limbo state time-boxed
- Origin-aware OPA denial closes confused-deputy/many-to-one collision vector
- Externally-architected staleness watchdog with heartbeat + dead-man switch

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

[Unreleased]: https://github.com/deghosal-2026/mcp-fabric/compare/v0.4.0...HEAD
[v0.4.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.4.0
[v0.3.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.3.0
[v0.2.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.2.0
[v0.1.0]: https://github.com/deghosal-2026/mcp-fabric/releases/tag/v0.1.0
