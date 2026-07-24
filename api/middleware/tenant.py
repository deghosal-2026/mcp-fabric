from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        namespace = None
        agent_class = getattr(request.state, "agent_class", None)
        if agent_class and ":" in agent_class:
            namespace = agent_class.split(":")[0]
        request.state.tenant_namespace = namespace
        return await call_next(request)
