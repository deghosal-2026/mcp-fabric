from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from api.config import settings

resource = Resource.create({"service.name": "mcp-fabric"})
provider = TracerProvider(resource=resource)

if settings.environment == "production" and settings.otel_endpoint:
    exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
    provider.add_span_processor(BatchSpanProcessor(exporter))

trace.set_tracer_provider(provider)

tracer = trace.get_tracer("mcp-fabric")


def instrument_fastapi(app):
    FastAPIInstrumentor.instrument_app(app, tracer_provider=provider)
