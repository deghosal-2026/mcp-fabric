"""In-memory sliding-window rate limiter keyed by agent identity and path.

Uses per-instance state (not global) so each FastAPI app gets its own
rate-limit bucket, and the lock ensures correctness under concurrent
requests.  Stale entries are cleaned up every 5 minutes to cap memory
usage.  Health-check and metrics paths bypass rate limiting entirely.

DIFFERENCE FROM IPRateLimitMiddleware:
  - IPRateLimitMiddleware runs BEFORE auth and keys on client IP
    (max 20 req/min) to protect against unauthenticated floods.
  - RateLimitMiddleware runs AFTER auth and keys on agent_id
    (max 100 req/min by default) to enforce per-agent quotas.

KEY DESIGN DECISIONS:
  - Falls back to client IP if agent_id is not set: Handles the rare
    case where auth was bypassed or failed but the request continues.
  - Per-path limits: Each agent gets independent rate-limit buckets
    per URL path, so a burst on one endpoint does not exhaust the
    agent's budget for another endpoint.
  - Sliding window + asyncio.Lock: Same approach as IPRateLimitMiddleware
    for consistency and correctness.

REQUEST PROCESSING ORDER:
  1. Skip rate limiting for health-check paths.
  2. Determine the requesting identity:
     a. Use request.state.agent_id if set (from AuthMiddleware).
     b. Fall back to client IP if no agent_id (unauthenticated path).
  3. Compute the rate-limit key: "{agent_id}:{path}".
  4. Acquire the asyncio.Lock and:
     a. Clean up stale entries (every 5 minutes).
     b. Filter timestamps within the sliding window.
     c. If count >= max_requests, return 429.
     d. Otherwise, append the current timestamp.
  5. Call the next middleware/router.

FAILURE BEHAVIOR:
  - Returns 429 with error code "rate_limit_exceeded" and message
    indicating the limit and window. Same format as IPRateLimitMiddleware.
  - If a bad agent exhausts their quota, only that agent is blocked —
    other agents (and IPs) continue unaffected.
"""

import asyncio
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from api.config import settings
from api.middleware.constants import HEALTH_PATHS


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware: sliding-window rate limiter keyed by authenticated agent + path.

    WHAT: Limits the number of requests from a single authenticated agent
    to a specific endpoint path within a sliding time window. Uses the
    same in-memory sliding-window algorithm as IPRateLimitMiddleware but
    keys on agent identity instead of client IP.

    WHY:
      - Fair resource allocation: prevents any single agent from
        consuming a disproportionate share of server resources.
      - Per-agent quotas: each agent gets the full limit (default 100/min),
        unlike the IP-based limiter which caps at 20/min.
      - Auth-gated: runs after AuthMiddleware so it operates on a trusted
        identity rather than a potentially spoofed IP address.

    HOW: Maintains a dict[rate_key, list[timestamps]] in memory keyed by
    agent_id + path. The sliding window algorithm filters out expired
    timestamps, checks the count against max_requests, and appends the
    current timestamp. Periodic cleanup removes stale entries.
    """

    def __init__(self, app: ASGIApp, max_requests: int | None = None, window: float = 60.0):
        super().__init__(app)
        # Use the full default_rate_limit (100 by default) since the
        # caller is authenticated and identifiable.
        self.max_requests = max_requests or settings.default_rate_limit
        self.window = window
        self._rates: dict[str, list[float]] = {}
        self._lock = asyncio.Lock()
        self._last_cleanup: float = 0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)

        # Use agent_id if available (set by AuthMiddleware), otherwise
        # fall back to client IP as a best-effort identity.
        agent_id = getattr(request.state, "agent_id", None) or (
            request.client.host if request.client else "unknown"
        )
        now = time.time()
        key = f"{agent_id}:{request.url.path}"

        async with self._lock:
            if now - self._last_cleanup > 300:
                stale = [
                    k for k, ts in self._rates.items() if not ts or now - max(ts) > self.window
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
