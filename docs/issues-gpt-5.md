## Codebase Review — Findings and Recommendations

Scope: Middleware, services, telemetry, and app wiring as of this commit. Findings are grouped by severity (P0 = critical, P1 = high-value quality, P2 = style/ergonomics). File/line references match the current tree.

### P0 — Critical Bugs / Security Risks

1) Duplicate tracing spans per request
- Location: `api/main.py:54-63` (auto-instrumentation), `api/middleware/tracing.py` (custom span)
- Issue: `instrument_fastapi(app)` creates a server span for each request while `TracingMiddleware` also creates a span. This yields duplicate/nested spans for the same request.
- Fix: Pick one strategy:
  - Keep auto-instrumentation: remove `TracingMiddleware` and add span attributes via hooks if needed.
  - Keep custom middleware: remove `instrument_fastapi(app)` and explicitly add attributes you want to persist.
- How to test:
  - Configure a test exporter (e.g., OTLP to a local collector or in-memory exporter) and send a single request to `/health`. Verify only one server span exists per request. Add a unit/integration test that inspects exported spans count for one request equals 1.

2) Health endpoints return fabricated statuses
- Location: `api/main.py:66-76`
- Issue: `/health` always returns "connected" for DB/Redis/OPA; readiness/liveness do not probe dependencies.
- Fix: Implement probes:
  - DB: execute `SELECT 1` using the engine/AsyncSession.
  - Redis: `PING` via client.
  - OPA: `GET /health` or evaluate a trivial rule.
  - Make `/health/ready` return 503 if any dependency is down; keep `/health/live` minimal.
- How to test:
  - Unit: monkeypatch probe functions to return failure and assert readiness is 503.
  - Integration: bring Redis/OPA down (or point to invalid URL) and assert readiness reports degraded.

3) Rate limiting order and proxy-awareness
- Location: `api/main.py:59-63` (middleware order), `api/middleware/rate_limit.py:21-28` (IP fallback)
- Issue: Limiter runs after Auth so unauthenticated traffic bypasses throttling; fallback keys by `request.client.host`, ignoring `X-Forwarded-For`.
- Fix:
  - Introduce a pre-auth IP limiter (trusted proxy aware) placed before `AuthMiddleware`.
  - Keep post-auth per-agent limiter for authenticated routes.
  - Parse `X-Forwarded-For` only if `request.client.host` is a trusted proxy; otherwise ignore.
- How to test:
  - Create a minimal app in tests registering pre-auth limiter; fire 3 unauthenticated requests with `max_requests=2` and assert the 3rd is 429.
  - Send requests with different `X-Forwarded-For` values and assert they map to distinct buckets; confirm behavior when no trusted proxy is configured.

4) JWT hardening gaps
- Location: `api/services/auth_service.py:15-17, 34-41, 46-51`
- Issue: Single HS256 secret, no issuer/audience validation, no rotation (`kid`), no `nbf`/`jti`.
- Fix:
  - Add `iss` and `aud` to payload and validate them on decode.
  - Switch to RS256 with public-key verification; include `kid` header and key lookup.
  - Optionally add `nbf` and `jti` and maintain a revoked-JTI store for logout/revocation.
- How to test:
  - Generate token with wrong `aud`/`iss` and assert 401.
  - Generate RS256 tokens with different `kid` and assert verification picks correct key.
  - Add a revoked `jti` to store and assert token is rejected.

### P1 — High-Value Quality / Design Gaps

5) API version negotiation mismatches vendor media type
- Location: `api/middleware/api_version.py:34-43`
- Issue: Parses `Accept: application/json; version=1` and `Accept-Version`, but not vendor type `application/vnd.fabric.v1+json` referenced in WBS.
- Fix: Add detection for `application/vnd.fabric.v(\d+)\+json` and return that version when matched.
- How to test:
  - Add tests sending `Accept: application/vnd.fabric.v1+json` and assert `Fabric-API-Version` is `1`.
  - Add a `v2` request and assert 406 with supported_versions containing `1`.

