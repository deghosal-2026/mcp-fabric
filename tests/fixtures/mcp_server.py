"""In-process mock MCP server for testing MCPClient.

Implements a minimal FastAPI app that mimics the MCP protocol
(/tools/list and /tools/call) for use as a test fixture.
Provides an async context manager and a model factory for custom
server configurations.
"""

from __future__ import annotations

import asyncio
import socket
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress
from typing import Any

from fastapi import FastAPI
from fastapi.responses import JSONResponse
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
    tool_list = tools if tools is not None else [
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
            return JSONResponse({"error": "internal error"}, status_code=500)
        if list_delay > 0:
            await asyncio.sleep(list_delay)
        return {"tools": tool_list}

    @app.post("/tools/call")
    async def call_tool(body: ToolCallRequest):
        if body.name == fail_call:
            return JSONResponse({"error": "not found"}, status_code=404)
        if call_delay > 0:
            await asyncio.sleep(call_delay)
        response = responses.get(body.name, {"result": None})
        return response

    return app


@asynccontextmanager
async def async_mock_server(app: FastAPI) -> AsyncGenerator[str, None]:
    """Start a mock MCP server on a random port and yield its URL.

    Args:
        app: A configured FastAPI application.

    Yields:
        The server's base URL (e.g. http://127.0.0.1:54321).
        Server is shut down after the block exits.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]

    config = Config(app=app, host="127.0.0.1", port=port, log_level="critical")
    server = Server(config=config)
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
