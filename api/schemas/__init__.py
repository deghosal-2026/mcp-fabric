"""
Convenience re-exports for all Pydantic schemas.

Import schemas from `api.schemas` rather than individual modules.
The model_rebuild() calls after imports resolve forward references
(used in PaginatedServers and ServerDetail which reference each other).
"""

from api.schemas.admin import AdminUserInvite, AdminUserResponse, AdminUserUpdate
from api.schemas.agent import (
    AgentClassCreate,
    AgentClassResponse,
    AgentConnectResponse,
    AgentIdentityCreate,
    AgentIdentityResponse,
    CapabilitySurfaceItem,
    TrustAssignmentCreate,
    TrustAssignmentResponse,
)
from api.schemas.approval import (
    ApprovalAction,
    ApprovalRequestCreate,
    ApprovalRequestResponse,
    ApprovalStatusResponse,
)
from api.schemas.audit import AuditEventResponse, AuditExportRequest
from api.schemas.auth import (
    LoginRequest,
    MFARecoveryRequest,
    MFASetupResponse,
    MFAVerifyRequest,
    PasswordResetRequest,
    SetupCompleteRequest,
    TokenResponse,
    WebhookRegistrationRequest,
    WebhookResponse,
)
from api.schemas.capability import (
    CapabilityCreate,
    CapabilityMappingCreate,
    CapabilityMappingResponse,
    CapabilityResponse,
)
from api.schemas.common import (
    FabricError,
    PaginatedApprovals,
    PaginatedAudit,
    PaginatedServers,
    PaginationMeta,
    PolicyDecision,
)
from api.schemas.pack import ClonePackRequest, PackAssignmentRequest, PackCreate, PackResponse
from api.schemas.routing import (
    BatchCapabilityRequest,
    BatchResult,
    CapabilityRequest,
    RouteResult,
    RoutingRuleCreate,
)
from api.schemas.server import (
    DecommissionRequest,
    DecommissionResult,
    DecommissionTimeline,
    DependencyReport,
    RoutingRuleResponse,
    ServerCreate,
    ServerDetail,
    ServerInspectResponse,
    ServerResponse,
    ToolChange,
    ToolResponse,
    ToolVersionResponse,
)

PaginatedServers.model_rebuild()
ServerDetail.model_rebuild()

__all__ = [
    "ApprovalAction",
    "ApprovalRequestCreate",
    "ApprovalRequestResponse",
    "ApprovalStatusResponse",
    "ServerCreate",
    "ServerResponse",
    "ToolResponse",
    "ToolChange",
    "ServerInspectResponse",
    "ServerDetail",
    "ToolVersionResponse",
    "RoutingRuleResponse",
    "DecommissionTimeline",
    "DecommissionRequest",
    "DecommissionResult",
    "DependencyReport",
    "PaginationMeta",
    "PaginatedServers",
    "PaginatedAudit",
    "PaginatedApprovals",
    "FabricError",
    "PolicyDecision",
    "CapabilityCreate",
    "CapabilityResponse",
    "CapabilityMappingCreate",
    "CapabilityMappingResponse",
    "AgentClassCreate",
    "AgentClassResponse",
    "AgentIdentityCreate",
    "AgentIdentityResponse",
    "AgentConnectResponse",
    "CapabilitySurfaceItem",
    "TrustAssignmentCreate",
    "TrustAssignmentResponse",
    "LoginRequest",
    "TokenResponse",
    "MFASetupResponse",
    "MFAVerifyRequest",
    "MFARecoveryRequest",
    "PasswordResetRequest",
    "SetupCompleteRequest",
    "WebhookRegistrationRequest",
    "WebhookResponse",
    "AuditEventResponse",
    "AuditExportRequest",
    "PackCreate",
    "PackResponse",
    "PackAssignmentRequest",
    "ClonePackRequest",
    "AdminUserInvite",
    "AdminUserResponse",
    "AdminUserUpdate",
    "CapabilityRequest",
    "BatchCapabilityRequest",
    "RouteResult",
    "BatchResult",
    "RoutingRuleCreate",
]
