from __future__ import annotations

from collections.abc import AsyncGenerator

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mcp import MCPClient
from api.models import MCPServer, ServerTool
from api.schemas.server import ServerCreate
from api.services import DuplicateServerError, RegistryService, ServerUnreachableError
from tests.fixtures.mcp_server import async_mock_server, create_mock_mcp_server


@pytest_asyncio.fixture
async def registry_service(
    db_session: AsyncSession,
) -> RegistryService:
    client = MCPClient()
    return RegistryService(db=db_session, mcp_client=client)


@pytest_asyncio.fixture
async def mock_server_url() -> AsyncGenerator[str, None]:
    async with async_mock_server(create_mock_mcp_server()) as url:
        yield url


class TestRegister:
    async def test_register_creates_server_and_tools(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(
            name="test-server",
            endpoint=mock_server_url,
            owner_team="platform",
            labels=["production"],
        )
        result = await registry_service.register(params)

        assert result.name == "test-server"
        assert result.endpoint == mock_server_url
        assert result.owner_team == "platform"
        assert result.labels == ["production"]
        assert result.trust_level == "unreviewed"
        assert result.health_status == "unknown"

        result2 = await db_session.execute(
            select(MCPServer).where(MCPServer.id == result.id)
        )
        server = result2.scalar_one()
        assert server.name == "test-server"

        result3 = await db_session.execute(
            select(ServerTool).where(ServerTool.server_id == result.id)
        )
        tools = result3.scalars().all()
        assert len(tools) == 2
        assert {t.tool_name for t in tools} == {"test_tool", "search"}

    async def test_register_with_all_read_only_tools(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
    ) -> None:
        app = create_mock_mcp_server(
            tools=[
                {
                    "name": "list_items",
                    "description": "List all items",
                    "input_schema": {"type": "object", "properties": {}},
                },
                {
                    "name": "get_item",
                    "description": "Get an item",
                    "input_schema": {"type": "object", "properties": {}},
                },
            ],
        )
        async with async_mock_server(app) as url:
            params = ServerCreate(name="readonly-server", endpoint=url)
            result = await registry_service.register(params)
        assert result.trust_level == "trusted"

    async def test_register_duplicate_endpoint(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="first", endpoint=mock_server_url)
        await registry_service.register(params)

        params2 = ServerCreate(name="second", endpoint=mock_server_url)
        with pytest.raises(DuplicateServerError):
            await registry_service.register(params2)

    async def test_register_unreachable_endpoint(
        self,
        registry_service: RegistryService,
    ) -> None:
        params = ServerCreate(
            name="unreachable",
            endpoint="http://127.0.0.1:1",
        )
        with pytest.raises(ServerUnreachableError):
            await registry_service.register(params)

    async def test_register_empty_tool_list(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
    ) -> None:
        app = create_mock_mcp_server(tools=[])
        async with async_mock_server(app) as url:
            params = ServerCreate(name="empty-server", endpoint=url)
            result = await registry_service.register(params)
        assert result.trust_level == "unreviewed"

        result2 = await db_session.execute(
            select(ServerTool).where(ServerTool.server_id == result.id)
        )
        tools = result2.scalars().all()
        assert len(tools) == 0

    async def test_register_error_messages_include_context(
        self,
        registry_service: RegistryService,
    ) -> None:
        bad_url = "http://127.0.0.1:1"
        params = ServerCreate(name="fail", endpoint=bad_url)
        with pytest.raises(ServerUnreachableError) as exc:
            await registry_service.register(params)
        assert bad_url in str(exc.value)
