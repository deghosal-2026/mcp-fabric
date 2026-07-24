from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime as dt
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mcp import MCPClient
from api.models import MCPServer, ServerTool, ToolVersion
from api.schemas.server import ServerCreate
from api.services import (
    DuplicateServerError,
    RegistryService,
    ServerNotFoundError,
    ServerUnreachableError,
)
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


class TestInspect:
    @pytest_asyncio.fixture
    async def registered_server(
        self,
        registry_service: RegistryService,
    ) -> MCPServer:
        async with async_mock_server(create_mock_mcp_server()) as url:
            result = await registry_service.register(
                ServerCreate(name="inspect-test", endpoint=url)
            )
            result2 = await registry_service.db.execute(
                select(MCPServer).where(MCPServer.id == result.id)
            )
            return result2.scalar_one()

    async def test_inspect_no_changes(
        self,
        registry_service: RegistryService,
        registered_server: MCPServer,
        db_session: AsyncSession,
    ) -> None:
        async with async_mock_server(create_mock_mcp_server()) as url:
            registered_server.endpoint = url
            await db_session.commit()

            result = await registry_service.inspect(registered_server.id)
        assert len(result.tools_added) == 0
        assert len(result.tools_removed) == 0
        assert len(result.tools_changed) == 0

    async def test_inspect_detects_added_tool(
        self,
        registry_service: RegistryService,
        registered_server: MCPServer,
        db_session: AsyncSession,
    ) -> None:
        original_tools = [
            {"name": "list_items", "input_schema": {"type": "object", "properties": {}}},
        ]
        new_tools = [
            {"name": "list_items", "input_schema": {"type": "object", "properties": {}}},
            {"name": "get_detail", "input_schema": {"type": "object", "properties": {}}},
        ]
        app = create_mock_mcp_server(tools=original_tools)
        async with async_mock_server(app) as url:
            reg_result = await registry_service.register(
                ServerCreate(name="srv", endpoint=url)
            )
            server_obj = (await db_session.execute(
                select(MCPServer).where(MCPServer.id == reg_result.id)
            )).scalar_one()

            app2 = create_mock_mcp_server(tools=new_tools)
            async with async_mock_server(app2) as url2:
                server_obj.endpoint = url2
                await db_session.commit()

                result = await registry_service.inspect(server_obj.id)
        assert len(result.tools_added) == 1
        assert result.tools_added[0].tool_name == "get_detail"
        assert len(result.tools_removed) == 0
        assert len(result.tools_changed) == 0

    async def test_inspect_detects_removed_tool(
        self,
        registry_service: RegistryService,
        registered_server: MCPServer,
        db_session: AsyncSession,
    ) -> None:
        original_tools = [
            {"name": "tool_a", "input_schema": {"type": "object", "properties": {}}},
            {"name": "tool_b", "input_schema": {"type": "object", "properties": {}}},
        ]
        reduced_tools = [
            {"name": "tool_a", "input_schema": {"type": "object", "properties": {}}},
        ]
        app = create_mock_mcp_server(tools=original_tools)
        async with async_mock_server(app) as url:
            reg_result = await registry_service.register(
                ServerCreate(name="srv", endpoint=url)
            )
            server_obj = (await db_session.execute(
                select(MCPServer).where(MCPServer.id == reg_result.id)
            )).scalar_one()

            app2 = create_mock_mcp_server(tools=reduced_tools)
            async with async_mock_server(app2) as url2:
                server_obj.endpoint = url2
                await db_session.commit()

                result = await registry_service.inspect(server_obj.id)
        assert len(result.tools_removed) == 1
        assert result.tools_removed[0].tool_name == "tool_b"

    async def test_inspect_detects_changed_tool(
        self,
        registry_service: RegistryService,
        registered_server: MCPServer,
        db_session: AsyncSession,
    ) -> None:
        old_schema = {"type": "object", "properties": {"x": {"type": "string"}}, "required": ["x"]}
        new_schema = {
            "type": "object",
            "properties": {"x": {"type": "string"}, "y": {"type": "integer"}},
        }
        original_tools = [
            {"name": "greet", "input_schema": old_schema},
        ]
        changed_tools = [
            {"name": "greet", "input_schema": new_schema},
        ]
        app = create_mock_mcp_server(tools=original_tools)
        async with async_mock_server(app) as url:
            reg_result = await registry_service.register(
                ServerCreate(name="srv", endpoint=url)
            )
            server_obj = (await db_session.execute(
                select(MCPServer).where(MCPServer.id == reg_result.id)
            )).scalar_one()

            app2 = create_mock_mcp_server(tools=changed_tools)
            async with async_mock_server(app2) as url2:
                server_obj.endpoint = url2
                await db_session.commit()

                result = await registry_service.inspect(server_obj.id)
        assert len(result.tools_changed) == 1
        assert result.tools_changed[0].tool_name == "greet"

    async def test_inspect_archives_removed_tool(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
    ) -> None:
        original_tools = [
            {"name": "tool_a", "input_schema": {"type": "object", "properties": {}}},
            {"name": "tool_b", "input_schema": {"type": "object", "properties": {}}},
        ]
        reduced_tools = [
            {"name": "tool_a", "input_schema": {"type": "object", "properties": {}}},
        ]
        app = create_mock_mcp_server(tools=original_tools)
        async with async_mock_server(app) as url:
            reg_result = await registry_service.register(
                ServerCreate(name="srv", endpoint=url)
            )
            server_obj = (await db_session.execute(
                select(MCPServer).where(MCPServer.id == reg_result.id)
            )).scalar_one()

            app2 = create_mock_mcp_server(tools=reduced_tools)
            async with async_mock_server(app2) as url2:
                server_obj.endpoint = url2
                await db_session.commit()
                await registry_service.inspect(server_obj.id)

        result = await db_session.execute(
            select(ToolVersion).where(ToolVersion.server_id == server_obj.id)
        )
        versions = result.scalars().all()
        assert len(versions) == 1
        assert versions[0].tool_name == "tool_b"
        assert versions[0].is_breaking is True

    async def test_inspect_server_not_found(
        self,
        registry_service: RegistryService,
    ) -> None:
        with pytest.raises(ServerNotFoundError):
            await registry_service.inspect(uuid4())

    async def test_inspect_unreachable_server(
        self,
        registry_service: RegistryService,
        registered_server: MCPServer,
        db_session: AsyncSession,
    ) -> None:
        registered_server.endpoint = "http://127.0.0.1:1"
        await db_session.commit()

        with pytest.raises(ServerUnreachableError):
            await registry_service.inspect(registered_server.id)


