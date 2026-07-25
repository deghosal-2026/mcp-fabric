# Phase 8: Error Handling

> **Tasks:** 8 · **Effort:** 8h (1 day)  
> **Dependencies:** Phase 3, Phase 5

### P8-01: FabricError Exception Class (#102) — ✅ Done
- [x] `api/errors.py` — FabricError base class with status_code, error_code, message, details, suggestion, retry_after
- [x] 17 concrete error subclasses covering all HTTP status codes
- [x] `__str__` returns `error_code: message`

### P8-02: FastAPI Exception Handlers (#104) — ✅ Done
- [x] `@app.exception_handler(FabricError)` → JSON {error, message, details, request_id, suggestion?, retry_after?}
- [x] `@app.exception_handler(RequestValidationError)` → 422 with field-level Pydantic errors
- [x] `@app.exception_handler(Exception)` → 500 with generic message, stack logged
- [x] Binds request_id from request.state

### P8-03: Error Catalog — 400/401 Errors (#106) — ✅ Done
- [x] InvalidParameterError (400) — expected/received in details
- [x] InvalidTokenError (401) — missing/expired
- [x] TokenExpiredError (401) — past expiry
- [x] RateLimitedError (429) — retry_after included

### P8-04: Error Catalog — 403/404 Errors (#108) — ✅ Done
- [x] AccessDeniedError (403) — policy_reason in details
- [x] NamespaceRestrictedError (403) — cross-team
- [x] CapabilityNotFoundError (404) — suggestion "Did you mean X?"
- [x] ServerNotFoundError (404)

### P8-05: Error Catalog — 409/410/422/503 Errors (#110) — ✅ Done
- [x] CapabilityConflictError (409) — overlap details
- [x] SchemaBreakingChangeError (409) — breaking change details
- [x] CapabilityDeprecatedError (410) — retired_on + guidance
- [x] FabricDegradedError (503) — component + retry_after
- [x] NoHealthyServerError (503) — retry_after

### P8-06: Error Catalog — MCP-Specific Errors (#112) — ✅ Done
- [x] MCPTimeoutError → 503 no_healthy_server
- [x] MCPServerError → pass-through status from MCP server
- [x] MCPToolError → 400 invalid_parameter
- [x] MCPConnectionError → 503 fabric_degraded

### P8-07: Graceful Degradation Handlers (#114) — ✅ Done
- [x] FabricError handler catches all structured errors
- [x] Global Exception handler catches unhandled → 500
- [x] DB/Redis/OPA errors routed through FabricError hierarchy

### P8-08: Error Integration Tests (#116) — ✅ Done
- [x] 39 tests: instantiation (18), handler integration (14), response shape (7)
- [x] Tests cover all 14+ error types
- [x] Verifies status code, JSON structure, suggestion, retry_after
