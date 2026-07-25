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
**Checklist:**
- [x] api/telemetry/tracing.py — TracerProvider, resource, instrument_fastapi()
- [x] TracingMiddleware — span per request with method+url+status+request_id attributes
- [x] Registered in main.py middleware pipeline
**Success Criteria:** Every request traced. Span includes method+url+status+duration. Traces exported to backend.

### P4-03: Auth Middleware (#9)
**Effort:** 3h | **Deps:** P3-52 (auth service)
**Checklist:**
- [x] api/services/auth_service.py — JWT create/validate, bcrypt password hash/verify
- [x] AuthService.create_token() + validate_token() + hash_password() + verify_password()
- [x] AuthMiddleware — Bearer token validation, skip health/metrics, set agent_id/agent_type/agent_class
- [x] Registered in main.py middleware pipeline
- [x] 4 unit tests for AuthService, 3 integration tests for middleware
**Success Criteria:** Valid token passes. Invalid → 401. Health endpoints accessible without auth.

### P4-04: Tenant Middleware (#12)
**Effort:** 2h | **Deps:** P4-03
**Checklist:**
- [x] TenantMiddleware — extract namespace from agent_class (split on ":"), set request.state.tenant_namespace
- [x] Registered in main.py middleware pipeline
**Success Criteria:** Platform agent cannot see security servers. Editor cannot modify outside team.

### P4-05: RateLimit Middleware (#15)
**Effort:** 2h | **Deps:** P4-03
**Checklist:**
- [x] RateLimitMiddleware — in-memory sliding window per agent+path, configurable max_requests+window
- [x] Skip health/metrics endpoints
- [x] Return 429 with error message when exceeded
- [x] Registered in main.py middleware pipeline
**Success Criteria:** At limit → 429. Health/metrics bypass rate limiting.

### P4-06: Audit Middleware (#18)
**Effort:** 1.5h | **Deps:** P3-31 (audit service)
**Checklist:**
- [x] api/services/audit_service.py — log_event, query, cleanup methods
- [x] AuditMiddleware — structlog info entry per request (method+path+status+agent_id+request_id)
- [x] Skip health/metrics endpoints
- [x] Registered in main.py middleware pipeline
- [x] 3 unit tests for AuditService (log, query, cleanup)
**Success Criteria:** Audit event per authenticated request. Zero latency impact. Health not logged.

### P4-07: CORS Middleware (#21)
**Effort:** 1h | **Deps:** None
**Checklist:**
- [x] CORS_CONFIG dict in api/middleware/cors.py
- [x] Registered as CORSMiddleware in main.py via **CORS_CONFIG
- [x] Expose Fabric headers (Request-Id, Routing-Server, API-Version)
**Success Criteria:** Preflight OPTIONS returns correct CORS headers. All responses include exposed headers.

### P4-08: API Version Middleware (#24)
**Effort:** 1h | **Deps:** None
**Checklist:**
- [x] APIVersionMiddleware — Accept header/Accept-Version/query param parsing
- [x] Default to v1, unknown version → 406, Fabric-API-Version response header
- [x] 5 tests — default, Accept, Accept-Version, query param, unsupported 406
**Success Criteria:** v1 requested → v1 confirmed. No version → v1 default. Unknown → 406.
