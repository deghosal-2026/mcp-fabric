"""Extracts a tenant namespace from the authenticated agent's class label.

Uses the convention that an agent_class value of the form
"<namespace>:<role>" encodes the tenant in the segment before the first
colon.  This namespace is propagated via request.state for downstream
use in data isolation and multi-tenancy filters.

TENANT ENCODING CONVENTION:
  The JWT's agent_class claim follows the format: "namespace:role"
  Examples:
    - "acme-corp:admin"     → namespace = "acme-corp", role = "admin"
    - "acme-corp:developer" → namespace = "acme-corp", role = "developer"
    - "agent"               → namespace = None (no colon — no tenant)

  When agent_class does not contain a colon (e.g., just "agent" or
  "my-agent"), the tenant_namespace is None, meaning the agent operates
  in the global namespace with access to all capabilities.

REQUEST PROCESSING ORDER:
  1. Skip tenant extraction for health-check paths.
  2. Read request.state.agent_class (set by AuthMiddleware).
  3. If agent_class contains a colon, extract the prefix as namespace.
  4. If no colon, namespace remains None (global access).
  5. Set request.state.tenant_namespace.
  6. Call the next middleware/router.

STATE SET ON REQUEST:
  - request.state.tenant_namespace (str | None): the extracted namespace,
    or None if the agent has no tenant restriction.

DOWNSTREAM USAGE:
  - Repository layers filter database queries by tenant_namespace to
    enforce data isolation between tenants.
  - Route handlers check tenant_namespace before returning data to
    ensure agents only see resources within their namespace.
  - NamespaceRestrictedError (403) is raised when an agent attempts
    cross-namespace access.

WHY HEALTH CHECK SKIP: Health check paths have no auth context
(no agent_class), so we skip parsing to avoid AttributeError on
missing request.state values.

IMPORTANT: This middleware does NOT enforce namespace isolation itself —
it only extracts and propagates the tenant identifier. Enforcement
happens in the service/repository layer where each query includes
a tenant_namespace filter. This separation of concerns keeps the
middleware focused on request enrichment vs. business logic.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.middleware.constants import HEALTH_PATHS


class TenantMiddleware(BaseHTTPMiddleware):
    """Middleware: extract tenant namespace from agent_class for multi-tenancy.

    WHAT: Reads the agent_class from request.state (set by AuthMiddleware)
    and, if it follows the "namespace:role" convention, extracts the
    namespace portion and stores it in request.state.tenant_namespace.

    WHY: MCP Fabric supports multi-tenancy where different teams or
    organizations have isolated capability registries. The agent_class
    field in the JWT encodes which namespace the agent belongs to,
    enabling data isolation without separate database instances.

    HOW: The agent_class string is split on the first colon. The left
    side is the namespace (tenant identifier), the right side is the
    role within that tenant. If there is no colon, the agent is treated
    as global (no namespace restriction).
    """

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
