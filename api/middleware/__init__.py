"""FastAPI middleware for request ID, CORS, tracing, auth, tenant, rate limit, and audit.

Middleware are registered in api/main.py in the following order:
1. CORSMiddleware — preflight OPTIONS handling
2. RequestIDMiddleware — assign unique ID per request
3. TracingMiddleware — OpenTelemetry span
4. AuthMiddleware — Bearer token / admin session validation
5. TenantMiddleware — namespace filter from agent_class
6. RateLimitMiddleware — per-agent Redis-based rate limiting
7. AuditMiddleware — log request start/end via background task
"""

from api.middleware.request_id import RequestIDMiddleware

__all__ = [
    "RequestIDMiddleware",
]
