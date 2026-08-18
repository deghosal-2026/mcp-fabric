"""Integration tests for resource dimension management and policy enforcement.

Tests the full resource-aware policy pipeline end-to-end:
  1. Create capability, add resource dimensions
  2. Set value mapping (param extraction + constant)
  3. Bind resource values to identity and pack
  4. Verify merge_bindings intersection logic
  5. Verify resolve_resources extracts values correctly
  6. Verify resource validation in OPA via RoutingService
"""

from typing import cast

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.agent import AgentClass, AgentIdentity, CapabilityPack
from api.models.capability import Capability
from api.models.resource import (
    DimensionValueMap,
    IdentityResourceBinding,
    PackResourceBinding,
)
from api.schemas.resource import (
    DimensionValueMapCreate,
    ResourceBindingBulkRequest,
    ResourceBindingValue,
    ResourceDimensionCreate,
)
from api.services.resource_service import ResourceNotFoundError, ResourceService


@pytest.mark.asyncio
async def test_create_and_list_dimensions(db_session: AsyncSession):
    cap = Capability(name="test:dimensions", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    created = await svc.create_dimension(
        cap.id, ResourceDimensionCreate(dimension_key="env", display_name="Environment")
    )
    assert created.dimension_key == "env"
    assert created.display_name == "Environment"
    assert created.capability_id == cap.id

    dims = await svc.list_dimensions(cap.id)
    assert len(dims) == 1
    assert dims[0].dimension_key == "env"

    # List for a capability with no dimensions returns empty
    cap2 = Capability(name="test:no-dims", domain="test")
    db_session.add(cap2)
    await db_session.commit()
    await db_session.refresh(cap2)
    empty = await svc.list_dimensions(cap2.id)
    assert len(empty) == 0


@pytest.mark.asyncio
async def test_delete_dimension(db_session: AsyncSession):
    cap = Capability(name="test:delete-dim", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    dim = await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="env"))
    await svc.delete_dimension(dim.id)

    dims = await svc.list_dimensions(cap.id)
    assert len(dims) == 0

    with pytest.raises(ResourceNotFoundError):
        await svc.delete_dimension(dim.id)


@pytest.mark.asyncio
async def test_value_map_param_extraction(db_session: AsyncSession):
    cap = Capability(name="test:value-map", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    dim = await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="env"))

    mapping = await svc.set_value_map(
        dim.id,
        DimensionValueMapCreate(source="param", param_path="params.deploy.env"),
    )
    assert mapping.source == "param"
    assert mapping.param_path == "params.deploy.env"
    assert mapping.resource_dimension_id == dim.id

    stmt = select(DimensionValueMap).where(DimensionValueMap.resource_dimension_id == dim.id)
    result = await db_session.execute(stmt)
    rows = result.scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_value_map_constant(db_session: AsyncSession):
    cap = Capability(name="test:const-map", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    dim = await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="tenant"))

    mapping = await svc.set_value_map(
        dim.id,
        DimensionValueMapCreate(source="constant", constant_value="acme-corp"),
    )
    assert mapping.source == "constant"
    assert mapping.constant_value == "acme-corp"


@pytest.mark.asyncio
async def test_identity_resource_bindings_crud(db_session: AsyncSession):
    ac = AgentClass(name="agent:test-bindings")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)

    identity = AgentIdentity(
        name="test-identity",
        agent_class_id=ac.id,
        token_hash="test-hash",
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    svc = ResourceService(db=db_session)

    # Set bindings (bulk replace)
    bindings = await svc.set_identity_bindings(
        identity.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="staging"),
                ResourceBindingValue(dimension_key="env", allowed_value="dev"),
                ResourceBindingValue(dimension_key="tenant", allowed_value="acme-corp"),
            ]
        ),
    )
    assert len(bindings) == 3

    # List bindings
    listed = await svc.list_identity_bindings(identity.id)
    assert len(listed) == 3

    # Bulk replace removes old and adds new
    bindings2 = await svc.set_identity_bindings(
        identity.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="staging"),
            ]
        ),
    )
    assert len(bindings2) == 1
    assert bindings2[0].allowed_value == "staging"

    # Delete binding
    await svc.delete_identity_binding(bindings2[0].id)
    listed2 = await svc.list_identity_bindings(identity.id)
    assert len(listed2) == 0

    with pytest.raises(ResourceNotFoundError):
        await svc.delete_identity_binding(bindings2[0].id)


