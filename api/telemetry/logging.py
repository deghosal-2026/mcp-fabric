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
