import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.telemetry.metrics import fabric_request_duration_seconds, fabric_requests_total
from api.telemetry.tracing import _get_tracer


class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        tracer = _get_tracer()
        with tracer.start_as_current_span(
            f"{request.method} {request.url.path}"
        ) as span:
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
            method=request.method, path=request.url.path,
            status=response.status_code, agent_class=agent_class,
        ).inc()
        fabric_request_duration_seconds.labels(
            method=request.method, path=request.url.path,
            status=response.status_code,
        ).observe(duration)
        return response
