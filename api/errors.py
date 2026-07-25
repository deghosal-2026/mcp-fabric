"""Structured error types for the MCP Fabric API.

Every service- or route-level error inherits from FabricError, carrying
a machine-readable error_code, HTTP status_code, human message, optional
details, suggestion, and retry_after hint.  Exception handlers in
main.py map these to consistent JSON responses.

ERROR HIERARCHY:
  FabricError (base)
  ├── 400 Bad Request
  │   ├── InvalidParameterError
  │   └── MCPToolError
  ├── 401 Unauthorized
  │   ├── InvalidTokenError
  │   └── TokenExpiredError
  ├── 403 Forbidden
  │   ├── AccessDeniedError
  │   └── NamespaceRestrictedError
  ├── 404 Not Found
  │   ├── CapabilityNotFoundError
  │   └── ServerNotFoundError
  ├── 409 Conflict
  │   ├── CapabilityConflictError
  │   └── SchemaBreakingChangeError
  ├── 410 Gone
  │   └── CapabilityDeprecatedError
  ├── 429 Too Many Requests
  │   └── RateLimitedError
  └── 503 Service Unavailable
      ├── FabricDegradedError
      ├── NoHealthyServerError
      ├── MCPTimeoutError
      ├── MCPServerError (status may vary)
      └── MCPConnectionError

ERROR CODE → HTTP STATUS MAPPING:
  invalid_parameter        → 400  (bad request)
  invalid_token            → 401  (auth failure)
  token_expired            → 401  (expired auth)
  access_denied            → 403  (policy denied)
  namespace_restricted     → 403  (tenant boundary)
  capability_not_found     → 404  (not found)
  server_not_found         → 404  (not found)
  capability_conflict      → 409  (duplicate/overlap)
  schema_breaking_change   → 409  (breaking schema change)
  capability_deprecated    → 410  (permanently gone)
  rate_limited             → 429  (throttle)
  fabric_degraded          → 503  (deps down)
  no_healthy_server        → 503  (MCP unavailable)
  mcp_server_error         → 502+ (upstream error)

RESPONSE FORMAT (from fabric_error_handler in main.py):
  {
    "error":       "<error_code>",      # machine-readable
    "message":     "<human message>",    # human-readable
    "details":     {...} | null,         # optional context
    "request_id":  "<uuid>",            # correlation id
    "suggestion":  "<text> | null,       # optional fix guidance
    "retry_after": <int> | null          # seconds (429/503)
  }
"""


class FabricError(Exception):
    """Base exception for all structured fabric errors.

    Every MCP Fabric error inherits from this class. It carries:
      - error_code:  a machine-readable string (e.g., "invalid_token")
                     for programmatic handling by API clients
      - message:     a human-readable description
      - status_code: the HTTP status code to return to the client
      - details:     optional dict with additional context (field names,
                     server addresses, conflicting IDs, etc.)
      - suggestion:  optional guidance on how to resolve the error
                     (e.g., "Use a different name" or "Regenerate token")
      - retry_after: optional integer seconds to wait before retrying
                     (meaningful for 429 and 503 responses)

    WHY A CUSTOM EXCEPTION HIERARCHY:
      - Ensures every error response follows the same JSON envelope,
        making client-side error handling predictable.
      - The error_code allows automated agents to make decisions based
        on the error type without parsing human text.
      - Subclassing makes it easy to add domain-specific attributes
        (e.g., InvalidParameterError has expected/received fields) while
        keeping the same serialization interface in main.py.
    """

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
# These errors indicate the client sent a malformed or semantically
# invalid request. The client should not retry without modification.


class InvalidParameterError(FabricError):
    """400: Malformed, missing, or contradictory request parameters.

    Raised when a request contains invalid field values, missing required
    fields, or a combination of parameters that does not make sense
    (e.g., specifying both "include_archived" and "status=active" on a
    resource that cannot be in both states).

    The `expected` and `received` optional fields help the client
    understand exactly what went wrong — useful for form-like APIs
    where the client needs to highlight specific fields.
    """

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
    """400: An MCP server returned a tool-level error.

    Raised when a downstream MCP server successfully processes a
    tool invocation request but reports a logical error (e.g., the
    tool could not complete its operation due to invalid arguments
    or an internal failure on the MCP server side).

    Differs from MCPServerError (503) which indicates the MCP server
    itself is unreachable or returned an HTTP error. MCPToolError
    implies reachable MCP server + failed tool execution.

    IMPORTANT: The error_code is "invalid_parameter" (same as
    InvalidParameterError) because from the MCP Fabric API's
    perspective, the request to the downstream tool was invalid.
    The `details` dict usually contains the MCP server's error
    response body.
    """

    def __init__(self, message: str = "MCP tool error", details: dict | None = None):
        super().__init__(
            error_code="invalid_parameter",
            message=message,
            status_code=400,
            details=details,
        )


