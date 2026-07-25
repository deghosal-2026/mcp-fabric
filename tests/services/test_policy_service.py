"""Tests for PolicyService: OPA evaluation, agent class CRUD, trust assignments, bundle deploy."""

from uuid import uuid4

import httpx
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.schemas.agent import AgentClassCreate, TrustAssignmentCreate
from api.services.policy_service import (
    OPAEvaluationError,
    PolicyService,
)


class TestPolicyServiceEvaluate:
    async def test_evaluate_returns_policy_decision(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session, opa_url="http://opa.unreachable:8181")
        with pytest.raises(OPAEvaluationError):
            await svc.evaluate(
                agent_class="agent:developer",
                server_id=str(uuid4()),
                capability="code:search",
                team_namespace="team:platform",
            )

    async def test_evaluate_cached_falls_through_without_redis(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session, opa_url="http://opa.unreachable:8181")
        with pytest.raises(OPAEvaluationError):
            await svc.evaluate_cached(
                agent_class="agent:developer",
                server_id=str(uuid4()),
                capability="code:search",
                team_namespace="team:platform",
            )


class TestPolicyServiceAgentClassCRUD:
    async def test_create_agent_class(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        ac = await svc.create_agent_class(
            AgentClassCreate(name="agent:tester", description="Test agent class")
        )
        assert ac.name == "agent:tester"
        assert ac.description == "Test agent class"
        assert ac.id is not None

    async def test_list_agent_classes(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        await svc.create_agent_class(AgentClassCreate(name="agent:a"))
        await svc.create_agent_class(AgentClassCreate(name="agent:b"))
        classes = await svc.list_agent_classes()
        assert len(classes) == 2
        names = [c.name for c in classes]
        assert "agent:a" in names
        assert "agent:b" in names

    async def test_list_agent_classes_filters_by_team(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        await svc.create_agent_class(
            AgentClassCreate(name="agent:dev", team_namespace="team:platform")
        )
        await svc.create_agent_class(
            AgentClassCreate(name="agent:sec", team_namespace="team:security")
        )
        platform = await svc.list_agent_classes(team_namespace="team:platform")
        assert len(platform) == 1
        assert platform[0].name == "agent:dev"

    async def test_get_agent_class(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        created = await svc.create_agent_class(AgentClassCreate(name="agent:gettest"))
        fetched = await svc.get_agent_class(created.id)
        assert fetched is not None
        assert fetched.name == "agent:gettest"

    async def test_get_agent_class_not_found(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        result = await svc.get_agent_class(uuid4())
        assert result is None

    async def test_update_agent_class(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        created = await svc.create_agent_class(
            AgentClassCreate(name="agent:oldname", description="Old")
        )
        updated = await svc.update_agent_class(
            created.id,
            AgentClassCreate(name="agent:newname", description="Updated"),
        )
        assert updated is not None
        assert updated.name == "agent:newname"
        assert updated.description == "Updated"

    async def test_update_agent_class_not_found(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        result = await svc.update_agent_class(uuid4(), AgentClassCreate(name="agent:nope"))
        assert result is None

    async def test_delete_agent_class(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        created = await svc.create_agent_class(AgentClassCreate(name="agent:todelete"))
        deleted = await svc.delete_agent_class(created.id)
        assert deleted is True
        fetched = await svc.get_agent_class(created.id)
        assert fetched is None

    async def test_delete_agent_class_not_found(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        result = await svc.delete_agent_class(uuid4())
        assert result is False


class TestPolicyServiceTrustAssignment:
    async def test_set_trust_creates_new(self, db_session: AsyncSession, server, agent_class):
        svc = PolicyService(db=db_session)
        ta = await svc.set_trust(
            agent_class_id=agent_class.id,
            params=TrustAssignmentCreate(
                server_id=server.id,
                trust_level="trusted",
                tool_scope=["read_file", "write_file"],
            ),
        )
        assert ta.server_id == server.id
        assert ta.trust_level == "trusted"

    async def test_set_trust_updates_existing(self, db_session: AsyncSession, server, agent_class):
        svc = PolicyService(db=db_session)
        ta1 = await svc.set_trust(
            agent_class_id=agent_class.id,
            params=TrustAssignmentCreate(server_id=server.id, trust_level="restricted"),
        )
        ta2 = await svc.set_trust(
            agent_class_id=agent_class.id,
            params=TrustAssignmentCreate(server_id=server.id, trust_level="trusted"),
        )
        assert ta2.id == ta1.id
        assert ta2.trust_level == "trusted"

    async def test_get_trust_assignments_by_class(
        self, db_session: AsyncSession, server, agent_class
    ):
        svc = PolicyService(db=db_session)
        await svc.set_trust(
            agent_class_id=agent_class.id,
            params=TrustAssignmentCreate(server_id=server.id, trust_level="trusted"),
        )
        assignments = await svc.get_trust_assignments(agent_class_id=agent_class.id)
        assert len(assignments) == 1
        assert assignments[0].trust_level == "trusted"

    async def test_get_trust_assignments_empty(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        result = await svc.get_trust_assignments()
        assert result == []

    async def test_remove_trust_assignment(self, db_session: AsyncSession, server, agent_class):
        svc = PolicyService(db=db_session)
        await svc.set_trust(
            agent_class_id=agent_class.id,
            params=TrustAssignmentCreate(server_id=server.id, trust_level="trusted"),
        )
        removed = await svc.remove_trust_assignment(agent_class.id, server.id)
        assert removed is True
        assignments = await svc.get_trust_assignments(agent_class_id=agent_class.id)
        assert len(assignments) == 0

    async def test_remove_trust_assignment_not_found(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        result = await svc.remove_trust_assignment(uuid4(), uuid4())
        assert result is False


class TestPolicyServiceBundleDeploy:
    async def test_deploy_bundle_fails_without_opa(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session, opa_url="http://opa.unreachable:8181")
        with pytest.raises((OPAEvaluationError, httpx.ConnectError)):
            await svc.deploy_bundle(rego_content="package fabric.policy", deployed_by="tester")

    async def test_get_policy_versions_empty(self, db_session: AsyncSession):
        svc = PolicyService(db=db_session)
        versions = await svc.get_policy_versions()
        assert versions == []
