from functools import lru_cache

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider


@lru_cache
def _get_tracer() -> trace.Tracer:
    from api.config import settings

    existing = trace.get_tracer_provider()
    default = trace._DefaultTracerProvider
    if not isinstance(existing, default):
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
