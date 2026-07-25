"""Capability CRUD and lifecycle management for MCP Fabric.

Provides create, list, get, and deprecate operations for capabilities
that define the normalized interface for MCP server tools.

Architectural notes:
  - Capabilities are the "what" — they define a normalized interface
    (input/output schema) independently of any specific MCP server.
  - Mappings (CapabilityMapping, managed by registry_service) connect
    capabilities to actual server endpoints.
  - Aliases provide alternative names for a capability, supporting
    backward compatibility and cross-team naming conventions.
  - Deprecation is a soft-delete: status='deprecated' with a grace period
    before the capability can be removed. Callers can check the status
    to warn about deprecated capabilities.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability, CapabilityAlias
from api.schemas.capability import CapabilityCreate, CapabilityResponse


class CapabilityService:
    """CRUD operations for capability definitions.

    Depends on: AsyncSession for DB access.
    Used by: admin capability UI, pack_service (for assigning capabilities
    to packs), routing_service (for capability resolution).

    Capabilities are the fundamental building block of the MCP Fabric
    abstraction layer. Every MCP server tool is mapped to a capability.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, params: CapabilityCreate) -> CapabilityResponse:
        """Create a new capability definition.

        WHY: Admin user journey — define a new capability that MCP servers
        can map to. The normalized schemas define the contract that all
        mapped servers must conform to.

        SIDE EFFECTS: Persists Capability row.
        RETURN: The created capability with server-generated id and timestamps.
        """
        cap = Capability(
            name=params.name,
            domain=params.domain,
            normalized_input_schema=params.normalized_input_schema,
            normalized_output_schema=params.normalized_output_schema,
            description=params.description,
        )
        self.db.add(cap)
        await self.db.commit()
        await self.db.refresh(cap)
        return await self._to_response(cap)

    async def list(self, domain: str | None = None) -> list[CapabilityResponse]:
        """List capabilities, optionally filtered by domain.

        WHY: Admin UI — browse available capabilities.
        Sorted alphabetically by name for a predictable ordering.
        """
        stmt = select(Capability).order_by(Capability.name)
        if domain:
            stmt = stmt.where(Capability.domain == domain)
        result = await self.db.execute(stmt)
        caps = result.scalars().all()
        return [await self._to_response(c) for c in caps]

    async def get(self, cap_id: UUID) -> CapabilityResponse | None:
        """Get a single capability by ID.

        WHY: Admin UI — view/edit a specific capability's details.
        RETURN: CapabilityResponse or None if not found.
        """
        result = await self.db.execute(select(Capability).where(Capability.id == cap_id))
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        return await self._to_response(cap)

    async def deprecate(self, cap_id: UUID) -> CapabilityResponse | None:
        """Mark a capability as deprecated.

        WHY: Admin user journey — soft-delete a capability that should
        no longer be used. Deprecated capabilities remain in the database
        with their mappings intact, but callers should warn when they
        are used. After the grace period, the capability can be removed.

        SIDE EFFECTS: Sets status to 'deprecated'.
        RETURN: Updated CapabilityResponse or None if not found.
        """
        result = await self.db.execute(select(Capability).where(Capability.id == cap_id))
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        cap.status = "deprecated"
        await self.db.commit()
        await self.db.refresh(cap)
        return await self._to_response(cap)

    async def add_alias(self, cap_id: UUID, alias: str) -> CapabilityResponse | None:
        """Add an alias to a capability.

        WHY: Admin user journey — provide an alternative name for a capability.
        This supports backward compatibility (old agent configurations using
        a previous name) and cross-team naming conventions.

        Aliases are resolved in routing_service.resolve_capability(): when
        a capability name is not found directly, aliases are checked.

        SIDE EFFECTS: Creates a CapabilityAlias row.
        RETURN: Updated CapabilityResponse or None if capability not found.
        """
        result = await self.db.execute(select(Capability).where(Capability.id == cap_id))
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        cap.aliases.append(CapabilityAlias(capability_id=cap_id, alias=alias))
        await self.db.commit()
        await self.db.refresh(cap)
        return await self._to_response(cap)

    async def _to_response(self, cap: Capability) -> CapabilityResponse:
        """Convert a Capability ORM object to a CapabilityResponse schema.

        Computes mappings_count (number of server mappings for this capability)
        and aliases list from the ORM relationships. These are not stored as
        columns but are derived from related tables.
        """
        return CapabilityResponse(
            id=cap.id,
            name=cap.name,
            domain=cap.domain,
            normalized_input_schema=cap.normalized_input_schema,
            normalized_output_schema=cap.normalized_output_schema,
            description=cap.description,
            status=cap.status or "active",
            deprecated_at=cap.deprecated_at,
            grace_period_days=cap.grace_period_days or 14,
            migration_guidance=cap.migration_guidance,
            created_at=cap.created_at,
            mappings_count=len(cap.mappings) if cap.mappings else 0,
            aliases=[a.alias for a in cap.aliases] if cap.aliases else [],
        )
