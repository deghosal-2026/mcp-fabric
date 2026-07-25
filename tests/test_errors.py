"""Integration tests for FabricError exception hierarchy and handlers.

Tests cover all 14 error catalog types from P8-03 through P8-06,
exception handler response format (P8-02), and graceful degradation
patterns (P8-07).
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient

from api.errors import (
    AccessDeniedError,
    CapabilityConflictError,
    CapabilityDeprecatedError,
    CapabilityNotFoundError,
    FabricDegradedError,
    FabricError,
    InvalidParameterError,
    InvalidTokenError,
    MCPConnectionError,
    MCPServerError,
    MCPTimeoutError,
    MCPToolError,
    NamespaceRestrictedError,
    NoHealthyServerError,
    RateLimitedError,
    SchemaBreakingChangeError,
    ServerNotFoundError,
    TokenExpiredError,
)


def _make_app() -> FastAPI:
    app = FastAPI()

    @app.exception_handler(FabricError)
    async def handler(request: Request, exc: FabricError):
        rid = getattr(request.state, "request_id", None)
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": exc.error_code,
                "message": exc.message,
                "details": exc.details,
                "request_id": rid,
                "suggestion": exc.suggestion,
                "retry_after": exc.retry_after,
            },
        )

    @app.get("/raise")
    async def raise_error(exc: str = "invalid_parameter"):
        mapping = {
            "invalid_parameter": InvalidParameterError(expected="int", received="str"),
            "mcp_tool": MCPToolError(details={"tool": "search"}),
            "invalid_token": InvalidTokenError(),
            "token_expired": TokenExpiredError(),
            "access_denied": AccessDeniedError(policy_reason="rate_limit_exceeded"),
            "namespace_restricted": NamespaceRestrictedError(),
            "capability_not_found": CapabilityNotFoundError(suggestion="Did you mean code:search?"),
            "server_not_found": ServerNotFoundError(),
            "capability_conflict": CapabilityConflictError(details={"overlap": "code:search"}),
            "schema_breaking": SchemaBreakingChangeError(
                details={"tool": "search", "field": "query"}
            ),
            "capability_deprecated": CapabilityDeprecatedError(
                retired_on="2026-08-01", guidance="Use code:search-v2"
            ),
            "rate_limited": RateLimitedError(retry_after=120),
            "fabric_degraded": FabricDegradedError(component="database"),
            "no_healthy_server": NoHealthyServerError(),
            "mcp_timeout": MCPTimeoutError(),
            "mcp_server_error": MCPServerError(status=502, details={"server": "mcp1"}),
            "mcp_connection": MCPConnectionError(),
        }
        raise mapping.get(exc, InvalidParameterError())

    return app


client = TestClient(_make_app())


class TestErrorInstantiation:
    """Each error type carries the correct status code and error_code."""

    def test_invalid_parameter(self):
        err = InvalidParameterError(expected="int", received="str")
        assert err.error_code == "invalid_parameter"
        assert err.status_code == 400
        assert err.details == {"expected": "int", "received": "str"}

    def test_mcp_tool_error(self):
        err = MCPToolError(details={"tool": "search"})
        assert err.error_code == "invalid_parameter"
        assert err.status_code == 400

    def test_invalid_token(self):
        err = InvalidTokenError()
        assert err.error_code == "invalid_token"
        assert err.status_code == 401

    def test_token_expired(self):
        err = TokenExpiredError()
        assert err.error_code == "token_expired"
        assert err.status_code == 401

    def test_access_denied(self):
        err = AccessDeniedError(policy_reason="rate_limit_exceeded")
        assert err.error_code == "access_denied"
        assert err.status_code == 403
        assert err.details == {"policy_reason": "rate_limit_exceeded"}

    def test_namespace_restricted(self):
        err = NamespaceRestrictedError()
        assert err.error_code == "namespace_restricted"
        assert err.status_code == 403

    def test_capability_not_found(self):
        err = CapabilityNotFoundError(suggestion="Did you mean code:search?")
        assert err.error_code == "capability_not_found"
        assert err.status_code == 404
        assert err.suggestion == "Did you mean code:search?"

    def test_server_not_found(self):
        err = ServerNotFoundError()
        assert err.error_code == "server_not_found"
        assert err.status_code == 404

    def test_capability_conflict(self):
        err = CapabilityConflictError(details={"overlap": "code:search"})
        assert err.error_code == "capability_conflict"
        assert err.status_code == 409

    def test_schema_breaking(self):
        err = SchemaBreakingChangeError()
        assert err.error_code == "schema_breaking_change"
        assert err.status_code == 409

    def test_capability_deprecated(self):
        err = CapabilityDeprecatedError(retired_on="2026-08-01", guidance="Use v2")
        assert err.error_code == "capability_deprecated"
        assert err.status_code == 410
        assert err.details == {"retired_on": "2026-08-01", "guidance": "Use v2"}

    def test_rate_limited(self):
        err = RateLimitedError(retry_after=120)
        assert err.error_code == "rate_limited"
        assert err.status_code == 429
        assert err.retry_after == 120

    def test_fabric_degraded(self):
        err = FabricDegradedError(component="database")
        assert err.error_code == "fabric_degraded"
        assert err.status_code == 503
        assert err.details == {"component": "database"}
        assert err.retry_after == 30

    def test_no_healthy_server(self):
        err = NoHealthyServerError()
        assert err.error_code == "no_healthy_server"
        assert err.status_code == 503

    def test_mcp_timeout(self):
        err = MCPTimeoutError()
        assert err.error_code == "no_healthy_server"
        assert err.status_code == 503

    def test_mcp_server_error(self):
        err = MCPServerError(status=502, details={"server": "mcp1"})
        assert err.error_code == "mcp_server_error"
        assert err.status_code == 502

    def test_mcp_connection_error(self):
        err = MCPConnectionError()
        assert err.error_code == "fabric_degraded"
        assert err.status_code == 503

    def test_str_representation(self):
        err = InvalidParameterError()
        assert str(err) == "invalid_parameter: Invalid parameter"


class TestExceptionHandlerIntegration:
    """FastAPI exception handlers return correct status + structured body."""

    def _assert_error_response(self, exc_name: str, expected_status: int, expected_code: str):
        resp = client.get(f"/raise?exc={exc_name}")
        assert (
            resp.status_code == expected_status
        ), f"Expected {expected_status} for {exc_name}, got {resp.status_code}"
        body = resp.json()
        assert body["error"] == expected_code
        assert "message" in body

    def test_400_invalid_parameter(self):
        self._assert_error_response("invalid_parameter", 400, "invalid_parameter")

    def test_401_invalid_token(self):
        self._assert_error_response("invalid_token", 401, "invalid_token")

    def test_401_token_expired(self):
        self._assert_error_response("token_expired", 401, "token_expired")

    def test_403_access_denied(self):
        self._assert_error_response("access_denied", 403, "access_denied")

    def test_403_namespace_restricted(self):
        self._assert_error_response("namespace_restricted", 403, "namespace_restricted")

    def test_404_capability_not_found(self):
        resp = client.get("/raise?exc=capability_not_found")
        assert resp.status_code == 404
        assert resp.json()["suggestion"] == "Did you mean code:search?"

    def test_404_server_not_found(self):
        self._assert_error_response("server_not_found", 404, "server_not_found")

    def test_409_capability_conflict(self):
        self._assert_error_response("capability_conflict", 409, "capability_conflict")

    def test_409_schema_breaking(self):
        self._assert_error_response("schema_breaking", 409, "schema_breaking_change")

    def test_410_deprecated(self):
        resp = client.get("/raise?exc=capability_deprecated")
        assert resp.status_code == 410
        body = resp.json()
        assert body["details"]["retired_on"] == "2026-08-01"

    def test_429_rate_limited(self):
        resp = client.get("/raise?exc=rate_limited")
        assert resp.status_code == 429
        assert resp.json()["retry_after"] == 120

    def test_503_fabric_degraded(self):
        resp = client.get("/raise?exc=fabric_degraded")
        assert resp.status_code == 503
        assert resp.json()["details"]["component"] == "database"

    def test_503_no_healthy_server(self):
        resp = client.get("/raise?exc=no_healthy_server")
        assert resp.status_code == 503
        assert resp.json()["retry_after"] == 30

    def test_502_mcp_server_error(self):
        resp = client.get("/raise?exc=mcp_server_error")
        assert resp.status_code == 502
        assert resp.json()["error"] == "mcp_server_error"

    def test_503_mcp_timeout(self):
        self._assert_error_response("mcp_timeout", 503, "no_healthy_server")

    def test_503_mcp_connection(self):
        self._assert_error_response("mcp_connection", 503, "fabric_degraded")


class TestErrorResponseShape:
    """Every error response includes the standard fields."""

    def test_response_structure(self):
        resp = client.get("/raise?exc=invalid_parameter")
        body = resp.json()
        assert "error" in body
        assert "message" in body
        assert isinstance(body.get("error"), str)

    def test_details_optional(self):
        resp = client.get("/raise?exc=server_not_found")
        body = resp.json()
        assert body["details"] is None

    def test_suggestion_on_404(self):
        resp = client.get("/raise?exc=capability_not_found")
        assert resp.json().get("suggestion") is not None

    def test_retry_after_on_429(self):
        resp = client.get("/raise?exc=rate_limited")
        assert resp.json().get("retry_after") is not None

    def test_retry_after_on_503(self):
        resp = client.get("/raise?exc=fabric_degraded")
        assert resp.json().get("retry_after") is not None
