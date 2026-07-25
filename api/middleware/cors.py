"""CORS configuration dictionary consumed by FastAPI's CORSMiddleware.

WHY A SEPARATE MODULE: Keeps the CORS config out of main.py to keep
it clean. The CORS_CONFIG dict is imported in main.py and unpacked as
**CORS_CONFIG when registering the middleware.

HEADERS:
  - allow_origins: controlled by the CORS_ORIGINS env var (defaults to
    http://localhost:3000, the React dev server). In production, this
    must be set to the actual frontend domain(s).
  - allow_methods: all standard REST methods including OPTIONS (preflight).
  - allow_headers: Authorization for Bearer tokens, Content-Type and
    Accept for content negotiation. These are the minimum required for
    the MCP Fabric API.
  - expose_headers: Fabric-Request-Id and Fabric-API-Version are exposed
    so browser-based clients (e.g., the admin UI) can read them.
  - max_age: 3600 seconds (1 hour) — browsers cache the preflight result
    for 1 hour, reducing OPTIONS requests.

IMPORTANT: In development with credentials (cookies/Authorization headers),
you may also need to set allow_credentials=True. This is not currently set
because MCP Fabric uses header-based auth (Bearer tokens), not cookies.
If cookie-based sessions are added in the future, add allow_credentials=True.
"""

from api.config import settings

CORS_CONFIG = {
    "allow_origins": settings.cors_origins,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "Accept"],
    "expose_headers": [
        "Fabric-Request-Id",
        "Fabric-API-Version",
    ],
    "max_age": 3600,
}
