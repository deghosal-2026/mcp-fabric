"""Health check utilities for MCP Fabric dependencies.

Provides async functions to check connectivity of database, Redis,
and OPA endpoints, returning a simple status string.
"""

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class HealthResult:
    """Aggregate health check result with per-dependency status strings."""

    status: str = "healthy"
    checks: dict[str, str] = field(default_factory=dict)


async def check_database(engine: AsyncEngine) -> str:
    """Return 'connected' if the database engine responds to SELECT 1, else 'disconnected'."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"


async def check_redis(redis_url: str) -> str:
    """Return 'connected' if Redis responds to PING within 2s, else 'disconnected'."""
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return "connected"
    except Exception:
        return "disconnected"


async def check_opa(opa_url: str) -> str:
    """Return 'connected' if OPA /health responds < 500, 'degraded' on 5xx, else 'disconnected'."""
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{opa_url}/health")
            if resp.status_code < 500:
                return "connected"
            return "degraded"
    except Exception:
        return "disconnected"
