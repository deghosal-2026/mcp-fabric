import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability, CapabilityAlias
from api.models.server import CapabilityMapping, MCPServer
from api.services.capability_service import CapabilityService


@pytest.mark.asyncio
async def test_list_capabilities_with_mappings_and_aliases(db_session: AsyncSession) -> None:
    server = MCPServer(
        name="demo-server",
        endpoint="https://demo.example/mcp",
        owner_team="platform",
        labels=["demo"],
    )
    capability = Capability(
        name="demo:knowledge-search",
        domain="knowledge",
        description="Demo capability",
        status="active",
    )
    db_session.add_all([server, capability])
    await db_session.flush()

    db_session.add(CapabilityAlias(capability_id=capability.id, alias="knowledge:search"))
    db_session.add(
        CapabilityMapping(
            capability_id=capability.id,
            server_id=server.id,
            tool_name="search_docs",
            is_primary=True,
        )
    )
    await db_session.commit()

    service = CapabilityService(db_session)
    items = await service.list()

    assert len(items) == 1
    assert items[0].name == "demo:knowledge-search"
    assert items[0].mappings_count == 1
    assert items[0].aliases == ["knowledge:search"]
