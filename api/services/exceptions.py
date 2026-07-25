"""Service-level exception classes for MCP Fabric.

These exceptions are raised by service methods to signal specific
error conditions. They are caught and translated to HTTP responses
by the API route handlers.

Architectural note: These exceptions are intentionally simple —
they carry a message string that is safe to return to the API client.
No sensitive information (stack traces, internal state) is included.
"""


class ServiceError(Exception):
    """Base exception for all service-layer errors.

    All service exceptions should inherit from this to allow catch-all
    handling at the API layer (e.g., returning a 500 for any ServiceError).
    """


class ServerUnreachableError(ServiceError):
    """Raised when an MCP server endpoint is unreachable or returns an error.

    Used by: registry_service.register(), registry_service.inspect().
    Carries the endpoint string so callers can identify which server failed.
    """

    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is unreachable or returned an error")


class DuplicateServerError(ServiceError):
    """Raised when attempting to register a server with an existing endpoint.

    Used by: registry_service.register().
    Endpoints must be unique within the registry (enforced by DB unique constraint).
    """

    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is already registered")


class ServerNotFoundError(ServiceError):
    """Raised when a server ID is not found in the registry.

    Used by: registry_service.get_server(), registry_service.decommission(),
    registry_service.update_health(), etc.
    """

    def __init__(self, server_id: str) -> None:
        super().__init__(f"Server {server_id} not found")


class DecommissionError(ServiceError):
    """Raised when a decommission operation is invalid or out of sequence.

    Used by: registry_service.decommission().
    Validates the phase transition order (grace_period -> migration -> sunset)
    and prevents skipping phases or re-decommissioning an already-sunset server.
    """

    def __init__(self, message: str) -> None:
        super().__init__(message)
