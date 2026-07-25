"""Telemetry subsystem for MCP Fabric.

Exports the key components needed to instrument, observe, and monitor the
application: structured logging, Prometheus metrics, OpenTelemetry tracing,
sensitive-data redaction, and SQLAlchemy/Redis instrumentation.

Exposes:
    - logging (structlog-based structured logger)
    - metrics (Prometheus metric families — Counter, Gauge, Histogram, Info)
    - tracing (OpenTelemetry TracerProvider with optional OTLP export)
    - redaction (sensitive data scrubber for log events)
    - instrumentation (hooks for DB/Redis connection tracking)
"""
