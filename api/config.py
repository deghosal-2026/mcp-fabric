"""Application configuration loaded from environment variables.

Uses pydantic-settings to read from .env or environment. Falls back to
SQLite for development; PostgreSQL in production.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Central configuration for MCP Fabric service."""


    database_url: str = "sqlite+aiosqlite:///fabric.db"
    redis_url: str = "redis://localhost:6379/0"
    opa_url: str = "http://localhost:8181"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"
    secret_key: str = "dev-secret-change-me"
    environment: str = "development"
    log_level: str = "INFO"
    audit_retention_days: int = 90
    server_health_interval: int = 30
    default_rate_limit: int = 100
    cors_origins: list[str] = ["http://localhost:3000"]
    admin_session_ttl_hours: int = 8
    approval_expiry_hours: int = 1
    max_batch_requests: int = 10
    mcp_timeout: float = 5.0
    mcp_connect_timeout: float = 2.0
    health_check_timeout: float = 2.0

    feature_flags: dict[str, bool] = {
        "enable_streaming": False,
        "enable_federation": False,
        "require_mfa_for_admins": False,
        "enable_fuzzy_capability_match": False,
    }

    celery_beat_schedule: dict = {
        "health-check-all-servers": {
            "task": "api.tasks.health_check_all_servers",
            "schedule": 30.0,
        },
        "cleanup-audit-logs": {
            "task": "api.tasks.cleanup_audit_logs",
            "schedule": "0 3 * * *",
        },
        "check-alert-thresholds": {
            "task": "api.tasks.check_alert_thresholds",
            "schedule": 60.0,
        },
    }

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    def model_post_init(self, __context):
        if self.environment == "production" and self.secret_key == "dev-secret-change-me":
            raise ValueError("SECRET_KEY must be changed from default in production")


settings = Settings()
