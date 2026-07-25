"""Application configuration loaded from environment variables.

Uses pydantic-settings to read from .env or environment. Falls back to
SQLite for development; PostgreSQL in production.

ARCHITECTURE NOTES:
  - All config values can be overridden via environment variables (e.g.,
    DATABASE_URL=postgresql+asyncpg://...). pydantic-settings reads env
    vars case-insensitively by default.
  - The module instantiates a single Settings() singleton at import time.
    Import `settings` from this module to access configuration everywhere.
  - In production, every variable with a dev-only default MUST be
    explicitly set. The model_post_init hook enforces this for secret_key.

PRODUCTION CHECKLIST:
  ☐ Set DATABASE_URL to PostgreSQL (never SQLite)
  ☐ Set SECRET_KEY to a strong, random value
  ☐ Set REDIS_URL to a secure, authenticated Redis instance
  ☐ Set CORS_ORIGINS to the actual frontend domain(s)
  ☐ Set OTEL_ENDPOINT if using OpenTelemetry tracing
  ☐ Review RATE_LIMIT defaults for your traffic patterns
"""

from celery.schedules import crontab
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for MCP Fabric service.

    All fields have dev-safe defaults. Override with environment variables
    or .env file entries matching the field name in UPPER_CASE (e.g.,
    DATABASE_URL, SECRET_KEY).
    """

    # ── Database ────────────────────────────────────────────────────
    # Default PostgreSQL URL for Docker-based development.
    # Override with DATABASE_URL env var. For local-only dev without
    # Docker, set to sqlite+aiosqlite:///fabric.db (requires aiosqlite).
    database_url: str = "postgresql+asyncpg://fabric:fabric@localhost:5432/mcp_fabric"

    # Redis connection string for caching, rate-limit state,
    # pub/sub, and Celery broker/backend.
    redis_url: str = "redis://localhost:6379/0"

    # Open Policy Agent (OPA) endpoint for policy-based authorization.
    # OPA evaluates Rego policies that determine access to capabilities.
    opa_url: str = "http://localhost:8181"

    # Celery broker URL (Redis by default, but can point to RabbitMQ).
    # Currently uses Redis DB 1 to separate broker messages from cache DB 0.
    celery_broker_url: str = "redis://localhost:6379/1"

    # Celery result backend for storing task results.
    # Uses Redis DB 2 for separation from broker messages.
    celery_result_backend: str = "redis://localhost:6379/2"

    # ── Auth / Security ─────────────────────────────────────────────
    # HMAC secret key used to sign and verify JWT tokens.
    # MUST be changed in production. Recommended: openssl rand -hex 32
    secret_key: str = "dev-secret-change-me"

    # Deployment environment label: "development", "staging", "production".
    # Controls behavior: dev uses SQLite, production enforces secret_key
    # override, and log formatting may differ (pretty vs JSON).
    environment: str = "development"

    # Standard log level: DEBUG, INFO, WARNING, ERROR.
    # In production, typically set to INFO or WARNING to reduce noise.
    log_level: str = "INFO"

    # ── Rate Limiting ───────────────────────────────────────────────
    # Maximum requests per sliding window (60s) for the per-agent
    # RateLimitMiddleware. The IP-based limiter (IPRateLimitMiddleware)
    # caps at min(100, 20) to protect against unauthenticated floods.
    default_rate_limit: int = 100

    # ── JWT ──────────────────────────────────────────────────────────
    # Expected "iss" (issuer) claim in JWT tokens. Used by AuthService
    # to reject tokens from unknown issuers.
    jwt_issuer: str = "mcp-fabric"

    # Expected "aud" (audience) claim in JWT tokens. Ensures tokens
    # minted for this service are not replayed against other services.
    jwt_audience: str = "mcp-fabric-api"

    # ── Observability ───────────────────────────────────────────────
    # OpenTelemetry gRPC/HTTP endpoint (e.g., "http://otel-collector:4318").
    # If empty, tracing is a no-op (TracingMiddleware still creates spans
    # but they are not exported).
    otel_endpoint: str = ""

    # ── CORS ─────────────────────────────────────────────────────────
    # Allowed origins for CORS. In development, this is the React dev
    # server. In production, set to your frontend domain(s).
    cors_origins: list[str] = ["http://localhost:3000"]

    # ── Session / Expiry ─────────────────────────────────────────────
    # How long an admin CLI session token remains valid (in hours).
    admin_session_ttl_hours: int = 8

    # How long a pending approval request is valid before auto-expiry.
    approval_expiry_hours: int = 1

    # ── Auditing ────────────────────────────────────────────────────
    # Number of days to retain audit log entries before cleanup.
    audit_retention_days: int = 90

    # ── Service Health ──────────────────────────────────────────────
    # Interval (seconds) between periodic health checks of registered
    # MCP servers (via Celery beat).
    server_health_interval: int = 30

    # ── Request Handling ────────────────────────────────────────────
    # Maximum number of tool calls allowed in a single batch request.
    max_batch_requests: int = 10

    # ── MCP Client Timeouts (seconds) ───────────────────────────────
    # Total timeout for a single MCP tool execution (including connect).
    mcp_timeout: float = 5.0

    # Timeout specifically for establishing the MCP SSE/stream connection.
    mcp_connect_timeout: float = 2.0

    # Timeout for internal health-check probes against external services.
    health_check_timeout: float = 2.0

    # ── Feature Flags ───────────────────────────────────────────────
    # Toggle experimental/in-progress features on/off without deploys.
    # These are checked at runtime in route handlers and services.
    feature_flags: dict[str, bool] = {
        # If True, MCP tool responses are streamed via SSE instead of
        # buffered. Not yet fully implemented across all MCP servers.
        "enable_streaming": False,
        # If True, the registry can federate capabilities across multiple
        # MCP Fabric instances. Still in design phase.
        "enable_federation": False,
        # If True, admin endpoints require MFA verification in addition
        # to the session token.
        "require_mfa_for_admins": False,
        # If True, capability matching uses fuzzy string matching (Levenshtein
        # distance) instead of exact name matching for routing requests.
        "enable_fuzzy_capability_match": False,
    }

    # ── Celery Beat Schedule ────────────────────────────────────────
    # Periodic tasks executed by the Celery beat scheduler. These run
    # regardless of HTTP traffic and are essential for background ops.
    celery_beat_schedule: dict = {
        # Periodically probes every registered MCP server for liveness.
        # Marks servers as unhealthy if they fail to respond.
        "health-check-all-servers": {
            "task": "api.tasks.health_check_all_servers",
            "schedule": 30.0,
        },
        # Daily at 3 AM, deletes audit log entries older than
        # audit_retention_days to prevent unbounded log growth.
        "cleanup-audit-logs": {
            "task": "api.tasks.cleanup_audit_logs",
            "schedule": crontab(minute=0, hour=3),
        },
        # Every 60s, evaluates alert thresholds (e.g., high error rate,
        # server degradation) and fires notifications if triggered.
        "check-alert-thresholds": {
            "task": "api.tasks.check_alert_thresholds",
            "schedule": 60.0,
        },
    }

    @property
    def is_sqlite(self) -> bool:
        """Boolean check if the current database URL targets SQLite.

        Used throughout the codebase to skip PostgreSQL-specific features
        (e.g., certain Alembic migration operations, full-text search,
        or connection pool tuning) when running in dev mode.
        """
        return self.database_url.startswith("sqlite")

    def model_post_init(self, __context):
        """Post-initialization validation hook called by pydantic-settings.

        WHAT: Runs after all fields have been populated from defaults and
        environment variables. Raises a ValueError in production if the
        secret_key is still the insecure dev default.

        WHY: Catches a common misconfiguration scenario early — deploying
        to production without changing the secret key means JWT tokens
        can be forged by anyone who reads the source code. This check
        prevents the process from starting with a weak key.

        IMPORTANT: This runs at import time when `settings = Settings()`
        is evaluated. If it raises, the process will crash immediately,
        which is the desired behavior — better to fail fast than run
        insecure.
        """
        if self.environment == "production" and self.secret_key == "dev-secret-change-me":
            raise ValueError("SECRET_KEY must be changed from default in production")


settings = Settings()
