"""Shared constants used across multiple middleware to avoid duplication."""

HEALTH_PATHS = frozenset({"/health", "/health/ready", "/health/live", "/v1/metrics"})

AUTH_PATHS = frozenset(
    {
        "/v1/auth/login",
        "/v1/auth/connect",
        "/v1/auth/setup",
        "/v1/auth/password-reset",
        "/v1/auth/password-reset/complete",
    }
)