6) Tenant extraction heuristic is brittle
- Location: `api/middleware/tenant.py:14-16`
- Issue: `agent_class.split(":")[0]` assumes exactly one colon; multi-part classes truncate incorrectly.
- Fix: Define a contract (e.g., `org:team` or `org:team:role`) and parse accordingly; validate and set `tenant_namespace=None` if invalid.
- How to test:
  - Provide `agent_class="acme:platform"` → expect `tenant_namespace="acme"`.
  - Provide `agent_class="acme:platform:read"` if allowed schema → expect `acme`; malformed inputs → `None`.

7) Missing audit for auth failures
- Location: Middleware order in `api/main.py:59-63`, logic in `api/middleware/audit.py`
- Issue: 401 responses from `AuthMiddleware` are not logged by `AuditMiddleware` which executes after `call_next`.
- Fix: Log failures in `AuthMiddleware` before returning 401 (emit structlog or async audit event) or move `AuditMiddleware` earlier with logic to record both success and failure.
- How to test:
  - Send request with missing token; assert an `audit:request` (or failure-specific) log is emitted with status 401 and no `agent_id`.

8) `WWW-Authenticate` header missing on 401
- Location: `api/middleware/auth.py:29-35, 41-44`
- Issue: 401 responses omit `WWW-Authenticate: Bearer` header with `error` and `error_description` per RFC 6750.
- Fix: Add header to both 401 responses.
- How to test:
  - Send request without token; assert response header `WWW-Authenticate` contains `Bearer` and error details.

9) OTel provider override may conflict with external init
- Location: `api/telemetry/tracing.py:25-31`
- Issue: `_get_tracer()` always sets a new provider; if a provider is already installed (e.g., via env-based init), this clobbers it.
- Fix: If `trace.get_tracer_provider()` is already an SDK provider with processors, skip `set_tracer_provider` and only add processors if needed.
- How to test:
  - Pre-initialize a provider in a test, call `_get_tracer()`, assert the original provider instance remains.

10) Logging lacks configuration/redaction
- Location: `api/telemetry/logging.py`
- Issue: `structlog.get_logger()` without processors/formatters/context binding/redaction.
- Fix: Add structlog configuration per P7-03 (JSON in prod, console in dev, contextvars, redaction for tokens/passwords/large bodies).
- How to test:
  - Unit: configure `environment=production`, emit a log with `token`, assert output is JSON and token value is redacted.

11) In-memory rate limit scalability/perf
- Location: `api/middleware/rate_limit.py`
- Issue: Per-process dict (not shared across workers), list of timestamps per key (O(n) sliding window), periodic global cleanup.
- Fix: For prod, Redis-backed limiter (atomic INCR/EXPIRE) as per WBS; otherwise switch to `collections.deque` with bounded size; persist to shared store for multi-worker consistency.
- How to test:
  - Functional: existing tests. Performance: micro-bench loop on hot keys; confirm stable latency and bounded memory growth.

12) AuditService commit-per-event overhead
- Location: `api/services/audit_service.py:30-33`
- Issue: One DB commit per event can add latency under bursts.
- Fix: Accept for now; later introduce async queue (Celery/Kafka) and batch writes.
- How to test:
  - Load test: fire N parallel log_event calls, measure latency; compare against queued/batched implementation in Phase 6.

13) Exception handler logs raw tracebacks without redaction
- Location: `api/main.py:105-111`
- Issue: Full traceback logged; without processors, secrets/PII may leak.
- Fix: Implement structlog processors that redact sensitive fields; avoid logging raw request bodies.
- How to test:
  - Trigger an exception with a fake token or password in context; assert logs contain redacted values.

14) CORS exposes `Fabric-Routing-Server` but nothing sets it
- Location: `api/middleware/cors.py:7-11`
- Issue: Header is exposed but not produced anywhere.
- Fix: Remove from `expose_headers` or implement the header when routing server is selected.
- How to test:
  - If removed: run a CORS preflight request and assert header not exposed. If implemented: assert header appears on routed responses.

