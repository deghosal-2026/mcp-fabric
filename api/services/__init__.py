"""Service layer for MCP Fabric business logic.

Services encapsulate domain operations that span HTTP clients, the
database, and other services. Each service class accepts its
dependencies via constructor injection for testability.
"""

from api.services.exceptions import DuplicateServerError, ServerUnreachableError, ServiceError
from api.services.registry_service import RegistryService

__all__ = [
    "RegistryService",
    "ServiceError",
    "DuplicateServerError",
    "ServerUnreachableError",
]
