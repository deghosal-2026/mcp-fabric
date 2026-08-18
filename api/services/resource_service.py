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
    #: Cohesion threshold; packs at/above this are flagged as a semantic band.
    BAND_THRESHOLD: float = 0.5

    def __init__(self, db: AsyncSession):
        self.db = db

    @staticmethod
    def _tokenize(value: str) -> set[str]:
        """Deterministic tokenization for cohesion: lowercase character 3-grams.

        Uses character n-grams (rather than word tokens) so it works on short
        resource values like ``staging``, ``staging-east`` or ``prod-1`` and is
        robust to hyphen/underscore separation. No external dependencies.
        """
        chars = "".join(c for c in value.lower() if c.isalnum())
        if len(chars) < 3:
            return {chars} if chars else set()
        return {chars[i : i + 3] for i in range(len(chars) - 2)}

    @classmethod
    def compute_cohesion(cls, values: list[str]) -> float:
        """Deterministic semantic cohesion = mean pairwise n-gram Jaccard similarity.

        A pack of resources that share tokens (e.g. ``staging-a``, ``staging-b``,
        ``staging-c``) yields a high score (tight semantic band); a scattered pack
        (e.g. ``staging``, ``prod``, ``eu-west``, ``db-shard``) yields a low score.
        Single/empty packs trivially have cohesion 1.0 (nothing to disperse).
        """
        if len(values) < 2:
            return 1.0

        grams = [cls._tokenize(v) for v in values]
        total = 0.0
        pairs = 0
        for i in range(len(grams)):
            for j in range(i + 1, len(grams)):
                a, b = grams[i], grams[j]
                if not a or not b:
                    continue
                intersection = len(a & b)
                if intersection == 0:
                    pairs += 1
                    continue
                union = len(a | b)
                total += intersection / union
                pairs += 1

        return total / pairs if pairs else 0.0

    @staticmethod
    def is_semantic_band(cohesion: float) -> bool:
        """True when a pack's resource members form a tight semantic cluster."""
        return cohesion >= ResourceService.BAND_THRESHOLD

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

    async def get_pack_cohesion(self) -> list[dict[str, object]]:
        """Per-pack cohesion score (independent of breadth) for the Trust Posture UI.

        Computes how tightly clustered each pack's resource members are. This is
        the second security axis: a tight semantic band of N resources is far more
        exposed to adversarial resource confusion than a scattered pack of the same
        size, even though the two share identical breadth (catch_rate).
        """
        from api.models.agent import CapabilityPack

        stmt = select(
            CapabilityPack.id,
            CapabilityPack.name,
            PackResourceBinding.allowed_value,
        ).join(PackResourceBinding, PackResourceBinding.pack_id == CapabilityPack.id)
        result = await self.db.execute(stmt)
        rows = result.all()

        # Ensure even bindless packs appear.
        pack_stmt = select(CapabilityPack.id, CapabilityPack.name)
        pack_result = await self.db.execute(pack_stmt)
        packs = pack_result.all()
        grouped: dict[UUID, list[str]] = {p.id: [] for p in packs}
        names: dict[UUID, str] = {p.id: p.name for p in packs}

        for pid, _name, value in rows:
            if pid in grouped:
                grouped[pid].append(value)

        computed: list[tuple[float, dict[str, object]]] = []
        for pid, values in grouped.items():
            cohesion = self.compute_cohesion(values)
            computed.append(
                (
                    cohesion,
                    {
                        "pack_id": pid,
                        "pack_name": names[pid],
                        "resource_count": len(set(values)),
                        "cohesion_score": round(cohesion, 4),
                        "is_semantic_band": self.is_semantic_band(cohesion),
                    },
                )
            )
        computed.sort(key=lambda t: t[0], reverse=True)
        return [row for _cohesion, row in computed]

    async def delete_pack_binding(self, binding_id: UUID) -> None:
        stmt = select(PackResourceBinding).where(PackResourceBinding.id == binding_id)
        result = await self.db.execute(stmt)
        binding = result.scalar_one_or_none()
        if binding is None:
            raise ResourceNotFoundError(f"Pack resource binding {binding_id} not found")
        await self.db.delete(binding)
        await self.db.commit()
