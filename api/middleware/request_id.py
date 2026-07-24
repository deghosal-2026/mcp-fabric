"""Assigns a unique request ID to every HTTP request.

Uses the Fabric-Request-Id header if the caller provides one (for
distributed trace correlation), otherwise generates a new UUID.  The ID
is echoed back on the response header so callers can correlate requests
with server-side logs.
"""

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        request_id = request.headers.get("Fabric-Request-Id", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["Fabric-Request-Id"] = request_id
        return response
