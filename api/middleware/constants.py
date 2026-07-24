"""Shared constants used across multiple middleware to avoid duplication."""

HEALTH_PATHS = frozenset({"/health", "/health/ready", "/health/live", "/v1/metrics"})