class TestGetServer:
    async def test_get_server_returns_full_detail(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(
            name="detail-test",
            endpoint=mock_server_url,
            owner_team="platform",
            labels=["test"],
        )
        created = await registry_service.register(params)
        result = await registry_service.get_server(created.id)

        assert result.id == created.id
        assert result.name == "detail-test"
        assert result.owner_team == "platform"
        assert result.labels == ["test"]
        assert len(result.tools) == 2
        assert result.decommission_timeline is None

    async def test_get_server_with_decommission_timeline(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="decom-test", endpoint=mock_server_url)
        created = await registry_service.register(params)
        server = (
            await registry_service.db.execute(
                select(MCPServer).where(MCPServer.id == created.id)
            )
        ).scalar_one()
        server.decommission_phase = "grace_period"
        server.decommissioned_at = dt(2026, 8, 1, 12, 0, 0)
        await registry_service.db.commit()

        result = await registry_service.get_server(created.id)
        assert result.decommission_timeline is not None
        assert result.decommission_timeline.phase == "grace_period"
        assert result.decommission_timeline.decommissioned_at is not None
        assert result.decommission_timeline.status == "grace_period"

    async def test_get_server_not_found(
        self,
        registry_service: RegistryService,
    ) -> None:
        with pytest.raises(ServerNotFoundError):
            await registry_service.get_server(uuid4())


class TestListServers:
    @pytest_asyncio.fixture(autouse=True)
    async def _seed_servers(
        self,
        registry_service: RegistryService,
    ) -> None:
        apps: list[tuple[str, str, str, str]] = [
            ("srv-a", "team-x", "trusted", "healthy"),
            ("srv-b", "team-x", "unreviewed", "healthy"),
            ("srv-c", "team-y", "trusted", "degraded"),
            ("srv-d", "team-y", "blocked", "down"),
            ("srv-e", "team-z", "trusted", "healthy"),
        ]
        for i, (name, team, trust, health) in enumerate(apps):
            app = create_mock_mcp_server()
            async with async_mock_server(app) as url:
                result = await registry_service.register(
                    ServerCreate(
                        name=name, endpoint=url,
                        owner_team=team, team_namespace=team,
                    )
                )
                srv = (await registry_service.db.execute(
                    select(MCPServer).where(MCPServer.id == result.id)
                )).scalar_one()
                srv.trust_level = trust
                srv.health_status = health
                srv.created_at = dt(2026, 7, 24, 0, 0, i)
                await registry_service.db.commit()

    async def test_list_all(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers()
        names = {s.name for s in result.servers}
        assert names == {"srv-a", "srv-b", "srv-c", "srv-d", "srv-e"}
        assert result.pagination.total == 5

    async def test_list_empty_result(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(team="nonexistent")
        assert len(result.servers) == 0
        assert result.pagination.total == 0
        assert result.pagination.has_more is False

    async def test_filter_by_team(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(team="team-x")
        names = {s.name for s in result.servers}
        assert names == {"srv-a", "srv-b"}
        assert result.pagination.total == 2

    async def test_filter_by_trust(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(trust="trusted")
        names = {s.name for s in result.servers}
        assert names == {"srv-a", "srv-c", "srv-e"}
        assert result.pagination.total == 3

    async def test_filter_by_health(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(health="healthy")
        names = {s.name for s in result.servers}
        assert names == {"srv-a", "srv-b", "srv-e"}
        assert result.pagination.total == 3

    async def test_search_by_name(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(search="srv-a")
        assert len(result.servers) == 1
        assert result.servers[0].name == "srv-a"
        assert result.pagination.total == 1

    async def test_combined_filters(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(
            team="team-x", trust="trusted", health="healthy"
        )
        names = {s.name for s in result.servers}
        assert names == {"srv-a"}
        assert result.pagination.total == 1

    async def test_cursor_pagination(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(per_page=2)
        assert len(result.servers) == 2
        assert result.pagination.has_more is True
        assert result.pagination.next_cursor is not None
        assert result.pagination.total == 5

        next_cursor = result.pagination.next_cursor
        result2 = await registry_service.list_servers(per_page=2, cursor=next_cursor)
        assert len(result2.servers) == 2
        assert result2.pagination.has_more is True

        next_cursor2 = result2.pagination.next_cursor
        result3 = await registry_service.list_servers(per_page=2, cursor=next_cursor2)
        assert len(result3.servers) == 1
        assert result3.pagination.has_more is False
        assert result3.pagination.next_cursor is None
