# Phase 5: API Routes

> **Tasks:** 55 · **Effort:** 40h (5 days)  
> **Dependencies:** Phase 3 (services), Phase 4 (middleware)

## 5.1 Registry Routes (5 tasks)

### P5-01: POST /v1/servers
**Effort:** 1.5h | **Deps:** P3-01
**Checklist:** Body validation via ServerCreate schema → call RegistryService.register() → 201 with ServerResponse → duplicate endpoint → 409 → unreachable → 400. Auth: admin/editor.
**Success Criteria:** Valid body → 201 with auto-discovered tools. Duplicate → 409. Unreachable → 400.

### P5-02: GET /v1/servers
**Effort:** 1.5h | **Deps:** P3-03
**Checklist:** Query params: team, trust, health, q (search), cursor, per_page → call list_servers() → 200 with PaginatedServers. Empty → 200 with []. Auth: admin/editor/viewer.
**Success Criteria:** All filter combinations work. Cursor pagination correct. Empty returns 200.

### P5-03: GET /v1/servers/{id}
**Effort:** 1h | **Deps:** P3-04
**Checklist:** Path param server_id UUID → call get_server() → 200 with ServerDetail. Not found → 404. Auth: admin/editor/viewer.
**Success Criteria:** Full detail returned. 404 for nonexistent.

### P5-04: POST /v1/servers/{id}/inspect
**Effort:** 1h | **Deps:** P3-02
**Checklist:** Call inspect() → 200 with ServerInspectResponse (tools_added/removed/changed). Auth: admin/editor.
**Success Criteria:** Diff returned. Breaking changes flagged.

### P5-05: POST /v1/servers/{id}/decommission
**Effort:** 1h | **Deps:** P3-05
**Checklist:** Body: {phase, replacement_server_id?} → call decommission() → 200 with DecommissionResult. Invalid phase → 400. Already decommissioned → 409. Auth: admin.
**Success Criteria:** Phase progression enforced. Dependency report returned.

## 5.2 Capability Routes (6 tasks)

### P5-06 to P5-11
POST /v1/capabilities (create), GET /v1/capabilities (list), GET /v1/capabilities/{id} (detail), POST /v1/capabilities/{id}/mappings (map tool), POST /v1/capabilities/{id}/deprecate, POST /v1/capabilities/{id}/aliases.
Each 1-1.5h. Auth: admin/editor for write, viewer for read.

## 5.3 Routing Routes (3 tasks)

### P5-12: POST /v1/capability/request
**Effort:** 2h | **Deps:** P3-23
**Checklist:** Agent auth → body validation (CapabilityRequest) → call RoutingService.execute() → 200 success / 202 approval_pending / 403 denied / 404 not_found → response headers: Fabric-Routing-Server, Fabric-Routing-Reason.
**Success Criteria:** All response types correct. Headers present. Agent token required.

### P5-13: POST /v1/capability/batch
**Effort:** 2h | **Deps:** P3-30
**Checklist:** Agent auth → body validation (BatchCapabilityRequest, 1-10 items) → call execute_batch() → 200 with BatchResult (per-item status). Exceeds limit → 422.
**Success Criteria:** Parallel execution. Mixed results supported. 11 items → 422.

### P5-14: GET /v1/capability/status/{request_id}
**Effort:** 1h | **Deps:** P3-38
**Checklist:** Agent auth → call ApprovalService.get_status() → 200 with status (pending/approved/denied/expired). Not found → 404.
**Success Criteria:** Agent polls for approval resolution.

## 5.4 Policy Routes (5 tasks)

### P5-15 to P5-19
POST /v1/agent-classes, GET /v1/agent-classes, GET /v1/agent-classes/{id}, POST /v1/agent-classes/{id}/trust, POST /v1/admin/policies/bundle.
Each 1h. Auth: admin/editor.

## 5.5 Routing Rule Routes (3 tasks)

### P5-20 to P5-22
POST /v1/routing-rules, GET /v1/routing-rules, DELETE /v1/routing-rules/{id}.
Each 0.5h. Auth: admin/editor.

## 5.6 Approval Routes (3 tasks)

### P5-23 to P5-25
GET /v1/approvals, POST /v1/approvals/{id}/approve, POST /v1/approvals/{id}/deny.
Each 1h. Auth: admin/editor for approve/deny.

## 5.7 Audit Routes (2 tasks)

### P5-26 to P5-27
GET /v1/audit (query+paginate), POST /v1/audit/export (create Celery task). Auth: admin/editor for export, viewer for query.

## 5.8 Pack Routes (8 tasks)

### P5-28 to P5-35
POST /v1/packs (create), GET /v1/packs (list), GET /v1/packs/{id} (detail+stats), POST /v1/packs/{id}/capabilities, DELETE /v1/packs/{id}/capabilities/{cap_id}, POST /v1/packs/{id}/classes, DELETE /v1/packs/{id}/classes/{class_id}, POST /v1/packs/{id}/clone, DELETE /v1/packs/{id}.
Each 0.5-1h. Auth: admin/editor.

## 5.9 Auth Routes (9 tasks)

### P5-36 to P5-44
POST /v1/auth/connect, POST /v1/auth/login, POST /v1/auth/mfa/verify, POST /v1/auth/mfa/setup, POST /v1/auth/mfa/verify-setup, POST /v1/auth/mfa/recover, POST /v1/auth/password-reset, POST /v1/auth/password-reset/complete, POST /v1/auth/setup, POST /v1/auth/logout.
Each 1h. Connect requires agent token. Rest are public.

## 5.10 Admin Routes (9 tasks)

### P5-45 to P5-53
POST /v1/admin/users/invite, GET /v1/admin/users, GET /v1/admin/users/{id}, PATCH /v1/admin/users/{id}, POST /v1/admin/users/{id}/deactivate, POST /v1/admin/users/{id}/unlock, POST /v1/admin/users/{id}/reset-mfa, POST /v1/admin/agent-identities (creates token - returned once), GET /v1/admin/agent-identities, POST /v1/admin/agent-identities/{id}/rotate, POST /v1/admin/agent-identities/{id}/revoke.
Each 0.5-1h. Auth: admin for user mgmt, admin/editor for agent mgmt.

## 5.11 Health + Metrics Routes (3 tasks)

### P5-54 to P5-56
GET /v1/health (full check: DB+Redis+OPA), GET /v1/health/ready (readiness probe), GET /v1/health/live (liveness probe). No auth. /ready returns 503 during shutdown.

## 5.12 Webhook Routes (4 tasks)

### P5-57 to P5-60
POST /v1/agents/{id}/webhooks (register + return secret), GET /v1/agents/{id}/webhooks (list), DELETE /v1/agents/{id}/webhooks/{id}, POST /v1/agents/{id}/webhooks/{id}/reactivate. Auth: agent token or admin.
