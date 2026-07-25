import re

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
