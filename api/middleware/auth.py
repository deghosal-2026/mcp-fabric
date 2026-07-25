"""Validates Bearer tokens for every non-health request.

Skips health-check and metrics endpoints so monitoring tools and
load balancers do not need credentials.  Uses AuthService internally
to validate JWT tokens and extract agent identity, agent class, and
role into request.state for downstream middleware and route handlers.

REQUEST PROCESSING ORDER:
  1. Skip auth for health-check paths (HEALTH_PATHS) and auth paths
     (AUTH_PATHS — e.g., login, token refresh) so unauthenticated
     clients can authenticate.
  2. Extract the Authorization header and validate it starts with "Bearer ".
  3. Strip the "Bearer " prefix to get the raw JWT token.
  4. Validate the JWT via AuthService.validate_token():
     - Verifies signature against secret_key
     - Checks "iss" claim matches jwt_issuer
     - Checks "aud" claim matches jwt_audience
     - Checks "exp" claim is not expired
     - Checks token not revoked (admin sessions)
  5. If validation fails, return 401 with WWW-Authenticate header.
  6. Extract claims from validated payload and set on request.state.
  7. Call the next middleware/router.

HEADERS READ:
  - Authorization: Bearer <JWT token>. The JWT is a JSON Web Token
    that encodes agent identity, type, class, and role.

HEADERS WRITTEN:
  - WWW-Authenticate (on 401 responses): Provides error details per
    RFC 6750 so conforming HTTP clients can react appropriately.

STATE SET ON REQUEST (all from JWT claims):
  - request.state.agent_id (str): unique identifier from "sub" claim
  - request.state.agent_type (str): "agent", "admin", or "system"
  - request.state.agent_class (str): namespace:role format for tenant
    isolation (used by TenantMiddleware)
  - request.state.role (str): RBAC role like "agent", "admin", "auditor"

FAILURE BEHAVIOR:
  - Missing Authorization header → 401 with
    error="invalid_token", WWW-Authenticate Bearer error="invalid_token"
  - Invalid/expired token → 401 with
    error="invalid_token", WWW-Authenticate Bearer error="invalid_token"
  - Token validation uses InvalidTokenError from auth_service, NOT the
    errors.py InvalidTokenError (those are for route handlers). The
    auth_service's InvalidTokenError is caught and converted to a
    401 response here.

IMPORTANT: This middleware returns a 401 JSONResponse directly without
going through the exception handler chain. This is because we want to
fail fast with an auth failure before any service code runs. The
response format matches the FabricError envelope for consistency.
"""

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from api.middleware.constants import AUTH_PATHS, HEALTH_PATHS
from api.services.auth_service import AuthService, InvalidTokenError
from api.telemetry.logging import logger


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware: validate Bearer JWT and extract agent identity.

    WHAT: Intercepts every non-health, non-auth request to validate
    the Bearer JWT token. Extracts agent identity, type, class, and
    role from the JWT payload and stores them in request.state for
    downstream middleware (TenantMiddleware, RateLimitMiddleware) and
    route handlers.

    WHY: Ensures every API request is authenticated before it reaches
    any route handler. This is the single point where authentication
    happens — route handlers trust request.state values set here.

    HOW: Uses AuthService.validate_token() which performs full JWT
    validation (signature, issuer, audience, expiration, revocation).
    The validated JWT payload is unpacked into request.state fields.
    """

    def __init__(self, app: ASGIApp, auth_service: AuthService | None = None):
        super().__init__(app)
        # Accept an optional AuthService for testing (DI-friendly).
        # In production, create a default one.
        self.auth = auth_service or AuthService()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Allow health checks and auth endpoints (login, refresh) without token
        if request.url.path in HEALTH_PATHS | AUTH_PATHS:
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            logger.warning("auth:missing_token", path=request.url.path, method=request.method)
            return JSONResponse(
                status_code=401,
                content={
                    "error": "invalid_token",
                    "message": "Missing or invalid Authorization header",
                },
                headers={
                    "WWW-Authenticate": (
                        'Bearer error="invalid_token",'
                        ' error_description="Missing or invalid Authorization header"'
                    ),
                },
            )

        token = auth_header.removeprefix("Bearer ")
        try:
            payload = self.auth.validate_token(token)
        except InvalidTokenError:
            logger.warning("auth:invalid_token", path=request.url.path, method=request.method)
            return JSONResponse(
                status_code=401,
                content={"error": "invalid_token", "message": "Token is invalid or expired"},
                headers={
                    "WWW-Authenticate": (
                        'Bearer error="invalid_token",'
                        ' error_description="Token is invalid or expired"'
                    ),
                },
            )

        # Propagate identity to downstream middleware and handlers
        request.state.agent_id = payload.get("sub")
        request.state.agent_type = payload.get("type", "agent")
        request.state.agent_class = payload.get("agent_class")
        request.state.role = payload.get("role", "agent")
        return await call_next(request)
