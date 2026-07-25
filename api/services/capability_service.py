"""Capability CRUD and lifecycle management for MCP Fabric.

Provides create, list, get, and deprecate operations for capabilities
that define the normalized interface for MCP server tools.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability
from api.schemas.capability import CapabilityCreate, CapabilityResponse


class CapabilityService:
    """CRUD operations for capability definitions."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, params: CapabilityCreate) -> CapabilityResponse:
        """Create a new capability definition."""
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
        """List capabilities, optionally filtered by domain."""
        stmt = select(Capability).order_by(Capability.name)
        if domain:
            stmt = stmt.where(Capability.domain == domain)
        result = await self.db.execute(stmt)
        caps = result.scalars().all()
        return [await self._to_response(c) for c in caps]

    async def get(self, cap_id: UUID) -> CapabilityResponse | None:
        """Get a single capability by ID, or None if not found."""
        result = await self.db.execute(select(Capability).where(Capability.id == cap_id))
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        return await self._to_response(cap)

    async def deprecate(self, cap_id: UUID) -> CapabilityResponse | None:
        """Mark a capability as deprecated. Returns None if not found."""
        result = await self.db.execute(select(Capability).where(Capability.id == cap_id))
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        cap.status = "deprecated"
        await self.db.commit()
        await self.db.refresh(cap)
        return await self._to_response(cap)

    async def _to_response(self, cap: Capability) -> CapabilityResponse:
        """Convert a Capability ORM object to a CapabilityResponse schema."""
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
