"""Pydantic schemas for capability definition and mapping.

Endpoints:
  POST /api/v1/capabilities               -> CapabilityCreate -> CapabilityResponse
  GET  /api/v1/capabilities               -> list[CapabilityResponse]
  GET  /api/v1/capabilities/{id}          -> CapabilityResponse
  POST /api/v1/capabilities/{id}/aliases  -> CapabilityAliasCreate
  POST /api/v1/capability-mappings         -> CapabilityMappingCreate -> CapabilityMappingResponse
  GET  /api/v1/capability-mappings         -> list[CapabilityMappingResponse]
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class CapabilityAliasCreate(BaseModel):
    """Request body for adding an alias to a capability.

    POST /api/v1/capabilities/{id}/aliases

    The alias must be 1-255 chars and will be validated for uniqueness
    across all aliases (not just for this capability).
    """

    alias: str = Field(min_length=1, max_length=255)


class CapabilityCreate(BaseModel):
    """Request body for defining a new normalized capability.

    POST /api/v1/capabilities

    name must follow the pattern `domain:verb`:
      - Lowercase domain prefix (e.g. "code", "search", "deploy").
      - Colon separator.
      - Lowercase verb with hyphens allowed (e.g. "review", "create-pr").

    Example valid names: "code:review", "search:web", "deploy:create-release".

    The normalized_input_schema and normalized_output_schema define the
    canonical interface that agents use when invoking this capability.
    """

    name: str = Field(min_length=1, max_length=255, pattern=r"^[a-z]+:[a-z][a-z-]*$")
    domain: str | None = None
    normalized_input_schema: dict[str, Any] | None = None
    normalized_output_schema: dict[str, Any] | None = None
    description: str | None = None


class CapabilityResponse(BaseModel):
    """Full capability representation returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.

    Includes computed aggregate fields:
      - mappings_count: number of server mappings for this capability.
      - aliases: list of alias name strings rather than full alias objects.

    Also includes deprecation metadata (deprecated_at, grace_period_days,
    migration_guidance) when applicable.
    """

    id: UUID
    name: str
    domain: str | None = None
    normalized_input_schema: dict[str, Any] | None = None
    normalized_output_schema: dict[str, Any] | None = None
    description: str | None = None
    status: str
    deprecated_at: datetime | None = None
    grace_period_days: int = 14
    migration_guidance: str | None = None
    created_at: datetime
    mappings_count: int = 0
    aliases: list[str] = []

    model_config = {"from_attributes": True}


class CapabilityMappingCreate(BaseModel):
    """Request body for mapping a capability to a server tool.

    POST /api/v1/capability-mappings

    Fields:
        server_id:     Target MCP server UUID.
        tool_name:     The tool on that server that implements this capability.
        input_mapping: Optional JSON describing parameter transformation from
                       capability normalized schema to tool native schema.
        output_mapping: Optional JSON describing result transformation from
                        tool native schema to capability normalized schema.
        is_primary:    Whether this should be the default/primary mapping
                       (used for routing when no routing rules apply).
    """

    server_id: UUID
    tool_name: str
    input_mapping: dict[str, Any] | None = None
    output_mapping: dict[str, Any] | None = None
    is_primary: bool = True


class CapabilityMappingResponse(BaseModel):
    """Capability-to-server mapping as returned by the API.

    model_config = {"from_attributes": True} for ORM conversion.

    Matches the CapabilityMapping ORM model. Includes routing_weight for
    load-balancing across multiple mappings.

    Fields:
        tool_schema_digest: SHA-256 digest of (tool_name + input_schema + output_schema)
            at the time the mapping was created or last reviewed. Routing verifies this
            against the current ServerTool schema before selecting this mapping.
        status: 'active' | 'stale' | 'rejected' - controls whether routing considers
            this mapping. Only 'active' mappings pass the routing filter.
    """

    id: UUID
    capability_id: UUID
    server_id: UUID
    tool_name: str
    input_mapping: dict[str, Any] | None = None
    output_mapping: dict[str, Any] | None = None
    is_primary: bool = True
    routing_weight: float = 1.0
    tool_schema_digest: str | None = None
    status: str = "active"
    pending_since: datetime | None = None
    failure_class: str | None = None

    model_config = {"from_attributes": True}


class MappingReviewResponse(BaseModel):
    """Admin review record for a schema-digest drift.

    Returned after an admin reviews (approves or rejects) a stale mapping.
    Captures the before and after digest values for the audit trail.

    model_config = {"from_attributes": True} for ORM conversion.

    Fields:
        previous_digest: The mapping's tool_schema_digest before review.
        new_digest:      The recomputed digest (on approval) or the same
                         as previous (on rejection).
        decision:        'approved' | 'rejected'.
        reason:          Optional justification from the admin.
        reviewed_by:     Admin user ID who made the decision.
    """

    id: UUID
    mapping_id: UUID
    previous_digest: str | None = None
    new_digest: str | None = None
    decision: str
    reason: str | None = None
    reviewed_by: UUID | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class MappingReviewCreate(BaseModel):
    """Request body for reviewing a stale mapping.

    POST /api/v1/admin/mappings/{id}/review

    Fields:
        decision: 'approved' | 'rejected'.
            'approved' reactivates the mapping with an updated schema digest.
            'rejected' keeps the mapping in 'rejected' status (skipped by routing).
        reason:   Optional justification for the decision. Stored in the audit trail.
    """

    decision: str
    reason: str | None = None


class BulkRetireRequest(BaseModel):
    """Request body for retiring a group of review items at once (#447).

    POST /api/v1/admin/mappings/retire

    Retires (marks 'rejected', clears pending_since) every limbo mapping that
    matches the given failure_class — a hands-off batch action for items that
    need no per-item assessment (e.g. all 'unreachable' servers), so they can
    be removed without burying the reviewer or counting toward the critical
    tally. One of failure_class / mapping_ids is required; either may be used.

    Fields:
        failure_class: Only retire items with this class (unreachable/drifted/...).
        mapping_ids:   Explicit list of mapping IDs to retire.
    """

    failure_class: str | None = None
    mapping_ids: list[UUID] | None = None


class BulkRetireResponse(BaseModel):
    """Result of a bulk retire action (#447).

    Fields:
        retired: number of mappings that were retired.
        failure_class: the class that was targeted (if provided).
    """

    retired: int
    failure_class: str | None = None


class ReviewQueueSummary(BaseModel):
    """Live view of the review queue grouped by failure reason (#447).

    The critical tally deliberately EXCLUDES unreachable/timeout items — those
    are hands-off (retire-or-wait) and must not pressure the reviewer. Only
    drifted/schema_mismatch items represent real, review-worthy change.

    Fields:
        total:            all review items currently in limbo.
        critical:         items needing hands-on review (drifted + schema_mismatch).
        unreachable:      items that are offline (unreachable + timeout).
        by_failure_class: raw count per failure_class value.
    """

    total: int
    critical: int
    unreachable: int
    by_failure_class: dict[str, int]
