# Phase 3: Core Services

> **Tasks:** 95 · **Effort:** 72h (9 days)  
> **Dependencies:** Phase 1, Phase 2

## 3.1 RegistryService (8 tasks)

### P3-01: Service Scaffold + Register (#233)
**Effort:** 3h | **Deps:** P1-01, P2-02
**Checklist:**
- [ ] `api/services/registry_service.py` — class RegistryService(db, mcp_client, audit_service)
- [ ] `register(name, endpoint, owner_team, description, labels, team_namespace) -> MCPServer`
- [ ] Creates MCPServer record with trust_level="unreviewed", health_status="unknown"
- [ ] Calls mcp_client.list_tools(endpoint) → creates ServerTool records
- [ ] Auto-suggests trust level: read-only tools → "trusted", otherwise "unreviewed"
- [ ] Logs audit_event(server_registered)
- [ ] Invalid endpoint → ServerUnreachableError(400)
- [ ] Duplicate endpoint → DuplicateServerError(409)

**Success Criteria:** Register → server + tools in DB. Unreachable → 400. Duplicate → 409.

### P3-02: Inspect Server (#234)
**Effort:** 2h | **Deps:** P3-01, P2-04
**Checklist:**
- [ ] `inspect(server_id) -> ServerInspectResponse`
- [ ] Calls mcp_client.diff_tools(endpoint, current_tools)
- [ ] Stores old tools in tool_versions table
- [ ] Updates ServerTool records with new schemas
- [ ] Returns: tools_added, tools_removed, tools_changed
- [ ] Updates server.updated_at + health_status
- [ ] Logs audit_event(schema_change_detected) if changes found

**Success Criteria:** Unchanged server → empty diff. New tool → tools_added. Breaking → is_breaking+alert.

### P3-03: List + Filter Servers (#235)
**Effort:** 2h | **Deps:** P3-01
**Checklist:**
- [ ] `list_servers(team, trust, health, search, cursor, per_page) -> PaginatedServers`
- [ ] Filters: team_namespace, trust_level, health_status, search (name ILIKE)
- [ ] Cursor-based pagination by registered_at DESC
- [ ] TenantMiddleware scope applied automatically
- [ ] Empty → returns {servers:[], pagination:{...}} with 200

**Success Criteria:** All filters work independently + combined. Cursor pagination correct.

### P3-04: Get Server Detail (#236)
**Effort:** 1h | **Deps:** P3-01
**Checklist:**
- [ ] `get_server(server_id) -> ServerDetail`
- [ ] Eager load: tools, tool_versions (latest), trust_assignments, capability_mappings, routing_rules
- [ ] Include decommission timeline if decommissioned
- [ ] Not found → 404

**Success Criteria:** Full detail in one query (no N+1). Decommissioned servers show timeline.

### P3-05: Decommission Server (#237)
**Effort:** 2h | **Deps:** P3-01
**Checklist:**
- [ ] `decommission(server_id, phase, replacement_id) -> DecommissionResult`
- [ ] Phase validation: must proceed grace_period → migration → sunset
- [ ] Dependency report: capabilities this server provides + agent classes depending on it + request count
- [ ] grace_period: set decommissioned_at, add deprecation header to responses
- [ ] migration: redirect capability mappings to replacement server
- [ ] sunset: remove from capability mappings, mark fully decommissioned
- [ ] SELECT FOR UPDATE row lock to prevent race
- [ ] Logs audit_event(server_decommissioned)

**Success Criteria:** Phased progression enforced. Dependency report accurate. Double-decommission → 409.

### P3-06: Health Status Management (#81)
**Effort:** 1h | **Deps:** P3-01
**Checklist:**
- [ ] `update_health(server_id, status)` → updates Redis + DB
- [ ] `get_server_health(server_id)` → reads from Redis (hot path)
- [ ] `get_all_health_statuses()` → returns {server_id: status} from Redis

**Success Criteria:** Health reads < 1ms from Redis. DB syncs on async write.

### P3-07: Schema Change Notification (#83)
**Effort:** 1h | **Deps:** P3-02
**Checklist:**
- [ ] After inspect detects changes → notify admins (Celery task)
- [ ] Breaking changes → high-priority notification
- [ ] Tool added/removed → info notification
- [ ] Links to server detail page for review

**Success Criteria:** Admins notified on schema change. Breaking changes highlighted.

### P3-08: RegistryService Tests (#85)
**Effort:** 2h | **Deps:** P3-01 through P3-07
**Checklist:**
- [ ] Register success + failure modes
- [ ] Inspect with changes + without
- [ ] List with all filter combinations
- [ ] Decommission full lifecycle (grace → migration → sunset)
- [ ] Health status updates
- [ ] Edge: duplicate endpoint, unreachable server, concurrent decommission

**Success Criteria:** 12+ tests. All pass. Covers P0 scenarios from spec test matrix.

## 3.2 CapabilityService (8 tasks)

### P3-09 to P3-16: CapabilityService Tasks
> Each 1-2h: create, map, resolve (name+alias), detect_conflicts, deprecate, add_alias, list, tests.

## 3.3 PolicyService (6 tasks)
### P3-17 to P3-22: PolicyService Tasks
> OPA evaluation (cache in Redis), deploy bundle (invalidate cache), agent class CRUD, trust assignment, tests.

## 3.4 RoutingService (8 tasks)
### P3-23 to P3-30: RoutingService Tasks
> Full routing pipeline: resolve→candidates→rules→policy→rank→call→fallback→normalize→audit. Single + batch. Tests.

## 3.5 AuditService (5 tasks)
### P3-31 to P3-35: AuditService Tasks
> Log event (append-only), query (filtered+cursor), export (Celery dispatch), scheduled export config, tests.

## 3.6 ApprovalService (5 tasks)
### P3-36 to P3-40: ApprovalService Tasks
> Create (pending+expiry), approve (route request), deny, get_status (agent polling), expire (auto-deny), tests.

## 3.7 PackService (6 tasks)
### P3-41 to P3-46: PackService Tasks
> Create, assign capabilities, assign to class, clone, usage stats, tests.

## 3.8 AlertService (5 tasks)
### P3-47 to P3-51: AlertService Tasks
> Create rule, evaluate thresholds, fire alert, acknowledge, tests.

## 3.9 AuthService (20 tasks)
### P3-52 to P3-71: AuthService Tasks
> Agent: create identity, validate token, rotate, revoke, capability surface. Admin: login, MFA setup/verify/recover, session, password reset, invite+setup, policy, first admin. Tests.

## 3.10 Service Integration Tests (8 tasks)
### P3-72 to P3-79: Service Integration Tests
> End-to-end flows: register→inspect→map→request. Approval flow. Fallback. Batch. Auth lifecycle.
