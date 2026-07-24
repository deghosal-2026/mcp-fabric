from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine


@dataclass
class HealthResult:
    status: str = "healthy"
    checks: dict[str, str] = field(default_factory=dict)


async def check_database(engine: AsyncEngine) -> str:
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return "connected"
    except Exception:
        return "disconnected"


async def check_redis(redis_url: str) -> str:
    try:
        import redis.asyncio as aioredis

        client = aioredis.from_url(redis_url, socket_connect_timeout=2)
        await client.ping()
        await client.aclose()
        return "connected"
    except Exception:
        return "disconnected"


async def check_opa(opa_url: str) -> str:
    try:
        import httpx

        async with httpx.AsyncClient(timeout=2) as client:
            resp = await client.get(f"{opa_url}/health")
            if resp.status_code < 500:
                return "connected"
            return "degraded"
    except Exception:
        return "disconnected"
