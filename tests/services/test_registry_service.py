from __future__ import annotations

from collections.abc import AsyncGenerator
from datetime import datetime as dt
from typing import Any
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mcp import MCPClient
from api.models import Capability, CapabilityMapping, MCPServer, ServerTool, ToolVersion
from api.schemas.server import ServerCreate
from api.services import (
    DecommissionError,
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
def mock_audit_service() -> Any:
    return AsyncMock()


@pytest_asyncio.fixture
async def registry_service_with_audit(
    db_session: AsyncSession,
    mock_audit_service: Any,
) -> RegistryService:
    client = MCPClient()
    return RegistryService(
        db=db_session, mcp_client=client, audit_service=mock_audit_service
    )


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

    async def test_register_with_audit_logging(
        self,
        registry_service_with_audit: RegistryService,
        mock_audit_service: Any,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="audit-test", endpoint=mock_server_url)
        result = await registry_service_with_audit.register(params)
        mock_audit_service.log_event.assert_awaited_once_with(
            event_type="server_registered",
            actor="system",
            resource_id=str(result.id),
            metadata={"name": result.name, "endpoint": result.endpoint},
        )

    async def test_register_audit_failure_does_not_block(
        self,
        db_session: AsyncSession,
        mock_server_url: str,
    ) -> None:
        audit_mock = AsyncMock()
        audit_mock.log_event.side_effect = Exception("audit down")
        svc = RegistryService(
            db=db_session, mcp_client=MCPClient(), audit_service=audit_mock
        )
        params = ServerCreate(name="audit-fail", endpoint=mock_server_url)
        result = await svc.register(params)
        assert result.name == "audit-fail"


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

    async def test_inspect_logs_audit_event(
        self,
        registry_service_with_audit: RegistryService,
        mock_audit_service: Any,
        db_session: AsyncSession,
    ) -> None:
        original_tools = [
            {"name": "tool_x", "input_schema": {"type": "object", "properties": {}}},
        ]
        new_tools = [
            {"name": "tool_x", "input_schema": {"type": "object", "properties": {}}},
            {"name": "tool_y", "input_schema": {"type": "object", "properties": {}}},
        ]
        app = create_mock_mcp_server(tools=original_tools)
        async with async_mock_server(app) as url:
            reg = await registry_service_with_audit.register(
                ServerCreate(name="inspect-audit", endpoint=url)
            )
            srv = (await db_session.execute(
                select(MCPServer).where(MCPServer.id == reg.id)
            )).scalar_one()
            app2 = create_mock_mcp_server(tools=new_tools)
            async with async_mock_server(app2) as url2:
                srv.endpoint = url2
                await db_session.commit()
                result = await registry_service_with_audit.inspect(srv.id)
        assert len(result.tools_added) == 1
        mock_audit_service.log_event.assert_awaited()

    async def test_inspect_audit_failure_does_not_block(
        self,
        db_session: AsyncSession,
    ) -> None:
        audit_mock = AsyncMock()
        audit_mock.log_event.side_effect = Exception("audit down")
        svc = RegistryService(
            db=db_session, mcp_client=MCPClient(), audit_service=audit_mock
        )
        original_tools = [
            {"name": "tool_old", "input_schema": {"type": "object", "properties": {}}},
        ]
        new_tools = [
            {"name": "tool_new", "input_schema": {"type": "object", "properties": {}}},
        ]
        app = create_mock_mcp_server(tools=original_tools)
        async with async_mock_server(app) as url:
            created = await svc.register(
                ServerCreate(name="inspect-audit-fail", endpoint=url)
            )
            srv = (await db_session.execute(
                select(MCPServer).where(MCPServer.id == created.id)
            )).scalar_one()
            app2 = create_mock_mcp_server(tools=new_tools)
            async with async_mock_server(app2) as url2:
                srv.endpoint = url2
                await db_session.commit()
                result = await svc.inspect(srv.id)
        assert result.health_status == "reachable"


class TestHealth:
    async def test_update_and_get_server_health(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="health-test", endpoint=mock_server_url)
        created = await registry_service.register(params)

        await registry_service.update_health(created.id, "healthy")
        status = await registry_service.get_server_health(created.id)
        assert status == "healthy"

    async def test_get_all_health_statuses(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
    ) -> None:
        urls: list[str] = []
        for name in ["h-a", "h-b", "h-c"]:
            app = create_mock_mcp_server()
            async with async_mock_server(app) as url:
                urls.append(url)
                params = ServerCreate(name=name, endpoint=url)
                created = await registry_service.register(params)
                await registry_service.update_health(created.id, "healthy")
        statuses = await registry_service.get_all_health_statuses()
        assert len(statuses) >= 3
        assert all(v == "healthy" for v in statuses.values())

    async def test_update_health_not_found(
        self,
        registry_service: RegistryService,
    ) -> None:
        with pytest.raises(ServerNotFoundError):
            await registry_service.update_health(uuid4(), "healthy")

    async def test_get_server_health_not_found(
        self,
        registry_service: RegistryService,
    ) -> None:
        with pytest.raises(ServerNotFoundError):
            await registry_service.get_server_health(uuid4())

    async def test_update_health_with_redis(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        redis_mock = AsyncMock()
        redis_mock.set = AsyncMock()
        svc = RegistryService(
            db=registry_service.db,
            mcp_client=MCPClient(),
            redis_client=redis_mock,
        )
        params = ServerCreate(name="redis-health", endpoint=mock_server_url)
        created = await svc.register(params)
        await svc.update_health(created.id, "healthy")
        redis_mock.set.assert_awaited_once_with(
            f"health:{created.id}", "healthy", ex=60
        )

    async def test_get_server_health_from_redis(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        redis_mock = AsyncMock()
        redis_mock.get = AsyncMock(return_value=b"healthy")
        svc = RegistryService(
            db=registry_service.db,
            mcp_client=MCPClient(),
            redis_client=redis_mock,
        )
        params = ServerCreate(name="redis-get", endpoint=mock_server_url)
        created = await svc.register(params)
        status = await svc.get_server_health(created.id)
        assert status == "healthy"
        redis_mock.get.assert_awaited_once_with(f"health:{created.id}")

    async def test_get_all_health_statuses_uses_redis_scan(
        self,
        registry_service: RegistryService,
    ) -> None:
        redis_mock = AsyncMock()
        redis_mock.scan = AsyncMock(return_value=(0, [b"health:srv-a"]))
        redis_mock.mget = AsyncMock(return_value=[b"healthy"])
        svc = RegistryService(
            db=registry_service.db,
            mcp_client=MCPClient(),
            redis_client=redis_mock,
        )
        statuses = await svc.get_all_health_statuses()
        assert statuses == {"srv-a": "healthy"}


class TestDecommission:
    async def test_decommission_grace_period(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="decom-srv", endpoint=mock_server_url)
        created = await registry_service.register(params)
        result = await registry_service.decommission(created.id, phase="grace_period")

        assert result.phase == "grace_period"
        assert result.timeline is not None
        assert result.timeline.phase == "grace_period"
        assert result.timeline.decommissioned_at is not None

        server = (
            await registry_service.db.execute(
                select(MCPServer).where(MCPServer.id == created.id)
            )
        ).scalar_one()
        assert server.decommission_phase == "grace_period"
        assert server.decommissioned_at is not None

    async def test_decommission_migration(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="migrate-srv", endpoint=mock_server_url)
        created = await registry_service.register(params)
        await registry_service.decommission(created.id, phase="grace_period")
        result = await registry_service.decommission(created.id, phase="migration")

        assert result.phase == "migration"

    async def test_decommission_sunset(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="sunset-srv", endpoint=mock_server_url)
        created = await registry_service.register(params)
        await registry_service.decommission(created.id, phase="grace_period")
        await registry_service.decommission(created.id, phase="migration")
        result = await registry_service.decommission(created.id, phase="sunset")

        assert result.phase == "sunset"

    async def test_decommission_migration_with_replacement(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
    ) -> None:
        app1 = create_mock_mcp_server()
        app2 = create_mock_mcp_server()
        async with async_mock_server(app1) as url1, async_mock_server(app2) as url2:
            old_srv = await registry_service.register(
                ServerCreate(name="old", endpoint=url1)
            )
            replacement = await registry_service.register(
                ServerCreate(name="replacement", endpoint=url2)
            )
            await registry_service.decommission(old_srv.id, phase="grace_period")
            await registry_service.decommission(
                old_srv.id, phase="migration", replacement_id=replacement.id
            )

            old_obj = (
                await db_session.execute(
                    select(MCPServer).where(MCPServer.id == old_srv.id)
                )
            ).scalar_one()
            assert old_obj.decommission_phase == "migration"

    async def test_decommission_first_phase_must_be_grace_period(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="first-phase", endpoint=mock_server_url)
        created = await registry_service.register(params)
        with pytest.raises(DecommissionError, match="grace_period"):
            await registry_service.decommission(created.id, phase="migration")

    async def test_decommission_skip_from_grace_period_to_sunset(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="skip-to-sunset", endpoint=mock_server_url)
        created = await registry_service.register(params)
        await registry_service.decommission(created.id, phase="grace_period")
        with pytest.raises(DecommissionError, match="migration"):
            await registry_service.decommission(created.id, phase="sunset")

    async def test_decommission_logs_audit_event(
        self,
        registry_service_with_audit: RegistryService,
        mock_audit_service: Any,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="decom-audit", endpoint=mock_server_url)
        created = await registry_service_with_audit.register(params)
        await registry_service_with_audit.decommission(created.id, phase="grace_period")
        mock_audit_service.log_event.assert_awaited_with(
            event_type="server_decommissioned",
            actor="system",
            resource_id=str(created.id),
            metadata={
                "name": "decom-audit",
                "phase": "grace_period",
                "replacement_id": None,
            },
        )

    async def test_decommission_audit_failure_does_not_block(
        self,
        db_session: AsyncSession,
        mock_server_url: str,
    ) -> None:
        audit_mock = AsyncMock()
        audit_mock.log_event.side_effect = Exception("audit down")
        svc = RegistryService(
            db=db_session, mcp_client=MCPClient(), audit_service=audit_mock
        )
        params = ServerCreate(name="decom-audit-fail", endpoint=mock_server_url)
        created = await svc.register(params)
        result = await svc.decommission(created.id, phase="grace_period")
        assert result.phase == "grace_period"

    async def test_decommission_migration_redirects_mappings(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
    ) -> None:
        app1 = create_mock_mcp_server()
        app2 = create_mock_mcp_server()
        async with async_mock_server(app1) as url1, async_mock_server(app2) as url2:
            old_srv = await registry_service.register(
                ServerCreate(name="migrate-map", endpoint=url1)
            )
            old_obj = (
                await db_session.execute(
                    select(MCPServer).where(MCPServer.id == old_srv.id)
                )
            ).scalar_one()
            cap = Capability(name="test:cap", status="active")
            db_session.add(cap)
            await db_session.flush()
            mapping = CapabilityMapping(
                capability_id=cap.id, server_id=old_obj.id, tool_name="test_tool"
            )
            db_session.add(mapping)
            await db_session.commit()

            replacement = await registry_service.register(
                ServerCreate(name="replacement2", endpoint=url2)
            )
            await registry_service.decommission(old_srv.id, phase="grace_period")
            await registry_service.decommission(
                old_srv.id, phase="migration", replacement_id=replacement.id
            )
        mapping_check = (
            await db_session.execute(
                select(CapabilityMapping).where(CapabilityMapping.id == mapping.id)
            )
        ).scalar_one()
        assert mapping_check.server_id == replacement.id

    async def test_decommission_sunset_deletes_mappings(
        self,
        registry_service: RegistryService,
        db_session: AsyncSession,
    ) -> None:
        app = create_mock_mcp_server()
        async with async_mock_server(app) as url:
            srv = await registry_service.register(
                ServerCreate(name="sunset-map", endpoint=url)
            )
            srv_obj = (
                await db_session.execute(
                    select(MCPServer).where(MCPServer.id == srv.id)
                )
            ).scalar_one()
            cap = Capability(name="test:sunset-cap", status="active")
            db_session.add(cap)
            await db_session.flush()
            mapping = CapabilityMapping(
                capability_id=cap.id, server_id=srv_obj.id, tool_name="test_tool"
            )
            db_session.add(mapping)
            await db_session.commit()

            await registry_service.decommission(srv.id, phase="grace_period")
            await registry_service.decommission(srv.id, phase="migration")
            await registry_service.decommission(srv.id, phase="sunset")
        remaining = (
            await db_session.execute(
                select(CapabilityMapping).where(CapabilityMapping.server_id == srv.id)
            )
        ).scalars().all()
        assert len(remaining) == 0

    async def test_decommission_skip_phase_raises_error(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="skip-srv", endpoint=mock_server_url)
        created = await registry_service.register(params)
        with pytest.raises(DecommissionError, match="grace_period"):
            await registry_service.decommission(created.id, phase="sunset")

    async def test_decommission_invalid_phase(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="bad-phase", endpoint=mock_server_url)
        created = await registry_service.register(params)
        with pytest.raises(DecommissionError, match="Invalid phase"):
            await registry_service.decommission(created.id, phase="invalid")

    async def test_decommission_already_sunset(
        self,
        registry_service: RegistryService,
        mock_server_url: str,
    ) -> None:
        params = ServerCreate(name="done-srv", endpoint=mock_server_url)
        created = await registry_service.register(params)
        await registry_service.decommission(created.id, phase="grace_period")
        await registry_service.decommission(created.id, phase="migration")
        await registry_service.decommission(created.id, phase="sunset")
        with pytest.raises(DecommissionError, match="already fully decommissioned"):
            await registry_service.decommission(created.id, phase="grace_period")

    async def test_decommission_not_found(
        self,
        registry_service: RegistryService,
    ) -> None:
        with pytest.raises(ServerNotFoundError):
            await registry_service.decommission(uuid4(), phase="grace_period")


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

    async def test_list_servers_invalid_cursor(
        self,
        registry_service: RegistryService,
    ) -> None:
        result = await registry_service.list_servers(cursor="not-a-valid-cursor")
        assert len(result.servers) <= 5
