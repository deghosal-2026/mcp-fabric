"""Service for resource-dimension policy management.

Handles CRUD for:
  - Resource dimensions on capabilities (dimension_key, display_name)
  - Param-to-value mapping (source, param_path, constant_value)
  - Identity resource bindings (which values an agent may use)
  - Pack resource bindings (which values a pack permits)
"""

from uuid import UUID

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability
from api.models.resource import (
    DimensionValueMap,
    IdentityResourceBinding,
    PackResourceBinding,
    ResourceDimension,
)
from api.schemas.resource import (
    DimensionValueMapCreate,
    DimensionValueMapResponse,
    ResourceBindingBulkRequest,
    ResourceBindingResponse,
    ResourceDimensionCreate,
    ResourceDimensionResponse,
)


class ResourceNotFoundError(ValueError):
    """Raised when a resource dimension or binding is not found."""


class ResourceConflictError(ValueError):
    """Raised when a duplicate dimension or binding would be created."""


class ResourceService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_dimension(
        self, capability_id: UUID, body: ResourceDimensionCreate
    ) -> ResourceDimensionResponse:
        stmt = select(Capability).where(Capability.id == capability_id)
        result = await self.db.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise ResourceNotFoundError(f"Capability {capability_id} not found")

        try:
            dim = ResourceDimension(
                capability_id=capability_id,
                dimension_key=body.dimension_key,
                display_name=body.display_name,
            )
            self.db.add(dim)
            await self.db.commit()
            await self.db.refresh(dim)
            return ResourceDimensionResponse.model_validate(dim)
        except IntegrityError:
            await self.db.rollback()
            raise ResourceConflictError(
                f"Dimension '{body.dimension_key}' already exists for this capability"
            ) from None

    async def list_dimensions(self, capability_id: UUID) -> list[ResourceDimensionResponse]:
        stmt = (
            select(ResourceDimension)
            .where(ResourceDimension.capability_id == capability_id)
            .order_by(ResourceDimension.created_at)
        )
        result = await self.db.execute(stmt)
        dims = result.scalars().all()
        return [ResourceDimensionResponse.model_validate(d) for d in dims]

    async def delete_dimension(self, dimension_id: UUID) -> None:
        stmt = select(ResourceDimension).where(ResourceDimension.id == dimension_id)
        result = await self.db.execute(stmt)
        dim = result.scalar_one_or_none()
        if dim is None:
            raise ResourceNotFoundError(f"Resource dimension {dimension_id} not found")
        await self.db.delete(dim)
        await self.db.commit()

    async def set_value_map(
        self, dimension_id: UUID, body: DimensionValueMapCreate
    ) -> DimensionValueMapResponse:
        stmt = select(ResourceDimension).where(ResourceDimension.id == dimension_id)
        result = await self.db.execute(stmt)
        dim = result.scalar_one_or_none()
        if dim is None:
            raise ResourceNotFoundError(f"Resource dimension {dimension_id} not found")

        if body.source == "param" and not body.param_path:
            raise ValueError("param_path is required when source is 'param'")
        if body.source == "constant" and not body.constant_value:
            raise ValueError("constant_value is required when source is 'constant'")

        await self.db.execute(
            delete(DimensionValueMap).where(DimensionValueMap.resource_dimension_id == dimension_id)
        )
        mapping = DimensionValueMap(
            resource_dimension_id=dimension_id,
            source=body.source,
            param_path=body.param_path,
            constant_value=body.constant_value,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return DimensionValueMapResponse.model_validate(mapping)

    async def set_identity_bindings(
        self, identity_id: UUID, body: ResourceBindingBulkRequest
    ) -> list[ResourceBindingResponse]:
        await self.db.execute(
            delete(IdentityResourceBinding).where(
                IdentityResourceBinding.agent_identity_id == identity_id
            )
        )
        for b in body.bindings:
            self.db.add(
                IdentityResourceBinding(
                    agent_identity_id=identity_id,
                    dimension_key=b.dimension_key,
                    allowed_value=b.allowed_value,
                )
            )
        await self.db.commit()

        stmt = (
            select(IdentityResourceBinding)
            .where(IdentityResourceBinding.agent_identity_id == identity_id)
            .order_by(IdentityResourceBinding.dimension_key, IdentityResourceBinding.allowed_value)
        )
        result = await self.db.execute(stmt)
        return [ResourceBindingResponse.model_validate(r) for r in result.scalars().all()]

    async def list_identity_bindings(self, identity_id: UUID) -> list[ResourceBindingResponse]:
        stmt = (
            select(IdentityResourceBinding)
            .where(IdentityResourceBinding.agent_identity_id == identity_id)
            .order_by(IdentityResourceBinding.dimension_key, IdentityResourceBinding.allowed_value)
        )
        result = await self.db.execute(stmt)
        return [ResourceBindingResponse.model_validate(r) for r in result.scalars().all()]

    async def delete_identity_binding(self, binding_id: UUID) -> None:
        stmt = select(IdentityResourceBinding).where(IdentityResourceBinding.id == binding_id)
        result = await self.db.execute(stmt)
        binding = result.scalar_one_or_none()
        if binding is None:
            raise ResourceNotFoundError(f"Identity resource binding {binding_id} not found")
        await self.db.delete(binding)
        await self.db.commit()

    async def set_pack_bindings(
        self, pack_id: UUID, body: ResourceBindingBulkRequest
    ) -> list[ResourceBindingResponse]:
        await self.db.execute(
            delete(PackResourceBinding).where(PackResourceBinding.pack_id == pack_id)
        )
        for b in body.bindings:
            self.db.add(
                PackResourceBinding(
                    pack_id=pack_id,
                    dimension_key=b.dimension_key,
                    allowed_value=b.allowed_value,
                )
            )
        await self.db.commit()

        stmt = (
            select(PackResourceBinding)
            .where(PackResourceBinding.pack_id == pack_id)
            .order_by(PackResourceBinding.dimension_key, PackResourceBinding.allowed_value)
        )
        result = await self.db.execute(stmt)
        return [ResourceBindingResponse.model_validate(r) for r in result.scalars().all()]

    async def list_pack_bindings(self, pack_id: UUID) -> list[ResourceBindingResponse]:
        stmt = (
            select(PackResourceBinding)
            .where(PackResourceBinding.pack_id == pack_id)
            .order_by(PackResourceBinding.dimension_key, PackResourceBinding.allowed_value)
        )
        result = await self.db.execute(stmt)
        return [ResourceBindingResponse.model_validate(r) for r in result.scalars().all()]

    async def get_pack_resource_counts(self, pack_ids: list[UUID] | None) -> dict[str, int]:
        if not pack_ids:
            return {}
        stmt = (
            select(
                PackResourceBinding.dimension_key,
                func.count(func.distinct(PackResourceBinding.allowed_value)),
            )
            .where(PackResourceBinding.pack_id.in_(pack_ids))
            .group_by(PackResourceBinding.dimension_key)
        )
        result = await self.db.execute(stmt)
        counts: dict[str, int] = {}
        for row in result.all():
            counts[str(row[0])] = int(row[1])
        return counts

    async def get_domain_resource_counts(self) -> dict[str, int]:
        pack_stmt = select(
            PackResourceBinding.dimension_key,
            func.count(func.distinct(PackResourceBinding.allowed_value)),
        ).group_by(PackResourceBinding.dimension_key)
        pack_result = await self.db.execute(pack_stmt)
        pack_counts: dict[str, int] = {}
        for row in pack_result.all():
            pack_counts[str(row[0])] = int(row[1])

        identity_stmt = select(
            IdentityResourceBinding.dimension_key,
            func.count(func.distinct(IdentityResourceBinding.allowed_value)),
        ).group_by(IdentityResourceBinding.dimension_key)
        identity_result = await self.db.execute(identity_stmt)
        identity_counts: dict[str, int] = {}
        for row in identity_result.all():
            identity_counts[str(row[0])] = int(row[1])

        all_dims = set(pack_counts) | set(identity_counts)
        return {dim: max(pack_counts.get(dim, 0), identity_counts.get(dim, 0)) for dim in all_dims}

    async def get_pack_breadth(self) -> list[dict[str, object]]:
        from api.models.agent import AgentClass, AgentClassPack, CapabilityPack

        stmt = select(AgentClass).order_by(AgentClass.name)
        result = await self.db.execute(stmt)
        classes = result.scalars().all()

        if not classes:
            return []

        pack_stmt = select(
            AgentClassPack.agent_class_id,
            CapabilityPack.id,
        ).join(CapabilityPack, AgentClassPack.pack_id == CapabilityPack.id)
        pack_result = await self.db.execute(pack_stmt)
        class_pack_map: dict[UUID, list[UUID]] = {}
        for row in pack_result.all():
            class_pack_map.setdefault(row[0], []).append(row[1])

        all_pack_ids = list({pid for pids in class_pack_map.values() for pid in pids})
        pack_counts = await self.get_pack_resource_counts(all_pack_ids)
        domain_counts = await self.get_domain_resource_counts()

        rows: list[dict[str, object]] = []
        for cls in classes:
            pids = class_pack_map.get(cls.id, [])
            pack_count = len(pids)

            resources_covered = sum(pack_counts.get(str(pid), 0) for pid in pids)

            total_in_domain = max(
                (domain_counts.get(dim, 0) for dim in pack_counts),
                default=0,
            )
            total_in_domain = max(total_in_domain, resources_covered)

            if total_in_domain <= 1 or resources_covered == 0:
                catch_rate = 1.0
            else:
                catch_rate = max(
                    0.0, min(1.0, 1.0 - (resources_covered - 1) / (total_in_domain - 1))
                )

            rows.append(
                {
                    "agent_class_id": cls.id,
                    "agent_class_name": cls.name,
                    "pack_count": pack_count,
                    "resources_covered": resources_covered,
                    "total_resources_in_domain": total_in_domain,
                    "catch_rate": round(catch_rate, 4),
                }
            )

        return rows

    async def delete_pack_binding(self, binding_id: UUID) -> None:
        stmt = select(PackResourceBinding).where(PackResourceBinding.id == binding_id)
        result = await self.db.execute(stmt)
        binding = result.scalar_one_or_none()
        if binding is None:
            raise ResourceNotFoundError(f"Pack resource binding {binding_id} not found")
        await self.db.delete(binding)
        await self.db.commit()
