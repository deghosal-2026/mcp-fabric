from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from api.middleware.constants import HEALTH_PATHS
from api.services.auth_service import AuthService, InvalidTokenError


class AuthMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, auth_service: AuthService | None = None):
        super().__init__(app)
        self.auth = auth_service or AuthService()

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_token",
                    "message": "Missing or invalid Authorization header",
                },
            )

        token = auth_header.removeprefix("Bearer ")
        try:
            payload = self.auth.validate_token(token)
        except InvalidTokenError:
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "message": "Token is invalid or expired"},
            )

        request.state.agent_id = payload.get("sub")
        request.state.agent_type = payload.get("type", "agent")
        request.state.agent_class = payload.get("agent_class")
        request.state.role = payload.get("role", "agent")
        return await call_next(request)
