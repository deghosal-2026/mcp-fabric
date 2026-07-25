"""Emits a structured audit log entry for every authenticated request.

Records the method, path, status code, agent identity, and request ID
so operators can trace who did what.  Health-check paths are skipped to
keep the audit log focused on business operations.

REQUEST PROCESSING ORDER:
  1. Skip audit logging for health-check paths (HEALTH_PATHS) to keep
     the audit log clean — health checks generate too much noise.
  2. Call the next middleware/router first (response is needed for status).
  3. AFTER the response is generated, extract metadata from request.state
     (set by earlier middleware: RequestIDMiddleware, AuthMiddleware).
  4. Log a structured audit entry at INFO level with event key "audit:request".

HEADERS READ: none (reads request.state set by other middleware).

STATE SET ON REQUEST: none (read-only).

FAILURE BEHAVIOR:
  - If request.state.agent_id is not set (no auth context), defaults to
    "anonymous". This can happen if a request reaches this middleware
    without passing through AuthMiddleware (e.g., if the path was not
    in HEALTH_PATHS but also did not match any auth-required path).
  - If request.state.request_id is not set (unlikely — RequestIDMiddleware
    runs before this), defaults to None in the log entry.
  - If the logger fails (extremely rare), the exception is caught by
    the middleware framework and the response is still returned — audit
    logging is best-effort and must not block the response.

WHY RUN LAST (innermost middleware):
  - AuditMiddleware runs closest to the router so it sees the final
    response status code after all other middleware have had their say.
    If it ran earlier (e.g., before AuthMiddleware), it would log 401
    responses at the wrong point in the chain, or miss status changes
    by inner middleware.
  - Running after call_next means the response is already generated and
    the status code is final. Running before call_next would require
    two log entries (request and response) and complicate the logic.

IMPORTANT: This middleware uses logger.info() with structured keyword
arguments, not f-strings. The logger (from api.telemetry.logging) is
configured to output structured JSON in production, so the log entry
becomes queryable in log aggregation tools (e.g., Elasticsearch,
Datadog, Grafana Loki).
"""

from datetime import UTC, datetime

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.middleware.constants import HEALTH_PATHS
from api.telemetry.logging import logger


class AuditMiddleware(BaseHTTPMiddleware):
    """Middleware: structured audit logging for every non-health request.

    WHAT: After every non-health HTTP request, logs a structured audit
    entry containing the method, path, response status, agent identity,
    request ID, and timestamp.

    WHY: Provides an audit trail for security and compliance. Operators
    can query the audit log to answer questions like:
      - "What did agent X do in the last hour?"
      - "Who deleted capability Y?"
      - "What is the error rate for each agent?"

    HOW: Runs AFTER the response is generated (innermost middleware),
    reads request.state values set by upstream middleware, and emits a
    single structured log entry per request.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip health checks to avoid noise in the audit log
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)

        # Call the next middleware/router first to get the final status
        response = await call_next(request)

        # Extract identity from request.state (set by AuthMiddleware).
        # Default to "anonymous" if not set (e.g., unauthenticated path).
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