# ── 401 Unauthorized ────────────────────────────────────────────────
# Authentication failures. The client must provide a valid credential.
# This is distinct from 403 (Forbidden) — 401 means "who are you?",
# 403 means "we know who you are, but you can't do that."


class InvalidTokenError(FabricError):
    """401: JWT token is missing, malformed, or invalid.

    Raised when:
      - The Authorization header is missing or does not start with "Bearer "
      - The JWT signature does not match (tampered token)
      - The JWT has an invalid issuer ("iss") or audience ("aud") claim
      - The token was revoked (admin session terminated)

    The AuthMiddleware returns a WWW-Authenticate header in the 401
    response so conforming clients (e.g., browsers, HTTP libraries)
    can react appropriately (e.g., prompt for credentials).
    """

    def __init__(self, message: str = "Invalid or expired token"):
        super().__init__(
            error_code="invalid_token",
            message=message,
            status_code=401,
        )


class TokenExpiredError(FabricError):
    """401: Token has exceeded its validity period.

    Raised when the JWT's "exp" (expiration) claim is in the past.
    This is distinct from InvalidTokenError because the token itself
    is valid — it just needs to be refreshed.

    WHY A SEPARATE TYPE: Clients can detect this error and
    automatically attempt a token refresh (using a refresh token
    or re-authentication) without bothering the user, whereas
    InvalidTokenError suggests the token is fundamentally broken.
    """

    def __init__(self, message: str = "Token has expired"):
        super().__init__(
            error_code="token_expired",
            message=message,
            status_code=401,
        )


# ── 403 Forbidden ───────────────────────────────────────────────────
# Authorization failures. The client is authenticated but does not
# have permission to perform the requested operation. The `policy_reason`
# field provides the specific OPA policy rule that denied the request.


class AccessDeniedError(FabricError):
    """403: The request was denied by an authorization policy.

    Raised when:
      - OPA evaluates a Rego policy and the result is "deny"
      - The agent's role does not include the required permission
      - A capability is restricted to certain agent classes
      - The request violates a resource-level access control rule

    The `policy_reason` field contains the specific Rego rule name
    or policy identifier that triggered the denial, which operators
    can use to audit and debug policy configurations.
    """

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
    """403: Cross-tenant namespace access is not allowed.

    Raised when an authenticated agent tries to access a capability
    or resource that belongs to a different tenant namespace. The
    tenant is extracted from the agent_class field of the JWT by
    TenantMiddleware (see api/middleware/tenant.py).

    WHY A SEPARATE TYPE FROM AccessDeniedError: Namespace violations
    are a specific, common multi-tenancy concern. A separate error
    code ("namespace_restricted") allows the client to distinguish
    between "you don't have this permission" (AccessDenied) and
    "this resource belongs to another team" (NamespaceRestricted),
    which often have different resolutions.
    """

    def __init__(self, message: str = "Cross-team access restricted"):
        super().__init__(
            error_code="namespace_restricted",
            message=message,
            status_code=403,
        )


# ── 404 Not Found ───────────────────────────────────────────────────
# The requested resource does not exist. The client should not retry
# without changing the resource identifier.


