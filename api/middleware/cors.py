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
