"""MCP Client for communicating with MCP servers.

Provides MCPClient with methods to list tools, call tools, and detect
schema drift across inspections. Uses httpx for async HTTP and the
official MCP protocol format.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from opentelemetry.propagate import inject


class MCPError(Exception):
    """Base exception for all MCP client errors."""


class MCPTimeoutError(MCPError):
    """Raised when an MCP server does not respond within the timeout."""

    def __init__(self, endpoint: str, timeout: float) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        super().__init__(f"MCP server at {endpoint} timed out after {timeout}s")


class MCPServerError(MCPError):
    """Raised when an MCP server returns a non-2xx status code."""

    def __init__(self, status_code: int, endpoint: str, body: Any) -> None:
        self.status_code = status_code
        self.endpoint = endpoint
        self.body = body
        super().__init__(f"MCP server at {endpoint} returned {status_code}: {body}")


class MCPToolError(MCPError):
    """Raised when an MCP server rejects a tool invocation."""

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"Tool '{tool_name}' error: {message}")


class MCPConnectionError(MCPError):
    """Raised when a connection to an MCP server cannot be established."""

    def __init__(self, endpoint: str, original_error: str) -> None:
        self.endpoint = endpoint
        self.original_error = original_error
        super().__init__(f"Cannot connect to MCP server at {endpoint}: {original_error}")


@dataclass
class ToolDefinition:
    """Describes a single tool exposed by an MCP server."""

    name: str
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] | None = None


@dataclass
class ToolResponse:
    """Result from invoking a tool on an MCP server."""

    result: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""
    tool_name: str = ""


@dataclass
class ToolChange:
    """A detected change in a tool definition between inspections."""

    tool_name: str
    changes: dict[str, Any]
    is_breaking: bool


@dataclass
class ToolDiff:
    """Result of comparing two sets of tool definitions."""

    tools_added: list[ToolDefinition] = field(default_factory=list)
    tools_removed: list[ToolDefinition] = field(default_factory=list)
    tools_changed: list[ToolChange] = field(default_factory=list)


def _extract_tool_list(data: Any, endpoint: str) -> list[dict[str, Any]]:
    """Extract a list of tool dicts from an MCP /tools/list response.

    Args:
        data: Parsed JSON response body.
        endpoint: The server URL (for error messages).

    Returns:
        List of raw tool dicts.

    Raises:
        MCPServerError: The response does not contain a tool list.
    """
    maybe: Any
    if isinstance(data, list):
        maybe = data
    elif isinstance(data, dict):
        maybe = data.get("tools")
        if maybe is None:
            # Older or custom MCP servers may wrap tools under "result" instead of "tools"
            maybe = data.get("result")
        if maybe is None:
            raise MCPServerError(
                200, endpoint,
                "Unexpected /tools/list response: missing 'tools' or 'result' key",
            )
    else:
        raise MCPServerError(
            200, endpoint,
            f"Unexpected /tools/list response type: {type(data).__name__}",
        )
    if not isinstance(maybe, list):
        raise MCPServerError(
            200, endpoint,
            "Unexpected /tools/list response: missing array of tools",
        )
    return maybe


def compare_tool_definitions(prev: ToolDefinition, curr: ToolDefinition) -> ToolChange | None:
    """Compare two versions of the same tool and detect breaking changes.

    Args:
        prev: Previous version of the tool definition.
        curr: Current version of the tool definition.

    Returns:
        A ToolChange if differences are found, None if identical.
    """
    changes: dict[str, Any] = {}
    is_breaking = False

    if prev.description != curr.description:
        changes["description"] = {"old": prev.description, "new": curr.description}

    prev_params = prev.input_schema.get("properties", {}) if prev.input_schema else {}
    curr_params = curr.input_schema.get("properties", {}) if curr.input_schema else {}
    prev_required = set(prev.input_schema.get("required", []) if prev.input_schema else [])
    curr_required = set(curr.input_schema.get("required", []) if curr.input_schema else [])

    added_params = set(curr_params) - set(prev_params)
    removed_params = set(prev_params) - set(curr_params)
    new_required = curr_required - prev_required

    if added_params:
        changes["params_added"] = list(added_params)
    if removed_params:
        changes["params_removed"] = list(removed_params)
        is_breaking = True
    if new_required:
        changes["params_now_required"] = list(new_required)
        is_breaking = True

    if prev.output_schema != curr.output_schema:
        changes["output_schema"] = {"old": prev.output_schema, "new": curr.output_schema}
        if prev.output_schema is not None and curr.output_schema is not None:
            is_breaking = True

    if not changes:
        return None

    return ToolChange(tool_name=curr.name, changes=changes, is_breaking=is_breaking)


class MCPClient:
    """Async HTTP client for interacting with MCP servers.

    Wraps the MCP protocol (/tools/list, /tools/call) with configurable
    timeouts, retry logic, connection pooling, and health state tracking.
    """

    def __init__(
        self,
        default_timeout: float = 5.0,
        connect_timeout: float = 2.0,
        max_connections: int = 20,
        max_keepalive: int = 10,
    ) -> None:
        self.default_timeout = default_timeout
        self.connect_timeout = connect_timeout
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self._clients: dict[str, httpx.AsyncClient] = {}

    def _get_client(self, endpoint: str) -> httpx.AsyncClient:
        """Return a cached httpx client for the given endpoint.

        Args:
            endpoint: Base URL of the MCP server.

        Returns:
            A shared httpx AsyncClient with connection pooling.
        """
        if endpoint not in self._clients:
            limits = httpx.Limits(
                max_connections=self.max_connections,
                max_keepalive_connections=self.max_keepalive,
            )
            self._clients[endpoint] = httpx.AsyncClient(
                base_url=endpoint,
                limits=limits,
                timeout=httpx.Timeout(self.default_timeout, connect=self.connect_timeout),
            )
        return self._clients[endpoint]

    def _trace_headers(self) -> dict[str, str]:
        headers: dict[str, str] = {}
        inject(headers)
        return headers

    async def list_tools(
        self, endpoint: str, timeout: float | None = None
    ) -> list[ToolDefinition]:
        """Fetch the tool list from an MCP server's /tools/list endpoint.

        Args:
            endpoint: Base URL of the MCP server.
            timeout: Request timeout in seconds (uses default if None).

        Returns:
            Parsed list of ToolDefinition objects.

        Raises:
            MCPTimeoutError: Server did not respond in time.
            MCPServerError: Server returned a non-2xx status.
            MCPConnectionError: Network-level connection failure.
        """
        client = self._get_client(endpoint)
        effective_timeout = timeout or self.default_timeout
        try:
            response = await client.get(
                "/tools/list",
                headers=self._trace_headers(),
                timeout=httpx.Timeout(effective_timeout, connect=self.connect_timeout),
            )
        except httpx.TimeoutException:
            raise MCPTimeoutError(endpoint, effective_timeout) from None
        except httpx.ConnectError as exc:
            raise MCPConnectionError(endpoint, str(exc)) from exc

        if response.status_code >= 400:
            raise MCPServerError(response.status_code, endpoint, response.text)

        data = response.json()
        tools = _extract_tool_list(data, endpoint)
        return [
            ToolDefinition(
                name=t.get("name", ""),
                description=t.get("description"),
                input_schema=t.get("input_schema", t.get("parameters", {})),
                output_schema=t.get("output_schema"),
            )
            for t in tools
        ]

    async def call_tool(
        self,
        endpoint: str,
        tool_name: str,
        arguments: dict[str, Any] | None = None,
        timeout: float | None = None,
    ) -> ToolResponse:
        """Invoke a tool on an MCP server via /tools/call.

        Args:
            endpoint: Base URL of the MCP server.
            tool_name: Name of the tool to invoke.
            arguments: Parameters to pass to the tool.
            timeout: Request timeout in seconds (uses default if None).

        Returns:
            ToolResponse with the server's result.

        Raises:
            MCPTimeoutError: Server did not respond in time.
            MCPServerError: Server returned a non-2xx status.
            MCPToolError: Server rejected the tool call.
            MCPConnectionError: Network-level connection failure.
        """
        client = self._get_client(endpoint)
        effective_timeout = timeout or self.default_timeout
        payload = {"name": tool_name, "arguments": arguments or {}}
        try:
            response = await client.post(
                "/tools/call",
                json=payload,
                headers=self._trace_headers(),
                timeout=httpx.Timeout(effective_timeout, connect=self.connect_timeout),
            )
        except httpx.TimeoutException:
            raise MCPTimeoutError(endpoint, effective_timeout) from None
        except httpx.ConnectError as exc:
            raise MCPConnectionError(endpoint, str(exc)) from exc

        if response.status_code == 404:
            raise MCPToolError(tool_name, f"Tool not found at {endpoint}")
        if response.status_code >= 400:
            raise MCPServerError(response.status_code, endpoint, response.text)

        data = response.json()
        # MCP servers may respond with "result" (standard) or "content" (content-oriented tools)
        if "result" in data:
            result = data["result"]
        elif "content" in data:
            result = data["content"]
        else:
            raise MCPServerError(
                200, endpoint,
                "Unexpected /tools/call response: missing 'result' or 'content'",
            )
        return ToolResponse(
            result=result,
            metadata=data.get("metadata", {}),
            server_name=endpoint,
            tool_name=tool_name,
        )

    async def diff_tools(
        self,
        endpoint: str,
        previous_tools: list[ToolDefinition],
        timeout: float | None = None,
    ) -> ToolDiff:
        """Compare the current tool list against a previous snapshot.

        Args:
            endpoint: Base URL of the MCP server.
            previous_tools: Previously fetched tool definitions to diff against.
            timeout: Request timeout in seconds (uses default if None).

        Returns:
            ToolDiff with added, removed, and changed tools.
        """
        current_tools = await self.list_tools(endpoint, timeout=timeout)
        prev_by_name = {t.name: t for t in previous_tools}
        curr_by_name = {t.name: t for t in current_tools}

        added_names = set(curr_by_name) - set(prev_by_name)
        removed_names = set(prev_by_name) - set(curr_by_name)
        common_names = set(prev_by_name) & set(curr_by_name)

        tools_added = [curr_by_name[n] for n in added_names]
        tools_removed = [prev_by_name[n] for n in removed_names]

        tools_changed: list[ToolChange] = []
        for name in common_names:
            prev_tool = prev_by_name[name]
            curr_tool = curr_by_name[name]
            change = self._compare_tool_definitions(prev_tool, curr_tool)
            if change is not None:
                tools_changed.append(change)

        return ToolDiff(
            tools_added=tools_added,
            tools_removed=tools_removed,
            tools_changed=tools_changed,
        )

    def _compare_tool_definitions(
        self, prev: ToolDefinition, curr: ToolDefinition
    ) -> ToolChange | None:
        return compare_tool_definitions(prev, curr)

    async def close(self) -> None:
        """Close all cached HTTP clients and release connections."""
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
