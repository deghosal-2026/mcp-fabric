"""OpenTelemetry tracing and Prometheus metrics middleware.

Wraps every request in an OpenTelemetry span and records Prometheus
HTTP metrics (request count, request duration). This middleware runs
after RequestIDMiddleware so it can attach the request_id to the span.

REQUEST PROCESSING ORDER:
  1. Record start time (monotonic clock for precision).
  2. Get the OpenTelemetry tracer from the telemetry module.
  3. Create a new span named "{METHOD} {PATH}" (e.g., "GET /capabilities").
  4. Set span attributes: http.method, http.url.
  5. Call the next middleware/router and capture the response.
  6. Set span attributes: http.status_code, http.request_id.
  7. Calculate duration.
  8. Increment Prometheus request counter (fabric_requests_total) with
     labels: method, path, status, agent_class.
  9. Record request duration in Prometheus histogram
     (fabric_request_duration_seconds) with labels: method, path, status.

HEADERS READ: none (reads request.state.request_id set by RequestIDMiddleware).

STATE SET ON REQUEST: none (only reads state set by others).

FAILURE BEHAVIOR:
  - If _get_tracer() returns a no-op tracer (OTEL not configured), the
    span is still created but discarded. No error is raised.
  - If an exception occurs during request processing, the span's status
    will be set to ERROR by the OpenTelemetry SDK automatically (when
    the span context manager exits with an exception).
  - Prometheus metric recording happens outside the span context manager,
    so even if the span is cancelled, metrics are still recorded.

IMPORTANT: Uses time.monotonic() for duration measurement (immune to
system clock changes) rather than time.time() which can jump.

IMPORTANT: Metrics are recorded with agent_class label for per-agent-class
visibility. This allows operators to see which types of agents are driving
the most traffic.
"""

import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.telemetry.metrics import fabric_request_duration_seconds, fabric_requests_total
from api.telemetry.tracing import _get_tracer


class TracingMiddleware(BaseHTTPMiddleware):
    """Middleware: creates OpenTelemetry spans and records Prometheus HTTP metrics.

    WHAT: Wraps every request in an OpenTelemetry trace span for distributed
    tracing and records Prometheus counters/histograms for request volume
    and latency monitoring.

    WHY: Provides observability into request patterns, error rates, and
    latency distributions. The span allows operators to trace a single
    request across service boundaries when OTEL is configured with an
    exporter endpoint.

    HOW: Uses time.monotonic() to measure request duration. The span is
    created with the tracer from api.telemetry.tracing (which may be a
    no-op if OTEL is not configured). Prometheus metrics are always
    recorded regardless of tracing configuration.
    """

    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.monotonic()
        tracer = _get_tracer()
        # start_as_current_span exits the span when the context manager exits
        with tracer.start_as_current_span(f"{request.method} {request.url.path}") as span:
            span.set_attribute("http.method", request.method)
            span.set_attribute("http.url", str(request.url))
            response = await call_next(request)
            span.set_attribute("http.status_code", response.status_code)
            request_id = getattr(request.state, "request_id", None)
            if request_id:
                span.set_attribute("http.request_id", request_id)

        duration = time.monotonic() - start
        agent_class = getattr(request.state, "agent_class", "")
        fabric_requests_total.labels(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            agent_class=agent_class,
        ).inc()
        fabric_request_duration_seconds.labels(
            method=request.method,
            path=request.url.path,
            status=response.status_code,
        ).observe(duration)
        return response
