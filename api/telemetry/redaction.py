import re

import structlog

TOKEN_PATTERN = re.compile(r"\b([A-Za-z0-9_-]{20,})\b")
PASSWORD_PATTERN = re.compile(r'(?i)(password|secret|token|api_key)\s*[=:]\s*["\']?[^"\'&\s]+')

REDACTED = "***"


def redact_sensitive_data(logger, method_name, event_dict):
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            value = TOKEN_PATTERN.sub(REDACTED, value)
            value = PASSWORD_PATTERN.sub(r"\1=" + REDACTED, value)
            event_dict[key] = value
        elif isinstance(value, dict):
            event_dict[key] = _redact_dict(value)
    return event_dict


def _redact_dict(d):
    redacted = {}
    for k, v in d.items():
        if isinstance(v, str):
            if any(s in k.lower() for s in ("token", "password", "secret", "key", "auth")):
                redacted[k] = REDACTED
            else:
                redacted[k] = TOKEN_PATTERN.sub(REDACTED, v)
        elif isinstance(v, dict):
            redacted[k] = _redact_dict(v)
        else:
            redacted[k] = v
    return redacted


structlog.configure(
    processors=[
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.dev.set_exc_info,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        redact_sensitive_data,
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)
