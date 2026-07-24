"""Emits a structured audit log entry for every authenticated request.

Records the method, path, status code, agent identity, and request ID
so operators can trace who did what.  Health-check paths are skipped to
keep the audit log focused on business operations.
"""

from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.middleware.constants import HEALTH_PATHS
from api.telemetry.logging import logger


class AuditMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)

        response = await call_next(request)

        agent_id = getattr(request.state, "agent_id", "anonymous")
        request_id = getattr(request.state, "request_id", None)

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
