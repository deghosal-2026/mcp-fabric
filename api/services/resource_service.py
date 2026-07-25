"""Service for resource-dimension policy management.

Handles CRUD for:
  - Resource dimensions on capabilities (dimension_key, display_name)
  - Param-to-value mapping (source, param_path, constant_value)
  - Identity resource bindings (which values an agent may use)
  - Pack resource bindings (which values a pack permits)
"""

from uuid import UUID

from sqlalchemy import delete, select
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
            delete(DimensionValueMap).where(
                DimensionValueMap.resource_dimension_id == dimension_id
            )
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

    async def delete_pack_binding(self, binding_id: UUID) -> None:
        stmt = select(PackResourceBinding).where(PackResourceBinding.id == binding_id)
        result = await self.db.execute(stmt)
        binding = result.scalar_one_or_none()
        if binding is None:
            raise ResourceNotFoundError(f"Pack resource binding {binding_id} not found")
        await self.db.delete(binding)
        await self.db.commit()
