# Phase 14: v0.3.0 — Security Hardening & Compliance — ✅ SHIPPED

> **Feature:** Resource-Aware Policy completions — docs, tests, audit, UI, schema-digest
> **Tasks:** 12 across 4 milestones · **Effort:** ~200h (5 weeks)
> **Dependencies:** v0.2.0 (shipped)
> **Target version:** v0.3.0 · **Shipped:** Jul 25, 2026
> **GitHub milestones:**
> - [M1 — Foundation: Docs & Tests](https://github.com/deghosal-2026/mcp-fabric/milestone/2) — ✅
> - [M2 — Backend: Audit & Observability](https://github.com/deghosal-2026/mcp-fabric/milestone/3) — ✅
> - [M3 — Frontend: UI Safety Signals](https://github.com/deghosal-2026/mcp-fabric/milestone/4) — ✅
> - [M4 — Security: Schema-Digest Mappings](https://github.com/deghosal-2026/mcp-fabric/milestone/5) — ✅

---

## Milestone M1 — Foundation: Docs & Tests (due Aug 1)

### M1-01: Pack Granularity Guidance Doc ([#407](https://github.com/deghosal-2026/mcp-fabric/issues/407)) — ✅ Done

**Files to create:**
- `docs/guides/pack-granularity.md` — NEW

**Description:** Document the catch-rate formula `catch = 1 - (P-1)/(R-1)` with plain-English intuition, recommended pack size thresholds by risk level, decision tree for splitting packs, worked example with real capability names, and a table of `pack_size → catch_rate` for common R values (128, 256, 512, 1024). Link to Alexey Spinov's external validation.

**Checklist:**
- [x] Formula explained with intuition (not just math)
- [x] Threshold table for R=128/256/512/1024
- [x] Risk-level recommendations: write (≤8), read (≤32), read-only low-sensitivity (≤64)
- [x] Decision tree: "When to split a pack" with blast-radius and criticality guidance
- [x] Worked example with real capability names (e.g. `deployment:promote`)
- [x] Link to Alexey's statistical validation
- [ ] Cross-reference from SECURITY.md and Trust Posture dashboard docs — ⏳ pending #410, #409

**Success Criteria:**
- ✅ Formula is explained with plain-English intuition
- ✅ Threshold table covers all common R values
- ✅ Decision tree actionable for platform engineers
- ✅ Worked example uses real capability names
- [~] Links are bidirectional (guide → SECURITY ✅, SECURITY → guide ⏳ #410)

---

### M1-02: SECURITY.md Threat Model Update ([#410](https://github.com/deghosal-2026/mcp-fabric/issues/410)) — ✅ Done

**Files to edit:**
- `SECURITY.md` — add "Intra-Pack Confused-Deputy Residual" section under Threat Mitigations
- `docs/PRD.md` — brief acknowledgment in Feature 10

**Description:** Document the architectural constraint: identity-binding scope is bounded by pack breadth. Include the formula, actionable recommendation (narrower packs, split by environment), and audit visibility note. Add a row to the Threat Mitigations table. Update PRD.md Feature 10 to acknowledge the residual.

**Checklist:**
- [x] Add "Intra-Pack Confused-Deputy Residual" section to SECURITY.md
- [x] Include formula: `catch = 1 - (pack_size - 1) / (total_resources_in_domain - 1)`
- [x] Include table: pack=1→100%, pack=16→97%, pack=64→88%, pack=R→0%
- [x] Add actionable recommendation (narrower packs)
- [x] Add audit visibility note for compliance teams
- [x] Add link to pack-granularity.md
- [x] Add row to Threat Mitigations table
- [x] Update PRD.md Feature 10 with residual acknowledgment

**Success Criteria:**
- ✅ SECURITY.md has the new section with formula and explanation
- ✅ Threat Mitigations table updated
- ✅ PRD.md updated with brief residual acknowledgment
- [~] Reviewed by at least one security engineer — ⏳ needs human review

---

### M1-03: Giant Pack Regression Test ([#412](https://github.com/deghosal-2026/mcp-fabric/issues/412)) — ✅ Done

**Files to edit:**
- `tests/services/test_resource_policy.py` — add 2 new test functions

**Description:** Two regression tests that document the architectural bounds of identity-binding:

1. `test_giant_pack_zero_protection_is_expected` — P=R=512 resources, 1000 confused-deputy mutations, assert exactly 0 blocked (catch=0.0000). Documents that identity-binding provides zero protection when pack covers all resources.

2. `test_per_resource_identity_full_close` — P=1 resource, 1000 mutations, assert exactly 1000 blocked (catch=1.0000). Documents the other end of the spectrum.

Both tests must complete in <5s. Test comments document the architectural constraint explicitly.

**Checklist:**
- [x] Add `test_giant_pack_zero_protection_is_expected` to `tests/services/test_resource_policy.py`
- [x] Setup: 512 resources in domain, 1 pack with all 512, assign to identity
- [x] Generate 1000 confused-deputy mutations (same capability, random resource within pack)
- [x] Assert: blocked_count == 0, catch_rate == 0.0
- [x] Add `test_per_resource_identity_full_close` (P=1 scenario)
- [x] Setup: 512 resources, 1 pack with 1 resource, assign to identity
- [x] Generate 1000 mutations → assert exactly 1000 blocked
- [x] Comment documents architectural constraint in both tests
- [x] Both complete in <5s (0.25s)
- [x] `ruff check` passes
- [x] Run `pytest tests/services/test_resource_policy.py -v -k giant` to verify

**Success Criteria:**
- ✅ `test_giant_pack_zero_protection_is_expected` asserts exactly 0 blocked
- ✅ `test_per_resource_identity_full_close` asserts exactly 1000 blocked
- ✅ Both complete in <5 seconds (0.25s)
- ✅ `ruff check` passes
- ✅ Both pass in CI
- [~] Failure triggers human review (architectural constraint changed) — ⏳ needs CI verification

---

### M1-04: Confused-Deputy Fuzz Test Script ([#411](https://github.com/deghosal-2026/mcp-fabric/issues/411)) — ✅ Done

**Files created:**
- `tests/security/test_confused_deputy_fuzz.py` — fuzz harness (8 scenarios, CLI, JSON report)
- `.github/workflows/nightly.yml` — nightly CI schedule (6 AM UTC + manual dispatch)
- `docs/guides/security-testing.md` — usage guide

**Description:** Standalone fuzz-test harness with 8 scenarios. Each scenario runs 40,000 iterations x 3 seeds. Empirically validates catch rate against Alexey's closed form (max error < 0.001). Outputs structured JSON report. CLI mode with configurable `--resources --iterations --seeds --output`.

**Checklist:**
- [x] Core algorithm: R resources → pack with P → N fuzz iterations
- [x] 8 scenarios with deterministic seeds (run each x3, aggregated)
- [x] Max error < 0.001 vs closed form (verified: 0.000622)
- [x] Structured JSON report with `--output` flag
- [x] CLI mode: `--resources --iterations --seeds --output`
- [x] Baseline comparison / regression detection
- [x] `.github/workflows/nightly.yml` with daily 6 AM UTC + `workflow_dispatch`
- [x] `docs/guides/security-testing.md` — how to run and interpret

**Success Criteria:**
- ✅ All 8 scenarios pass with deterministic seeds
- ✅ Max error < 0.001 vs closed form (0.000622)
- ✅ Structured JSON report output
- ✅ CLI mode with all configurable parameters
- ✅ Separated from PR-gate CI (nightly only)
- ✅ GitHub Actions nightly workflow created
- ✅ Security testing guide documents run/interpret workflow

---

## Milestone M2 — Backend: Audit & Observability (due Aug 8)

### M2-01: Pack Metrics in Audit Events ([#413](https://github.com/deghosal-2026/mcp-fabric/issues/413)) — ✅ Done

**Files edited:**
- `api/services/resource_service.py` — added `get_pack_resource_counts()`, `get_domain_resource_counts()`
- `api/services/routing_service.py` — added `compute_catch_rate()`, captures `pack_metrics` in audit `details`
- `api/schemas/audit.py` — added `min_pack_resource_count`, `max_catch_rate` to `AuditExportRequest`
- `api/services/audit_service.py` — added filter logic for new params in `query()`
- `api/routers/audit.py` — added `min_pack_resource_count`, `max_catch_rate` query params to `list_audit_events` + export

**Description:** At request time, capture `pack_metrics` per dimension (`pack_resource_count`, `total_resources_in_domain`, `implied_catch_rate`) in audit event details JSONB alongside existing `resource_check`. Formula: `catch = 1 - (pack_size - 1) / (total_resources - 1)`, clamped to [0.0, 1.0]. Queryable via `min_pack_resource_count` and `max_catch_rate` filters on GET and export endpoints.

**Checklist:**
- [x] Add `get_pack_resource_counts()` + `get_domain_resource_counts()` to resource_service.py
- [x] Compute `implied_catch_rate` via static method `RoutingService.compute_catch_rate()` (clamped, no NaN/Inf)
- [x] Capture `pack_metrics` dict in audit `details` alongside `resource_check` in execute()
- [x] Add `min_pack_resource_count` filter param to GET /v1/audit and POST /v1/audit/export
- [x] Add `max_catch_rate` filter param to GET /v1/audit and POST /v1/audit/export
- [x] Both params on `AuditExportRequest` schema
- [x] Backward compatible: existing events without `pack_metrics` return null/None (filter helpers skip non-matching events)
- [x] Run full test suite — all existing tests pass

**Success Criteria:**
- ✅ `pack_metrics` captured in audit event details (per dimension)
- ✅ `implied_catch_rate` computed and stored (clamped)
- ✅ Queryable via `min_pack_resource_count` and `max_catch_rate` filters
- ✅ Both params on audit export endpoint
- ✅ Backward compatible — existing audit events without these fields return null/None
- ✅ All existing audit tests pass

---

## Milestone M3 — Frontend: UI Safety Signals (due Aug 15)

### M3-01: Pack Breadth Warning in Pack Editor ([#408](https://github.com/deghosal-2026/mcp-fabric/issues/408)) — ✅ Done

**Files to create/edit:**
- `api/services/pack_service.py` — new method for pack security metrics
- `api/routers/pack.py` — new endpoint `GET /admin/packs/{id}/security-metrics`
- `ui/src/components/shared/PackBreadthWarning.tsx` — NEW warning component
- `ui/src/pages/Packs.tsx` — integrate warning into Resource Bindings modal
- `docs/ui-test/findings/screenshots/20-packs-bindings.png` — updated screenshot

**Description:** Visual warning in the Resource Bindings modal with 5 severity tiers based on configurable thresholds. Tooltip shows exact catch-rate %, resource count, server count, recommendation, and link to pack-granularity.md.

**Checklist:**
- [x] Backend: `GET /packs/{id}/security-metrics` returns `{ resource_count, total_resources_in_domain, implied_catch_rate, warning_tier }`
- [x] UI: PackBreadthWarning component as badge inside tooltip + banner variants
- [x] Tooltip with exact catch-rate, tier recommendation, and docs link
- [x] Integrate into Resource Bindings modal (Packs.tsx)
- [x] Edge case: 0 resources → no warning
- [x] Edge case: domain_total=1 → catch=100%
- [x] Unit tests for warning component (4 test cases)
- [x] Backend unit tests for security-metrics endpoint (2 test cases)
- [x] E2E tests updated with mock route + assertion
- [x] Screenshot captured (20-packs-bindings.png)
- [x] `ruff check` passes
- [x] Existing pack E2E tests pass

**Success Criteria:**
- ✅ Warning appears in Resource Bindings modal with correct tier
- ✅ Catch-rate computed from live data
- ✅ Tooltip includes recommendation and docs link
- ✅ Edge cases handled correctly
- ✅ Screenshots updated

---

### M3-02: Pack Breadth Score on Trust Posture Dashboard ([#409](https://github.com/deghosal-2026/mcp-fabric/issues/409)) — ✅ Done

**Files to create/edit:**
- `api/services/resource_service.py` — new method `get_pack_breadth()`
- `api/routers/admin.py` — new endpoint `GET /admin/trust-posture/pack-breadth`
- `api/schemas/admin.py` — new `PackBreadthRow` response schema
- `ui/src/components/shared/PackBreadthCard.tsx` — NEW card component
- `ui/src/pages/TrustPosture.tsx` — integrate card
- `docs/ui-test/findings/screenshots/22-trust-breadth.png` — updated screenshot

**Description:** New "Identity-Binding Coverage" card on the Trust Posture dashboard showing per-agent-class and per-pack identity-binding coverage with risk coloring, sort, and filter.

**Checklist:**
- [x] Backend: `GET /admin/trust-posture/pack-breadth` returns array of `{ agent_class_id, agent_class_name, pack_count, resources_covered, total_resources_in_domain, catch_rate }`
- [x] UI: PackBreadthCard component
- [x] 6-column table with correct data per row
- [x] Risk coloring: ≥95% green, 80-95% yellow, 50-80% orange, <50% red
- [x] Tooltip with explanation and link to pack-granularity.md
- [x] Default sort by catch rate ascending (worst first)
- [x] Filter by risk level (low/medium/high/critical)
- [x] Edge case: 0 packs → "N/A"
- [x] Edge case: domain_total=1 → catch=100%
- [x] Unit tests (2 backend + 2 frontend)
- [x] E2E mock assertions pass
- [x] Screenshot captured (22-trust-breadth.png)
- [x] `ruff check` passes

**Success Criteria:**
- ✅ Card visible on Trust Posture page with all 6 columns
- ✅ Correct catch-rate math, risk coloring, tooltip
- ✅ Sort and filter functional
- ✅ Edge cases handled
- ✅ Existing E2E tests pass
- ✅ Screenshots updated

---

## Milestone M4 — Security: Schema-Digest Mappings (due Aug 22)

### M4-01: Schema-Digest DB Schema ([#414](https://github.com/deghosal-2026/mcp-fabric/issues/414)) — ✅ Done

**Files to create/edit:**
- `alembic/versions/fe4c5b8d2a1a_add_schema_digest_and_mapping_reviews.py` — NEW migration
- `api/models/server.py` — new columns on `CapabilityMapping`, new `MappingReview` model

**Description:** Add schema-digest binding to capability_mappings and create mapping_reviews table. Backfill existing mappings by computing SHA-256 digest from current tool version and setting status to active.

**Checklist:**
- [x] Create Alembic migration with new columns on capability_mappings
- [x] Add unique constraint on (capability_id, server_id, tool_schema_digest)
- [x] Create mapping_reviews table with all columns
- [x] Add SQLAlchemy ORM model MappingReview
- [x] Update CapabilityMapping model with tool_schema_digest and status fields
- [x] Backfill migration: compute digest for existing mappings (SHA-256 from tool_name + input_schema + output_schema via join on server_tools)
- [x] Test migration forward and backward
- [x] Add indexes for hot-path queries

**Success Criteria:**
- ✅ Migration creates new columns and table with correct FKs and constraints
- ✅ Backfill script works for existing production data
- ✅ ORM models support all CRUD operations
- ✅ Migrations run cleanly forward and backward

### M4-02: Schema-Digest in Registry & Routing ([#414](https://github.com/deghosal-2026/mcp-fabric/issues/414)) — ✅ Done

**Files to edit:**
- `api/services/registry_service.py` — compute SHA256 digest on register/re-inspect, mark mappings stale on drift
- `api/services/routing_service.py` — digest check in candidate selection, NoServerFoundError for no valid candidates
- `api/services/capability_service.py` — `_compute_tool_digest`, `create_mapping` sets digest, mapping review workflow methods
- `api/routers/admin.py` — new mapping review endpoints
- `api/routers/capabilities.py` — use shared dependency from `dependencies.py`
- `api/schemas/capability.py` — `CapabilityMappingResponse.tool_schema_digest`, `CapabilityMappingResponse.status`, `MappingReviewResponse`, `MappingReviewCreate`
- `api/services/exceptions.py` — `ToolNotFoundError`

**Description:** Core routing logic changes:

1. **Schema-digest computation:** On mapping creation, compute `SHA256(tool_name + input_schema + output_schema)` from the ServerTool definition. Store on the CapabilityMapping.

2. **Stale detection on re-inspect:** When a server is re-inspected and a tool schema changes (or is removed), mark all affected CapabilityMappings as `stale`.

3. **Digest-bound routing:** Candidate server selection filters to mappings where `status='active'` AND stored digest matches the current ServerTool's computed digest. If no candidates pass, raises `NoServerFoundError`.

4. **Review state machine:** `active ↔ stale → active / rejected`

5. **New endpoints:**
   - `GET /admin/mappings/stale` — list mappings with stale digests
   - `POST /admin/mappings/{id}/review` — approve (updates digest, sets active) or reject (sets rejected)
   - `GET /admin/capabilities/{id}/ambiguity` — list all mappings for a capability

**Checklist:**
- [x] CapabilityService._compute_tool_digest static method (SHA-256 of name + schemas)
- [x] create_mapping looks up ServerTool, computes digest, stores digest + active status
- [x] RegistryService.inspect marks affected mappings stale on schema change/removal
- [x] RoutingService.select_server filters to status='active' + digest-match
- [x] RoutingService raises NoServerFoundError when no valid candidates
- [x] CapabilityService.get_stale_mappings() method
- [x] CapabilityService.review_mapping() approve/reject with digest update + MappingReview creation
- [x] New endpoint: `GET /admin/mappings/stale`
- [x] New endpoint: `POST /admin/mappings/{id}/review`
- [x] New endpoint: `GET /admin/capabilities/{id}/ambiguity`
- [x] Pydantic schemas for all new request/response types
- [x] Shared `get_capability_service` dependency moved to `dependencies.py`
- [x] ToolNotFoundError in exceptions module
- [x] Backend tests: test_schema_digest.py (3 tests), test_mapping_review.py (2 tests)
- [x] `ruff check` passes

**Deviation from spec:**
- Routing returns `NoServerFoundError` (404/500) instead of `409 Conflict` with ambiguity payload. Simpler approach — if all candidates fail digest validation, no server can serve the capability.

**Success Criteria:**
- ✅ Schema drift on re-inspect marks affected mappings as `stale`
- ✅ Stale mappings excluded from routing until re-approved
- ✅ Review workflow creates MappingReview audit trail
- ✅ All existing routing tests pass

### M4-03: Raw Context & Denial Rules in OPA ([#414](https://github.com/deghosal-2026/mcp-fabric/issues/414)) — ✅ Done

**Files to edit:**
- `policies/fabric/policy.rego` — add `deny_stale_mapping`, `untrusted_write`, `raw_context` rules; updated `allow` gate
- `policies/fabric/policy_test.rego` — 31 tests (existing + new)
- `api/services/policy_service.py` — pass `mapping_status` and `tool_name` to OPA input
- `api/schemas/common.py` — `PolicyDecision.deny_stale_mapping`, `PolicyDecision.untrusted_write`

**Description:** Extend OPA policy input with `mapping_status` and `tool_name`. Add denial rules:

| Rule | Condition | Effect |
|------|-----------|--------|
| `deny_stale_mapping` | `input.mapping_status != "active"` | Blocks routes through stale/rejected mappings |
| `untrusted_write` | `server_trust_level == "unreviewed"` AND tool is write (not read-only) | Blocks write ops on unreviewed servers |
| `raw_context` | Identity function | Returns raw input for debugging/audit |

**Checklist:**
- [x] Add `mapping_status` to OPA input schema
- [x] Add `tool_name` to OPA input schema
- [x] Implement `deny_stale_mapping` rule
- [x] Implement `untrusted_write` rule (write detection via `_read_only_prefixes` matching)
- [x] Gate `allow` with `not deny_stale_mapping`
- [x] Add `raw_context := input` for debug
- [x] Add `deny_stale_mapping` and `untrusted_write` to result output
- [x] Add Rego test cases: stale denial, active passes, stale+unreviewed combo
- [x] Add Rego test cases: write blocked on unreviewed, read allowed on unreviewed, write allowed on trusted
- [x] Add Rego test case: raw_context returns input
- [x] Update PolicyService.evaluate() to pass mapping_status and tool_name
- [x] Update PolicyService.evaluate() to return deny_stale_mapping and untrusted_write
- [x] Update RoutingService.execute() to pass mapping_status and tool_name to OPA
- [x] OPA tests updated to v1 syntax (require `if` keyword) — all 31 pass
- [x] `ruff check` passes

**Success Criteria:**
- ✅ OPA policy input includes `mapping_status` and `tool_name`
- ✅ `deny_stale_mapping` blocks requests for stale mappings
- ✅ `untrusted_write` blocks write requests from unreviewed servers
- ✅ All existing rules continue to work (backward compatible)
- ✅ All 31 OPA policy tests pass

### M4-04: Pending Reviews UI & Auditing ([#414](https://github.com/deghosal-2026/mcp-fabric/issues/414)) — Done

**Files to create/edit:**
- `ui/src/pages/Reviews.tsx` — NEW review page
- `ui/src/App.tsx` — add route and sidebar integration
- `ui/src/components/layout/Sidebar.tsx` — add Reviews nav link
- `ui/src/api/client.ts` — `fetchStaleMappings()`, `reviewMapping()`, `fetchCapability()`
- `ui/src/types/index.ts` — `CapabilityMapping.status`, `CapabilityMapping.tool_schema_digest`, `MappingReview`
- `ui/e2e/admin-ui-all-buttons.spec.ts` — mock routes, sidebar walkthrough tests
- `ui/e2e/admin-ui.spec.ts` — mock routes, navigation tour
- `ui/e2e/admin-ui-docker-all-buttons.spec.ts` — sidebar + walkthrough
- `ui/e2e/docker-sidebar-screenshot.spec.ts` — sidebar link assertion
- `ui/e2e/docker-screenshots.spec.ts` — screenshot capture
- `ui/e2e/docker-full-exercise.spec.ts` — walkthrough step
- `ui/e2e/docker-all-controls.spec.ts` — walkthrough step

**Description:**

1. **Reviews Page:** Shows each pending stale mapping with capability name (resolved), server name (resolved), tool name, digest prefix, status. Approve/Reject buttons with toast notifications.

2. **Sidebar:** "Reviews" nav link between Admin Users and Trust Posture.

3. **API integration:** `fetchStaleMappings()` (GET), `reviewMapping()` (POST), `fetchCapability()` for name resolution.

**Checklist:**
- [x] UI: ReviewsPage component with stale mapping table
- [x] UI: Approve/Reject action buttons with toast feedback
- [x] UI: Server and capability name resolution via React Query useQueries
- [x] Sidebar: "Reviews" nav link
- [x] App route: `/reviews`
- [x] API: `fetchStaleMappings`
- [x] API: `reviewMapping`
- [x] API: `fetchCapability` (for name resolution)
- [x] Types: extended CapabilityMapping, added MappingReview
- [x] Link from Trust Posture header to /reviews
- [x] E2E mock tests: sidebar link passes (12 links), Reviews page renders with approve/reject, full walkthrough includes /reviews
- [x] Docker E2E tests: sidebar link assertion, screenshot, walkthrough
- [x] 75/75 mock Playwright tests pass
- [ ] PendingReviewsBadge with count — NOT DONE (deferred)
- [ ] Schema diff visualization (side-by-side) — NOT DONE (deferred)
- [ ] Review decision audit events in audit_events table — NOT DONE (MappingReview IS the audit trail, not duplicated in audit_events)

**Success Criteria:**
- ✅ Reviews page shows pending stale mappings with name resolution
- ✅ Approve/reject workflow stores decision in MappingReview
- ✅ Toast feedback on approve/reject
- ✅ Sidebar link navigates to /reviews
- ✅ Trust Posture has link to Pending Reviews
- ✅ All Playwright E2E tests pass (75 mock + Docker specs updated)
- [~] Schema diff visualization, count badge, audit_events duplication — deferred

---

## All Files Touched Summary

| Area | Files | Status |
|------|-------|--------|
| **Docs** | `docs/guides/pack-granularity.md`, `docs/guides/security-testing.md`, `SECURITY.md`, `docs/PRD.md`, `docs/wbs/phase-14-v030.md` | NEW + EDIT |
| **Tests (Backend)** | `tests/services/test_resource_policy.py`, `tests/security/test_confused_deputy_fuzz.py`, `tests/services/test_schema_digest.py`, `tests/services/test_mapping_review.py` | NEW + EDIT |
| **CI** | `.github/workflows/nightly.yml` | NEW |
| **Backend** | `api/services/routing_service.py`, `api/services/audit_service.py`, `api/services/registry_service.py`, `api/services/capability_service.py`, `api/services/resource_service.py`, `api/services/pack_service.py`, `api/services/policy_service.py`, `api/services/exceptions.py` | EDIT |
| **Routers** | `api/routers/audit.py`, `api/routers/admin.py`, `api/routers/pack.py`, `api/routers/capabilities.py` | EDIT |
| **Schemas** | `api/schemas/audit.py`, `api/schemas/admin.py`, `api/schemas/capability.py`, `api/schemas/common.py` | EDIT |
| **DB** | `alembic/versions/fe4c5b8d2a1a_add_schema_digest_and_mapping_reviews.py`, `api/models/server.py` | NEW + EDIT |
| **OPA** | `policies/fabric/policy.rego`, `policies/fabric/policy_test.rego` | EDIT |
| **UI Pages** | `ui/src/pages/TrustPosture.tsx`, `ui/src/pages/Packs.tsx`, `ui/src/pages/Reviews.tsx` | NEW + EDIT |
| **UI Components** | `ui/src/components/shared/PackBreadthWarning.tsx`, `ui/src/components/shared/PackBreadthCard.tsx`, `ui/src/components/layout/Sidebar.tsx` | NEW + EDIT |
| **UI Core** | `ui/src/App.tsx`, `ui/src/api/client.ts`, `ui/src/types/index.ts` | EDIT |
| **E2E Tests** | `ui/e2e/admin-ui-all-buttons.spec.ts`, `ui/e2e/admin-ui.spec.ts`, `ui/e2e/admin-ui-docker-all-buttons.spec.ts`, `ui/e2e/docker-sidebar-screenshot.spec.ts`, `ui/e2e/docker-screenshots.spec.ts`, `ui/e2e/docker-full-exercise.spec.ts`, `ui/e2e/docker-all-controls.spec.ts` | EDIT |
| **Screenshots** | `docs/ui-test/findings/screenshots/20-packs-bindings.png`, `22-trust-breadth.png`, `17-trust-posture.png`, `18-trust-posture-class-selected.png` | EDIT |

---

## Build Order & Dependencies

```
M1-01 (pack-granularity.md) ───────────────────► M1-02 (SECURITY.md)
                                                      │
M1-03 (giant pack test) ──────► M1-04 (fuzz test)      │
                                  │                    │
                                  ▼                    ▼
                             M2-01 (audit enrich) ──► M3-01 (pack warning UI)
                                                        │
                                                        ▼
                                                   M3-02 (pack breadth UI)

M4-01 (DB schema) ──► M4-02 (routing + API) ──► M4-03 (OPA rules)
                                                      │
                                                      ▼
                                                 M4-04 (review UI)
```

- M1 can be done in parallel (docs and tests don't share files)
- M2 depends on M1 (enrichment references pack granularity concepts)
- M3 depends on M2 (UI depends on audit/metrics backend)
- M4 is independent of M1-M3 and can run in parallel
- M4-01 → M4-02 → M4-03 → M4-04 must be sequential

## Delivery Summary

All 4 milestones shipped on Jul 25, 2026. Total delivery: 12 tasks across docs, backend, OPA, frontend, and E2E testing.

### Test Results

| Check | Result |
|-------|--------|
| Python tests (pytest) | **326 passed**, 9 skipped, 0 failures |
| Ruff lint + format | **117 files** clean |
| Mypy | Clean (pre-existing auth_service/registry_service errors only) |
| OPA policy tests | **31/31 passed** (all rules + deny_stale_mapping + untrusted_write + raw_context) |
| UI typecheck | Clean |
| Playwright mock E2E | **75/75 passed** (admin-ui-all-buttons + admin-ui) |
| Playwright Docker E2E | Sidebar screenshot ✅, Full page screenshots ✅ (13 screenshots captured) |

### Screenshots Captured

| File | Description |
|------|-------------|
| `docker-02-dashboard.png` | Dashboard with stats |
| `docker-03-servers.png` | Servers list |
| `docker-05-capabilities.png` | Capability Catalog |
| `docker-07-agent-classes.png` | Agent Classes |
| `docker-08-policies.png` | Policy Editor |
| `docker-10-audit.png` | Audit Log |
| `docker-11-approvals.png` | Approvals |
| `docker-13-packs.png` | Capability Packs |
| `docker-13a-packs-bindings.png` | Resource Bindings modal |
| `docker-14-alerts.png` | Alerts |
| `docker-15-admin-users.png` | Admin Users |
| `docker-17-trust-posture.png` | Trust Posture |
| **`docker-18-reviews.png`** | **Pending Schema Reviews page** |
| `docker-sidebar-full.png` | Sidebar with 12 nav links |

### Files Touched (47 files)

| Area | Files |
|------|-------|
| **Docs** | `pack-granularity.md`, `security-testing.md`, `SECURITY.md`, `PRD.md`, `wbs/phase-14-v030.md` |
| **Backend Tests** | `test_resource_policy.py`, `test_confused_deputy_fuzz.py`, `test_schema_digest.py`, `test_mapping_review.py` |
| **CI** | `nightly.yml` |
| **Backend** | `routing_service.py`, `audit_service.py`, `registry_service.py`, `capability_service.py`, `resource_service.py`, `pack_service.py`, `policy_service.py`, `exceptions.py` |
| **Routers** | `audit.py`, `admin.py`, `pack.py`, `capabilities.py` |
| **Schemas** | `audit.py`, `admin.py`, `capability.py`, `common.py` |
| **DB** | Migration `fe4c5b8d2a1a`, `models/server.py` |
| **OPA** | `policy.rego`, `policy_test.rego` |
| **UI Pages** | `TrustPosture.tsx`, `Packs.tsx`, `Reviews.tsx` |
| **UI Components** | `PackBreadthWarning.tsx`, `PackBreadthCard.tsx`, `Sidebar.tsx` |
| **UI Core** | `App.tsx`, `client.ts`, `types/index.ts` |
| **E2E** | 7 Playwright spec files (mock + Docker) |

### Deferred (non-blocking)

- PendingReviewsBadge sidebar count badge (nice-to-have)
- Side-by-side schema diff visualization (nice-to-have)
- Duplicate review decisions in audit_events table (MappingReview table already serves as audit trail)
- docs/user-guide.md screenshot update