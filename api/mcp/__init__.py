"""MCP Client — async HTTP client for MCP server communication.

Provides the MCPClient class for listing tools, invoking tools, and
detecting schema drift across MCP servers. Exports all dataclasses
and error types for use by services and tests.
"""

from api.mcp.client import (
    MCPClient,
    MCPConnectionError,
    MCPError,
    MCPServerError,
    MCPTimeoutError,
    MCPToolError,
    ToolChange,
    ToolDefinition,
    ToolDiff,
    ToolResponse,
)

__all__ = [
    "MCPClient",
    "MCPConnectionError",
    "MCPError",
    "MCPServerError",
    "MCPTimeoutError",
    "MCPToolError",
    "ToolChange",
    "ToolDefinition",
    "ToolDiff",
    "ToolResponse",
]
