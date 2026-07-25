"""Default alert rule seeder.

Creates the initial set of AlertRule records that define when the system
should notify operators of notable conditions. Each rule specifies:
    - An alert_type categorising the kind of condition (server_health,
      governance, rate_limit, schema_change, error_rate).
    - A condition dict describing the metric, threshold, time window, and
      comparison operator.
    - One or more notification channels (currently only email).

Default rules:
    - server_degradation: Fires when 3+ servers are unhealthy in 5 minutes.
    - unreviewed_server: Fires when any server goes 48h without review.
    - denial_spike: Fires when denial rate exceeds 10% in 5 minutes.
    - schema_change_detected: Fires when any tool changes in 60 minutes.
    - fabric_error_rate: Fires when error rate exceeds 1% in 5 minutes.

Idempotency:
    - Each rule is looked up by name before insertion.
    - Existing rules are never modified or duplicated.
"""

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


async def seed_alert_rules() -> None:
    """Seed default alert rules if they do not already exist.

    Iterates over DEFAULT_ALERT_RULES and creates each one that does
    not already exist in the database (matched by name). Runs in a single
    transaction.

    Idempotent: safe to call multiple times. Only missing records are
    created; existing records are left untouched.
    """
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
