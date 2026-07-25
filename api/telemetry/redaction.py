"""Sensitive data redaction for structured log output.

Defines two redaction strategies applied by the structlog processor chain:

    1. Token redaction (TOKEN_PATTERN):
       Any standalone string of 20+ characters matching [A-Za-z0-9_-] is
       replaced with "***". This catches API keys, JWTs, session tokens,
       and similar opaque credential strings regardless of their key name.

    2. Credential key-value redaction (PASSWORD_PATTERN):
       Patterns like "password=mysecret" or "token: abc123..." are matched
       by looking for known credential key names (password, secret, token,
       api_key) followed by a separator and value.

    3. Recursive dict redaction (_redact_dict):
       Nested dictionaries are traversed recursively. Any key containing
       "token", "password", "secret", "key", or "auth" (case-insensitive)
       has its value fully replaced with "***". Non-sensitive string values
       still get token-pattern redaction.

Design rationale:
    - Pattern-based (not type-based): Catches secrets embedded in strings
      like URLs or headers, not just typed fields.
    - Conservative threshold (20 chars): Avoids false positives on short
      random strings like correlation IDs while still catching real tokens.
    - Recursive: Handles nested log context dicts (common in structlog).
"""

import re
from collections.abc import MutableMapping
from typing import Any

TOKEN_PATTERN = re.compile(r"\b([A-Za-z0-9_-]{20,})\b")
PASSWORD_PATTERN = re.compile(r'(?i)(password|secret|token|api_key)\s*[=:]\s*["\']?[^"\'&\s]+')

REDACTED = "***"


def redact_sensitive_data(
    logger: Any, method_name: str, event_dict: MutableMapping[str, Any]
) -> MutableMapping[str, Any]:
    """structlog processor that redacts sensitive data from log events.

    Called by structlog for every log event in the shared processor chain.
    Scans all string values in the event dict for tokens and credential
    patterns, and recursively processes nested dicts.

    Args:
        logger: The logger instance (passed by structlog, unused here).
        method_name: The log method name (passed by structlog, unused here).
        event_dict: Mutable dict of all key-value pairs in the log event.

    Returns:
        The modified event_dict with sensitive data replaced by "***".
    """
    for key, value in list(event_dict.items()):
        if isinstance(value, str):
            value = TOKEN_PATTERN.sub(REDACTED, value)
            value = PASSWORD_PATTERN.sub(r"\1=" + REDACTED, value)
            event_dict[key] = value
        elif isinstance(value, dict):
            event_dict[key] = _redact_dict(value)
    return event_dict


def _redact_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively redact sensitive values in a nested dictionary.

    Keys containing credential-related substrings (token, password, secret,
    key, auth) have their values fully replaced. Non-sensitive string values
    still get token-pattern scanning. Nested dicts recurse.

    Args:
        d: The dictionary to redact.

    Returns:
        A new dictionary with sensitive values replaced.
    """
    redacted: dict[str, Any] = {}
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
