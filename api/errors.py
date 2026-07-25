"""Structured error types for the MCP Fabric API.

Every service- or route-level error inherits from FabricError, carrying
a machine-readable error_code, HTTP status_code, human message, optional
details, suggestion, and retry_after hint.  Exception handlers in
main.py map these to consistent JSON responses.
"""


class FabricError(Exception):
    """Base exception for all structured fabric errors."""

    def __init__(
        self,
        error_code: str,
        message: str,
        status_code: int = 400,
        details: dict | None = None,
        suggestion: str | None = None,
        retry_after: int | None = None,
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.suggestion = suggestion
        self.retry_after = retry_after
        super().__init__(self.message)

    def __str__(self) -> str:
        return f"{self.error_code}: {self.message}"


# ── 400 Bad Request ─────────────────────────────────────────────────

class InvalidParameterError(FabricError):
    """Malformed or missing request parameters."""

    def __init__(
        self,
        message: str = "Invalid parameter",
        details: dict | None = None,
        expected: str | None = None,
        received: str | None = None,
    ):
        d = {"expected": expected, "received": received} if expected or received else details
        super().__init__(
            error_code="invalid_parameter",
            message=message,
            status_code=400,
            details=d or details,
        )


class MCPToolError(FabricError):
    """Error returned by an MCP server during tool execution."""

    def __init__(self, message: str = "MCP tool error", details: dict | None = None):
        super().__init__(
            error_code="invalid_parameter",
            message=message,
            status_code=400,
            details=details,
        )


# ── 401 Unauthorized ────────────────────────────────────────────────

class InvalidTokenError(FabricError):
    """Missing, malformed, or expired authentication token."""

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(
            error_code="invalid_token",
            message=message,
            status_code=401,
        )


class TokenExpiredError(FabricError):
    """Token has expired beyond any grace period."""

    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            error_code="token_expired",
            message=message,
            status_code=401,
        )


# ── 403 Forbidden ───────────────────────────────────────────────────

class AccessDeniedError(FabricError):
    """Policy denied the request."""

    def __init__(
        self,
        message: str = "Access denied",
        policy_reason: str | None = None,
    ):
        super().__init__(
            error_code="access_denied",
            message=message,
            status_code=403,
            details={"policy_reason": policy_reason} if policy_reason else None,
        )


class NamespaceRestrictedError(FabricError):
    """Cross-team namespace access denied."""

    def __init__(self, message: str = "Cross-team access restricted"):
        super().__init__(
            error_code="namespace_restricted",
            message=message,
            status_code=403,
        )


# ── 404 Not Found ───────────────────────────────────────────────────

class CapabilityNotFoundError(FabricError):
    """Requested capability does not exist."""

    def __init__(
        self,
        message: str = "Capability not found",
        suggestion: str | None = None,
    ):
        super().__init__(
            error_code="capability_not_found",
            message=message,
            status_code=404,
            suggestion=suggestion,
        )


class ServerNotFoundError(FabricError):
    """Requested MCP server does not exist."""

    def __init__(self, message: str = "Server not found"):
        super().__init__(
            error_code="server_not_found",
            message=message,
            status_code=404,
        )


# ── 409 Conflict ────────────────────────────────────────────────────

class CapabilityConflictError(FabricError):
    """Overlapping capability definition detected."""

    def __init__(self, message: str = "Capability conflict", details: dict | None = None):
        super().__init__(
            error_code="capability_conflict",
            message=message,
            status_code=409,
            details=details,
        )


class SchemaBreakingChangeError(FabricError):
    """A schema change would break existing consumers."""

    def __init__(self, message: str = "Schema breaking change", details: dict | None = None):
        super().__init__(
            error_code="schema_breaking_change",
            message=message,
            status_code=409,
            details=details,
        )


# ── 410 Gone ────────────────────────────────────────────────────────

class CapabilityDeprecatedError(FabricError):
    """Capability has been deprecated and is no longer available."""

    def __init__(
        self,
        message: str = "Capability deprecated",
        retired_on: str | None = None,
        guidance: str | None = None,
    ):
        d = None
        if retired_on or guidance:
            d = {"retired_on": retired_on, "guidance": guidance}
        super().__init__(
            error_code="capability_deprecated",
            message=message,
            status_code=410,
            details=d,
        )


# ── 429 Too Many Requests ───────────────────────────────────────────

class RateLimitedError(FabricError):
    """Request rate limit exceeded."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            error_code="rate_limited",
            message=message,
            status_code=429,
            retry_after=retry_after,
        )


# ── 503 Service Unavailable ─────────────────────────────────────────

class FabricDegradedError(FabricError):
    """A core dependency (DB, Redis, OPA) is unavailable."""

    def __init__(
        self,
        message: str = "Service degraded",
        component: str | None = None,
        retry_after: int = 30,
    ):
        super().__init__(
            error_code="fabric_degraded",
            message=message,
            status_code=503,
            details={"component": component} if component else None,
            retry_after=retry_after,
        )


class NoHealthyServerError(FabricError):
    """All candidate MCP servers are unhealthy or unreachable."""

    def __init__(self, message: str = "No healthy server available", retry_after: int = 30):
        super().__init__(
            error_code="no_healthy_server",
            message=message,
            status_code=503,
            retry_after=retry_after,
        )


class MCPTimeoutError(FabricError):
    """MCP server did not respond within the timeout window."""

    def __init__(self, message: str = "MCP server timed out", retry_after: int = 15):
        super().__init__(
            error_code="no_healthy_server",
            message=message,
            status_code=503,
            retry_after=retry_after,
        )


class MCPServerError(FabricError):
    """MCP server returned an error status."""

    def __init__(
        self,
        message: str = "MCP server error",
        status: int = 502,
        details: dict | None = None,
    ):
        super().__init__(
            error_code="mcp_server_error",
            message=message,
            status_code=status,
            details=details,
        )


class MCPConnectionError(FabricError):
    """Unable to establish a connection to the MCP server."""

    def __init__(self, message: str = "MCP connection error", retry_after: int = 30):
        super().__init__(
            error_code="fabric_degraded",
            message=message,
            status_code=503,
            retry_after=retry_after,
        )
