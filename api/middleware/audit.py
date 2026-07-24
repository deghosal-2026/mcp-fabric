from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path in ("/health", "/health/ready", "/health/live", "/v1/metrics"):
            return await call_next(request)

        response = await call_next(request)

        agent_id = getattr(request.state, "agent_id", "anonymous")
        request_id = getattr(request.state, "request_id", None)
        from api.telemetry.logging import logger

        logger.info(
            "audit:request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            agent_id=agent_id,
            timestamp=datetime.now(UTC).isoformat(),
        )
        return response
