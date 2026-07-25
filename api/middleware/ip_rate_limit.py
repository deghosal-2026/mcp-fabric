"""Per-IP sliding-window rate limiter that runs before authentication.

Protects against unauthenticated request floods (DDoS, brute-force
login attempts) by throttling traffic based on the client IP address.
Runs before AuthMiddleware so that unauthenticated traffic is limited
before auth processing overhead is incurred.

KEY DESIGN DECISIONS:
  - Per-instance state (not shared across replicas): This means the
    rate limit is per-process. With multiple replicas, the effective
    limit is max_requests * number_of_replicas. A shared Redis-based
    limiter would be more accurate at scale but adds latency to every
    request. The per-instance approach is a pragmatic tradeoff for
    simplicity and performance.
  - Sliding window (not fixed window): Uses a list of timestamps and
    filters to only those within the window. This avoids the "burst at
    window boundary" problem of fixed-window counters.
  - asyncio.Lock: Protects the in-memory dict from concurrent coroutine
    access. Without this, a race condition could allow bursts past the
    limit.

REQUEST PROCESSING ORDER:
  1. Skip rate limiting for health-check paths (HEALTH_PATHS).
  2. Extract the client IP from X-Forwarded-For header or direct
     connection (request.client.host).
  3. Compute the rate-limit key: "ip:{client_ip}:{path}".
  4. Acquire the asyncio.Lock and:
     a. Clean up stale entries (every 5 minutes).
     b. Filter timestamps to only those within the current window.
     c. If count >= max_requests, return 429 immediately.
     d. Otherwise, append the current timestamp and store.
  5. Call the next middleware/router.

HEADERS READ:
  - X-Forwarded-For: extracts the client's original IP when behind a
    reverse proxy. Takes the first IP in the chain (the original client).

STATE SET ON REQUEST: none (operates purely on IP).

FAILURE BEHAVIOR:
  - Returns 429 with error code "rate_limit_exceeded" and a human-readable
    message. Does NOT include retry_after header (the client must
    calculate backoff from the window size).
  - If extract_client_ip returns "unknown" (no IP available), all such
    requests share the same rate-limit bucket, which is intentional —
    it prevents a misconfigured proxy from bypassing rate limits.

IMPORTANT: max_requests defaults to min(settings.default_rate_limit, 20).
The cap at 20 is intentional — a single IP should never be allowed 100
requests per minute without authentication. The agent-based
RateLimitMiddleware applies the full limit after auth.
"""

import asyncio
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import ASGIApp

from api.config import settings
from api.middleware.constants import HEALTH_PATHS


def extract_client_ip(request: Request) -> str:
    """Extract the original client IP from request headers or connection.

    WHAT: Checks the X-Forwarded-For header (set by reverse proxies like
    Nginx, AWS ALB, or Kubernetes ingress) for the original client IP.
    Falls back to the direct TCP connection IP (request.client.host).

    WHY: Behind a proxy, request.client.host is the proxy's IP, not the
    client's. X-Forwarded-For preserves the original client IP in a
    comma-separated list (proxy adds itself to the end). We take the
    first IP as the most trustworthy client identifier.

    IMPORTANT: X-Forwarded-For can be spoofed by malicious clients.
    In production, trust X-Forwarded-For only if the reverse proxy is
    configured to strip or overwrite it from incoming requests.
    """
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class IPRateLimitMiddleware(BaseHTTPMiddleware):
    """Middleware: sliding-window rate limiter keyed by client IP + path.

    WHAT: Limits the number of requests from a single IP address to a
    specific endpoint path within a sliding time window. Uses in-memory
    state with an asyncio.Lock for thread-safe concurrent access.

    WHY:
      - Unauthenticated brute-force protection: prevents attackers from
        hammering login or discovery endpoints from one IP.
      - Pre-auth defense: runs before AuthMiddleware so auth processing
        overhead is not wasted on requests that will be rate-limited.
      - Per-path limits: prevents a single IP from saturating any one
        endpoint while allowing normal traffic to others.

    HOW: Maintains a dict[rate_key, list[timestamps]] in memory. On each
    request, timestamps outside the window are filtered out. If the count
    of remaining timestamps exceeds max_requests, a 429 is returned.
    A periodic cleanup (every 5 minutes) removes stale entries to cap
    memory growth.
    """

    def __init__(self, app: ASGIApp, max_requests: int | None = None, window: float = 60.0):
        super().__init__(app)
        # Cap unauthenticated IP rate limits at 20/min to prevent abuse.
        # The full limit (default_rate_limit, default 100) applies only
        # to authenticated agents (see RateLimitMiddleware).
        self.max_requests = max_requests or min(settings.default_rate_limit, 20)
        self.window = window
        # In-memory store: key → list of request timestamps
        self._rates: dict[str, list[float]] = {}
        # Prevents race conditions when multiple coroutines read/write _rates
        self._lock = asyncio.Lock()
        # Timestamp of last cleanup; cleanup runs when 300s have elapsed
        self._last_cleanup: float = 0

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in HEALTH_PATHS:
            return await call_next(request)

        client_ip = extract_client_ip(request)
        now = time.time()
        key = f"ip:{client_ip}:{request.url.path}"

        async with self._lock:
            # Periodic cleanup: every 5 minutes, remove stale entries
            # whose oldest timestamp is older than the window.
            if now - self._last_cleanup > 300:
                stale = [
                    k for k, ts in self._rates.items() if not ts or now - max(ts) > self.window
                ]
                for k in stale:
                    self._rates.pop(k, None)
                self._last_cleanup = now

            # Keep only timestamps within the sliding window
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
