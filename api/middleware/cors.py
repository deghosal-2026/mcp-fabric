"""CORS configuration consumed by FastAPI's built-in CORSMiddleware.

Exposes Fabric-specific response headers so the admin UI and MCP clients
can read request IDs, routing decisions, and API version information.
"""

from api.config import settings

CORS_CONFIG = {
    "allow_origins": settings.cors_origins,
    "allow_methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "allow_headers": ["Authorization", "Content-Type", "Accept"],
    "expose_headers": [
        "Fabric-Request-Id",
        "Fabric-Routing-Server",
        "Fabric-API-Version",
    ],
    "max_age": 3600,
}
