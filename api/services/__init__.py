"""Service layer for MCP Fabric business logic.

Services encapsulate domain operations that span HTTP clients, the
database, and other services. Each service class accepts its
dependencies via constructor injection for testability.
"""

from api.services.alert_service import AlertService
from api.services.approval_service import (
    ApprovalAlreadyResolvedError,
    ApprovalExpiredError,
    ApprovalNotFoundError,
    ApprovalService,
)
from api.services.audit_service import AuditService
from api.services.auth_service import AuthService, InvalidTokenError
from api.services.exceptions import (
    DecommissionError,
    DuplicateServerError,
    ServerNotFoundError,
    ServerUnreachableError,
    ServiceError,
)
from api.services.pack_service import (
    PackNotFoundError,
    PackService,
)
from api.services.policy_service import (
    OPAEvaluationError,
    OPAServiceError,
    PolicyService,
)
from api.services.registry_service import RegistryService
from api.services.resource_service import ResourceNotFoundError, ResourceService

__all__ = [
    "ApprovalAlreadyResolvedError",
    "ApprovalExpiredError",
    "ApprovalNotFoundError",
    "ApprovalService",
    "AlertService",
    "AuditService",
    "AuthService",
    "InvalidTokenError",
    "OPAEvaluationError",
    "OPAServiceError",
    "PackNotFoundError",
    "PackService",
    "PolicyService",
    "RegistryService",
    "ResourceNotFoundError",
    "ResourceService",
    "ServiceError",
    "DecommissionError",
    "DuplicateServerError",
    "ServerNotFoundError",
    "ServerUnreachableError",
]
