"""FastAPI middleware for request ID, CORS, tracing, auth, tenant, rate limit, and audit.

Middleware are registered in api/main.py in the following order:
1. CORSMiddleware — preflight OPTIONS handling
2. APIVersionMiddleware — Accept header version negotiation
3. RequestIDMiddleware — assign unique ID per request
4. TracingMiddleware — OpenTelemetry span
5. AuthMiddleware — Bearer token / admin session validation
6. TenantMiddleware — namespace filter from agent_class
7. RateLimitMiddleware — per-agent in-memory rate limiting
8. AuditMiddleware — log request method+path+status+agent_id
"""

from api.middleware.api_version import APIVersionMiddleware
from api.middleware.audit import AuditMiddleware
from api.middleware.auth import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.request_id import RequestIDMiddleware
from api.middleware.tenant import TenantMiddleware
from api.middleware.tracing import TracingMiddleware

__all__ = [
    "APIVersionMiddleware",
    "AuditMiddleware",
    "AuthMiddleware",
    "RateLimitMiddleware",
    "RequestIDMiddleware",
    "TenantMiddleware",
    "TracingMiddleware",
]