class CapabilityNotFoundError(FabricError):
    """404: The requested capability does not exist in the registry.

    Raised when a client attempts to discover, invoke, or manage a
    capability by name or ID that is not registered in any MCP server.
    The optional `suggestion` field may recommend similar capabilities
    based on fuzzy matching (when enable_fuzzy_capability_match is on).

    Common causes:
      - Typo in capability name
      - Capability was removed or deprecated
      - The MCP server hosting the capability has not been registered
    """

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
    """404: The requested MCP server is not registered.

    Raised when a client references an MCP server ID or name that
    does not exist in the registry. This applies to server CRUD
    operations (e.g., updating, deleting, or querying a server).

    WHY SEPARATE FROM CapabilityNotFoundError: A server may exist
    but a specific capability on it may not (and vice versa). Separate
    error types allow clients to handle each case differently —
    e.g., suggesting available servers when a server ID is wrong.
    """

    def __init__(self, message: str = "Server not found"):
        super().__init__(
            error_code="server_not_found",
            message=message,
            status_code=404,
        )


# ── 409 Conflict ────────────────────────────────────────────────────
# The request conflicts with the current state of the resource. The
# client should resolve the conflict before retrying.


class CapabilityConflictError(FabricError):
    """409: A capability with the same name or signature already exists.

    Raised when:
      - Registering a capability with a name that is already registered
      - Two MCP servers advertise capabilities with overlapping names
        and the conflict resolution policy requires unique names
      - A capability was updated between the client's read and write

    The `details` dict typically includes the existing capability's
    name, ID, and the server it belongs to, so the client can present
    a clear conflict resolution UI.
    """

    def __init__(self, message: str = "Capability conflict", details: dict | None = None):
        super().__init__(
            error_code="capability_conflict",
            message=message,
            status_code=409,
            details=details,
        )


class SchemaBreakingChangeError(FabricError):
    """409: A capability schema update would break existing consumers.

    Raised when a client attempts to update a capability's input/output
    schema in a way that is not backward-compatible (e.g., removing a
    required parameter, changing a field type, or narrowing a return
    value). The registry tracks consumer subscriptions and computes
    compatibility via schema diffing.

    WHY BLOCK BREAKING CHANGES: MCP Fabric acts as a mesh between
    capability providers and consumers. A breaking schema change would
    silently break every agent that depends on that capability, causing
    cascading failures. This error forces providers to version their
    capabilities or use the deprecation workflow (CapabilityDeprecatedError)
    instead.
    """

    def __init__(self, message: str = "Schema breaking change", details: dict | None = None):
        super().__init__(
            error_code="schema_breaking_change",
            message=message,
            status_code=409,
            details=details,
        )


# ── 410 Gone ────────────────────────────────────────────────────────
# The resource is permanently gone. Unlike 404, a 410 indicates the
# resource existed before but was intentionally removed. Clients that
# receive this for a cached capability should remove it from their
# local registry and not retry.


class CapabilityDeprecatedError(FabricError):
    """410: The capability has been deprecated and removed.

    Raised when a client attempts to invoke a capability that was
    previously available but has been formally deprecated by its
    provider. The `retired_on` field provides the deprecation date,
    and `guidance` may suggest a replacement capability.

    WHY 410 INSTEAD OF 404: Returning 410 (Gone) signals to automated
    clients that this was a deliberate removal, not a typo. Automated
    agents can use this signal to:
      1. Remove the capability from their available-tools list
      2. Search for the suggested replacement (if provided)
      3. Report the deprecation to their operator
    """

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
# The client has exceeded the allowed number of requests within a
# sliding time window. The `retry_after` field indicates when to
# try again. Clients MUST respect this header to avoid exacerbating
# load on the service.


class RateLimitedError(FabricError):
    """429: Request rate limit exceeded — back off and retry later.

    Raised by RateLimitMiddleware (per-agent) or IPRateLimitMiddleware
    (per-IP) when a client exceeds the configured maximum requests per
    window. The `retry_after` field (in seconds) indicates the
    recommended minimum wait time before retrying.

    WHY TWO RATE LIMITERS: The IP-based limiter runs before auth to
    protect against unauthenticated floods (DDoS, brute force). The
    agent-based limiter runs after auth to enforce per-agent quotas
    and prevent any single agent from starving others.
    """

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            error_code="rate_limited",
            message=message,
            status_code=429,
            retry_after=retry_after,
        )


# ── 503 Service Unavailable ─────────────────────────────────────────
# The service cannot handle the request because a core dependency or
# upstream MCP server is unavailable. The client SHOULD retry after
# respecting `retry_after`. These errors are transient by nature.


