"""Capability pack management for MCP Fabric.

Packs are curated groups of capabilities assigned to agent classes.
Provides create, assign capabilities, assign to class, clone, and
usage statistics.

Architectural notes:
  - Packs sit between capabilities and agent classes: a pack groups
    related capabilities (e.g., "data-processing" pack might contain
    "transform", "aggregate", "filter" capabilities).
  - Agent classes get capabilities through packs (not directly).
    This indirection enables grouping and simplifies administration.
  - PackAssignment links packs to capabilities. AgentClassPack links
    packs to agent classes. Both use separate join tables.
  - The clone operation uses multiple DB round-trips rather than a
    single bulk-copy. For large packs, this could be optimized.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.agent import AgentClass, AgentClassPack, CapabilityPack, PackAssignment
from api.models.capability import Capability
from api.schemas.pack import (
    ClonePackRequest,
    PackAssignmentRequest,
    PackCreate,
    PackResponse,
    PackSecurityMetricsResponse,
)
from api.services.resource_service import ResourceService


class PackNotFoundError(Exception):
    """Raised when a capability pack ID is not found."""


class CapabilityNotFoundError(Exception):
    """Raised when a capability ID is not found during pack assignment."""


class AgentClassNotFoundError(Exception):
    """Raised when an agent class ID is not found during pack assignment."""


class DuplicateAssignmentError(Exception):
    """Raised when a capability or class is already assigned to a pack."""


class PackService:
    """Capability pack management — create, assign, clone, and query packs.

    Depends on: AsyncSession for DB access.
    Used by: admin pack management UI, auth_service (for computing
    capability surfaces from class -> pack -> capability chain).

    Packs are the unit of capability distribution. Instead of assigning
    individual capabilities to classes, administrators compose packs
    and assign the pack to a class.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_pack(self, params: PackCreate) -> PackResponse:
        """Create a new capability pack.

        WHY: Admin user journey — define a new pack for grouping capabilities.

        SIDE EFFECTS: Persists CapabilityPack row.
        RETURN: The created pack with server-generated id and timestamps.
        """
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
        """Get a single pack by ID.

        WHY: Admin UI — view pack details including capability and class counts.

        RAISES: PackNotFoundError if missing.
        """
        result = await self.db.execute(select(CapabilityPack).where(CapabilityPack.id == pack_id))
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
        """List packs with optional team namespace filter.

        WHY: Admin UI — browse all packs or filter by team.
        Uses offset/limit pagination and bulk-loads counts via
        _to_response_batch to avoid N+1 queries.
        """
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
        """Update all fields of an existing pack.

        WHY: Admin user journey — modify pack name, description, or namespace.
        Full-field replacement (not partial patch).

        RAISES: PackNotFoundError if missing.
        """
        result = await self.db.execute(select(CapabilityPack).where(CapabilityPack.id == pack_id))
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
        """Delete a pack by ID.

        WHY: Admin user journey — remove a pack.
        Note: Does NOT cascade-delete PackAssignment or AgentClassPack rows
        (those are separate join tables). The ORM cascade settings on the
        CapabilityPack model handle that.

        RAISES: PackNotFoundError if missing.
        """
        result = await self.db.execute(select(CapabilityPack).where(CapabilityPack.id == pack_id))
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
        """Assign a capability to a pack.

        WHY: Admin user journey — add a capability to a pack.
        Validates that the capability exists and is not already assigned.

        RAISES:
          - CapabilityNotFoundError if the capability_id doesn't exist.
          - DuplicateAssignmentError if the capability is already in the pack.
        SIDE EFFECTS: Creates a PackAssignment row.
        """
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
        """Remove a capability from a pack.

        WHY: Admin user journey — remove a capability from a pack.
        No-op if the assignment does not exist (idempotent removal).

        SIDE EFFECTS: Deletes the PackAssignment row if it exists.
        """
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
        """Assign a pack to an agent class.

        WHY: Admin user journey — grant a class access to all capabilities
        in the pack. This is the primary mechanism for capability authorization.

        Validates that the agent class exists and the assignment is not a duplicate.

        RAISES:
          - AgentClassNotFoundError if the agent_class_id doesn't exist.
          - DuplicateAssignmentError if the pack is already assigned to this class.
        SIDE EFFECTS: Creates an AgentClassPack row.
        """
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
        """Remove a pack assignment from an agent class.

        WHY: Admin user journey — revoke a class's access to a pack.
        No-op if the assignment does not exist (idempotent removal).

        SIDE EFFECTS: Deletes the AgentClassPack row if it exists.
        """
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
        """Clone an existing pack including all capability and class assignments.

        WHY: Admin user journey — create a variant of an existing pack
        (e.g., for a different team or environment). The clone copies
        all capability assignments and class assignments from the source.

        The clone is a deep copy of the pack structure:
          1. Create a new CapabilityPack with the source's description/namespace.
          2. Copy all PackAssignment rows (capabilities).
          3. Copy all AgentClassPack rows (class assignments).

        RAISES: PackNotFoundError if the source pack doesn't exist.
        SIDE EFFECTS: Creates CapabilityPack + multiple PackAssignment + AgentClassPack rows.
        """
        result = await self.db.execute(select(CapabilityPack).where(CapabilityPack.id == pack_id))
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

    async def get_usage_stats(self, pack_id: UUID) -> dict[str, Any]:
        """Return usage statistics for a pack.

        WHY: Admin insight — understand how much a pack is being used.
        Returns:
          - capabilities_count: number of capabilities in the pack
          - classes_count: number of agent classes using the pack
          - usage_count: number of AuditEvent rows with event_type='capability_request'
            referencing any capability in this pack

        The usage_count query uses json_extract to filter AuditEvent.details
        for the capability_id. This is a JSON path query and may be slow
        on large audit tables — consider adding a GIN index for production use.

        RAISES: PackNotFoundError if the pack doesn't exist.
        """
        from api.models.audit import AuditEvent

        result = await self.db.execute(select(CapabilityPack).where(CapabilityPack.id == pack_id))
        pack = result.scalar_one_or_none()
        if pack is None:
            raise PackNotFoundError(f"Pack {pack_id} not found")

        cap_count = (
            await self.db.execute(
                select(func.count(PackAssignment.id)).where(PackAssignment.pack_id == pack_id)
            )
        ).scalar() or 0

        class_count = (
            await self.db.execute(
                select(func.count(AgentClassPack.id)).where(AgentClassPack.pack_id == pack_id)
            )
        ).scalar() or 0

        cap_ids = (
            (
                await self.db.execute(
                    select(PackAssignment.capability_id).where(PackAssignment.pack_id == pack_id)
                )
            )
            .scalars()
            .all()
        )

        usage_count = 0
        if cap_ids:
            usage_count = (
                await self.db.execute(
                    select(func.count(AuditEvent.id)).where(
                        AuditEvent.event_type == "capability_request",
                        func.json_extract(AuditEvent.details, "$.capability_id").in_(
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

    async def get_security_metrics(self, pack_id: UUID) -> PackSecurityMetricsResponse:
        result = await self.db.execute(select(CapabilityPack).where(CapabilityPack.id == pack_id))
        pack = result.scalar_one_or_none()
        if pack is None:
            raise PackNotFoundError(f"Pack {pack_id} not found")

        rsvc = ResourceService(db=self.db)
        pack_counts = await rsvc.get_pack_resource_counts([pack_id])
        domain_counts = await rsvc.get_domain_resource_counts()

        resource_count = sum(pack_counts.values())
        total_in_domain = max(
            (domain_counts.get(dim, 0) for dim in pack_counts),
            default=0,
        )
        total_in_domain = max(total_in_domain, resource_count)

        if total_in_domain <= 1 or resource_count == 0:
            implied_catch_rate = 1.0
        else:
            implied_catch_rate = max(
                0.0, min(1.0, 1.0 - (resource_count - 1) / (total_in_domain - 1))
            )

        if resource_count == 0:
            warning_tier = "none"
        elif implied_catch_rate >= 1.0:
            warning_tier = "full"
        elif implied_catch_rate >= 0.97:
            warning_tier = "strong"
        elif implied_catch_rate >= 0.87:
            warning_tier = "moderate"
        elif implied_catch_rate >= 0.50:
            warning_tier = "reduced"
        else:
            warning_tier = "low"

        return PackSecurityMetricsResponse(
            id=pack.id,
            name=pack.name,
            resource_count=resource_count,
            total_resources_in_domain=total_in_domain,
            implied_catch_rate=round(implied_catch_rate, 4),
            warning_tier=warning_tier,
        )

    async def get_capabilities_for_class(
        self,
        agent_class_id: UUID,
    ) -> list[dict[str, Any]]:
        """Return all capabilities available to an agent class through its assigned packs.

        WHY: Used by auth_service.get_agent_capability_surface() to compute
        the capability surface for an agent identity. Also used by admin UI
        to show what capabilities a class has access to.

        Traverses: AgentClassPack -> CapabilityPack -> PackAssignment -> Capability.
        Uses selectinload to eagerly load the pack and its assignments in one query,
        avoiding N+1 queries for each class pack.

        RETURN: Sorted list of {id, name, domain} dicts.
        """
        from sqlalchemy.orm import selectinload

        result = await self.db.execute(
            select(AgentClassPack)
            .options(
                selectinload(AgentClassPack.pack).selectinload(CapabilityPack.pack_assignments)
            )
            .where(AgentClassPack.agent_class_id == agent_class_id)
        )
        class_packs = result.unique().scalars().all()
        cap_ids: set[UUID] = set()
        for acp in class_packs:
            for pa in acp.pack.pack_assignments:
                cap_ids.add(pa.capability_id)

        if not cap_ids:
            return []

        caps_result = await self.db.execute(select(Capability).where(Capability.id.in_(cap_ids)))
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
        """Convert multiple packs to responses with bulk-loaded counts.

        WHY: Performance optimization — when listing packs, this method loads
        counts for ALL packs in a single query each (2 queries total: one for
        cap counts, one for class counts) instead of 2 queries per pack.
        This is the classic N+1 query optimization pattern.
        """
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
                id=p.id,
                name=p.name,
                description=p.description,
                team_namespace=p.team_namespace,
                created_at=p.created_at,
                capabilities_count=cap_counts.get(p.id, 0),
                classes_count=class_counts.get(p.id, 0),
            )
            for p in packs
        ]

    async def _count_for_pack(self, pack_id: UUID) -> tuple[int, int]:
        """Return (capabilities_count, classes_count) for a given pack.

        Uses scalar subqueries with func.count and a WHERE filter.
        Both queries are indexed on the foreign key columns.
        """
        cap = (
            await self.db.execute(
                select(func.count(PackAssignment.id)).where(PackAssignment.pack_id == pack_id)
            )
        ).scalar() or 0
        cls = (
            await self.db.execute(
                select(func.count(AgentClassPack.id)).where(AgentClassPack.pack_id == pack_id)
            )
        ).scalar() or 0
        return cap, cls
