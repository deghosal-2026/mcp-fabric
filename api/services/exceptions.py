class ServiceError(Exception):
    """Base exception for all service-layer errors."""


class ServerUnreachableError(ServiceError):
    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is unreachable or returned an error")


class DuplicateServerError(ServiceError):
    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is already registered")


class ServerNotFoundError(ServiceError):
    def __init__(self, server_id: str) -> None:
        super().__init__(f"Server {server_id} not found")


class DecommissionError(ServiceError):
    def __init__(self, message: str) -> None:
        super().__init__(message)
