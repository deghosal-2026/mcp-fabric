"""Structured logging configuration via structlog.

Configures structlog with a shared processor chain that is applied to all
log messages before output. In production the output is JSON (consumable
by log aggregators like Loki/Datadog); in development it uses a coloured
console renderer for readability.

Processor chain (order matters):
  1. add_log_level    — attaches the log level name (INFO, ERROR, etc.)
  2. add_logger_name  — attaches the logger name for source attribution
  3. set_exc_info     — captures exception info when an exception is in context
  4. TimeStamper(iso) — adds an ISO-8601 timestamp to every event
  5. StackInfoRenderer — renders stack info when present
  6. format_exc_info  — formats exception tracebacks into readable strings
  7. UnicodeDecoder   — ensures all string values are unicode
  8. redact_sensitive_data — custom processor that scrubs tokens/passwords/secrets

Redaction rules (see redaction.py):
    - Any string token 20+ characters of [A-Za-z0-9_-] is replaced with "***"
    - Common credential key names (password, secret, token, api_key) with
      their values are redacted in key=value patterns
    - Nested dicts are recursively scanned for sensitive keys

Output format:
    - Production: JSONRenderer — one JSON object per line, ingestible by
      structured log backends (ELK, Loki, Datadog, etc.)
    - Non-production: ConsoleRenderer — human-readable coloured output
"""

import logging
import sys

import structlog

from api.config import settings
from api.telemetry.redaction import redact_sensitive_data

shared_processors = [
    structlog.stdlib.add_log_level,
    structlog.stdlib.add_logger_name,
    structlog.dev.set_exc_info,
    structlog.processors.TimeStamper(fmt="iso"),
    structlog.processors.StackInfoRenderer(),
    structlog.processors.format_exc_info,
    structlog.processors.UnicodeDecoder(),
    redact_sensitive_data,
]

if settings.environment == "production":
    output_processor = structlog.processors.JSONRenderer()
else:
    output_processor = structlog.dev.ConsoleRenderer()

structlog.configure(
    processors=shared_processors + [output_processor],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logging.basicConfig(stream=sys.stdout, level=settings.log_level)

logger = structlog.get_logger("mcp-fabric")
