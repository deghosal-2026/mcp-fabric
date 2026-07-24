class ServiceError(Exception):
    """Base exception for all service-layer errors."""


class ServerUnreachableError(ServiceError):
    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is unreachable or returned an error")


class DuplicateServerError(ServiceError):
    def __init__(self, endpoint: str) -> None:
        super().__init__(f"Server at {endpoint} is already registered")
