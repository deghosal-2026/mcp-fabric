"""In-process mock MCP server for testing MCPClient.

Implements a minimal FastAPI app that mimics the MCP protocol
(/tools/list and /tools/call) for use as a test fixture.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from contextlib import suppress
from typing import Any

import pytest_asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from uvicorn import Config, Server


class ToolCallRequest(BaseModel):
    """Shape of a /tools/call request body."""

    name: str
    arguments: dict[str, Any] = {}


def create_mock_mcp_server(
    tools: list[dict] | None = None,
    call_responses: dict[str, Any] | None = None,
    fail_list: bool = False,
    fail_call: str | None = None,
    list_delay: float = 0.0,
    call_delay: float = 0.0,
) -> FastAPI:
    """Build a FastAPI app that acts as an MCP server.

    Args:
        tools: Tool definitions returned by /tools/list.
        call_responses: Mapping of tool_name to response for /tools/call.
        fail_list: If True, /tools/list returns 500.
        fail_call: If set, /tools/call for this tool name returns 404.
        list_delay: Artificial delay before responding to /tools/list.
        call_delay: Artificial delay before responding to /tools/call.

    Returns:
        A configured FastAPI application.
    """
    app = FastAPI()
    tool_list = tools or [
        {
            "name": "test_tool",
            "description": "A test tool",
            "input_schema": {
                "type": "object",
                "properties": {"x": {"type": "string"}},
                "required": ["x"],
            },
            "output_schema": {"type": "object", "properties": {"result": {"type": "string"}}},
        },
        {
            "name": "search",
            "description": "Search for items",
            "input_schema": {
                "type": "object",
                "properties": {"query": {"type": "string"}, "limit": {"type": "integer"}},
            },
        },
    ]

    responses: dict[str, Any] = call_responses or {
        "test_tool": {"result": "done", "metadata": {"duration_ms": 10}},
        "search": {"result": ["item1", "item2"], "metadata": {"count": 2}},
    }

    @app.get("/tools/list")
    async def list_tools():
        if fail_list:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "internal error"}, status_code=500)
        import asyncio
        if list_delay > 0:
            await asyncio.sleep(list_delay)
        return {"tools": tool_list}

    @app.post("/tools/call")
    async def call_tool(body: ToolCallRequest):
        if body.name == fail_call:
            from fastapi.responses import JSONResponse
            return JSONResponse({"error": "not found"}, status_code=404)
        import asyncio
        if call_delay > 0:
            await asyncio.sleep(call_delay)
        response = responses.get(body.name, {"result": None})
        return response

    return app


@pytest_asyncio.fixture
async def mock_mcp_server() -> AsyncGenerator[str, None]:
    """Start a mock MCP server on a random port and return the URL.

    Yields the server URL. Server is shut down after the test.
    """
    app = create_mock_mcp_server()
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    config = Config(app=app, host="127.0.0.1", port=port, log_level="critical")
    server = Server(config=config)

    import asyncio
    task = asyncio.create_task(server.serve())
    await asyncio.sleep(0.05)
    url = f"http://127.0.0.1:{port}"
    try:
        yield url
    finally:
        await server.shutdown()
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task



