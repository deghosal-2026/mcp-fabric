from sqlalchemy import event as sa_event
from sqlalchemy.ext.asyncio import AsyncEngine

from api.telemetry.metrics import fabric_db_connections, fabric_redis_connections


def instrument_engine(engine: AsyncEngine) -> None:
    sa_event.listen(engine.sync_engine, "checkout", _on_db_checkout)
    sa_event.listen(engine.sync_engine, "checkin", _on_db_checkin)


def _on_db_checkout(dbapi_connection, connection_record, connection_proxy):
    fabric_db_connections.labels(pool="main").inc()


def _on_db_checkin(dbapi_connection, connection_record):
    fabric_db_connections.labels(pool="main").dec()


def instrument_redis(client) -> None:
    pool = client.connection_pool if hasattr(client, "connection_pool") else None
    if pool and hasattr(pool, "_created_connections"):
        fabric_redis_connections.labels(pool="main").set(pool._created_connections)