class FabricDegradedError(FabricError):
    """503: A core infrastructure dependency is unavailable.

    Raised when the service detects that the database, Redis, or OPA
    is unreachable or not responding. The `component` field identifies
    which dependency failed (e.g., "database", "redis", "opa").

    WHY A SEPARATE TYPE: Operators can aggregate FabricDegradedError
    occurrences by component to identify which infrastructure layer
    is having issues. A spike in "redis" degraded errors might indicate
    a Redis cluster problem, while "database" errors suggest a DB
    connection pool or failover event.

    IMPORTANT: This error is raised by services when they encounter
    a dependency failure during a request. The health check endpoints
    (/health, /health/ready) return similar information but do NOT
    raise this exception — they return a structured response instead.
    """

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
    """503: All candidate MCP servers for this capability are unhealthy.

    Raised during capability routing when the routing algorithm finds
    one or more MCP servers that advertise the requested capability,
    but every candidate server fails its health check (either does not
    respond or returns a non-healthy status).

    WHY THIS IS 503 NOT 404: The capability exists (it is registered),
    but the infrastructure delivering it is temporarily unavailable.
    503 signals a transient condition; the client should retry later.
    A 404 would suggest the capability never existed, which is a
    different problem.

    COMMON CAUSES:
      - All MCP servers are restarting/deploying
      - Network partition between MCP Fabric and MCP servers
      - All servers exceeded their resource limits
    """

    def __init__(self, message: str = "No healthy server available", retry_after: int = 30):
        super().__init__(
            error_code="no_healthy_server",
            message=message,
            status_code=503,
            retry_after=retry_after,
        )


class MCPTimeoutError(FabricError):
    """503: An MCP server did not respond within mcp_timeout seconds.

    Raised when an MCP Fabric to MCP server request exceeds the
    configured mcp_timeout (default: 5s). This includes both the
    connection establishment time (mcp_connect_timeout: 2s) and the
    tool execution time.

    WHY SEPARATE FROM NoHealthyServerError: A timeout means the server
    is reachable (connection established) but slow to respond. The
    server might be under load or processing a long-running tool.
    NoHealthyServerError means the server is entirely unreachable.
    These have different operational responses (scale up vs. restart).
    """

    def __init__(self, message: str = "MCP server timed out", retry_after: int = 15):
        super().__init__(
            error_code="no_healthy_server",
            message=message,
            status_code=503,
            retry_after=retry_after,
        )


class MCPServerError(FabricError):
    """502/503: An MCP server returned a non-2xx HTTP status.

    Raised when the downstream MCP server responds with an HTTP error
    (e.g., 500, 503, 502). The `status` field captures the actual
    status code from the MCP server, and `details` may include the
    response body for debugging.

    WHY STATUS_MAY_VARY: The error_code is "mcp_server_error" but the
    HTTP status returned to the client depends on the MCP server's
    response:
      - MCP server 502 → Fabric returns 502 (upstream bad gateway)
      - MCP server 503 → Fabric returns 503 (upstream unavailable)
      - MCP server 500 → Fabric returns 502 (upstream internal error)
    The default is 502 (Bad Gateway) because Fabric acts as a gateway
    to MCP servers.

    IMPORTANT: This is for HTTP-level errors from the MCP server.
    For MCP protocol-level errors (e.g., tool execution failed), use
    MCPToolError.
    """

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
    """503: Unable to establish a TCP/TLS/SSE connection to the MCP server.

    Raised when the MCP client cannot connect to the MCP server at all
    — DNS lookup failure, connection refused, connection timeout, or
    TLS handshake failure. This is distinct from MCPTimeoutError
    (which means the connection was established but the response did
    not arrive in time).

    WHY THE SAME error_code AS FabricDegradedError: Both indicate an
    infrastructure failure. From the client's perspective, a "fabric_degraded"
    response is the right signal regardless of whether it was the
    database or an MCP server that failed. Operators can inspect
    `details` or logs to differentiate.

    COMMON CAUSES:
      - MCP server is not running
      - Firewall rules blocking the connection
      - MCP server URL is misconfigured in registry
      - TLS certificate expired or invalid
    """

    def __init__(self, message: str = "MCP connection error", retry_after: int = 30):
        super().__init__(
            error_code="fabric_degraded",
            message=message,
            status_code=503,
            retry_after=retry_after,
        )
