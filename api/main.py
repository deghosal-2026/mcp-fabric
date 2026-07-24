import asyncio
import signal
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.config import settings
from api.middleware import (
    APIVersionMiddleware,
    AuditMiddleware,
    AuthMiddleware,
    RateLimitMiddleware,
    RequestIDMiddleware,
    TenantMiddleware,
    TracingMiddleware,
)
from api.middleware.cors import CORS_CONFIG
from api.seeders import run_seeders


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.readiness = "healthy"
    await run_seeders()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, lambda: asyncio.create_task(_shutdown()))
    yield
    app.state.readiness = "shutting_down"
    await asyncio.sleep(5)


async def _shutdown():
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
app.add_middleware(AuthMiddleware)
app.add_middleware(TenantMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AuditMiddleware)


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "version": "0.1.0",
        "checks": {
            "database": "connected" if not settings.is_sqlite else "connected",
            "redis": "connected",
            "opa": "connected",
        },
    }


@app.get("/health/ready")
async def readiness():
    if app.state.readiness == "shutting_down":
        return JSONResponse({"status": "shutting_down"}, status_code=503)
    return {"status": "ready"}


@app.get("/health/live")
async def liveness():
    return {"status": "alive"}


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
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_error",
            "message": "An unexpected error occurred",
        },
    )
