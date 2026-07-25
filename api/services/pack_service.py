"""Capability pack management for MCP Fabric.

Packs are curated groups of capabilities assigned to agent classes.
Provides create, assign capabilities, assign to class, clone, and
usage statistics.
"""

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.agent import AgentClass, AgentClassPack, CapabilityPack, PackAssignment
from api.models.capability import Capability
from api.schemas.pack import ClonePackRequest, PackAssignmentRequest, PackCreate, PackResponse


class PackNotFoundError(Exception):
    """Raised when a capability pack ID is not found."""


class CapabilityNotFoundError(Exception):
    """Raised when a capability ID is not found during pack assignment."""


class AgentClassNotFoundError(Exception):
    """Raised when an agent class ID is not found during pack assignment."""


class DuplicateAssignmentError(Exception):
    """Raised when a capability or class is already assigned to a pack."""


class PackService:
    """Capability pack management — create, assign, clone, and query packs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pack(self, params: PackCreate) -> PackResponse:
        """Create a new capability pack."""
        pack = CapabilityPack(
            name=params.name,
            description=params.description,
            team_namespace=params.team_namespace,
        )
        self.db.add(pack)
        await self.db.commit()
        await self.db.refresh(pack)
        return await self._to_response(pack)

    async def get_pack(self, pack_id: UUID) -> PackResponse:
        """Get a single pack by ID. Raises PackNotFoundError if missing."""
        result = await self.db.execute(
            select(CapabilityPack).where(CapabilityPack.id == pack_id)
        )
        pack = result.scalar_one_or_none()
        if pack is None:
            raise PackNotFoundError(f"Pack {pack_id} not found")
        return await self._to_response(pack)

    async def list_packs(
        self,
        team_namespace: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[PackResponse]:
        """List packs with optional team namespace filter."""
        stmt = select(CapabilityPack).order_by(CapabilityPack.name)
        if team_namespace:
            stmt = stmt.where(CapabilityPack.team_namespace == team_namespace)
        stmt = stmt.offset(offset).limit(limit)
        result = await self.db.execute(stmt)
        packs = list(result.scalars().all())
        return await self._to_response_batch(packs)

    async def update_pack(
        self,
        pack_id: UUID,
        params: PackCreate,
    ) -> PackResponse:
        """Update all fields of an existing pack."""
        result = await self.db.execute(
            select(CapabilityPack).where(CapabilityPack.id == pack_id)
        )
        pack = result.scalar_one_or_none()
        if pack is None:
            raise PackNotFoundError(f"Pack {pack_id} not found")
        pack.name = params.name
        pack.description = params.description
        pack.team_namespace = params.team_namespace
        await self.db.commit()
        await self.db.refresh(pack)
        return await self._to_response(pack)

    async def delete_pack(self, pack_id: UUID) -> None:
        """Delete a pack by ID. Raises PackNotFoundError if missing."""
        result = await self.db.execute(
            select(CapabilityPack).where(CapabilityPack.id == pack_id)
        )
        pack = result.scalar_one_or_none()
        if pack is None:
            raise PackNotFoundError(f"Pack {pack_id} not found")
        await self.db.delete(pack)
        await self.db.commit()

    async def assign_capability(
        self,
        pack_id: UUID,
        params: PackAssignmentRequest,
    ) -> None:
        """Assign a capability to a pack. Raises DuplicateAssignmentError if already assigned."""
        cap = await self.db.get(Capability, params.capability_id)
        if cap is None:
            raise CapabilityNotFoundError(f"Capability {params.capability_id} not found")

        result = await self.db.execute(
            select(PackAssignment).where(
                PackAssignment.pack_id == pack_id,
                PackAssignment.capability_id == params.capability_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise DuplicateAssignmentError(
                f"Capability {params.capability_id} already assigned to pack {pack_id}"
            )

        assignment = PackAssignment(
            pack_id=pack_id,
            capability_id=params.capability_id,
        )
        self.db.add(assignment)
        await self.db.commit()

    async def remove_capability(
        self,
        pack_id: UUID,
        capability_id: UUID,
    ) -> None:
        """Remove a capability from a pack. No-op if the assignment does not exist."""

        result = await self.db.execute(
            select(PackAssignment).where(
                PackAssignment.pack_id == pack_id,
                PackAssignment.capability_id == capability_id,
            )
        )
        assignment = result.scalar_one_or_none()
        if assignment is None:
            return
        await self.db.delete(assignment)
        await self.db.commit()

    async def assign_to_class(
        self,
        pack_id: UUID,
        agent_class_id: UUID,
    ) -> None:
        """Assign a pack to an agent class. Raises DuplicateAssignmentError if already assigned."""

        ac = await self.db.get(AgentClass, agent_class_id)
        if ac is None:
            raise AgentClassNotFoundError(f"Agent class {agent_class_id} not found")

        result = await self.db.execute(
            select(AgentClassPack).where(
                AgentClassPack.pack_id == pack_id,
                AgentClassPack.agent_class_id == agent_class_id,
            )
        )
        if result.scalar_one_or_none() is not None:
            raise DuplicateAssignmentError(
                f"Pack {pack_id} already assigned to agent class {agent_class_id}"
            )

        acp = AgentClassPack(
            pack_id=pack_id,
            agent_class_id=agent_class_id,
        )
        self.db.add(acp)
        await self.db.commit()

    async def remove_from_class(
        self,
        pack_id: UUID,
        agent_class_id: UUID,
    ) -> None:
        """Remove a pack assignment from an agent class. No-op if the assignment does not exist."""

        result = await self.db.execute(
            select(AgentClassPack).where(
                AgentClassPack.pack_id == pack_id,
                AgentClassPack.agent_class_id == agent_class_id,
            )
        )
        acp = result.scalar_one_or_none()
        if acp is None:
            return
        await self.db.delete(acp)
        await self.db.commit()

    async def clone_pack(
        self,
        pack_id: UUID,
        params: ClonePackRequest,
    ) -> PackResponse:
        """Clone an existing pack including all capability and class assignments."""

        result = await self.db.execute(
            select(CapabilityPack).where(CapabilityPack.id == pack_id)
        )
        source = result.scalar_one_or_none()
        if source is None:
            raise PackNotFoundError(f"Source pack {pack_id} not found")

        clone = CapabilityPack(
            name=params.name,
            description=source.description,
            team_namespace=source.team_namespace,
        )
        self.db.add(clone)
        await self.db.commit()
        await self.db.refresh(clone)

        cap_result = await self.db.execute(
            select(PackAssignment).where(PackAssignment.pack_id == pack_id)
        )
        for assignment in cap_result.scalars().all():
            self.db.add(
                PackAssignment(
                    pack_id=clone.id,
                    capability_id=assignment.capability_id,
                )
            )

        class_result = await self.db.execute(
            select(AgentClassPack).where(AgentClassPack.pack_id == pack_id)
        )
        for acp in class_result.scalars().all():
            self.db.add(
                AgentClassPack(
                    pack_id=clone.id,
                    agent_class_id=acp.agent_class_id,
                )
            )

        await self.db.commit()
        return await self._to_response(clone)

    async def get_usage_stats(self, pack_id: UUID) -> dict:
        """Return usage statistics for a pack including capability count,

        class count, and invocation count.
        """
        from api.models.audit import AuditEvent

        result = await self.db.execute(
            select(CapabilityPack).where(CapabilityPack.id == pack_id)
        )
        pack = result.scalar_one_or_none()
        if pack is None:
            raise PackNotFoundError(f"Pack {pack_id} not found")

        cap_count = (
            await self.db.execute(
                select(func.count(PackAssignment.id)).where(
                    PackAssignment.pack_id == pack_id
                )
            )
        ).scalar() or 0

        class_count = (
            await self.db.execute(
                select(func.count(AgentClassPack.id)).where(
                    AgentClassPack.pack_id == pack_id
                )
            )
        ).scalar() or 0

        cap_ids = (
            await self.db.execute(
                select(PackAssignment.capability_id).where(
                    PackAssignment.pack_id == pack_id
                )
            )
        ).scalars().all()

        usage_count = 0
        if cap_ids:
            usage_count = (
                await self.db.execute(
                    select(func.count(AuditEvent.id)).where(
                        AuditEvent.event_type == "capability_request",
                        func.json_extract(AuditEvent.details, '$.capability_id').in_(
                            [str(c) for c in cap_ids]
                        ),
                    )
                )
            ).scalar() or 0

        return {
            "pack_id": str(pack_id),
            "name": pack.name,
            "capabilities_count": cap_count,
            "classes_count": class_count,
            "usage_count": usage_count,
        }

    async def get_capabilities_for_class(
        self,
        agent_class_id: UUID,
    ) -> list[dict]:
        """Return all capabilities available to an agent class through its assigned packs."""

        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(AgentClassPack)
            .options(selectinload(AgentClassPack.pack).selectinload(CapabilityPack.pack_assignments))
            .where(AgentClassPack.agent_class_id == agent_class_id)
        )
        class_packs = result.unique().scalars().all()
        cap_ids: set[UUID] = set()
        for acp in class_packs:
            for pa in acp.pack.pack_assignments:
                cap_ids.add(pa.capability_id)

        if not cap_ids:
            return []

        caps_result = await self.db.execute(
            select(Capability).where(Capability.id.in_(cap_ids))
        )
        capabilities = [
            {"id": str(cap.id), "name": cap.name, "domain": cap.domain}
            for cap in caps_result.scalars().all()
        ]
        return sorted(capabilities, key=lambda c: c["name"])

    async def _to_response(self, pack: CapabilityPack) -> PackResponse:
        """Convert a CapabilityPack ORM object to a PackResponse schema with counts."""
        cap_count, class_count = await self._count_for_pack(pack.id)
        return PackResponse(
            id=pack.id,
            name=pack.name,
            description=pack.description,
            team_namespace=pack.team_namespace,
            created_at=pack.created_at,
            capabilities_count=cap_count,
            classes_count=class_count,
        )

    async def _to_response_batch(self, packs: list[CapabilityPack]) -> list[PackResponse]:
        """Convert multiple packs to responses with bulk-loaded counts."""

        if not packs:
            return []
        pack_ids = [p.id for p in packs]
        cap_counts: dict[UUID, int] = {}
        class_counts: dict[UUID, int] = {}
        for row in (
            await self.db.execute(
                select(PackAssignment.pack_id, func.count(PackAssignment.id))
                .where(PackAssignment.pack_id.in_(pack_ids))
                .group_by(PackAssignment.pack_id)
            )
        ).all():
            cap_counts[row[0]] = row[1]
        for row in (
            await self.db.execute(
                select(AgentClassPack.pack_id, func.count(AgentClassPack.id))
                .where(AgentClassPack.pack_id.in_(pack_ids))
                .group_by(AgentClassPack.pack_id)
            )
        ).all():
            class_counts[row[0]] = row[1]
        return [
            PackResponse(
                id=p.id, name=p.name, description=p.description,
                team_namespace=p.team_namespace, created_at=p.created_at,
                capabilities_count=cap_counts.get(p.id, 0),
                classes_count=class_counts.get(p.id, 0),
            )
            for p in packs
        ]

    async def _count_for_pack(self, pack_id: UUID) -> tuple[int, int]:
        """Return (capabilities_count, classes_count) for a given pack."""

        cap = (
            await self.db.execute(
                select(func.count(PackAssignment.id)).where(
                    PackAssignment.pack_id == pack_id
                )
            )
        ).scalar() or 0
        cls = (
            await self.db.execute(
                select(func.count(AgentClassPack.id)).where(
                    AgentClassPack.pack_id == pack_id
                )
            )
        ).scalar() or 0
        return cap, cls
