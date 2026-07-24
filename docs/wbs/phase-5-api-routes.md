# Phase 5: API Routes

> **Tasks:** 55 · **Effort:** 40h (5 days)  
> **Dependencies:** Phase 3 (services), Phase 4 (middleware)

## 5.1 Registry Routes (5 tasks) — ✅ Done

### P5-01: POST /v1/servers (#27)
- [x] Body validation via ServerCreate schema
- [x] call RegistryService.register() → 201 with ServerResponse
- [x] duplicate endpoint → 409, unreachable → 400
- [x] api/routers/registry.py

### P5-02: GET /v1/servers (#30)
- [x] Query params: team, trust, health, q, cursor, per_page
- [x] call list_servers() → 200 with PaginatedServers
- [x] api/routers/registry.py

### P5-03: GET /v1/servers/{id} (#32)
- [x] Path param server_id UUID → call get_server()
- [x] 200 with ServerDetail. Not found → 404
- [x] api/routers/registry.py

### P5-04: POST /v1/servers/{id}/inspect (#35)
- [x] Call inspect() → 200 with ServerInspectResponse
- [x] api/routers/registry.py

### P5-05: POST /v1/servers/{id}/decommission (#40)
- [x] Body: {phase, replacement_server_id?} → call decommission()
- [x] 200 with DecommissionResult, Invalid phase → 400
- [x] api/routers/registry.py

## 5.2 Capability Routes (6 tasks) — ✅ Done

### P5-06 to P5-11
- [x] POST /v1/capabilities (create) — api/routers/capabilities.py
- [x] GET /v1/capabilities (list) — with domain filter
- [x] GET /v1/capabilities/{id} (detail) — 404 if missing
- [x] POST /v1/capabilities/{id}/mappings (map tool)
- [x] POST /v1/capabilities/{id}/deprecate
- [x] CapabilityService: create, list, get, deprecate, _to_response

## 5.3 Routing Routes (3 tasks) — ✅ Done

### P5-12: POST /v1/capability/request (#61)
- [x] Body validation (CapabilityRequest)
- [x] Call RoutingService.execute() → 200 / 404
- [x] api/routers/routing.py

### P5-13: POST /v1/capability/batch (#64)
- [x] Body validation (BatchCapabilityRequest, 1-10 items)
- [x] 200 with BatchResult (per-item status)
- [x] api/routers/routing.py

### P5-14: GET /v1/capability/status/{request_id} (#68)
- [x] ApprovalService status lookup → 200 / 404
- [x] api/routers/routing.py

## 5.4 Policy Routes (5 tasks) — ⏳ Pending (need PolicyService)

### P5-15 to P5-19
POST /v1/agent-classes, GET /v1/agent-classes, GET /v1/agent-classes/{id}, POST /v1/agent-classes/{id}/trust, POST /v1/admin/policies/bundle.

## 5.5 Routing Rule Routes (3 tasks) — ✅ Done

### P5-20 to P5-22
- [x] POST /v1/routing-rules — api/routers/routing.py
- [x] GET /v1/routing-rules — api/routers/routing.py
- [x] DELETE /v1/routing-rules/{id} — api/routers/routing.py

## 5.6 Approval Routes (3 tasks) — ⏳ Pending (need ApprovalService)

### P5-23 to P5-25

## 5.7 Audit Routes (2 tasks) — ✅ Done

### P5-26 to P5-27
- [x] GET /v1/audit (query+paginate) — api/routers/audit.py
- [x] POST /v1/audit/export (Celery task stub) — 501

## 5.8 Pack Routes (8 tasks) — ⏳ Pending (need PackService)

### P5-28 to P5-35

## 5.9 Auth Routes (9 tasks) — ✅ Partial

### P5-36 to P5-44
- [x] POST /v1/auth/connect — api/routers/auth.py
- [x] POST /v1/auth/login — api/routers/auth.py
- [ ] POST /v1/auth/mfa/verify
- [ ] POST /v1/auth/mfa/setup
- [ ] POST /v1/auth/mfa/verify-setup
- [ ] POST /v1/auth/mfa/recover
- [ ] POST /v1/auth/password-reset
- [ ] POST /v1/auth/password-reset/complete
- [ ] POST /v1/auth/setup + POST /v1/auth/logout

## 5.10 Admin Routes (9 tasks) — ⏳ Pending

### P5-45 to P5-53

## 5.11 Health + Metrics Routes (3 tasks) — ✅ Done

### P5-54 to P5-56
- [x] GET /v1/health (real DB+Redis+OPA checks)
- [x] GET /v1/health/ready (503 during shutdown, depends on DB)
- [x] GET /v1/health/live (always alive)
- [x] GET /v1/metrics (Prometheus format)

## 5.12 Webhook Routes (4 tasks) — ⏳ Pending

### P5-57 to P5-60
