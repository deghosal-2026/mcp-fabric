# Phase 8: Error Handling

> **Tasks:** 8 · **Effort:** 8h (1 day)  
> **Dependencies:** Phase 3, Phase 5

### P8-01: FabricError Exception Class
**Effort:** 1h | **Deps:** None
**Checklist:** `api/errors.py` — class FabricError(Exception): status_code, error_code, message, details, suggestion, retry_after → constructor with defaults → __str__ returns error_code.
**Success Criteria:** All error types instantiable. Exception carries structured data.

### P8-02: FastAPI Exception Handlers
**Effort:** 1.5h | **Deps:** P8-01
**Checklist:** Register in main.py: @app.exception_handler(FabricError) → returns JSON {error, message, details, request_id, suggestion?, retry_after?} → @app.exception_handler(RequestValidationError) → returns 422 with field-level details → @app.exception_handler(Exception) → returns 500 with generic message (no stack trace in prod) → binds request_id from request.state.
**Success Criteria:** All errors return consistent JSON format. Validation errors show field details. 500 never leaks stack.

### P8-03: Error Catalog — 400/401 Errors
**Effort:** 1h | **Deps:** P8-01
**Checklist:** invalid_parameter (400) — malformed params with expected/received → invalid_token (401) — missing/expired → token_expired (401) — past expiry, no grace → rate_limited (429) — with Retry-After header.
**Success Criteria:** Each error returns correct status + structured body. Suggestion/retry hints present.

### P8-04: Error Catalog — 403/404 Errors
**Effort:** 1h | **Deps:** P8-01
**Checklist:** access_denied (403) — policy denied → namespace_restricted (403) — cross-team → capability_not_found (404) — with suggestion "Did you mean X?" → server_not_found (404).
**Success Criteria:** Suggestions for close matches. Access denied includes policy reason.

### P8-05: Error Catalog — 409/410/422/503 Errors
**Effort:** 1h | **Deps:** P8-01
**Checklist:** capability_conflict (409) — overlap detected → schema_breaking_change (409) — breaking upgrade → capability_deprecated (410) — {status:"deprecated", retired_on, guidance} → validation_error (422) — Pydantic errors → fabric_degraded (503) — DB/Redis/OPA down → no_healthy_server (503) — all candidates unhealthy.
**Success Criteria:** 410 includes deprecation guidance. 503 includes retry_after. 422 shows per-field errors.

### P8-06: Error Catalog — MCP-Specific Errors
**Effort:** 0.5h | **Deps:** P8-01, P2-05
**Checklist:** Map MCP client errors to HTTP: MCPTimeoutError → 503 no_healthy_server, MCPServerError → pass-through status from MCP server, MCPToolError → 400 invalid_parameter, MCPConnectionError → 503 fabric_degraded.
**Success Criteria:** MCP errors surfaced correctly to agents. Original error details preserved in response.

### P8-07: Graceful Degradation Handlers
**Effort:** 1h | **Deps:** P8-01
**Checklist:** DB connection error → catch OperationalError, return 503 with fabric_degraded → Redis connection error → catch ConnectionError, rate limiting fail-open, sessions fail-closed (re-authenticate) → OPA unreachable → policy evaluation returns deny-all (fail-secure), return 503.
**Success Criteria:** DB down → 503 not 500. Redis down → requests still flow (degraded). OPA down → all denied.

### P8-08: Error Integration Tests
**Effort:** 1h | **Deps:** P8-02 through P8-06
**Checklist:** Test all 14 error types → verify status code → verify JSON structure → verify request_id present → verify suggestion for 404 → verify retry_after for 429/503 → verify field-level details for 422 → verify no stack trace in prod mode.
**Success Criteria:** 14/14 error tests pass. Response format consistent. Sensitive data not leaked.
