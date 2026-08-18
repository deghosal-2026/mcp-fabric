"""Tests for many-to-one capability-mapping collision detection (#441).

When multiple distinct tools (different name or schema) map to the same
normalized capability, the system must detect the collision and gate
it behind admin review before it becomes routable.
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability as CapabilityModel
from api.models.server import MCPServer, ServerTool
from api.schemas.capability import CapabilityMappingCreate
from api.services.capability_service import CapabilityService


async def _setup(db_session: AsyncSession) -> tuple[CapabilityModel, MCPServer, ServerTool]:
    cap = CapabilityModel(name="collision:test", domain="test")
    server = MCPServer(name="collision-server", endpoint="http://localhost:9999")
    db_session.add_all([cap, server])
    await db_session.commit()
    await db_session.refresh(cap)
    await db_session.refresh(server)
    tool = ServerTool(
        server_id=server.id,
        tool_name="read_logs",
        input_schema={"type": "object"},
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(tool)
    return cap, server, tool


@pytest.mark.asyncio
async def test_first_mapping_is_active(db_session: AsyncSession) -> None:
    """The first mapping for a capability is created as active (no collision)."""
    cap, server, tool = await _setup(db_session)
    svc = CapabilityService(db=db_session)
    mapping = await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server.id, tool_name=tool.tool_name),
    )
    assert mapping.status == "active"


@pytest.mark.asyncio
async def test_second_different_tool_creates_collision(db_session: AsyncSession) -> None:
    """Mapping a *different* tool to the same capability creates a pending_review collision."""
    cap, server, tool = await _setup(db_session)
    svc = CapabilityService(db=db_session)

    # Tool A: read_logs
    await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server.id, tool_name="read_logs"),
    )

    # Tool B: write_logs (different tool_name) — collision!
    tool2 = ServerTool(
        server_id=server.id,
        tool_name="write_logs",
        input_schema={"type": "object"},
    )
    db_session.add(tool2)
    await db_session.commit()
    await db_session.refresh(tool2)

    mapping2 = await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server.id, tool_name="write_logs"),
    )
    assert mapping2.status == "pending_review"


@pytest.mark.asyncio
async def test_same_tool_different_server_not_collision(db_session: AsyncSession) -> None:
    """Same tool on different servers is load-balancing, not a collision."""
    cap, server, tool = await _setup(db_session)
    svc = CapabilityService(db=db_session)

    await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server.id, tool_name=tool.tool_name),
    )

    server2 = MCPServer(name="collision-server-2", endpoint="http://localhost:9998")
    db_session.add(server2)
    await db_session.commit()
    await db_session.refresh(server2)
    tool_on_s2 = ServerTool(
        server_id=server2.id,
        tool_name=tool.tool_name,  # same tool name
        input_schema={"type": "object"},  # same schema → same digest
    )
    db_session.add(tool_on_s2)
    await db_session.commit()
    await db_session.refresh(tool_on_s2)

    mapping2 = await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server2.id, tool_name=tool.tool_name),
    )
    assert mapping2.status == "active"


@pytest.mark.asyncio
async def test_get_collisions_returns_when_multiple_tools(db_session: AsyncSession) -> None:
    """get_collisions() returns the colliding mappings when >1 distinct tool maps."""
    cap, server, tool = await _setup(db_session)
    svc = CapabilityService(db=db_session)

    await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server.id, tool_name="read_logs"),
    )

    tool2 = ServerTool(
        server_id=server.id,
        tool_name="query_logs",
        input_schema={"type": "object"},
    )
    db_session.add(tool2)
    await db_session.commit()
    await db_session.refresh(tool2)
    await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server.id, tool_name="query_logs"),
    )

    collisions = await svc.get_collisions(cap.id)
    assert len(collisions) >= 2
    tool_names = {m.tool_name for m in collisions}
    assert "read_logs" in tool_names
    assert "query_logs" in tool_names


@pytest.mark.asyncio
async def test_get_collisions_empty_for_single_tool(db_session: AsyncSession) -> None:
    """No collisions when only one tool identity maps to the capability."""
    cap, server, tool = await _setup(db_session)
    svc = CapabilityService(db=db_session)

    await svc.create_mapping(
        cap.id,
        CapabilityMappingCreate(server_id=server.id, tool_name=tool.tool_name),
    )

    collisions = await svc.get_collisions(cap.id)
    assert collisions == []
