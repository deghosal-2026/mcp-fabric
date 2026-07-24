import asyncio
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from api.config import settings
from api.middleware.constants import HEALTH_PATHS


def extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class IPRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, max_requests: int | None = None, window: float = 60.0):
        super().__init__(app)
        self.max_requests = max_requests or min(settings.default_rate_limit, 20)
        self.window = window
        self._rates: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup: float = 0

    async def dispatch(self, request: Request, call_next) -> Response:
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)

        client_ip = extract_client_ip(request)
        now = time.time()
        key = f"ip:{client_ip}:{request.url.path}"

        async with self._lock:
            if now - self._last_cleanup > 300:
                stale = [
                    k for k, ts in self._rates.items()
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
