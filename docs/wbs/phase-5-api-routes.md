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

## 5.4 Policy Routes (5 tasks) — ✅ Done

### P5-15: POST /v1/agent-classes (#agent-classes)
- [x] Body validation via AgentClassCreate schema
- [x] Call PolicyService.create_agent_class() → 201 with AgentClassResponse
- [x] api/routers/policy.py

### P5-16: GET /v1/agent-classes
- [x] Query param: team_namespace filter
- [x] Call list_agent_classes() → 200 with list[AgentClassResponse]
- [x] api/routers/policy.py

### P5-17: GET /v1/agent-classes/{class_id}
- [x] Path param class_id UUID → call get_agent_class()
- [x] 200 with AgentClassResponse, not found → 404
- [x] api/routers/policy.py

### P5-18: POST /v1/agent-classes/{class_id}/trust
- [x] Body: TrustAssignmentCreate with server_id and trust_level
- [x] Call PolicyService.set_trust() → 201 with TrustAssignmentResponse
- [x] api/routers/policy.py

### P5-19: POST /v1/admin/policies/bundle
- [x] Body: BundleDeployRequest with rego_content
- [x] Call deploy_bundle() → 201 with OPAPolicyVersionResponse
- [x] api/routers/policy.py

## 5.5 Routing Rule Routes (3 tasks) — ✅ Done

### P5-20 to P5-22
- [x] POST /v1/routing-rules — api/routers/routing.py
- [x] GET /v1/routing-rules — api/routers/routing.py
- [x] DELETE /v1/routing-rules/{id} — api/routers/routing.py

## 5.6 Approval Routes (3 tasks) — ✅ Done

### P5-23: POST /v1/approvals
- [x] Body: ApprovalRequestCreate with agent, capability, server IDs
- [x] Call ApprovalService.create_request() → 201 with ApprovalRequestResponse
- [x] api/routers/approval.py

### P5-24: GET /v1/approvals/{request_id}
- [x] Path param → call get_status() → 200 with ApprovalStatusResponse
- [x] Not found → 404
- [x] api/routers/approval.py

### P5-25: POST /v1/approvals/{request_id}/review
- [x] Body: ApprovalAction with approver_id + optional note
- [x] Call approve(request_id, action) → 200 with ApprovalRequestResponse
- [x] Not found → 404, already resolved → 409, expired → 410
- [x] api/routers/approval.py

## 5.7 Audit Routes (2 tasks) — ✅ Done

### P5-26 to P5-27
- [x] GET /v1/audit (query+paginate) — api/routers/audit.py
- [x] POST /v1/audit/export (Celery task stub) — 501

## 5.8 Pack Routes (8 tasks) — ✅ Done

### P5-28: POST /v1/packs
- [x] Body: PackCreate with name, description, team_namespace
- [x] Call PackService.create_pack() → 201 with PackResponse
- [x] api/routers/pack.py

### P5-29: GET /v1/packs
- [x] Query params: team_namespace, limit, offset
- [x] Call list_packs() → 200 with list[PackResponse]
- [x] api/routers/pack.py

### P5-30: GET /v1/packs/{pack_id}
- [x] Path param → call get_pack() → 200 with PackResponse
- [x] Not found → 404
- [x] api/routers/pack.py

### P5-31: PUT /v1/packs/{pack_id}
- [x] Body: PackCreate → call update_pack() → 200 with PackResponse
- [x] Not found → 404
- [x] api/routers/pack.py

### P5-32: DELETE /v1/packs/{pack_id}
- [x] Path param → call delete_pack() → 204 No Content
- [x] Not found → 404
- [x] api/routers/pack.py

### P5-33: POST /v1/packs/{pack_id}/capabilities
- [x] Body: PackAssignmentRequest → assign + return updated pack
- [x] Not found → 404
- [x] api/routers/pack.py

### P5-34: POST /v1/packs/{pack_id}/clone
- [x] Body: ClonePackRequest → call clone_pack() → 201 with PackResponse
- [x] Not found → 404
- [x] api/routers/pack.py

### P5-35: GET /v1/packs/{pack_id}/usage
- [x] Path param → call get_usage_stats() → 200 with dict
- [x] Not found → 404
- [x] api/routers/pack.py

## 5.9 Auth Routes (9 tasks) — ✅ Done

### P5-36: POST /v1/auth/login
- [x] Body: LoginRequest → call admin_login() → 200 with TokenResponse
- [x] Account locked → 423, invalid credentials → 401
- [x] api/routers/auth.py

### P5-37: POST /v1/auth/connect
- [x] Body: LoginRequest → create agent token → 200 with TokenResponse
- [x] api/routers/auth.py

### P5-38: POST /v1/auth/setup
- [x] Body: SetupCompleteRequest → call first_admin_bootstrap() → 201
- [x] Already set up → 409
- [x] api/routers/auth.py

### P5-39: POST /v1/auth/mfa/setup
- [x] Requires admin auth → call mfa_setup() → 200 with MFASetupResponse
- [x] admin not found → 404
- [x] api/routers/auth.py

### P5-40: POST /v1/auth/mfa/verify-setup
- [x] Requires admin auth → call mfa_verify_setup() → 200
- [x] Invalid code → 400
- [x] api/routers/auth.py

### P5-41: POST /v1/auth/mfa/verify
- [x] Requires admin auth → TOTP verification against stored secret
- [x] Not found / not configured → 404, invalid code → 400
- [x] api/routers/auth.py

### P5-42: POST /v1/auth/mfa/recover
- [x] Requires admin auth → validate recovery code hash, consume on use
- [x] Not found → 404, invalid → 400
- [x] api/routers/auth.py

### P5-43: POST /v1/auth/password-reset
- [x] Body: email → look up admin, log request (idempotent response)
- [x] api/routers/auth.py

### P5-44: POST /v1/auth/logout
- [x] Invalidate X-Session-Token via logout_admin_session()
- [x] api/routers/auth.py

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
