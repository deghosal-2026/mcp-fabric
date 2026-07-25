"""Comprehensive model validation tests.

Tests cover JSONB compatibility, relationship loading, and
cascade delete behavior across all ORM models.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from api.models.agent import (
    AgentClass,
    AgentClassPack,
    AgentIdentity,
    CapabilityPack,
    PackAssignment,
    TrustAssignment,
)
from api.models.capability import Capability, CapabilityAlias
from api.models.server import CapabilityMapping, MCPServer, ServerTool, ToolVersion


class TestJSONBCompatibility:
    """Verify JSON/B column read, write, query, default, and update."""

    async def test_jsonb_labels_read_write(self, db_session, server):
        assert server.labels == ["production"]

    async def test_jsonb_input_schema(self, db_session, tool):
        assert tool.input_schema == {"type": "object", "properties": {"x": {"type": "string"}}}

    async def test_jsonb_query_labels_contains(self, db_session, server):
        result = await db_session.execute(select(MCPServer).where(MCPServer.name == "test-server"))
        srv = result.scalar_one()
        assert "production" in srv.labels
        assert srv.labels[0] == "production"

    async def test_jsonb_null_defaults(self, db_session):
        srv = MCPServer(
            name="no-labels-server",
            endpoint="https://example.com/mcp",
        )
        db_session.add(srv)
        await db_session.commit()

        result = await db_session.execute(
            select(MCPServer).where(MCPServer.name == "no-labels-server")
        )
        fetched = result.scalar_one()
        assert fetched.labels == []

    async def test_jsonb_update_in_place(self, db_session, server):
        server.labels = ["production", "staging"]
        await db_session.commit()
        await db_session.refresh(server)
        assert server.labels == ["production", "staging"]


class TestRelationshipLoading:
    """Verify bidirectional relationship loading across models."""

    async def test_server_tools_relationship(self, db_session, server, tool):
        stmt = (
            select(MCPServer)
            .where(MCPServer.id == server.id)
            .options(selectinload(MCPServer.tools))
        )
        result = await db_session.execute(stmt)
        srv = result.scalar_one()
        assert len(srv.tools) == 1
        assert srv.tools[0].tool_name == "test_tool"

    async def test_tool_server_backref(self, db_session, server, tool):
        stmt = (
            select(ServerTool)
            .where(ServerTool.id == tool.id)
            .options(selectinload(ServerTool.server))
        )
        result = await db_session.execute(stmt)
        t = result.scalar_one()
        assert t.server.name == "test-server"

    async def test_capability_mappings_relationship(self, db_session, server, capability):
        mapping = CapabilityMapping(
            capability_id=capability.id,
            server_id=server.id,
            tool_name="test_tool",
        )
        db_session.add(mapping)
        await db_session.commit()

        stmt = (
            select(Capability)
            .where(Capability.id == capability.id)
            .options(selectinload(Capability.mappings))
        )
        result = await db_session.execute(stmt)
        cap = result.scalar_one()
        assert len(cap.mappings) == 1

    async def test_agent_class_identities(self, db_session, agent_class):
        identity = AgentIdentity(
            name=f"test-identity-{uuid.uuid4()}",
            agent_class_id=agent_class.id,
            token_hash="fakehash",
            token_prefix="test",
        )
        db_session.add(identity)
        await db_session.commit()

        stmt = (
            select(AgentClass)
            .where(AgentClass.id == agent_class.id)
            .options(selectinload(AgentClass.agent_identities))
        )
        result = await db_session.execute(stmt)
        ac = result.scalar_one()
        assert len(ac.agent_identities) == 1

    async def test_agent_class_trust_assignments(self, db_session, agent_class, server):
        ta = TrustAssignment(
            agent_class_id=agent_class.id,
            server_id=server.id,
            trust_level="trusted",
        )
        db_session.add(ta)
        await db_session.commit()

        stmt = (
            select(AgentClass)
            .where(AgentClass.id == agent_class.id)
            .options(selectinload(AgentClass.trust_assignments))
        )
        result = await db_session.execute(stmt)
        ac = result.scalar_one()
        assert len(ac.trust_assignments) == 1

    async def test_pack_assignments(self, db_session, pack, capability):
        pa = PackAssignment(pack_id=pack.id, capability_id=capability.id)
        db_session.add(pa)
        await db_session.commit()

        stmt = (
            select(CapabilityPack)
            .where(CapabilityPack.id == pack.id)
            .options(selectinload(CapabilityPack.pack_assignments))
        )
        result = await db_session.execute(stmt)
        fetched = result.scalar_one()
        assert len(fetched.pack_assignments) == 1

    async def test_class_packs(self, db_session, agent_class, pack):
        cp = AgentClassPack(agent_class_id=agent_class.id, pack_id=pack.id)
        db_session.add(cp)
        await db_session.commit()

        stmt = (
            select(AgentClass)
            .where(AgentClass.id == agent_class.id)
            .options(selectinload(AgentClass.class_packs))
        )
        result = await db_session.execute(stmt)
        ac = result.scalar_one()
        assert len(ac.class_packs) == 1

    async def test_server_mapping_cascade(self, db_session, server, capability):
        mapping = CapabilityMapping(
            capability_id=capability.id,
            server_id=server.id,
            tool_name="test_tool",
        )
        db_session.add(mapping)
        await db_session.commit()

        await db_session.delete(server)
        await db_session.commit()

        result = await db_session.execute(
            select(CapabilityMapping).where(CapabilityMapping.server_id == server.id)
        )
        assert result.scalar_one_or_none() is None


class TestCascadeDeletes:
    """Verify CASCADE deletes propagate correctly across FKs."""

    async def test_delete_server_cascades_to_tools(self, db_session, server, tool):
        await db_session.delete(server)
        await db_session.commit()

        result = await db_session.execute(
            select(ServerTool).where(ServerTool.server_id == server.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_server_cascades_to_tool_versions(self, db_session, server):
        tv = ToolVersion(
            server_id=server.id,
            tool_name="test_tool",
            input_schema={"type": "object"},
        )
        db_session.add(tv)
        await db_session.commit()

        await db_session.delete(server)
        await db_session.commit()

        result = await db_session.execute(
            select(ToolVersion).where(ToolVersion.server_id == server.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_capability_cascades_to_mappings(self, db_session, server, capability):
        mapping = CapabilityMapping(
            capability_id=capability.id,
            server_id=server.id,
            tool_name="test_tool",
        )
        db_session.add(mapping)
        await db_session.commit()

        await db_session.delete(capability)
        await db_session.commit()

        result = await db_session.execute(
            select(CapabilityMapping).where(CapabilityMapping.capability_id == capability.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_capability_cascades_to_aliases(self, db_session, capability):
        alias = CapabilityAlias(capability_id=capability.id, alias="code:find")
        db_session.add(alias)
        await db_session.commit()

        await db_session.delete(capability)
        await db_session.commit()

        result = await db_session.execute(
            select(CapabilityAlias).where(CapabilityAlias.capability_id == capability.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_pack_cascades_to_assignments(self, db_session, pack, capability):
        pa = PackAssignment(pack_id=pack.id, capability_id=capability.id)
        db_session.add(pa)
        await db_session.commit()

        await db_session.delete(pack)
        await db_session.commit()

        result = await db_session.execute(
            select(PackAssignment).where(PackAssignment.pack_id == pack.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_class_cascades_to_class_packs(self, db_session, agent_class, pack):
        cp = AgentClassPack(agent_class_id=agent_class.id, pack_id=pack.id)
        db_session.add(cp)
        await db_session.commit()

        await db_session.delete(agent_class)
        await db_session.commit()

        result = await db_session.execute(
            select(AgentClassPack).where(AgentClassPack.agent_class_id == agent_class.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_class_cascades_to_identities(self, db_session, agent_class):
        identity = AgentIdentity(
            name=f"cascade-test-{uuid.uuid4()}",
            agent_class_id=agent_class.id,
            token_hash="fakehash",
            token_prefix="test",
        )
        db_session.add(identity)
        await db_session.commit()

        await db_session.delete(agent_class)
        await db_session.commit()

        result = await db_session.execute(
            select(AgentIdentity).where(AgentIdentity.agent_class_id == agent_class.id)
        )
        assert result.scalar_one_or_none() is None

    async def test_delete_class_cascades_to_trust(self, db_session, agent_class, server):
        ta = TrustAssignment(
            agent_class_id=agent_class.id,
            server_id=server.id,
            trust_level="trusted",
        )
        db_session.add(ta)
        await db_session.commit()

        await db_session.delete(agent_class)
        await db_session.commit()

        result = await db_session.execute(
            select(TrustAssignment).where(TrustAssignment.agent_class_id == agent_class.id)
        )
        assert result.scalar_one_or_none() is None