15) DI ergonomics for AuthMiddleware
- Location: `api/middleware/auth.py:19-22`
- Issue: Middleware constructs `AuthService()` internally, making swapping secrets/implementations harder.
- Fix: Provide `AuthService` instance from app startup (via dependency container/factory) and pass into `add_middleware(AuthMiddleware, auth_service=svc)`.
- How to test:
  - In tests, inject a stub `AuthService` and assert middleware uses it (e.g., validate special tokens).

### P2 — Style / Ergonomics / Tests

16) Missing valid-token middleware test
- Location: `tests/middleware/test_auth.py`
- Issue: Only failure paths are tested; no success path asserting `request.state` values.
- Fix: Add a test that issues a valid JWT and asserts the downstream handler receives populated `request.state.*`.
- How to test:
  - Create a token with `AuthService(secret_key="test")`; call a protected route with `Authorization: Bearer <token>`; assert 200 and state fields.

17) Suppressed type hints in middleware dispatch
- Location: `api/middleware/*` (`dispatch` methods)
- Issue: `# type: ignore[no-untyped-def]` hides typing gaps.
- Fix: Update signatures to `dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response` and import appropriate types.
- How to test:
  - Run `mypy --strict` and confirm no `no-untyped-def` errors in middleware.

18) RegistryService typing inconsistencies
- Location: `api/services/registry_service.py`, `tests/services/test_registry_service.py`
- Issue: LSP shows ORM `Column[...]` leaking into DTOs; strict typing is not satisfied.
- Fix: Introduce DTO mappers or Pydantic ORM models with `model_config = from_attributes`; avoid passing raw Columns to functions.
- How to test:
  - Run `mypy --strict` and confirm these errors are resolved; keep unit tests passing.

19) Readiness/teardown lifecycle
- Location: `api/main.py:27-43`
- Issue: Shutdown only toggles readiness and sleeps; no client/engine closes.
- Fix: Close DB/Redis/httpx/otel exporters in `_shutdown`; update readiness state only after cleanup completes.
- How to test:
  - Add test that patches client close methods and asserts they are called during lifespan shutdown.

20) TenantMiddleware health-path behavior inconsistent
- Location: `api/middleware/tenant.py`
- Issue: Does not skip health/metrics like others (Auth/RateLimit/Audit). Not a bug, but inconsistent.
- Fix: Either skip or not across all middleware for predictability; document behavior.
- How to test:
  - Add a test hitting `/health` and assert TenantMiddleware is bypassed if standardizing on skipping.

### Open Questions / Assumptions

1. Tracing strategy: Prefer a single server span (auto-instrumentation) or a custom span with tailored attributes? If custom, remove auto-instrumentation to avoid duplicates and adopt a sampler/exporter policy explicitly.
2. Auth token semantics: Define `iss`/`aud`? Should tokens be environment-scoped to prevent reuse? Will we need MFA/admin claims encoded? Plan for rotation?
3. Rate limit policy: Throttle unauthenticated endpoints too? If yes, move IP limiter pre-auth; add proxy-awareness.
4. Audit logging target: Synchronous DB writes acceptable, or move to async queue per Phase 6 for durability/latency isolation?

### Suggested Changes (Actionable Summary)

1. Tracing
   - Remove either `TracingMiddleware` or `instrument_fastapi(app)`; if keeping custom middleware, enrich spans and document attributes; add sampler/exporter config.

2. Health Checks
   - Replace fabricated statuses with real probes; wire readiness to dependency states; keep liveness minimal.

3. Auth Hardening
   - Add `iss`/`aud`, consider RS256, add `nbf`/`jti`, support `kid` rotation.

4. Rate Limiting
   - Introduce pre-auth IP limiting (proxy-aware) and retain post-auth per-agent limiting; plan Redis-backed implementation for prod.

5. Logging
   - Implement structlog config (P7-03): prod JSON, dev console, redaction processors, request/agent context binding.

6. API Version
   - Support `application/vnd.fabric.vN+json` in version middleware; align with WBS and client expectations.

7. Tests
   - Add success-path AuthMiddleware test; add tenant parsing tests; once tracing strategy chosen, add a test ensuring no duplicate server spans.

8. Types/Consistency
   - Remove `type: ignore` on middleware; fix RegistryService/model typing issues; adopt mypy-strict discipline outlined in AGENTS.md.
