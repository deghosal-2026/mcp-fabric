"""Creates an OpenTelemetry span for every HTTP request.

Span attributes capture the HTTP method, URL, status code, and request
ID so that each request's end-to-end lifecycle is visible in the trace
backend.  The tracer is obtained lazily from the telemetry module to
avoid import-time side effects.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from api.telemetry.tracing import _get_tracer


class TracingMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp):
        super().__init__(app)

    async def dispatch(self, request: Request, call_next) -> Response:
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
        return response
