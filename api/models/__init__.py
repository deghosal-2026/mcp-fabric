"""
Convenience re-exports for all ORM models.

Why all models must be imported here:
  SQLAlchemy's declarative Base metadata (Base.metadata) is the source of truth
  for Alembic autogeneration. Alembic inspects Base.metadata to detect table
  changes, but it only sees tables whose models have been imported and thus
  registered. If a model module is never imported at application startup,
  Alembic will silently ignore that table and try to drop it (or never create
  it). This __init__.py guarantees every model class is loaded and registered
  on Base.metadata simply by importing from api.models.
"""

from api.models.admin import AdminUser, BackgroundTask
from api.models.agent import (
    AgentClass,
    AgentClassPack,
    AgentIdentity,
    CapabilityPack,
    PackAssignment,
    TrustAssignment,
)
from api.models.audit import AlertEvent, AlertRule, ApprovalRequest, AuditEvent
from api.models.base import Base
from api.models.capability import Capability, CapabilityAlias
from api.models.policy import OPAPolicyVersion
from api.models.resource import (
    DimensionValueMap,
    IdentityResourceBinding,
    PackResourceBinding,
    ResourceDimension,
)
from api.models.server import CapabilityMapping, MCPServer, RoutingRule, ServerTool, ToolVersion

__all__ = [
    "Base",
    "MCPServer",
    "ServerTool",
    "ToolVersion",
    "CapabilityMapping",
    "RoutingRule",
    "Capability",
    "CapabilityAlias",
    "AgentClass",
    "TrustAssignment",
    "AgentIdentity",
    "CapabilityPack",
    "PackAssignment",
    "AgentClassPack",
    "AuditEvent",
    "ApprovalRequest",
    "AlertRule",
    "AlertEvent",
    "AdminUser",
    "BackgroundTask",
    "OPAPolicyVersion",
    "ResourceDimension",
    "DimensionValueMap",
    "IdentityResourceBinding",
    "PackResourceBinding",
]
