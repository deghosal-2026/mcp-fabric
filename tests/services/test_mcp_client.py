"""Tests for the MCP Client layer.

Covers list_tools, call_tool, diff_tools, error types, timeout
handling, malformed response validation, and the mock MCP server fixture.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Any

import pytest
import pytest_asyncio
from fastapi import Body, FastAPI

from api.mcp.client import (
    MCPClient,
    MCPConnectionError,
    MCPServerError,
    MCPTimeoutError,
    MCPToolError,
    ToolDefinition,
)
from tests.fixtures.mcp_server import async_mock_server, create_mock_mcp_server


@pytest_asyncio.fixture
async def client() -> AsyncGenerator[MCPClient, None]:
    """Provide an MCPClient with short timeouts for fast test failures."""
    c = MCPClient(default_timeout=5.0, connect_timeout=1.0)
    try:
        yield c
    finally:
        await c.close()


class TestListTools:
    """Tests for MCPClient.list_tools()."""

    async def test_list_tools_returns_tools(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        tools = await client.list_tools(mock_mcp_server)
        assert len(tools) >= 1
        assert isinstance(tools[0], ToolDefinition)
        assert tools[0].name == "test_tool"

    async def test_list_tools_parses_schema(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        tools = await client.list_tools(mock_mcp_server)
        tool = next(t for t in tools if t.name == "test_tool")
        assert tool.input_schema == {
            "type": "object",
            "properties": {"x": {"type": "string"}},
            "required": ["x"],
        }
        expected_output = {
            "type": "object",
            "properties": {"result": {"type": "string"}},
        }
        assert tool.output_schema == expected_output

    async def test_list_tools_server_error(self, client: MCPClient) -> None:
        async with async_mock_server(create_mock_mcp_server(fail_list=True)) as url:
            with pytest.raises(MCPServerError) as exc:
                await client.list_tools(url)
            assert exc.value.status_code == 500

    async def test_list_tools_connection_error(self, client: MCPClient) -> None:
        with pytest.raises(MCPConnectionError):
            await client.list_tools("http://127.0.0.1:1")

    async def test_list_tools_malformed_dict_response(self, client: MCPClient) -> None:
        """Server returns a dict without a 'tools' key."""
        app = FastAPI()

        @app.get("/tools/list")
        async def list_tools():
            return {"not_tools": "oops"}

        async with async_mock_server(app) as url:
            with pytest.raises(MCPServerError) as exc:
                await client.list_tools(url)
            assert "missing" in str(exc.value).lower()

    async def test_list_tools_malformed_non_list_non_dict(self, client: MCPClient) -> None:
        """Server returns a string instead of a list or dict."""
        app = FastAPI()

        @app.get("/tools/list")
        async def list_tools():
            return "just a string"

        async with async_mock_server(app) as url:
            with pytest.raises(MCPServerError) as exc:
                await client.list_tools(url)
            assert "unexpected" in str(exc.value).lower()


class TestCallTool:
    """Tests for MCPClient.call_tool()."""

    async def test_call_tool_returns_result(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        response = await client.call_tool(mock_mcp_server, "test_tool", {"x": "hello"})
        assert response.result == "done"
        assert response.tool_name == "test_tool"
        assert response.server_name == mock_mcp_server

    async def test_call_tool_without_arguments(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        response = await client.call_tool(mock_mcp_server, "search")
        assert response.result == ["item1", "item2"]
        assert response.metadata == {"count": 2}

    async def test_call_tool_not_found(self, client: MCPClient) -> None:
        async with async_mock_server(
            create_mock_mcp_server(fail_call="nonexistent")
        ) as url:
            with pytest.raises(MCPToolError) as exc:
                await client.call_tool(url, "nonexistent")
            assert "nonexistent" in str(exc.value)

    async def test_call_tool_timeout(self, client: MCPClient) -> None:
        async with async_mock_server(
            create_mock_mcp_server(call_delay=0.5)
        ) as url:
            c = MCPClient(default_timeout=0.1, connect_timeout=0.1)
            with pytest.raises(MCPTimeoutError):
                await c.call_tool(url, "test_tool")
            await c.close()

    async def test_call_tool_content_key(self, client: MCPClient) -> None:
        """Server responds with 'content' key (MCP content-based response)."""
        app = FastAPI()

        @app.post("/tools/call")
        async def call_tool(body: dict[str, Any] = Body(...)):
            return {"content": [{"type": "text", "text": "hello world"}]}

        async with async_mock_server(app) as url:
            response = await client.call_tool(url, "test", {})
            assert response.result == [{"type": "text", "text": "hello world"}]

    async def test_call_tool_unexpected_response(self, client: MCPClient) -> None:
        """Server returns a dict without 'result' or 'content' keys."""
        app = FastAPI()

        @app.post("/tools/call")
        async def call_tool(body: dict[str, Any] = Body(...)):
            return {"something_else": 42}

        async with async_mock_server(app) as url:
            with pytest.raises(MCPServerError) as exc:
                await client.call_tool(url, "test", {})
            assert "missing" in str(exc.value).lower()


class TestDiffTools:
    """Tests for MCPClient.diff_tools()."""

    async def test_diff_identical_tools(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        prev = await client.list_tools(mock_mcp_server)
        diff = await client.diff_tools(mock_mcp_server, prev)
        assert len(diff.tools_added) == 0
        assert len(diff.tools_removed) == 0
        assert len(diff.tools_changed) == 0

    async def test_diff_detects_added_tool(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        prev = [ToolDefinition(name="old_tool", input_schema={})]
        diff = await client.diff_tools(mock_mcp_server, prev)
        assert any(t.name == "test_tool" for t in diff.tools_added)
        assert any(t.name == "search" for t in diff.tools_added)
        assert any(t.name == "old_tool" for t in diff.tools_removed)
        assert diff.tools_changed == []

    async def test_diff_detects_removed_tool(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        prev = await client.list_tools(mock_mcp_server)
        extra = ToolDefinition(name="extra_tool", input_schema={})
        prev.append(extra)
        diff = await client.diff_tools(mock_mcp_server, prev)
        assert any(t.name == "extra_tool" for t in diff.tools_removed)

    async def test_diff_detects_param_removed_breaking(self) -> None:
        prev = ToolDefinition(
            name="tool",
            input_schema={"type": "object", "properties": {"x": {}, "y": {}}},
        )
        curr = ToolDefinition(
            name="tool",
            input_schema={"type": "object", "properties": {"x": {}}},
        )
        c = MCPClient()
        change = c._compare_tool_definitions(prev, curr)
        assert change is not None
        assert change.is_breaking
        assert "params_removed" in change.changes

    async def test_diff_detects_new_required_param_breaking(self) -> None:
        prev = ToolDefinition(
            name="tool",
            input_schema={
                "type": "object",
                "properties": {"x": {}},
                "required": [],
            },
        )
        curr = ToolDefinition(
            name="tool",
            input_schema={
                "type": "object",
                "properties": {"x": {}, "y": {}},
                "required": ["y"],
            },
        )
        c = MCPClient()
        change = c._compare_tool_definitions(prev, curr)
        assert change is not None
        assert change.is_breaking
        assert "params_now_required" in change.changes

    async def test_diff_output_schema_change_breaking(self) -> None:
        prev = ToolDefinition(name="tool", input_schema={}, output_schema={"type": "string"})
        curr = ToolDefinition(name="tool", input_schema={}, output_schema={"type": "integer"})
        c = MCPClient()
        change = c._compare_tool_definitions(prev, curr)
        assert change is not None
        assert change.is_breaking
        assert "output_schema" in change.changes

    async def test_diff_no_change_when_identical(self) -> None:
        prev = ToolDefinition(name="tool", input_schema={"type": "object"}, description="desc")
        curr = ToolDefinition(name="tool", input_schema={"type": "object"}, description="desc")
        c = MCPClient()
        change = c._compare_tool_definitions(prev, curr)
        assert change is None


class TestMCPClientErrors:
    """Tests for MCP client error types and edge cases."""

    async def test_error_messages_include_context(self) -> None:
        err = MCPTimeoutError("http://example.com", 5.0)
        assert "example.com" in str(err)
        assert "5.0" in str(err)

        err2 = MCPServerError(500, "http://example.com", "internal error")
        assert "500" in str(err2)

        err3 = MCPToolError("my_tool", "not available")
        assert "my_tool" in str(err3)

        err4 = MCPConnectionError("http://example.com", "connection refused")
        assert "connection refused" in str(err4)

    async def test_create_and_close_client(self) -> None:
        c = MCPClient()
        await c.close()
        assert len(c._clients) == 0

    async def test_connection_pool_reuse(
        self, client: MCPClient, mock_mcp_server: str
    ) -> None:
        await client.list_tools(mock_mcp_server)
        await client.list_tools(mock_mcp_server)
        assert mock_mcp_server in client._clients
