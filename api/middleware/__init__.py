"""FastAPI middleware barrel export: imports all middleware classes and re-exports them.

This module exists so that api/main.py can import all middleware with a
single `from api.middleware import (...)` statement instead of importing
from each individual module.

MIDDLEWARE REGISTRATION ORDER (outermost → innermost, top → bottom in stack):
  1. CORSMiddleware (from fastapi.middleware.cors)
     Handles CORS preflight OPTIONS and adds CORS headers. Runs first so
     that preflight requests are handled before any other middleware logic.

  2. APIVersionMiddleware
     Negotiates API version from Accept/Accept-Version header or query param.
     Returns 406 for unsupported versions. Sets request.state.api_version.

  3. RequestIDMiddleware
     Assigns or preserves a unique request ID. Sets request.state.request_id
     and echoes it in the Fabric-Request-Id response header.

  4. TracingMiddleware
     Wraps the request in an OpenTelemetry span. Records HTTP method, URL,
     status code, and request_id on the span. Also increments Prometheus
     counters and histograms.

  5. IPRateLimitMiddleware
     Per-IP rate limiting. Runs before auth so unauthenticated traffic
     is throttled before auth processing overhead. Keyed by client IP + path.

  6. AuthMiddleware
     Validates Bearer JWT tokens. Sets agent_id, agent_type, agent_class,
     and role on request.state. Skips health-check and auth endpoints.
     Returns 401 with WWW-Authenticate header on failure.

  7. TenantMiddleware
     Extracts tenant namespace from agent_class (format: "namespace:role").
     Sets request.state.tenant_namespace for downstream data isolation.

  8. RateLimitMiddleware
     Per-agent rate limiting. Keyed by agent_id + path. Uses the same
     sliding-window algorithm as IPRateLimitMiddleware but operates on
     the authenticated identity instead of the IP address.

  9. AuditMiddleware
     Logs a structured audit entry for every non-health request after
     the response is generated. Records method, path, status, agent_id,
     request_id, and timestamp.

WHY THIS ORDER:
  - CORS and version negotiation should fail fast before any auth or
    processing overhead.
  - RequestID is assigned early so all downstream middleware and handlers
    can log with a correlation ID.
  - Tracing wraps the entire remaining chain so the span covers all
    processing including other middleware.
  - IP-based rate limiting before auth protects auth processing from
    brute-force/DoS attacks.
  - Auth runs early so tenant extraction and agent-based rate limiting
    have identity context.
  - Audit runs last (innermost, closest to the router) so it captures
    the final response status code after all other middleware have had
    their say (e.g., rate limit rejection, auth rejection).
"""

from api.middleware.api_version import APIVersionMiddleware
from api.middleware.audit import AuditMiddleware
from api.middleware.auth import AuthMiddleware
from api.middleware.ip_rate_limit import IPRateLimitMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.request_id import RequestIDMiddleware
from api.middleware.tenant import TenantMiddleware
from api.middleware.tracing import TracingMiddleware

__all__ = [
    "APIVersionMiddleware",
    "AuditMiddleware",
    "AuthMiddleware",
    "IPRateLimitMiddleware",
    "RateLimitMiddleware",
    "RequestIDMiddleware",
    "TenantMiddleware",
    "TracingMiddleware",
]
