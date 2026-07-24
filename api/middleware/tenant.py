"""Extracts a tenant namespace from the authenticated agent's class label.

Uses the convention that an agent_class value of the form
"<namespace>:<role>" encodes the tenant in the segment before the first
colon.  This namespace is propagated via request.state for downstream
use in data isolation and multi-tenancy filters.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.middleware.constants import HEALTH_PATHS


class TenantMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        namespace = None
        if request.url.path not in HEALTH_PATHS:
            agent_class = getattr(request.state, "agent_class", None)
            if agent_class and ":" in agent_class:
                namespace = agent_class.split(":")[0]
        request.state.tenant_namespace = namespace
        return await call_next(request)
