"""OpenTelemetry tracer provider and span setup.

Provides a lazily-initialised, cached tracer instance for the "mcp-fabric"
service. The tracer is created on first use and then cached via @lru_cache,
so subsequent calls return the same instance.

Span lifecycle:
    - On first call: checks if a TracerProvider is already registered. If
      one exists (e.g. configured by an external agent), reuses it.
    - If none exists: creates a new TracerProvider with a Resource carrying
      service.name="mcp-fabric".
    - In production with an otel_endpoint configured: attaches a BatchSpanProcessor
      that exports spans via OTLP/HTTP to the configured collector endpoint.

Trace propagation:
    - Inbound: FastAPI middleware captures incoming W3C traceparent headers
      and creates/continues spans automatically.
    - Outbound: MCPClient._trace_headers() injects the current trace context
      into HTTP requests to MCP servers (see api/mcp/client.py).
"""

from functools import lru_cache

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider


@lru_cache
def _get_tracer() -> trace.Tracer:
    """Return a lazily-initialised, cached OpenTelemetry tracer.

    Creates a TracerProvider once (on first call) with the service name
    "mcp-fabric" and, in production, attaches an OTLP/HTTP span exporter
    that sends spans to settings.otel_endpoint. Subsequent calls return
    the cached tracer.

    Uses @lru_cache to ensure singleton behaviour without module-level
    state, making it safe for concurrent use and testable (cache can be
    cleared for test isolation).

    Returns:
        An OpenTelemetry Tracer instance scoped to "mcp-fabric".
    """
    from api.config import settings

    existing = trace.get_tracer_provider()
    if isinstance(existing, TracerProvider):
        return trace.get_tracer("mcp-fabric")

    resource = Resource.create({"service.name": "mcp-fabric"})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    if settings.environment == "production" and settings.otel_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    return trace.get_tracer("mcp-fabric")