@pytest.mark.asyncio
async def test_pack_resource_bindings_crud(db_session: AsyncSession):
    pack = CapabilityPack(name="test-pack-bindings")
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)

    svc = ResourceService(db=db_session)

    bindings = await svc.set_pack_bindings(
        pack.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="staging"),
                ResourceBindingValue(dimension_key="env", allowed_value="prod"),
            ]
        ),
    )
    assert len(bindings) == 2

    listed = await svc.list_pack_bindings(pack.id)
    assert len(listed) == 2

    await svc.delete_pack_binding(listed[0].id)
    listed2 = await svc.list_pack_bindings(pack.id)
    assert len(listed2) == 1

    with pytest.raises(ResourceNotFoundError):
        await svc.delete_pack_binding(listed[0].id)


@pytest.mark.asyncio
async def test_merge_bindings_intersection(db_session: AsyncSession):
    """Verify that merge_bindings computes identity ∩ pack intersection."""
    ac = AgentClass(name="agent:test-intersection")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)

    identity = AgentIdentity(
        name="intersection-identity",
        agent_class_id=ac.id,
        token_hash="test-hash-2",
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    pack = CapabilityPack(name="intersection-pack")
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)

    svc = ResourceService(db=db_session)

    # Identity allows env: [staging, prod]
    await svc.set_identity_bindings(
        identity.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="staging"),
                ResourceBindingValue(dimension_key="env", allowed_value="prod"),
            ]
        ),
    )

    # Pack allows env: [staging] — stricter
    await svc.set_pack_bindings(
        pack.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="staging"),
            ]
        ),
    )

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    merged = await routing.merge_bindings(identity.id, [pack.id])

    assert "env" in merged
    assert merged["env"] == ["staging"]
    assert "prod" not in merged["env"]


@pytest.mark.asyncio
async def test_resolve_resources_from_params(db_session: AsyncSession):
    """Test that resolve_resources extracts values from params via value_map."""
    cap = Capability(name="test:resolve-params", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    dim = await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="env"))
    await svc.set_value_map(dim.id, DimensionValueMapCreate(source="param", param_path="env"))
    await db_session.commit()

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    resources = await routing.resolve_resources(
        cap.id,
        {"env": "staging", "query": "test"},
        None,
    )
    assert resources == {"env": "staging"}


@pytest.mark.asyncio
async def test_resolve_resources_fallback_to_explicit(db_session: AsyncSession):
    """Test that resolve_resources falls back to the explicit resources field."""
    cap = Capability(name="test:resolve-explicit", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="env"))
    # No value_map set — will fall back to explicit resources
    await db_session.commit()

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    resources = await routing.resolve_resources(
        cap.id,
        {"query": "test"},
        {"env": "staging"},
    )
    assert resources == {"env": "staging"}


@pytest.mark.asyncio
async def test_resolve_resources_missing_dimension_raises(db_session: AsyncSession):
    """Test that resolve_resources raises when a declared dimension has no value."""
    cap = Capability(name="test:resolve-missing", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="env"))
    await db_session.commit()

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    with pytest.raises(ValueError, match="Missing value for resource dimension"):
        await routing.resolve_resources(
            cap.id,
            {"query": "test"},
            None,
        )


@pytest.mark.asyncio
async def test_resolve_resources_no_dimensions_returns_empty(db_session: AsyncSession):
    """Test that a capability with no declared dimensions returns empty dict."""
    cap = Capability(name="test:no-dims-resolve", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    resources = await routing.resolve_resources(cap.id, {"query": "test"}, None)
    assert resources == {}


@pytest.mark.asyncio
async def test_resource_dimension_deletes_cascade_to_value_maps(db_session: AsyncSession):
    """Deleting a ResourceDimension cascades to its DimensionValueMap rows."""
    cap = Capability(name="test:cascade-map", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    dim = await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="env"))
    await svc.set_value_map(
        dim.id, DimensionValueMapCreate(source="constant", constant_value="prod")
    )
    await db_session.commit()

    await svc.delete_dimension(dim.id)

    stmt = select(DimensionValueMap).where(DimensionValueMap.resource_dimension_id == dim.id)
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_identity_bindings_cascade_on_identity_delete(db_session: AsyncSession):
    """Deleting an AgentIdentity cascades to its IdentityResourceBinding rows."""
    ac = AgentClass(name="agent:cascade-test")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)

    identity = AgentIdentity(
        name="cascade-identity",
        agent_class_id=ac.id,
        token_hash="cascade-hash",
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    svc = ResourceService(db=db_session)
    await svc.set_identity_bindings(
        identity.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="staging"),
            ]
        ),
    )

    await db_session.delete(identity)
    await db_session.commit()

    stmt = select(IdentityResourceBinding).where(
        IdentityResourceBinding.agent_identity_id == identity.id
    )
    result = await db_session.execute(stmt)
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_merge_bindings_pack_only(db_session: AsyncSession):
    """Verify merge_bindings works with pack bindings and no identity bindings."""
    pack = CapabilityPack(name="pack-only-test")
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)

    svc = ResourceService(db=db_session)
    await svc.set_pack_bindings(
        pack.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="staging"),
            ]
        ),
    )

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    merged = await routing.merge_bindings(identity_id=None, pack_ids=[pack.id])

    assert "env" in merged
    assert merged["env"] == ["staging"]


