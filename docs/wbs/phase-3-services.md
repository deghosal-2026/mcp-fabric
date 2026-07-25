# Phase 3: Core Services

> **Tasks:** 95 · **Effort:** 72h (9 days)  
> **Dependencies:** Phase 1, Phase 2

## 3.1 RegistryService (8 tasks)

### P3-01: Service Scaffold + Register (#233)
**Effort:** 3h | **Deps:** P1-01, P2-02
**Checklist:**
- [x] `api/services/registry_service.py` — class RegistryService(db, mcp_client, audit_service)
- [x] `register(name, endpoint, owner_team, description, labels, team_namespace) -> MCPServer`
- [x] Creates MCPServer record with trust_level="unreviewed", health_status="unknown"
- [x] Calls mcp_client.list_tools(endpoint) → creates ServerTool records
- [x] Auto-suggests trust level: read-only tools → "trusted", otherwise "unreviewed"
- [x] Logs audit_event(server_registered)
- [x] Invalid endpoint → ServerUnreachableError(400)
- [x] Duplicate endpoint → DuplicateServerError(409)

**Success Criteria:** Register → server + tools in DB. Unreachable → 400. Duplicate → 409.

### P3-02: Inspect Server (#234)
**Effort:** 2h | **Deps:** P3-01, P2-04
**Checklist:**
- [x] `inspect(server_id) -> ServerInspectResponse`
- [x] Calls mcp_client.list_tools(endpoint) to diff against current tools
- [x] Stores old tools in tool_versions table
- [x] Updates ServerTool records with new schemas
- [x] Returns: tools_added, tools_removed, tools_changed
- [x] Updates server.updated_at + health_status
- [x] Logs audit_event(schema_change_detected) if changes found

**Success Criteria:** Unchanged server → empty diff. New tool → tools_added. Breaking → is_breaking+alert.

### P3-03: List + Filter Servers (#235)
**Effort:** 2h | **Deps:** P3-01
**Checklist:**
- [x] `list_servers(team, trust, health, search, cursor, per_page) -> PaginatedServers`
- [x] Filters: team_namespace, trust_level, health_status, search (name ILIKE)
- [x] Cursor-based pagination by (created_at, id) composite key
- [x] TenantMiddleware scope applied automatically
- [x] Empty → returns {servers:[], pagination:{...}} with 200

**Success Criteria:** All filters work independently + combined. Cursor pagination correct.

### P3-04: Get Server Detail (#236)
**Effort:** 1h | **Deps:** P3-01
**Checklist:**
- [x] `get_server(server_id) -> ServerDetail`
- [x] Eager load: tools, tool_versions (latest), trust_assignments, capability_mappings, routing_rules
- [x] Include decommission timeline if decommissioned
- [x] Not found → 404

**Success Criteria:** Full detail in one query (no N+1). Decommissioned servers show timeline.

### P3-05: Decommission Server (#237)
**Effort:** 2h | **Deps:** P3-01
**Checklist:**
- [x] `decommission(server_id, phase, replacement_id) -> DecommissionResult`
- [x] Phase validation: must proceed grace_period → migration → sunset
- [x] Dependency report: capabilities this server provides + agent classes depending on it
- [x] grace_period: set decommissioned_at + decommission_phase
- [x] migration: redirect capability mappings to replacement server
- [x] sunset: remove from capability mappings, mark fully decommissioned
- [x] SELECT FOR UPDATE row lock to prevent race
- [x] Logs audit_event(server_decommissioned)

**Success Criteria:** Phased progression enforced. Dependency report accurate. Double-decommission → 409.

### P3-06: Health Status Management (#81)
**Effort:** 1h | **Deps:** P3-01
**Checklist:**
- [x] `update_health(server_id, status)` → updates Redis + DB
- [x] `get_server_health(server_id)` → reads from Redis (hot path), falls back to DB
- [x] `get_all_health_statuses()` → returns {server_id: status} from Redis/DB
- [x] Redis client injected via constructor, gracefully degraded without Redis

**Success Criteria:** Health reads < 1ms from Redis. DB syncs on async write.

### P3-07: Schema Change Notification (#83)
**Effort:** 1h | **Deps:** P3-02
**Checklist:**
- [x] `notify_schema_change` Celery task defined with auto-retry
- [x] Task: breaking changes → high-priority log warning
- [x] Task: tool added/removed → info log notification
- [x] inspect() dispatches task after detecting changes

**Success Criteria:** Admins notified on schema change. Breaking changes highlighted.

### P3-08: RegistryService Tests (#85)
**Effort:** 2h | **Deps:** P3-01 through P3-07
**Checklist:**
- [x] Register: create, read-only trust, duplicate, unreachable, empty tools, audit logging, audit failure resilience
- [x] Inspect: no changes, added, removed, changed, archived, not found, unreachable, audit logging, audit failure resilience
- [x] List: all, empty, team filter, trust filter, health filter, search, combined, cursor pagination, invalid cursor
- [x] GetServer: full detail, decommission timeline, not found
- [x] Decommission: grace_period, migration, sunset, skip phase, invalid phase, already sunset, first phase migration, migration with replacement, redirect mappings, sunset deletes mappings, audit logging, audit failure resilience
- [x] Health: update + get, get all, not found, Redis write path, Redis read path, Redis scan path

