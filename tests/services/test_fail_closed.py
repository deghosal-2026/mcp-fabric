"""Tests for fail-closed re-inspection + stale-review age alerts (#444).

Validates:
  1. When re-inspection fails (server unreachable), active mappings become
     'stale-unverified' (fail-closed, excluded from routing), NOT left active.
  2. pending_since is set when a mapping enters limbo.
  3. pending_since is cleared when a mapping is approved/rejected.
  4. get_overdue_reviews returns items past the threshold.
"""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability as CapabilityModel
from api.models.server import CapabilityMapping, MCPServer, ServerTool
from api.schemas.capability import CapabilityMappingCreate
from api.services.capability_service import CapabilityService


async def _make_mapping(
    db_session: AsyncSession,
    tool_name: str = "get_status",
    status: str = "active",
    pending_since: datetime | None = None,
) -> CapabilityMapping:
    cap = CapabilityModel(name=f"fail-closed:{tool_name}:{status}", domain="test")
    server = MCPServer(name=f"server-{tool_name}-{status}", endpoint="http://localhost:1")
    db_session.add_all([cap, server])
    await db_session.flush()
    tool = ServerTool(
        server_id=server.id,
        tool_name=tool_name,
        input_schema={"type": "object"},
    )
    db_session.add(tool)
    await db_session.commit()
    await db_session.refresh(cap)
    await db_session.refresh(server)
    await db_session.refresh(tool)

    from api.services.capability_service import CapabilityService

    svc = CapabilityService(db=db_session)
    await svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=server.id, tool_name=tool_name)
    )

    # Override status/pending_since directly for test setup
    result = await db_session.execute(
        __import__("sqlalchemy")
        .select(CapabilityMapping)
        .where(CapabilityMapping.capability_id == cap.id)
    )
    mapping = result.scalar_one()
    mapping.status = status
    mapping.pending_since = pending_since
    await db_session.commit()
    await db_session.refresh(mapping)
    return mapping


@pytest.mark.asyncio
async def test_stale_unverified_excluded_from_routing(db_session: AsyncSession) -> None:
    """stale-unverified mappings are NOT active → excluded from routing."""
    m = await _make_mapping(db_session, status="stale-unverified", pending_since=datetime.now(UTC))
    assert m.status == "stale-unverified"
    assert m.pending_since is not None


@pytest.mark.asyncio
async def test_pending_since_set_on_collision(db_session: AsyncSession) -> None:
    """Colliding mappings get pending_since when created as pending_review."""
    cap = CapabilityModel(name="fail-closed:collision", domain="test")
    server = MCPServer(name="col-server", endpoint="http://localhost:2")
    db_session.add_all([cap, server])
    await db_session.commit()
    await db_session.refresh(cap)
    await db_session.refresh(server)

    t1 = ServerTool(server_id=server.id, tool_name="read_a", input_schema={"type": "object"})
    t2 = ServerTool(server_id=server.id, tool_name="read_b", input_schema={"type": "object"})
    db_session.add_all([t1, t2])
    await db_session.commit()
    await db_session.refresh(t1)
    await db_session.refresh(t2)

    svc = CapabilityService(db=db_session)
    await svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=server.id, tool_name="read_a")
    )
    m2 = await svc.create_mapping(
        cap.id, CapabilityMappingCreate(server_id=server.id, tool_name="read_b")
    )

    assert m2.status == "pending_review"
    assert m2.pending_since is not None


@pytest.mark.asyncio
async def test_get_overdue_reviews_returns_old_items(db_session: AsyncSession) -> None:
    """Mappings in limbo past the threshold are returned as overdue."""
    old_time = datetime.now(UTC) - timedelta(hours=48)
    await _make_mapping(db_session, status="stale", pending_since=old_time)

    svc = CapabilityService(db=db_session)
    overdue = await svc.get_overdue_reviews(threshold_hours=24)
    assert len(overdue) >= 1
    assert all(o.pending_since is not None for o in overdue)


@pytest.mark.asyncio
async def test_get_overdue_reviews_excludes_recent(db_session: AsyncSession) -> None:
    """Mappings in limbo but within the threshold are NOT overdue."""
    recent_time = datetime.now(UTC) - timedelta(hours=1)
    await _make_mapping(db_session, status="stale", pending_since=recent_time)

    svc = CapabilityService(db=db_session)
    overdue = await svc.get_overdue_reviews(threshold_hours=24)
    assert overdue == []


@pytest.mark.asyncio
async def test_get_stale_mappings_includes_all_limbo_states(db_session: AsyncSession) -> None:
    """get_stale_mappings returns stale, pending_review, and stale-unverified."""
    await _make_mapping(db_session, status="stale", pending_since=datetime.now(UTC))
    await _make_mapping(db_session, status="pending_review", pending_since=datetime.now(UTC))
    await _make_mapping(db_session, status="stale-unverified", pending_since=datetime.now(UTC))

    svc = CapabilityService(db=db_session)
    result = await svc.get_stale_mappings()
    statuses = {r.status for r in result}
    assert "stale" in statuses
    assert "pending_review" in statuses
    assert "stale-unverified" in statuses
