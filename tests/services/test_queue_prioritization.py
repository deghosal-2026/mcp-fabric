"""Tests for queue prioritization — unreachable vs genuinely changed (#447).

Validates:
  1. failure_class is set when mappings enter limbo:
     - re-inspection failure -> 'unreachable' (or 'timeout' on MCPTimeoutError)
     - schema drift -> 'drifted'
     - capability-mapping collision -> 'schema_mismatch'
  2. Review queue getters can filter by failure_class.
  3. bulk_retire retires an entire failure_class without per-item review.
  4. get_queue_summary separates critical (drifted/schema_mismatch) from
     unreachable (unreachable/timeout), so unreachable items never count
     toward the reviewer's pending-critical tally.
  5. Prioritized ordering surfaces real changes above unreachable noise.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mcp import MCPClient, MCPError, MCPTimeoutError
from api.models.capability import Capability
from api.models.server import CapabilityMapping, MCPServer, ServerTool
from api.schemas.capability import CapabilityMappingCreate
from api.schemas.server import ServerCreate
from api.services.capability_service import CapabilityService
from api.services.exceptions import ServiceError
from api.services.registry_service import RegistryService
from tests.fixtures.mcp_server import async_mock_server, create_mock_mcp_server


class _FakeMCP:
    """MCPClient stand-in that raises a preset error on list_tools."""

    def __init__(self, exc: BaseException) -> None:
        self._exc = exc

    async def list_tools(self, endpoint: str, timeout: float | None = None) -> list[Any]:
        raise self._exc


async def _server_with_mapping(db_session: AsyncSession) -> MCPServer:
    """Create a server + capability + active mapping, return the server."""
    server = MCPServer(name="prio-server", endpoint="http://localhost:1")
    db_session.add(server)
    await db_session.flush()
    cap = Capability(name=f"prio:cap-{server.id}", domain="test")
    db_session.add(cap)
    tool = ServerTool(server_id=server.id, tool_name="prio_tool", input_schema={"type": "object"})
    db_session.add(tool)
    await db_session.commit()
    svc = CapabilityService(db=db_session)
    await svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=server.id, tool_name="prio_tool")
    )
    return server


async def _mapping_for_server(db_session: AsyncSession, server: MCPServer) -> CapabilityMapping:
    result = await db_session.execute(
        select(CapabilityMapping).where(CapabilityMapping.server_id == server.id)
    )
    return result.scalar_one()


@pytest.mark.asyncio
async def test_reinspection_failure_sets_unreachable_failure_class(
    db_session: AsyncSession,
) -> None:
    server = await _server_with_mapping(db_session)
    reg = RegistryService(
        db=db_session,
        mcp_client=_FakeMCP(MCPError("boom")),  # type: ignore[arg-type]
    )

    with pytest.raises(ServiceError):
        await reg.inspect(server.id)

    mapping = await _mapping_for_server(db_session, server)
    assert mapping.status == "stale-unverified"
    assert mapping.failure_class == "unreachable"


@pytest.mark.asyncio
async def test_reinspection_timeout_sets_timeout_failure_class(
    db_session: AsyncSession,
) -> None:
    server = await _server_with_mapping(db_session)
    reg = RegistryService(
        db=db_session,
        mcp_client=_FakeMCP(MCPTimeoutError("http://localhost:1", 5.0)),  # type: ignore[arg-type]
    )

    with pytest.raises(ServiceError):
        await reg.inspect(server.id)

    mapping = await _mapping_for_server(db_session, server)
    assert mapping.status == "stale-unverified"
    assert mapping.failure_class == "timeout"


@pytest.mark.asyncio
async def test_schema_drift_sets_drifted_failure_class(db_session: AsyncSession) -> None:
    original_tools = [
        {
            "name": "drift_tool",
            "description": "",
            "input_schema": {"type": "object", "properties": {}},
        },
    ]
    app = create_mock_mcp_server(tools=original_tools)
    async with async_mock_server(app) as url:
        reg = RegistryService(db=db_session, mcp_client=MCPClient())
        created = await reg.register(ServerCreate(name="drift-srv", endpoint=url))
        srv = (
            await db_session.execute(select(MCPServer).where(MCPServer.id == created.id))
        ).scalar_one()
        cap = Capability(name="drift:cap", domain="test")
        db_session.add(cap)
        await db_session.flush()
        svc = CapabilityService(db=db_session)
        await svc.create_mapping(
            cap.id, CapabilityMappingCreate(server_id=srv.id, tool_name="drift_tool")
        )

        changed_tools = [
            {
                "name": "drift_tool",
                "description": "",
                "input_schema": {"type": "object", "properties": {"x": {"type": "string"}}},
            }
        ]
        app2 = create_mock_mcp_server(tools=changed_tools)
        async with async_mock_server(app2) as url2:
            srv.endpoint = url2
            await db_session.commit()
            await reg.inspect(srv.id)

    mapping = (
        await db_session.execute(
            select(CapabilityMapping).where(CapabilityMapping.capability_id == cap.id)
        )
    ).scalar_one()
    assert mapping.status == "stale"
    assert mapping.failure_class == "drifted"


@pytest.mark.asyncio
async def test_collision_mapping_sets_schema_mismatch_failure_class(
    db_session: AsyncSession,
) -> None:
    cap = Capability(name="coll:cap", domain="test")
    server = MCPServer(name="coll-server", endpoint="http://localhost:2")
    db_session.add_all([cap, server])
    await db_session.flush()
    db_session.add_all(
        [
            ServerTool(server_id=server.id, tool_name="read_a", input_schema={"type": "object"}),
            ServerTool(server_id=server.id, tool_name="read_b", input_schema={"type": "object"}),
        ]
    )
    await db_session.commit()

    svc = CapabilityService(db=db_session)
    await svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=server.id, tool_name="read_a")
    )
    m2 = await svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=server.id, tool_name="read_b")
    )

    assert m2.status == "pending_review"
    assert m2.failure_class == "schema_mismatch"


@pytest.mark.asyncio
async def test_bulk_retire_retires_only_target_failure_class(
    db_session: AsyncSession,
) -> None:
    svc = CapabilityService(db=db_session)
    servers: list[MCPServer] = []
    for _ in range(3):
        server = await _server_with_mapping(db_session)
        mapping = await _mapping_for_server(db_session, server)
        mapping.status = "stale-unverified"
        mapping.failure_class = "unreachable"
        servers.append(server)
    server2 = await _server_with_mapping(db_session)
    m2 = await _mapping_for_server(db_session, server2)
    m2.status = "stale"
    m2.failure_class = "drifted"
    await db_session.commit()

    retired = await svc.bulk_retire(failure_class="unreachable")

    assert retired == 3
    result = await db_session.execute(
        select(CapabilityMapping).where(CapabilityMapping.failure_class == "unreachable")
    )
    retired_unreachable = result.scalars().all()
    assert {m.status for m in retired_unreachable} == {"rejected"}
    assert all(m.pending_since is None for m in retired_unreachable)

    drifted = (
        await db_session.execute(
            select(CapabilityMapping).where(CapabilityMapping.failure_class == "drifted")
        )
    ).scalar_one()
    assert drifted.status == "stale"


@pytest.mark.asyncio
async def test_get_stale_mappings_filters_by_failure_class(db_session: AsyncSession) -> None:
    unreachable = await _server_with_mapping(db_session)
    um = await _mapping_for_server(db_session, unreachable)
    um.status = "stale-unverified"
    um.failure_class = "unreachable"
    drifted = await _server_with_mapping(db_session)
    dm = await _mapping_for_server(db_session, drifted)
    dm.status = "stale"
    dm.failure_class = "drifted"
    await db_session.commit()

    svc = CapabilityService(db=db_session)
    unreachable_only = await svc.get_stale_mappings(failure_class="unreachable")
    assert all(r.failure_class == "unreachable" for r in unreachable_only)
    assert len(unreachable_only) == 1

    all_limbo = await svc.get_stale_mappings()
    assert {r.failure_class for r in all_limbo} == {"unreachable", "drifted"}


@pytest.mark.asyncio
async def test_queue_summary_excludes_unreachable_from_critical(
    db_session: AsyncSession,
) -> None:
    for _ in range(2):
        server = await _server_with_mapping(db_session)
        mapping = await _mapping_for_server(db_session, server)
        mapping.status = "stale-unverified"
        mapping.failure_class = "unreachable"
    drifted = await _server_with_mapping(db_session)
    dm = await _mapping_for_server(db_session, drifted)
    dm.status = "stale"
    dm.failure_class = "drifted"
    coll = await _server_with_mapping(db_session)
    cm = await _mapping_for_server(db_session, coll)
    cm.status = "pending_review"
    cm.failure_class = "schema_mismatch"
    await db_session.commit()

    svc = CapabilityService(db=db_session)
    summary = await svc.get_queue_summary()

    assert summary.total == 4
    assert summary.critical == 2  # drifted + schema_mismatch only
    assert summary.unreachable == 2
    assert summary.by_failure_class["unreachable"] == 2
    assert summary.by_failure_class["drifted"] == 1
    assert summary.by_failure_class["schema_mismatch"] == 1


@pytest.mark.asyncio
async def test_prioritized_queue_surfaces_real_changes_above_unreachable(
    db_session: AsyncSession,
) -> None:
    old = datetime.now(UTC) - timedelta(hours=48)
    fresh = datetime.now(UTC) - timedelta(hours=1)
    for _ in range(50):
        server = await _server_with_mapping(db_session)
        mapping = await _mapping_for_server(db_session, server)
        mapping.status = "stale-unverified"
        mapping.failure_class = "unreachable"
        mapping.pending_since = old
    await db_session.commit()

    for _ in range(2):
        server = await _server_with_mapping(db_session)
        mapping = await _mapping_for_server(db_session, server)
        mapping.status = "stale"
        mapping.failure_class = "drifted"
        mapping.pending_since = fresh
    await db_session.commit()

    svc = CapabilityService(db=db_session)
    queue = await svc.get_prioritized_reviews()

    assert len(queue) == 52
    classes_in_order = [r.failure_class for r in queue]
    assert classes_in_order.count("drifted") == 2
    # Despite the 50 unreachable items being older, the 2 genuine changes
    # lead the queue so they are not buried by unreachable noise.
    assert classes_in_order[0] == "drifted"
    assert classes_in_order[1] == "drifted"
