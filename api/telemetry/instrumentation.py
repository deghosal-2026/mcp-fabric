"""SQLAlchemy and Redis instrumentation hooks.

Hooks into SQLAlchemy engine lifecycle events (connection checkout/checkin)
to track the live database connection count as a Prometheus gauge. Similarly
reads Redis connection pool state to track Redis connections.

These hooks are called once at application startup during the telemetry
initialisation phase and attach side-effect-free listeners that update
metrics on every pool event.

Naming convention:
    - fabric_db_connections{pool="main"} — current DB connections
    - fabric_redis_connections{pool="main"} — current Redis connections
"""

from typing import Any

from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncEngine

from api.telemetry.metrics import fabric_db_connections, fabric_redis_connections


def instrument_engine(engine: AsyncEngine) -> None:
    """Attach SQLAlchemy event listeners to track connection pool usage.

    Listens on the sync_engine (SQLAlchemy fires events on the sync version
    even for async engines) for checkout (connection acquired) and checkin
    (connection released) events, incrementing/decrementing the gauge.

    Args:
        engine: The async SQLAlchemy engine to instrument.
    """
    sa_event.listen(engine.sync_engine, "checkout", _on_db_checkout)
    sa_event.listen(engine.sync_engine, "checkin", _on_db_checkin)


def _on_db_checkout(dbapi_connection: Any, connection_record: Any, connection_proxy: Any) -> None:
    """Increment the DB connection gauge when a connection is checked out."""
    fabric_db_connections.labels(pool="main").inc()


def _on_db_checkin(dbapi_connection: Any, connection_record: Any) -> None:
    """Decrement the DB connection gauge when a connection is checked in."""
    fabric_db_connections.labels(pool="main").dec()


def instrument_redis(client: Any) -> None:
    """Set the Redis connection pool gauge to the current pool size.

    Reads _created_connections from the client's connection pool (if
    available) to report how many connections the pool has created.
    Unlike the DB hooks, this is a one-shot snapshot rather than a
    continuously updated gauge, because Redis asyncio does not fire
    lifecycle events.

    Args:
        client: A Redis client instance (sync or async).
    """
    pool = client.connection_pool if hasattr(client, "connection_pool") else None
    if pool and hasattr(pool, "_created_connections"):
        fabric_redis_connections.labels(pool="main").set(pool._created_connections)
