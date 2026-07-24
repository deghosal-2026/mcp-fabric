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
