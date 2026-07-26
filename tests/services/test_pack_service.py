"""Tests for PackService: CRUD, capability assignment, class assignment, clone, stats."""

from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.pack import ClonePackRequest, PackAssignmentRequest, PackCreate
from api.services.pack_service import (
    CapabilityNotFoundError,
    DuplicateAssignmentError,
    PackNotFoundError,
    PackService,
)


@pytest.fixture
def pack_svc(db_session: AsyncSession) -> PackService:
    return PackService(db=db_session)


class TestPackCRUD:
    async def test_create_pack(self, pack_svc):
        pack = await pack_svc.create_pack(
            PackCreate(name="new-hire-pack", description="Tools for new hires")
        )
        assert pack.name == "new-hire-pack"
        assert pack.description == "Tools for new hires"
        assert pack.capabilities_count == 0

    async def test_get_pack(self, pack_svc):
        created = await pack_svc.create_pack(PackCreate(name="test-pack"))
        fetched = await pack_svc.get_pack(created.id)
        assert fetched.name == "test-pack"

    async def test_get_pack_not_found(self, pack_svc):
        with pytest.raises(PackNotFoundError):
            await pack_svc.get_pack(uuid4())

    async def test_list_packs(self, pack_svc):
        await pack_svc.create_pack(PackCreate(name="pack-a"))
        await pack_svc.create_pack(PackCreate(name="pack-b"))
        packs = await pack_svc.list_packs()
        assert len(packs) == 2

    async def test_list_packs_empty(self, pack_svc):
        assert await pack_svc.list_packs() == []

    async def test_list_packs_filters_by_team(self, pack_svc):
        await pack_svc.create_pack(PackCreate(name="platform-pack", team_namespace="team:platform"))
        await pack_svc.create_pack(PackCreate(name="sec-pack", team_namespace="team:security"))
        result = await pack_svc.list_packs(team_namespace="team:platform")
        assert len(result) == 1
        assert result[0].name == "platform-pack"

    async def test_update_pack(self, pack_svc):
        created = await pack_svc.create_pack(PackCreate(name="old-name"))
        updated = await pack_svc.update_pack(
            created.id, PackCreate(name="new-name", description="Updated")
        )
        assert updated.name == "new-name"
        assert updated.description == "Updated"

    async def test_update_pack_not_found(self, pack_svc):
        with pytest.raises(PackNotFoundError):
            await pack_svc.update_pack(uuid4(), PackCreate(name="nope"))

    async def test_delete_pack(self, pack_svc):
        created = await pack_svc.create_pack(PackCreate(name="to-delete"))
        await pack_svc.delete_pack(created.id)
        with pytest.raises(PackNotFoundError):
            await pack_svc.get_pack(created.id)

    async def test_delete_pack_not_found(self, pack_svc):
        with pytest.raises(PackNotFoundError):
            await pack_svc.delete_pack(uuid4())


class TestPackCapabilityAssignment:
    async def test_assign_capability(self, pack_svc, capability):
        pack = await pack_svc.create_pack(PackCreate(name="pack-with-cap"))
        await pack_svc.assign_capability(
            pack.id, PackAssignmentRequest(capability_id=capability.id)
        )
        fetched = await pack_svc.get_pack(pack.id)
        assert fetched.capabilities_count == 1

    async def test_assign_capability_not_found(self, pack_svc):
        pack = await pack_svc.create_pack(PackCreate(name="pack"))
        with pytest.raises(CapabilityNotFoundError):
            await pack_svc.assign_capability(pack.id, PackAssignmentRequest(capability_id=uuid4()))

    async def test_assign_capability_duplicate(self, pack_svc, capability):
        pack = await pack_svc.create_pack(PackCreate(name="pack"))
        await pack_svc.assign_capability(
            pack.id, PackAssignmentRequest(capability_id=capability.id)
        )
        with pytest.raises(DuplicateAssignmentError):
            await pack_svc.assign_capability(
                pack.id, PackAssignmentRequest(capability_id=capability.id)
            )

    async def test_remove_capability(self, pack_svc, capability):
        pack = await pack_svc.create_pack(PackCreate(name="pack"))
        await pack_svc.assign_capability(
            pack.id, PackAssignmentRequest(capability_id=capability.id)
        )
        await pack_svc.remove_capability(pack.id, capability.id)
        fetched = await pack_svc.get_pack(pack.id)
        assert fetched.capabilities_count == 0