@pytest.mark.asyncio
async def test_merge_bindings_identity_only(db_session: AsyncSession):
    """Verify merge_bindings works with identity bindings and no pack bindings."""
    ac = AgentClass(name="agent:identity-only")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)

    identity = AgentIdentity(
        name="identity-only",
        agent_class_id=ac.id,
        token_hash="identity-hash",
    )
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    svc = ResourceService(db=db_session)
    await svc.set_identity_bindings(
        identity.id,
        ResourceBindingBulkRequest(
            bindings=[
                ResourceBindingValue(dimension_key="env", allowed_value="prod"),
            ]
        ),
    )

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    merged = await routing.merge_bindings(identity_id=identity.id, pack_ids=None)

    assert "env" in merged
    assert merged["env"] == ["prod"]


@pytest.mark.asyncio
async def test_giant_pack_zero_protection_is_expected(db_session: AsyncSession):
    """P=R=512: giant pack with all resource bindings → catch rate = 0.0

    Demonstrates the intra-pack confused-deputy residual: when a pack
    covers every resource in a domain, resource-aware policy provides
    zero protection against confused-deputy attacks within the pack.
    """
    n = 512
    mutations = 1000

    cap = Capability(name="test:giant-pack", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="tool"))

    ac = AgentClass(name="agent:giant-pack")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)

    identity = AgentIdentity(name="giant-pack-id", agent_class_id=ac.id, token_hash="ghp")
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    pack = CapabilityPack(name="giant-pack-pack")
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)

    values = [
        ResourceBindingValue(dimension_key="tool", allowed_value=f"tool-{i}") for i in range(n)
    ]
    await svc.set_identity_bindings(identity.id, ResourceBindingBulkRequest(bindings=values))
    await svc.set_pack_bindings(pack.id, ResourceBindingBulkRequest(bindings=values))

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    merged = await routing.merge_bindings(identity_id=identity.id, pack_ids=[pack.id])

    assert "tool" in merged
    assert len(merged["tool"]) == n

    import random

    random.seed(42)
    blocked = 0
    for _ in range(mutations):
        resource = f"tool-{random.randint(0, n - 1)}"
        if resource not in merged["tool"]:
            blocked += 1

    assert blocked == 0
    catch = blocked / mutations
    formula_catch = 1.0 - (n - 1) / (n - 1)
    assert catch == formula_catch == 0.0


@pytest.mark.asyncio
async def test_per_resource_identity_full_close(db_session: AsyncSession):
    """P=1: narrow pack with single resource binding → catch rate = 1.0

    Mirror of the giant-pack test: when identity and pack both bind
    exactly one resource, every confused-deputy request outside that
    resource is blocked.
    """
    n = 512
    mutations = 1000

    cap = Capability(name="test:per-resource", domain="test")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)

    svc = ResourceService(db=db_session)
    await svc.create_dimension(cap.id, ResourceDimensionCreate(dimension_key="tool"))

    ac = AgentClass(name="agent:per-resource")
    db_session.add(ac)
    await db_session.commit()
    await db_session.refresh(ac)

    identity = AgentIdentity(name="per-resource-id", agent_class_id=ac.id, token_hash="prh")
    db_session.add(identity)
    await db_session.commit()
    await db_session.refresh(identity)

    pack = CapabilityPack(name="per-resource-pack")
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)

    await svc.set_identity_bindings(
        identity.id,
        ResourceBindingBulkRequest(
            bindings=[ResourceBindingValue(dimension_key="tool", allowed_value="tool-0")]
        ),
    )
    await svc.set_pack_bindings(
        pack.id,
        ResourceBindingBulkRequest(
            bindings=[ResourceBindingValue(dimension_key="tool", allowed_value="tool-0")]
        ),
    )

    from api.services.routing_service import RoutingService

    routing = RoutingService(db=db_session)
    merged = await routing.merge_bindings(identity_id=identity.id, pack_ids=[pack.id])

    assert "tool" in merged
    assert len(merged["tool"]) == 1
    assert merged["tool"] == ["tool-0"]

    import random

    random.seed(43)
    blocked = 0
    for _ in range(mutations):
        resource = f"tool-{random.randint(1, n)}"
        if resource not in merged["tool"]:
            blocked += 1

    assert blocked == mutations
    catch = blocked / mutations
    formula_catch = 1.0 - (1 - 1) / (n - 1)
    assert catch == formula_catch == 1.0


