from sqlalchemy import select

from api.database import async_session
from api.models import AlertRule

DEFAULT_ALERT_RULES = [
    {
        "name": "server_degradation",
        "alert_type": "server_health",
        "condition": {"metric": "unhealthy_count", "threshold": 3, "window_minutes": 5},
        "channels": ["email"],
    },
    {
        "name": "unreviewed_server",
        "alert_type": "governance",
        "condition": {
            "metric": "unreviewed_servers",
            "threshold": 0,
            "window_hours": 48,
            "comparison": "gt",
        },
        "channels": ["email"],
    },
    {
        "name": "denial_spike",
        "alert_type": "rate_limit",
        "condition": {"metric": "denial_rate", "threshold": 0.1, "window_minutes": 5},
        "channels": ["email"],
    },
    {
        "name": "schema_change_detected",
        "alert_type": "schema_change",
        "condition": {
            "metric": "tool_changes",
            "threshold": 0,
            "window_minutes": 60,
            "comparison": "gt",
        },
        "channels": ["email"],
    },
    {
        "name": "fabric_error_rate",
        "alert_type": "error_rate",
        "condition": {"metric": "error_rate", "threshold": 0.01, "window_minutes": 5},
        "channels": ["email"],
    },
]


async def seed_alert_rules():
    """Seed default alert rules if they do not already exist."""
    async with async_session() as session:
        for rule_data in DEFAULT_ALERT_RULES:
            result = await session.execute(
                select(AlertRule).where(AlertRule.name == rule_data["name"])
            )
            existing = result.scalar_one_or_none()
            if existing is not None:
                continue
            session.add(AlertRule(**rule_data))
        await session.commit()