class TestPackClassAssignment:
    async def test_assign_to_class(self, pack_svc, agent_class):
        pack = await pack_svc.create_pack(PackCreate(name="pack"))
        await pack_svc.assign_to_class(pack.id, agent_class.id)
        fetched = await pack_svc.get_pack(pack.id)
        assert fetched.classes_count == 1

    async def test_assign_to_class_duplicate(self, pack_svc, agent_class):
        pack = await pack_svc.create_pack(PackCreate(name="pack"))
        await pack_svc.assign_to_class(pack.id, agent_class.id)
        with pytest.raises(DuplicateAssignmentError):
            await pack_svc.assign_to_class(pack.id, agent_class.id)

    async def test_remove_from_class(self, pack_svc, agent_class):
        pack = await pack_svc.create_pack(PackCreate(name="pack"))
        await pack_svc.assign_to_class(pack.id, agent_class.id)
        await pack_svc.remove_from_class(pack.id, agent_class.id)
        fetched = await pack_svc.get_pack(pack.id)
        assert fetched.classes_count == 0


class TestPackClone:
    async def test_clone_pack(self, pack_svc, capability, agent_class):
        pack = await pack_svc.create_pack(PackCreate(name="original"))
        await pack_svc.assign_capability(
            pack.id, PackAssignmentRequest(capability_id=capability.id)
        )
        await pack_svc.assign_to_class(pack.id, agent_class.id)

        cloned = await pack_svc.clone_pack(pack.id, ClonePackRequest(name="cloned-pack"))
        assert cloned.name == "cloned-pack"
        assert cloned.capabilities_count == 1
        assert cloned.classes_count == 1
        assert cloned.id != pack.id

    async def test_clone_pack_not_found(self, pack_svc):
        with pytest.raises(PackNotFoundError):
            await pack_svc.clone_pack(uuid4(), ClonePackRequest(name="ghost-pack"))


class TestPackUsageStats:
    async def test_get_usage_stats(self, pack_svc):
        pack = await pack_svc.create_pack(PackCreate(name="usage-pack"))
        stats = await pack_svc.get_usage_stats(pack.id)
        assert stats["name"] == "usage-pack"
        assert stats["capabilities_count"] == 0
        assert stats["classes_count"] == 0
        assert stats["usage_count"] == 0

    async def test_get_usage_stats_with_data(self, pack_svc, capability, db_session: AsyncSession):
        from api.models.audit import AuditEvent

        pack = await pack_svc.create_pack(PackCreate(name="stats-pack"))
        await pack_svc.assign_capability(
            pack.id, PackAssignmentRequest(capability_id=capability.id)
        )
        db_session.add(
            AuditEvent(
                event_type="capability_request",
                actor_type="agent",
                actor_id="test-agent",
                target_type="capability",
                target_id=str(capability.id),
                details={"capability_id": str(capability.id)},
            )
        )
        db_session.add(
            AuditEvent(
                event_type="capability_request",
                actor_type="agent",
                actor_id="test-agent-2",
                target_type="capability",
                target_id=str(capability.id),
                details={"capability_id": str(capability.id)},
            )
        )
        await db_session.commit()
        stats = await pack_svc.get_usage_stats(pack.id)
        assert stats["name"] == "stats-pack"
        assert stats["capabilities_count"] == 1
        assert stats["usage_count"] == 2

    async def test_get_usage_stats_not_found(self, pack_svc):
        with pytest.raises(PackNotFoundError):
            await pack_svc.get_usage_stats(uuid4())


class TestPackCapabilitiesForClass:
    async def test_get_capabilities_for_class(self, pack_svc, capability, agent_class):
        pack = await pack_svc.create_pack(PackCreate(name="pack"))
        await pack_svc.assign_capability(
            pack.id, PackAssignmentRequest(capability_id=capability.id)
        )
        await pack_svc.assign_to_class(pack.id, agent_class.id)
        caps = await pack_svc.get_capabilities_for_class(agent_class.id)
        assert len(caps) == 1
        assert caps[0]["name"] == capability.name

    async def test_get_capabilities_for_class_empty(self, pack_svc, agent_class):
        caps = await pack_svc.get_capabilities_for_class(agent_class.id)
        assert caps == []


class TestPackSecurityMetrics:
    async def test_security_metrics_no_bindings(self, pack_svc):
        pack = await pack_svc.create_pack(PackCreate(name="no-bindings-pack"))
        metrics = await pack_svc.get_security_metrics(pack.id)
        assert metrics.resource_count == 0
        assert metrics.total_resources_in_domain == 0
        assert metrics.implied_catch_rate == 1.0
        assert metrics.warning_tier == "none"

    async def test_security_metrics_not_found(self, pack_svc):
        from api.services.pack_service import PackNotFoundError

        with pytest.raises(PackNotFoundError):
            await pack_svc.get_security_metrics(uuid4())
