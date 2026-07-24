"""In-memory sliding-window rate limiter keyed by agent identity and path.

Uses per-instance state (not global) so each FastAPI app gets its own
rate-limit bucket, and the lock ensures correctness under concurrent
requests.  Stale entries are cleaned up every 5 minutes to cap memory
usage.  Health-check and metrics paths bypass rate limiting entirely.
"""

import asyncio
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from api.config import settings
from api.middleware.constants import HEALTH_PATHS


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_requests: int | None = None, window: float = 60.0):
        super().__init__(app)
        self.max_requests = max_requests or settings.default_rate_limit
        self.window = window
        self._rates: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup: float = 0

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)

        agent_id = (
            getattr(request.state, "agent_id", None)
            or (request.client.host if request.client else "unknown")
        )
        now = time.time()
        key = f"{agent_id}:{request.url.path}"

        async with self._lock:
            if now - self._last_cleanup > 300:
                stale = [
                    k
                    for k, ts in self._rates.items()
                    if not ts or now - max(ts) > self.window
                ]
                for k in stale:
                    self._rates.pop(k, None)
                self._last_cleanup = now

            timestamps = [ts for ts in self._rates.get(key, []) if now - ts < self.window]
            if len(timestamps) >= self.max_requests:
                return JSONResponse(
                    status_code=429,
                    content={
                        "error": "rate_limit_exceeded",
                        "message": (
                            f"Rate limit of {self.max_requests} requests per"
                            f" {self.window}s exceeded"
                        ),
                    },
                )

            timestamps.append(now)
            self._rates[key] = timestamps

        return await call_next(request)
