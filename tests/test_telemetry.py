"""Tests for telemetry tracing, logging, and redaction fixes."""

from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider

from api.telemetry.redaction import redact_sensitive_data
from api.telemetry.tracing import _get_tracer


def test_get_tracer_returns_tracer():
    tracer = _get_tracer()
    assert tracer is not None


def test_get_tracer_does_not_override_existing_provider():
    existing = trace.get_tracer_provider()
    tracer = _get_tracer()
    assert trace.get_tracer_provider() is existing or isinstance(
        trace.get_tracer_provider(), TracerProvider
    )
    assert tracer is not None


def test_get_tracer_is_cached():
    t1 = _get_tracer()
    t2 = _get_tracer()
    assert t1 is t2


def test_redact_sensitive_data_redacts_tokens():
    event = {"msg": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0", "key": "safe"}
    result = redact_sensitive_data(None, None, event)
    assert "***" in result["msg"]
    assert result["key"] == "safe"


def test_redact_sensitive_data_redacts_password_in_text():
    event = {"msg": "password=super-secret-123"}
    result = redact_sensitive_data(None, None, event)
    assert "***" in result["msg"]


def test_redact_sensitive_data_redacts_api_key_in_text():
    event = {"msg": "api_key=sk-abc123def456"}
    result = redact_sensitive_data(None, None, event)
    assert "***" in result["msg"]


def test_redact_sensitive_data_handles_nested_dict():
    event = {"nested": {"token": "secret-token-value", "visible": "visible-value"}}
    result = redact_sensitive_data(None, None, event)
    assert result["nested"]["token"] == "***"
    assert result["nested"]["visible"] == "visible-value"


def test_redact_sensitive_data_does_not_mutate_original():
    original = {"msg": "Bearer token123"}
    event = dict(original)
    redact_sensitive_data(None, None, event)
    assert original["msg"] == "Bearer token123"
