"""Assigns a unique request ID to every HTTP request.

Uses the Fabric-Request-Id header if the caller provides one (for
distributed trace correlation), otherwise generates a new UUID.  The ID
is echoed back on the response header so callers can correlate requests
with server-side logs.

REQUEST PROCESSING ORDER:
  1. Check for an incoming Fabric-Request-Id header (for distributed tracing).
  2. If present, use it; if absent, generate a new UUID4.
  3. Set request.state.request_id for all downstream middleware and handlers.
  4. Call the next middleware/router.
  5. Set the Fabric-Request-Id response header (always overwrites any
     incoming header value — the response always carries the resolved ID).

HEADERS READ:
  - Fabric-Request-Id: optional; if provided by the client (e.g., a proxy,
    load balancer, or another service in the mesh), it is propagated
    through the system for end-to-end trace correlation.

HEADERS WRITTEN:
  - Fabric-Request-Id: always set on the response, regardless of whether
    the client provided one or we generated one.

STATE SET ON REQUEST:
  - request.state.request_id (str): used by all downstream middleware
    (AuditMiddleware, TracingMiddleware) and exception handlers
    (fabric_error_handler) to correlate log entries.

WHY GENERATE IF NOT PROVIDED: Without a request ID, correlating log
entries across middleware, services, and databases for a single request
is extremely difficult. Every error response includes the request_id
so clients can report it when filing bug reports.

IMPORTANT: This middleware should run as early as possible in the
middleware stack (currently position 3, after CORS and APIVersion)
so all downstream middleware can use request.state.request_id.
"""

from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """Middleware: assign or propagate a unique request ID.

    WHAT: Ensures every HTTP request has a unique identifier for logging,
    tracing, and error correlation. Respects an incoming Fabric-Request-Id
    header for distributed tracing scenarios.

    WHY: Without a request ID, operators cannot correlate an error response
    with the server-side logs. This is especially important in a
    microservice/mesh architecture where a single user action may span
    multiple services.

    HOW: If the client provides a Fabric-Request-Id header (e.g., from a
    load balancer or upstream proxy), it is passed through. Otherwise, a
    new UUID4 is generated. The ID is stored in request.state for the
    duration of the request and echoed back on the response.
    """

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = request.headers.get("Fabric-Request-Id", str(uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["Fabric-Request-Id"] = request_id
        return response
