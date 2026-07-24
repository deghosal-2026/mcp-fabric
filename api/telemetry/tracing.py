"""Lazy-initialized OpenTelemetry tracer with configurable export.

Uses lru_cache so the TracerProvider and its processors are created
only once, on first access.  In production with an otel_endpoint set,
spans are exported via OTLP HTTP; otherwise only the SDK default
(no-op) exporter is active, keeping test output clean.

The instrument_fastapi helper wires auto-instrumentation into a
FastAPI app for automatic span creation on every route handler.
"""

from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider

if TYPE_CHECKING:
    from fastapi import FastAPI


@lru_cache
def _get_tracer() -> trace.Tracer:
    resource = Resource.create({"service.name": "mcp-fabric"})
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    from api.config import settings

    if settings.environment == "production" and settings.otel_endpoint:
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        exporter = OTLPSpanExporter(endpoint=settings.otel_endpoint)
        provider.add_span_processor(BatchSpanProcessor(exporter))

    return trace.get_tracer("mcp-fabric")


def instrument_fastapi(app: FastAPI) -> None:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    _get_tracer()
    FastAPIInstrumentor.instrument_app(app)
