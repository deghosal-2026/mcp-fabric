# Phase 4: Middleware

> **Tasks:** 8 · **Effort:** 16h (2 days)  
> **Dependencies:** Phase 3 (services for auth/tenant lookup)

### P4-01: RequestID Middleware (#2)
**Effort:** 1.5h | **Deps:** None
**Checklist:**
- [x] Generate UUID per request (or passthrough existing Fabric-Request-Id header)
- [x] Set request.state.request_id
- [x] Set Fabric-Request-Id response header
- [x] Registered in main.py middleware pipeline
**Success Criteria:** Every response has Fabric-Request-Id. All logs for a request share same ID.

### P4-02: Tracing Middleware (#5)
**Effort:** 2h | **Deps:** P7-02 (OTel setup)
**Checklist:** Create OTel span "http_request" → set attributes (method, url, status, request_id, agent_id if auth'd) → propagate trace context via headers → end span after response.
**Success Criteria:** Every request traced. Span includes method+url+status+duration. Traces exported to backend.

### P4-03: Auth Middleware (#9)
**Effort:** 3h | **Deps:** P3-52 (auth service)
**Checklist:** Extract Bearer token from Authorization header → agent endpoints: validate via AuthService → admin endpoints: validate JWT session → public endpoints: skip (health, metrics, docs) → set request.state.agent_identity or admin_user → invalid/expired → 401.
**Success Criteria:** Valid token passes. Invalid → 401. Health endpoints accessible without auth.

### P4-04: Tenant Middleware (#12)
**Effort:** 2h | **Deps:** P4-03
**Checklist:** After auth → extract team_namespace from agent_identity.agent_class or admin_user → set request.state.tenant_namespace → editor admin scoped to their team → global admin sees all → all DB queries auto-filtered.
**Success Criteria:** Platform agent cannot see security servers. Editor cannot modify outside team.

### P4-05: RateLimit Middleware (#15)
**Effort:** 2h | **Deps:** P4-03
**Checklist:** Key: fcp:ratelimit:{identity_id}:{minute} → Redis INCR → if > limit → 429 → response headers: Retry-After, X-RateLimit-Limit, X-RateLimit-Remaining → Redis down → fail-open.
**Success Criteria:** At limit → 429. Headers present. Redis outage → requests pass.

### P4-06: Audit Middleware (#18)
**Effort:** 1.5h | **Deps:** P3-31 (audit service)
**Checklist:** FastAPI background task after response → log: method+path+status+agent_id+request_id+latency → skip health/metrics → skip 401 (no identity) → fail-open.
**Success Criteria:** Audit event per authenticated request. Zero latency impact. Health not logged.

### P4-07: CORS Middleware (#21)
**Effort:** 1h | **Deps:** None
**Checklist:** allow_origins from config (default localhost:3000) → allow_methods GET/POST/PUT/PATCH/DELETE/OPTIONS → allow_headers Authorization/Content-Type/Accept → expose_headers Fabric-Request-Id/Fabric-Routing-Server/Fabric-API-Version → max_age 3600.
**Success Criteria:** Admin UI calls from different origin work. Preflight OPTIONS returns correct headers.

### P4-08: API Version Middleware (#24)
**Effort:** 1h | **Deps:** None
**Checklist:** Parse Accept header for application/vnd.fabric.vX+json → set request.state.api_version → default v1 if absent + warning header → unknown version → 406 → response: Fabric-API-Version + Content-Type headers.
**Success Criteria:** v1 requested → v1 confirmed. No version → v1 default + warning. Unknown → 406.
