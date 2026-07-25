class ServiceError(Exception):
    """Base exception for all service-layer errors."""


class ServerUnreachableError(ServiceError):
    """Raised when an MCP server endpoint is unreachable or returns an error."""

    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is unreachable or returned an error")


class DuplicateServerError(ServiceError):
    """Raised when attempting to register a server with an existing endpoint."""

    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is already registered")


class ServerNotFoundError(ServiceError):
    """Raised when a server ID is not found in the registry."""

    def __init__(self, server_id: str) -> None:
        super().__init__(f"Server {server_id} not found")


class DecommissionError(ServiceError):
    """Raised when a decommission operation is invalid or out of sequence."""

    def __init__(self, message: str) -> None:
        super().__init__(message)