**Success Criteria:** 50 tests. 100% line coverage. All pass.

## 3.2 CapabilityService (8 tasks)

### P3-09 to P3-16: CapabilityService Tasks
> Each 1-2h: create, map, resolve (name+alias), detect_conflicts, deprecate, add_alias, list, tests.

## 3.3 PolicyService (6 tasks)
### P3-17 to P3-22: PolicyService Tasks
- [x] P3-17: evaluate() — OPA REST call, return PolicyDecision (allow/deny + matched rules)
- [x] P3-18: evaluate_cached() — Redis cache (TTL 5min), falls through without Redis
- [x] P3-19: AgentClass CRUD — create, get, list (team filter), update, delete
- [x] P3-20: TrustAssignment — upsert, get_by_class, remove, cache invalidation on write
- [x] P3-21: deploy_bundle() — OPA bundle push with version tracking
- [x] P3-22: Tests — 19 tests (evaluate, cached, CRUD, trust, bundle deploy)

## 3.4 RoutingService (8 tasks)
### P3-23 to P3-30: RoutingService Tasks
> Full routing pipeline: resolve→candidates→rules→policy→rank→call→fallback→normalize→audit. Single + batch. Tests.
- [x] P3-23: resolve_capability() — exact name match + alias lookup in CapabilityService
- [x] P3-24: find_candidates() — query MCPServer with capability mapping
- [x] P3-25: resolve_routing_rules(server_id, agent_class_id) — weighted rules from DB
- [x] P3-26: evaluate_policy(candidates, agent_class) — OPA policy check per candidate
- [x] P3-27: rank_candidates — by routing_weight DESC, then health_score DESC
- [x] P3-28: execute() — full pipeline, post-call audit log
- [x] P3-29: execute_batch() — 1-10 capabilities, per-item success/error, partial results
- [x] P3-30: Tests — 15 tests (full pipeline, fallback, batch, policy deny)

## 3.5 AuditService (5 tasks)
### P3-31 to P3-35: AuditService Tasks
- [x] P3-31: AuditService — log_event, query, cleanup methods (api/services/audit_service.py)
- [x] P3-32 through P3-35: Deferred — export, scheduled export pending Celery integration

## 3.6 ApprovalService (5 tasks)
### P3-36 to P3-40: ApprovalService Tasks
- [x] P3-36: create() — pending request with configurable expiry
- [x] P3-37: approve() — route via RoutingService, update approved_at
- [x] P3-38: deny() — set status=denied with approver note
- [x] P3-39: get_status() — agent polling endpoint, expire_pending() — batch expire overdue
- [x] P3-40: list() — filter by status, Tests — 19 tests

## 3.7 PackService (6 tasks)
### P3-41 to P3-46: PackService Tasks
- [x] P3-41: create_pack() — name, description, team, labels
- [x] P3-42: assign_capability() — link capability to pack
- [x] P3-43: assign_to_class() — link pack to agent class
- [x] P3-44: clone_pack() — deep copy capabilities + class assignments
- [x] P3-45: get_usage_stats() — query audit events for pack usage
- [x] P3-46: Tests — 23 tests (CRUD, capability/class assignment, clone, stats)

## 3.8 AlertService (5 tasks)
### P3-47 to P3-51: AlertService Tasks
- [x] P3-47: create_rule() — type (degraded_servers|denied_requests), threshold, enabled
- [x] P3-48: fire_alert() — create AlertEvent with context, status=open
- [x] P3-49: acknowledge() — set acknowledged_at
- [x] P3-50: list_events() — filter by rule_id, toggle enable/disable rule
- [x] P3-51: Tests — 20 tests (CRUD, fire, acknowledge, thresholds, toggle)

## 3.9 AuthService (20 tasks)
### P3-52 to P3-71: AuthService Tasks
- [x] P3-52: create_token, validate_token (JWT), hash_password, verify_password (bcrypt)
- [x] P3-53: Agent identity — create with hashed token (fcp_ prefix)
- [x] P3-54: Agent identity — rotate token
- [x] P3-55: Agent identity — revoke token
- [x] P3-56: Agent capability surface — resolve from class → packs → capabilities
- [x] P3-57: validate_agent_token_db() — lookup + verify
- [x] P3-58: Agent identity tests
- [x] P3-59: first_admin_bootstrap() — creates first admin session
- [x] P3-60: Multiple bootstrap prevention (BootstrapError)
- [x] P3-61: admin_login() — username/password check with failed_attempts tracking
- [x] P3-62: Account lockout after 5 failures
- [x] P3-63: MFA setup — generate TOTP secret + QR URL
- [x] P3-64: MFA verify — validate TOTP code
- [x] P3-65: Admin login tests
- [x] P3-66: create_admin_session() — Redis-backed session
- [x] P3-67: validate_admin_session() — Redis lookup
- [x] P3-68: logout_admin_session() — Redis delete
- [x] P3-69: Password reset with history (last 5)
- [x] P3-70: Password policy enforcement (8+ chars, upper+lower+digit)
- [x] P3-71: Tests — 22 tests (tokens, agent lifecycle, bootstrap, login, MFA, sessions, password policy)

## 3.10 Service Integration Tests (8 tasks)
### P3-72 to P3-79: Service Integration Tests
> End-to-end flows: register→inspect→map→request. Approval flow. Fallback. Batch. Auth lifecycle.