@pytest.mark.asyncio
async def test_pack_breadth_empty(db_session: AsyncSession):
    """No classes or packs → empty list."""
    svc = ResourceService(db=db_session)
    result = await svc.get_pack_breadth()
    assert result == []


@pytest.mark.asyncio
async def test_pack_breadth_with_class_and_pack(db_session: AsyncSession):
    """Class with one pack and no bindings → catch=1.0, pack_count=1."""
    cls = AgentClass(name="test-pack-breadth-class")
    db_session.add(cls)
    await db_session.commit()
    await db_session.refresh(cls)

    pack = CapabilityPack(name="bp-pack")
    db_session.add(pack)
    await db_session.commit()
    await db_session.refresh(pack)

    from api.models.agent import AgentClassPack

    db_session.add(AgentClassPack(agent_class_id=cls.id, pack_id=pack.id))
    await db_session.commit()

    svc = ResourceService(db=db_session)
    result = await svc.get_pack_breadth()
    assert len(result) == 1
    row = result[0]
    assert row["agent_class_name"] == "test-pack-breadth-class"
    assert row["pack_count"] == 1
    assert row["resources_covered"] == 0
    assert row["total_resources_in_domain"] == 0
    assert row["catch_rate"] == 1.0


@pytest.mark.asyncio
async def test_compute_cohesion_separates_scattered_from_band(db_session: AsyncSession):
    """A tight semantic band scores far higher than a scattered pack of the same size."""
    svc = ResourceService(db=db_session)

    scattered = svc.compute_cohesion(
        ["staging", "prod", "eu-west", "us-east", "ap-south", "db-shard", "cache", "auth"]
    )
    band = svc.compute_cohesion(
        [
            "staging-a",
            "staging-b",
            "staging-c",
            "staging-d",
            "staging-e",
            "staging-f",
            "staging-g",
            "staging-h",
        ]
    )

    assert band > scattered
    assert svc.is_semantic_band(band)
    assert not svc.is_semantic_band(scattered)


@pytest.mark.asyncio
async def test_compute_cohesion_single_and_empty(db_session: AsyncSession):
    """Single/empty packs are trivially cohesive (nothing to disperse)."""
    svc = ResourceService(db=db_session)
    assert svc.compute_cohesion([]) == 1.0
    assert svc.compute_cohesion(["only-resource"]) == 1.0


@pytest.mark.asyncio
async def test_get_pack_cohesion_reports_band(db_session: AsyncSession):
    """Two same-size packs — scattered vs tight band — are clearly separated."""
    scattered = CapabilityPack(name="scattered-pack")
    band = CapabilityPack(name="band-pack")
    db_session.add_all([scattered, band])
    await db_session.commit()
    await db_session.refresh(scattered)
    await db_session.refresh(band)

    db_session.add_all(
        [
            PackResourceBinding(pack_id=scattered.id, dimension_key="env", allowed_value="staging"),
            PackResourceBinding(pack_id=scattered.id, dimension_key="env", allowed_value="prod"),
            PackResourceBinding(pack_id=scattered.id, dimension_key="env", allowed_value="eu-west"),
            PackResourceBinding(pack_id=band.id, dimension_key="env", allowed_value="staging-a"),
            PackResourceBinding(pack_id=band.id, dimension_key="env", allowed_value="staging-b"),
            PackResourceBinding(pack_id=band.id, dimension_key="env", allowed_value="staging-c"),
        ]
    )
    await db_session.commit()

    svc = ResourceService(db=db_session)
    result = await svc.get_pack_cohesion()
    band_row = next(r for r in result if r["pack_name"] == "band-pack")
    scatter_row = next(r for r in result if r["pack_name"] == "scattered-pack")

    assert band_row["is_semantic_band"] is True
    assert scatter_row["is_semantic_band"] is False
    assert float(cast(float, band_row["cohesion_score"])) > float(
        cast(float, scatter_row["cohesion_score"])
    )
    assert band_row["resource_count"] == 3
    assert scatter_row["resource_count"] == 3
