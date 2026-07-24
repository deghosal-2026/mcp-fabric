"""FastAPI middleware for request ID, CORS, tracing, auth, tenant, rate limit, and audit.

Middleware are registered in api/main.py in the following order:
1. CORSMiddleware — preflight OPTIONS handling
2. APIVersionMiddleware — Accept header version negotiation
3. RequestIDMiddleware — assign unique ID per request
4. TracingMiddleware — OpenTelemetry span
5. IPRateLimitMiddleware — pre-auth IP-based rate limiting
6. AuthMiddleware — Bearer token / admin session validation
7. TenantMiddleware — namespace filter from agent_class
8. RateLimitMiddleware — per-agent in-memory rate limiting
9. AuditMiddleware — log request method+path+status+agent_id
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
