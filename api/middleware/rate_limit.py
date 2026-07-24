import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.types import ASGIApp

from api.config import settings

_rates: dict[str, list[float]] = {}


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_requests: int | None = None, window: float = 60.0):
        super().__init__(app)
        self.max_requests = max_requests or settings.default_rate_limit
        self.window = window

    async def dispatch(self, request: Request, call_next):  # type: ignore[no-untyped-def]
        if request.url.path in ("/health", "/health/ready", "/health/live", "/v1/metrics"):
            return await call_next(request)

        agent_id = (
            getattr(request.state, "agent_id", None)
            or (request.client.host if request.client else "unknown")
        )
        now = time.time()
        key = f"{agent_id}:{request.url.path}"

        timestamps = _rates.get(key, [])
        timestamps = [ts for ts in timestamps if now - ts < self.window]
        if len(timestamps) >= self.max_requests:
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "message": (
                        f"Rate limit of {self.max_requests} requests per {self.window}s exceeded"
                    ),
                },
            )

        timestamps.append(now)
        _rates[key] = timestamps
        return await call_next(request)
