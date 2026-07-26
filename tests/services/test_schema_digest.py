from __future__ import annotations

import hashlib
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mcp import MCPClient
from api.models.capability import Capability
from api.models.server import CapabilityMapping, MCPServer, ServerTool
from api.schemas.capability import CapabilityMappingCreate
from api.schemas.server import ServerCreate
from api.services.capability_service import CapabilityService
from api.services.registry_service import RegistryService
from tests.fixtures.mcp_server import async_mock_server, create_mock_mcp_server


def _sha256(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


# Verifies that creating a capability mapping computes a SHA-256 digest from
# the tool's name, input_schema, and output_schema, and sets status="active".
@pytest.mark.asyncio
async def test_create_mapping_sets_digest_and_active(db_session: AsyncSession) -> None:
    server = MCPServer(name="s", endpoint="http://local/test")
    db_session.add(server)
    await db_session.flush()

    tool_schema: dict[str, Any] = {"type": "object", "properties": {"q": {"type": "string"}}}
    db_session.add(
        ServerTool(
            server_id=server.id,
            tool_name="search",
            description="",
            input_schema=tool_schema,
            output_schema=None,
        )
    )
    cap = Capability(name="code:search", status="active")
    db_session.add(cap)
    await db_session.commit()

    svc = CapabilityService(db_session)
    mapping = await svc.create_mapping(
        capability_id=cap.id,
        params=CapabilityMappingCreate(server_id=server.id, tool_name="search"),
    )

    result = (
        await db_session.execute(
            select(CapabilityMapping).where(CapabilityMapping.id == mapping.id)
        )
    ).scalar_one()
    assert result.status == "active"
    assert result.tool_schema_digest is not None and len(result.tool_schema_digest) == 64


# Full integration flow: starts a mock MCP server with a tool, creates a
# mapping (which records the digest), then changes the server's tool schema
# and runs registry_service.inspect(). Verifies that inspect detects the
# schema drift and marks the mapping as "stale".
@pytest.mark.asyncio
async def test_inspect_marks_mapping_stale_on_schema_change(
    db_session: AsyncSession,
) -> None:
    # Start mock MCP server with a tool "greet" and register it
    original_tools = [
        {"name": "greet", "description": "", "input_schema": {"type": "object", "properties": {}}},
    ]
    app = create_mock_mcp_server(tools=original_tools)
    async with async_mock_server(app) as url:
        reg = RegistryService(db=db_session, mcp_client=MCPClient())
        created = await reg.register(ServerCreate(name="srv", endpoint=url))
        srv = (
            await db_session.execute(select(MCPServer).where(MCPServer.id == created.id))
        ).scalar_one()

        # Create a capability and mapping (digest stored at creation time)
        cap = Capability(name="demo:greet", status="active")
        db_session.add(cap)
        await db_session.flush()
        cap_svc = CapabilityService(db_session)
        await cap_svc.create_mapping(
            capability_id=cap.id,
            params=CapabilityMappingCreate(server_id=srv.id, tool_name="greet"),
        )

        # Change the tool schema on the mock server, then inspect
        changed_tools = [
            {
                "name": "greet",
                "description": "",
                "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}},
            }
        ]
        app2 = create_mock_mcp_server(tools=changed_tools)
        async with async_mock_server(app2) as url2:
            srv.endpoint = url2
            await db_session.commit()
            await reg.inspect(srv.id)

    # Mapping should now be marked stale
    mapping = (
        await db_session.execute(
            select(CapabilityMapping)
            .where(CapabilityMapping.capability_id == cap.id)
            .where(CapabilityMapping.server_id == srv.id)
        )
    ).scalar_one()
    assert mapping.status == "stale"


# Verifies that the routing service compares stored digests against the
# current tool schema. When mapping 1's digest no longer matches (schema
# mutated), routing skips it and selects mapping 2 which is still valid.
@pytest.mark.asyncio
async def test_routing_skips_mismatch_digest_and_picks_valid(
    db_session: AsyncSession,
) -> None:
    # Two servers with same tool name, different schemas.
    s1 = MCPServer(name="a", endpoint="http://a")
    s2 = MCPServer(name="b", endpoint="http://b")
    db_session.add_all([s1, s2])
    await db_session.flush()

    tool_a = ServerTool(
        server_id=s1.id,
        tool_name="work",
        input_schema={"type": "object", "properties": {"v": {"type": "integer"}}},
        output_schema=None,
    )
    tool_b = ServerTool(
        server_id=s2.id,
        tool_name="work",
        input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
        output_schema=None,
    )
    db_session.add_all([tool_a, tool_b])
    cap = Capability(name="ops:work", status="active")
    db_session.add(cap)
    await db_session.commit()

    cap_svc = CapabilityService(db_session)
    # Create both mappings; both are active and have correct digests initially
    await cap_svc.create_mapping(cap.id, CapabilityMappingCreate(server_id=s1.id, tool_name="work"))
    m2 = await cap_svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=s2.id, tool_name="work")
    )

    # Raise routing weight on server 2 so it's preferred when both valid
    m2_row = (
        await db_session.execute(select(CapabilityMapping).where(CapabilityMapping.id == m2.id))
    ).scalar_one()
    m2_row.routing_weight = 2.0
    await db_session.commit()

    # Now mutate server 1's tool schema to cause digest mismatch while mapping remains active
    tool_a.input_schema = {"type": "object", "properties": {"v": {"type": "string"}}}
    await db_session.commit()

    from api.services.routing_service import RoutingService

    rsvc = RoutingService(db_session)
    picked = await rsvc.select_server(cap.id)
    # Should select mapping 2 (server b) since mapping 1 digest no longer matches
    assert picked.server_id == s2.id


# Verifies that when both mappings have stale digests (both tool schemas
# mutated), routing raises NoServerFoundError — no valid target exists.
@pytest.mark.asyncio
async def test_routing_no_valid_mappings_raises(db_session: AsyncSession) -> None:
    s1 = MCPServer(name="a2", endpoint="http://a2")
    s2 = MCPServer(name="b2", endpoint="http://b2")
    db_session.add_all([s1, s2])
    await db_session.flush()

    tool_a = ServerTool(
        server_id=s1.id,
        tool_name="work2",
        input_schema={"type": "object", "properties": {"v": {"type": "integer"}}},
        output_schema=None,
    )
    tool_b = ServerTool(
        server_id=s2.id,
        tool_name="work2",
        input_schema={"type": "object", "properties": {"q": {"type": "string"}}},
        output_schema=None,
    )
    db_session.add_all([tool_a, tool_b])
    cap = Capability(name="ops:work2", status="active")
    db_session.add(cap)
    await db_session.commit()

    cap_svc = CapabilityService(db_session)
    await cap_svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=s1.id, tool_name="work2")
    )
    await cap_svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=s2.id, tool_name="work2")
    )

    # Mutate both tool schemas so both digests mismatch
    tool_a.input_schema = {"type": "object", "properties": {"v": {"type": "string"}}}
    tool_b.input_schema = {"type": "object", "properties": {"q": {"type": "number"}}}
    await db_session.commit()

    from api.services.routing_service import NoServerFoundError, RoutingService

    rsvc = RoutingService(db_session)
    with pytest.raises(NoServerFoundError):
        await rsvc.select_server(cap.id)
