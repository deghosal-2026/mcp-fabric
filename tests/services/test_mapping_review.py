from __future__ import annotations

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability
from api.models.server import CapabilityMapping, MCPServer, ServerTool
from api.schemas.capability import CapabilityMappingCreate, MappingReviewCreate
from api.services.capability_service import CapabilityService


# Tests the approve flow: creates a mapping with a known digest, mutates the
# tool schema to simulate drift, marks it stale manually, then calls
# review_mapping(decision="approved"). Verifies the status resets to "active"
# and the digest is recomputed to match the new schema.
@pytest.mark.asyncio
async def test_review_mapping_approve_updates_digest_and_status(db_session: AsyncSession) -> None:
    srv = MCPServer(name="s", endpoint="http://s")
    db_session.add(srv)
    await db_session.flush()

    tool = ServerTool(
        server_id=srv.id,
        tool_name="op",
        input_schema={"type": "object", "properties": {"a": {"type": "string"}}},
        output_schema=None,
    )
    db_session.add(tool)
    cap = Capability(name="demo:op", status="active")
    db_session.add(cap)
    await db_session.commit()

    csvc = CapabilityService(db_session)
    mapping = await csvc.create_mapping(
        cap.id,
        params=CapabilityMappingCreate(server_id=srv.id, tool_name="op"),
    )

    # Mutate tool schema to trigger drift and mark stale manually for this unit test
    tool.input_schema = {"type": "object", "properties": {"b": {"type": "integer"}}}
    get_mapping = select(CapabilityMapping).where(CapabilityMapping.id == mapping.id)
    row = (await db_session.execute(get_mapping)).scalar_one()
    row.status = "stale"
    await db_session.commit()

    # Approve review
    review = await csvc.review_mapping(mapping.id, MappingReviewCreate(decision="approved"))
    assert review.decision == "approved"

    updated = (await db_session.execute(get_mapping)).scalar_one()
    assert updated.status == "active"
    assert updated.tool_schema_digest is not None and len(updated.tool_schema_digest) == 64


# Tests the reject flow: marks a mapping stale, then calls
# review_mapping(decision="rejected"). Verifies the status is set to "rejected"
# permanently and the digest is NOT recomputed (status stays rejected).
@pytest.mark.asyncio
async def test_review_mapping_reject_sets_rejected(db_session: AsyncSession) -> None:
    srv = MCPServer(name="s2", endpoint="http://s2")
    db_session.add(srv)
    await db_session.flush()

    tool = ServerTool(
        server_id=srv.id,
        tool_name="beta",
        input_schema={"type": "object", "properties": {}},
        output_schema=None,
    )
    db_session.add(tool)
    cap = Capability(name="demo:beta", status="active")
    db_session.add(cap)
    await db_session.commit()

    csvc = CapabilityService(db_session)
    mapping = await csvc.create_mapping(
        cap.id,
        params=CapabilityMappingCreate(server_id=srv.id, tool_name="beta"),
    )

    get_mapping = select(CapabilityMapping).where(CapabilityMapping.id == mapping.id)

    row = (await db_session.execute(get_mapping)).scalar_one()
    row.status = "stale"
    await db_session.commit()

    review = await csvc.review_mapping(
        mapping.id, MappingReviewCreate(decision="rejected", reason="bad schema")
    )
    assert review.decision == "rejected"

    updated = (await db_session.execute(get_mapping)).scalar_one()
    assert updated.status == "rejected"
