"""FastAPI application entrypoint for MCP Fabric.

This module is the root of the HTTP service. It:
  - Creates the FastAPI app with metadata, lifespan hooks, and all middleware
  - Registers 11 route modules (admin, registry, auth, routing, policy, etc.)
  - Defines three health-check endpoints (/health, /health/ready, /health/live)
  - Exposes a /v1/metrics endpoint for Prometheus scraping
  - Registers three exception handlers that convert exceptions into a
    consistent JSON error envelope

Architecture notes:
  - Middleware order matters: CORSMiddleware runs first (outermost), then
    APIVersion, RequestID, Tracing, IPRateLimit, Auth, Tenant, RateLimit,
    and Audit runs last (innermost, closest to the router). This ordering
    ensures auth and tenant context are set before rate-limit checks and
    audit logging.
  - The lifespan context manager handles graceful startup (engine creation,
    seeder execution, signal handlers) and shutdown (engine disposal).
  - Exception handlers are registered on the app so FabricError subclasses
    produce structured JSON, validation errors produce 422 with field-level
    details, and truly unhandled exceptions produce 500 with a generic
    message (no stack trace leakage).
"""

import asyncio
import signal
import traceback
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from api.config import settings
from api.errors import FabricError
from api.middleware import (
    APIVersionMiddleware,
    AuditMiddleware,
    AuthMiddleware,
    IPRateLimitMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    TenantMiddleware,
    TracingMiddleware,
)
from api.middleware.cors import CORS_CONFIG
from api.routers.admin import router as admin_router
from api.routers.alert import router as alert_router
from api.routers.approval import router as approval_router
from api.routers.audit import router as audit_router
from api.routers.auth import router as auth_router
from api.routers.capabilities import router as capabilities_router
from api.routers.pack import router as pack_router
from api.routers.policy import router as policy_router
from api.routers.registry import router as registry_router
from api.routers.resource import router as resource_router
from api.routers.routing import router as routing_router
from api.routers.routing import router_rules
from api.routers.webhooks import router as webhooks_router
from api.seeders import run_seeders
from api.services.health import check_database, check_opa, check_redis
from api.telemetry.instrumentation import instrument_engine
from api.telemetry.logging import logger
from api.telemetry.metrics import fabric_info


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """FastAPI lifespan context manager for startup and shutdown logic.

    WHAT: Runs on application startup (before handling the first request)
    and shutdown (after the last response is sent). Startup creates the
    async SQLAlchemy engine, attaches OpenTelemetry instrumentation,
    runs database seeders (e.g., admin user, default capabilities), and
    registers signal handlers for graceful SIGTERM/SIGINT shutdown.

    WHY: This replaces the deprecated on_event("startup")/on_event("shutdown")
    pattern. It guarantees the engine is created exactly once and disposed
    cleanly, and it gives the app a chance to set readiness state before
    the load balancer sends traffic.

    IMPORTANT: The signal handler registration is wrapped in
    suppress(NotImplementedError) because asyncio signal handlers are
    not supported on Windows or in some event loop implementations
    (e.g., uvloop may not support add_signal_handler on all platforms).
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    app.state.readiness = "healthy"
    app.state.db_engine = create_async_engine(settings.database_url, echo=False)
    instrument_engine(app.state.db_engine)
    fabric_info.info({"version": "0.3.0", "environment": settings.environment})
    await run_seeders()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(app)))
    yield
    app.state.readiness = "shutting_down"
    await app.state.db_engine.dispose()
    await asyncio.sleep(5)


async def _shutdown(app: FastAPI) -> None:
    """Graceful shutdown handler for SIGTERM/SIGINT.

    WHAT: Sets readiness to "shutting_down" and waits 5 seconds so
    in-flight requests can complete and the load balancer can route
    traffic away before the engine is disposed.

    WHY: Without this delay, the engine disposal in lifespan() would
    cut off active database operations, causing 500 errors for users
    whose requests are still being processed.
    """
    app.state.readiness = "shutting_down"
    await asyncio.sleep(5)


app = FastAPI(
    title="MCP Fabric",
    description="Composable tool mesh for MCP ecosystems",
    version="0.3.0",
    lifespan=lifespan,
    contact={"name": "Debashish Ghosal", "email": "debashish@ghosal.dev"},
    license_info={"name": "MIT", "identifier": "MIT"},
)

# Middleware registration order (outermost → innermost):
#   1. CORSMiddleware       — handle CORS preflight and headers
#   2. APIVersionMiddleware — negotiate API version from Accept header
#   3. RequestIDMiddleware  — assign a unique traceable ID per request
#   4. TracingMiddleware    — create OpenTelemetry span and record metrics
#   5. IPRateLimitMiddleware— rate-limit by client IP before auth
#   6. AuthMiddleware       — validate Bearer JWT, set agent identity
#   7. TenantMiddleware     — extract tenant namespace from agent_class
#   8. RateLimitMiddleware  — rate-limit by authenticated agent identity
#   9. AuditMiddleware      — log request/response summary to audit trail
app.add_middleware(CORSMiddleware, **CORS_CONFIG)  # type: ignore
app.add_middleware(APIVersionMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(IPRateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)

app.include_router(admin_router)
app.include_router(alert_router)
app.include_router(registry_router)
app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(capabilities_router)
app.include_router(routing_router)
app.include_router(router_rules)
app.include_router(policy_router)
app.include_router(approval_router)
app.include_router(pack_router)
app.include_router(webhooks_router)
app.include_router(resource_router)


@app.get("/health")
async def health(request: Request) -> dict[str, object]:
    """Detailed health check probing database, Redis, and OPA connectivity.

    WHAT: Probes all three core dependencies in parallel and returns a
    per-component status dict. The overall status is "healthy" only if
    every dependency reports "connected"; otherwise it is "degraded".

    WHY: Load balancers and Kubernetes probes use this to determine if
    the service can accept traffic. A degraded status does not kill the
    pod — it alerts operators that a dependency is down while the
    service may still serve cached or unaffected requests.

    IMPORTANT: Falls back to creating a temporary engine if the lifespan
    engine was not yet initialized (edge case during early startup).
    """
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = getattr(request.app.state, "db_engine", None) or create_async_engine(
        settings.database_url, echo=False
    )
    db = await check_database(engine)
    redis = await check_redis(settings.redis_url)
    opa = await check_opa(settings.opa_url)
    checks = {"database": db, "redis": redis, "opa": opa}
    overall = "healthy" if all(v == "connected" for v in checks.values()) else "degraded"
    return {
        "status": overall,
        "version": "0.3.0",
        "checks": checks,
    }


@app.get("/health/ready")
async def readiness(request: Request) -> Response:
    """Kubernetes readiness probe — returns 503 if shutting down or DB is down.

    WHAT: A lightweight check that only verifies the database connection.
    Returns 503 immediately if the app is in shutting_down state (graceful
    shutdown in progress) or if the database is unreachable.

    WHY: Kubernetes uses this probe to stop sending traffic to a pod
    that is draining or unhealthy. A 503 response causes the pod to be
    removed from the service's endpoint list, avoiding request failures.
    """
    if app.state.readiness == "shutting_down":
        return JSONResponse({"status": "shutting_down"}, status_code=503)
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = getattr(request.app.state, "db_engine", None) or create_async_engine(
        settings.database_url, echo=False
    )
    db = await check_database(engine)
    if db != "connected":
        return JSONResponse({"status": "not_ready", "checks": {"database": db}}, status_code=503)
    return JSONResponse({"status": "ready"})


@app.get("/health/live")
async def liveness() -> dict[str, str]:
    """Kubernetes liveness probe — returns 200 if the process is alive.

    WHAT: The simplest possible health check — does not probe any
    dependency. Returns {"status": "alive"} immediately.

    WHY: Kubernetes uses this probe to detect if the process has frozen
    or deadlocked (no response at all). This probe should never depend
    on any external service to avoid cascading failures.
    """
    return {"status": "alive"}


@app.get("/v1/metrics")
async def metrics() -> Response:
    """Prometheus metrics endpoint.

    WHAT: Exposes all Prometheus metrics (counters, histograms, gauges)
    registered via api/telemetry/metrics.py in the standard Prometheus
    text format.

    WHY: Prometheus scrapes this endpoint periodically. By using
    generate_latest(), we avoid maintaining a separate metrics server
    and keep everything in-process.
    """
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(FabricError)
async def fabric_error_handler(request: Request, exc: FabricError) -> JSONResponse:
    """Structured JSON error response for all FabricError subclasses.

    WHAT: Catches any FabricError (or subclass) raised anywhere in the
    application and returns a consistent JSON envelope containing:
      - error:      machine-readable error code (e.g., "invalid_token")
      - message:    human-readable description
      - details:    optional dict with additional context
      - request_id: correlated request ID for log tracing
      - suggestion: optional guidance on how to fix the issue
      - retry_after: optional seconds to wait before retrying (429/503)

    WHY: Returning a consistent error format lets API clients (especially
    other agents) parse errors programmatically without guessing the
    response structure.

    IMPORTANT: The request_id is read from request.state (set by
    RequestIDMiddleware). It is set to None if the middleware has not
    yet run or if an error occurs before the middleware chain.
    """
    rid = getattr(request.state, "request_id", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.error_code,
            "message": exc.message,
            "details": exc.details,
            "request_id": rid,
            "suggestion": exc.suggestion,
            "retry_after": exc.retry_after,
        },
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handles Pydantic/FastAPI request validation errors (422).

    WHAT: Catches RequestValidationError (raised by FastAPI when request
    body, query parameters, or path parameters fail validation against
    Pydantic schemas) and returns a 422 with field-level error details
    from exc.errors().

    WHY: Without this handler, FastAPI returns the default 422 response
    which uses a different format than FabricError responses. This
    handler ensures all error responses follow the same envelope pattern
    (error code + message + details) so clients have a consistent
    contract.

    IMPORTANT: The request_id is intentionally omitted here because
    this error path is triggered by FastAPI's request parsing, which
    may happen before the middleware chain has set request.state.
    Using getattr with a default would mask bugs, so we lean toward
    omission in the response.
    """
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unexpected/unhandled exceptions (500).

    WHAT: Catches any Exception that is NOT a FabricError or
    RequestValidationError. Logs the full traceback at ERROR level
    with request context (method, path, error string) and returns a
    generic 500 response with no stack trace.

    WHY: This is a safety net — if a bug or unexpected condition
    surfaces, we want to:
      1) Log enough context for debugging without leaking internals
      2) Return a safe, non-revealing error to the client
      3) Avoid crashing the process (the server keeps running)

    IMPORTANT: The response intentionally omits details and stack trace
    to avoid leaking sensitive information. Logging the traceback to
    the structured logger allows operators to correlate the 500 with
    the full context in the log aggregator.
    """
    logger.error(
        "unhandled_exception",
        method=request.method,
        path=request.url.path,
        error=str(exc),
        traceback=traceback.format_exc(),
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
        },
    )
