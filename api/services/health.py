"""Health check utilities for MCP Fabric dependencies.

Provides async functions to check connectivity of database, Redis,
and OPA endpoints, returning a simple status string.

Architectural notes:
  - These are standalone functions (not a class) since health checks
    are stateless: each call establishes its own connection, checks,
    and tears down.
  - Each function is self-contained with its own imports. This avoids
    requiring optional dependencies (redis, httpx) at module load time;
    they're only imported when the specific check runs.
  - Health checks use short timeouts (2s) to avoid hanging the health
    endpoint when a dependency is slow or down.
  - The overall system health is an aggregate: if any check fails,
    the system may be degraded, but individual component statuses
    are always reported separately.
"""

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class HealthResult:
    """Aggregate health check result with per-dependency status strings.

    Attributes:
        status: Overall status ('healthy' or 'degraded'). Set by the caller
               based on individual check results.
        checks: Dict mapping component name to status string
                (e.g., {'database': 'connected', 'redis': 'disconnected'}).
    """

    status: str = "healthy"
    checks: dict[str, str] = field(default_factory=dict)


async def check_database(engine: AsyncEngine) -> str:
    """Return 'connected' if the database engine responds to SELECT 1, else 'disconnected'.

    WHY: Verifies the database connection pool is functional.
    Uses a simple SELECT 1 ping — the lightest possible query.
    The engine is already configured (connection string, pool settings),
    so we just test that we can acquire a connection and execute.

    RETURN: 'connected' or 'disconnected'.
    """
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"


async def check_redis(redis_url: str) -> str:
    """Return 'connected' if Redis responds to PING within 2s, else 'disconnected'.

    WHY: Verifies Redis connectivity. Redis is used for session storage,
    policy caching, and health caching — if it's down, those features
    degrade but the system continues.

    Uses socket_connect_timeout=2 to prevent hanging on an unresponsive
    Redis instance. The import is inline because redis is an optional
    dependency.

    RETURN: 'connected' or 'disconnected'.
    """
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(redis_url, socket_connect_timeout=2)  # type: ignore[no-untyped-call]
        await client.ping()
        await client.aclose()
        return "connected"
    except Exception:
        return "disconnected"


async def check_opa(opa_url: str) -> str:
    """Return 'connected' if OPA /health responds < 500, 'degraded' on 5xx, else 'disconnected'.

    WHY: Verifies the Open Policy Agent service is reachable and healthy.
    OPA has a built-in /health endpoint that returns 200 when healthy.
    We return 'degraded' for 5xx responses (OPA is running but not fully
    functional) vs 'disconnected' for connection failures.

    Uses httpx with a 2s timeout. The import is inline because httpx
    is an optional dependency (only needed for OPA communication).

    RETURN: 'connected', 'degraded', or 'disconnected'.
    """
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{opa_url}/health")
            if resp.status_code < 500:
                return "connected"
            return "degraded"
    except Exception:
        return "disconnected"
