import asyncio
import signal
import traceback
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
from api.routers.approval import router as approval_router
from api.routers.audit import router as audit_router
from api.routers.auth import router as auth_router
from api.routers.capabilities import router as capabilities_router
from api.routers.pack import router as pack_router
from api.routers.policy import router as policy_router
from api.routers.registry import router as registry_router
from api.routers.routing import router as routing_router
from api.routers.routing import router_rules
from api.routers.webhooks import router as webhooks_router
from api.seeders import run_seeders
from api.services.health import check_database, check_opa, check_redis
from api.telemetry.instrumentation import instrument_engine
from api.telemetry.logging import logger
from api.telemetry.metrics import fabric_info


@asynccontextmanager
async def lifespan(app: FastAPI):
    from sqlalchemy.ext.asyncio import create_async_engine

    app.state.readiness = "healthy"
    app.state.db_engine = create_async_engine(settings.database_url, echo=False)
    instrument_engine(app.state.db_engine)
    fabric_info.info({"version": "0.1.0", "environment": settings.environment})
    await run_seeders()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown(app)))
    yield
    app.state.readiness = "shutting_down"
    await app.state.db_engine.dispose()
    await asyncio.sleep(5)


async def _shutdown(app: FastAPI):
    app.state.readiness = "shutting_down"
    await asyncio.sleep(5)


app = FastAPI(
    title="MCP Fabric",
    description="Composable tool mesh for MCP ecosystems",
    version="0.1.0",
    lifespan=lifespan,
    contact={"name": "Debashish Ghosal", "email": "debashish@ghosal.dev"},
    license_info={"name": "MIT", "identifier": "MIT"},
)

app.add_middleware(CORSMiddleware, **CORS_CONFIG)
app.add_middleware(APIVersionMiddleware)
app.add_middleware(RequestIDMiddleware)
app.add_middleware(TracingMiddleware)
app.add_middleware(IPRateLimitMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)

app.include_router(admin_router)
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

@app.get("/health")
async def health(request: Request):
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
        "version": "0.1.0",
        "checks": checks,
    }


@app.get("/health/ready")
async def readiness(request: Request):
    if app.state.readiness == "shutting_down":
        return JSONResponse({"status": "shutting_down"}, status_code=503)
    from sqlalchemy.ext.asyncio import create_async_engine

    engine = getattr(request.app.state, "db_engine", None) or create_async_engine(
        settings.database_url, echo=False
    )
    db = await check_database(engine)
    if db != "connected":
        return JSONResponse({"status": "not_ready", "checks": {"database": db}}, status_code=503)
    return {"status": "ready"}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


@app.get("/v1/metrics")
async def metrics():
    from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.exception_handler(FabricError)
async def fabric_error_handler(request: Request, exc: FabricError):
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
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "error": "validation_error",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
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
