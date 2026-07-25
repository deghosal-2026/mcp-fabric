"""MCP Client for communicating with MCP servers.

Provides MCPClient with methods to list tools, call tools, and detect
schema drift across inspections. Uses httpx for async HTTP and the
official MCP protocol format.

Architecture:
    - Exception hierarchy (MCPError base + 4 subclasses) maps every failure mode
      (timeout, connection error, HTTP error, tool rejection) to a distinct type
      so callers can handle each case specifically.
    - Dataclasses (ToolDefinition, ToolResponse, ToolDiff, ToolChange) serve as
      the typed contract between the MCP wire protocol and the rest of the codebase.
    - MCPClient pools httpx.AsyncClient instances per endpoint for connection reuse
      and injects OpenTelemetry trace context into every outgoing request for
      distributed tracing.
    - compare_tool_definitions() detects schema drift between inspections, flagging
      breaking changes (removed params, newly required params, output schema changes)
      that could break agents at runtime.

Usage:
    client = MCPClient()
    tools = await client.list_tools("http://localhost:8001")
    result = await client.call_tool("http://localhost:8001", "my_tool", {"arg": 1})
    diff = await client.diff_tools("http://localhost:8001", previous_snapshot)
    await client.close()
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import httpx
from opentelemetry.propagate import inject


class MCPError(Exception):
    """Base exception for all MCP client errors.

    All MCP-related exceptions inherit from this so callers can catch
    a single base type or handle specific subclasses individually.
    """


class MCPTimeoutError(MCPError):
    """Raised when an MCP server does not respond within the timeout.

    Stores the endpoint and timeout value so callers can log or surface
    which specific server is slow.
    """

    def __init__(self, endpoint: str, timeout: float) -> None:
        self.endpoint = endpoint
        self.timeout = timeout
        super().__init__(f"MCP server at {endpoint} timed out after {timeout}s")


class MCPServerError(MCPError):
    """Raised when an MCP server returns a non-2xx status code.

    Captures the HTTP status code, endpoint, and response body so
    callers can inspect the exact error returned by the server.
    Also raised when a 200 response has an unexpected payload shape
    (missing expected keys or wrong type).
    """

    def __init__(self, status_code: int, endpoint: str, body: Any) -> None:
        self.status_code = status_code
        self.endpoint = endpoint
        self.body = body
        super().__init__(f"MCP server at {endpoint} returned {status_code}: {body}")


class MCPToolError(MCPError):
    """Raised when an MCP server rejects a tool invocation.

    Distinct from MCPServerError: the server responded successfully at the
    HTTP layer (e.g. 200 or 404) but the tool call itself was invalid
    (tool not found, bad arguments, etc.).
    """

    def __init__(self, tool_name: str, message: str) -> None:
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"Tool '{tool_name}' error: {message}")


class MCPConnectionError(MCPError):
    """Raised when a connection to an MCP server cannot be established.

    Wraps network-level failures (DNS resolution failure, connection refused,
    SSL handshake errors) reported by httpx.ConnectError, preserving the
    original error message for diagnostics.
    """

    def __init__(self, endpoint: str, original_error: str) -> None:
        self.endpoint = endpoint
        self.original_error = original_error
        super().__init__(f"Cannot connect to MCP server at {endpoint}: {original_error}")


@dataclass
class ToolDefinition:
    """Describes a single tool exposed by an MCP server.

    Captures the tool's name, description, input schema (JSON Schema for
    parameters), and optional output schema. Used both as the return type
    from /tools/list and as the element type in diff snapshots.
    """

    name: str
    description: str | None = None
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] | None = None


@dataclass
class ToolResponse:
    """Result from invoking a tool on an MCP server.

    Contains the tool's return value (result), any metadata returned by
    the server, and identifiers (server_name, tool_name) for traceability.
    """

    result: Any
    metadata: dict[str, Any] = field(default_factory=dict)
    server_name: str = ""
    tool_name: str = ""


@dataclass
class ToolChange:
    """A detected change in a tool definition between inspections.

    Records what changed (changed field names and their old/new values)
    and whether the change is breaking (removed params, newly required
    params, or output schema changes).
    """

    tool_name: str
    changes: dict[str, Any]
    is_breaking: bool


@dataclass
class ToolDiff:
    """Result of comparing two sets of tool definitions.

    Produced by MCPClient.diff_tools(). Contains three lists:
      - tools_added: tools that exist now but did not before
      - tools_removed: tools that existed before but are now gone
      - tools_changed: tools whose definition changed (with breaking flag)
    """

    tools_added: list[ToolDefinition] = field(default_factory=list)
    tools_removed: list[ToolDefinition] = field(default_factory=list)
    tools_changed: list[ToolChange] = field(default_factory=list)


def _extract_tool_list(data: Any, endpoint: str) -> list[dict[str, Any]]:
    """Extract a list of tool dicts from an MCP /tools/list response.

    Handles three response shapes:
      1. A bare list (simplest MCP servers).
      2. A dict with a "tools" key (standard MCP format).
      3. A dict with a "result" key (wrapped response from some servers).

    Args:
        data: Parsed JSON response body.
        endpoint: The server URL (for error messages).

    Returns:
        List of raw tool dicts.

    Raises:
        MCPServerError: The response does not contain a tool list at any
            of the expected locations, or the value is not a list.
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
                200,
                endpoint,
                "Unexpected /tools/list response: missing 'tools' or 'result' key",
            )
    else:
        raise MCPServerError(
            200,
            endpoint,
            f"Unexpected /tools/list response type: {type(data).__name__}",
        )
    if not isinstance(maybe, list):
        raise MCPServerError(
            200,
            endpoint,
            "Unexpected /tools/list response: missing array of tools",
        )
    return maybe


def compare_tool_definitions(prev: ToolDefinition, curr: ToolDefinition) -> ToolChange | None:
    """Compare two versions of the same tool and detect breaking changes.

    Detects the following differences:
      - Description text changed.
      - Parameters added or removed from the input schema.
      - Existing parameters that became required (were optional, now required).
      - Output schema changed (if both previous and current define one).

    A change is considered *breaking* when:
      - A parameter was removed (downstream callers may still pass it).
      - A parameter became required (downstream callers may not pass it).
      - The output schema changed while both versions defined one.

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

    Design decisions:
      - Per-endpoint connection pooling (one httpx.AsyncClient per endpoint)
        avoids the overhead of creating a new TCP connection for every request.
      - Timeout are split into connect timeout (fast-fail on unreachable hosts)
        and default/request timeout (for slow tool responses).
      - OpenTelemetry trace context is injected into every outgoing request
        header so the entire request flow can be traced across service boundaries.
      - The class does NOT do its own retries; retry logic lives in the
        Celery tasks (api/tasks.py) that call this client.

    Usage:
        client = MCPClient(default_timeout=10.0)
        tools = await client.list_tools("http://localhost:8001")
        await client.close()
    """

    def __init__(
        self,
        default_timeout: float = 5.0,
        connect_timeout: float = 2.0,
        max_connections: int = 20,
        max_keepalive: int = 10,
    ) -> None:
        """Initialise the MCP client with configurable connection and timeout settings.

        Args:
            default_timeout: Default per-request timeout in seconds (5s default).
            connect_timeout: TCP connection timeout in seconds (2s default).
            max_connections: Maximum concurrent connections per endpoint (20 default).
            max_keepalive: Maximum keepalive connections to hold in the pool (10 default).
        """
        self.default_timeout = default_timeout
        self.connect_timeout = connect_timeout
        self.max_connections = max_connections
        self.max_keepalive = max_keepalive
        self._clients: dict[str, httpx.AsyncClient] = {}

    def _get_client(self, endpoint: str) -> httpx.AsyncClient:
        """Return a cached httpx client for the given endpoint.

        Maintains one httpx.AsyncClient per unique endpoint URL. Clients are
        created lazily on first access and reused for all subsequent requests
        to the same server. This provides:
          - Connection pooling (TCP connections are reused across requests).
          - Shared timeout configuration per endpoint.
          - Automatic keepalive management.

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
        """Generate HTTP headers carrying the current OpenTelemetry trace context.

        Calls opentelemetry.propagate.inject() to populate a dict with W3C
        traceparent/tracestate headers, which are then attached to every
        outbound request. This enables end-to-end distributed tracing across
        MCP Fabric and the MCP servers it communicates with.
        """
        headers: dict[str, str] = {}
        inject(headers)
        return headers

    async def list_tools(self, endpoint: str, timeout: float | None = None) -> list[ToolDefinition]:
        """Fetch the tool list from an MCP server's /tools/list endpoint.

        This is the discovery endpoint: it returns every tool the server
        exposes along with their JSON Schema input/output definitions.
        Results are cached at the caller level (no caching here) for
        periodic diffing by the schema drift detection system.

        Args:
            endpoint: Base URL of the MCP server.
            timeout: Request timeout in seconds (uses default if None).

        Returns:
            Parsed list of ToolDefinition objects.

        Raises:
            MCPTimeoutError: Server did not respond in time.
            MCPServerError: Server returned a non-2xx status or the
                response body is malformed.
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

        This is the execution endpoint: it sends the tool name and arguments
        to the MCP server and returns the result. The response body is
        flexible — it accepts both "result" (standard MCP) and "content"
        (content-oriented tools) response keys.

        A 404 response is treated as an MCPToolError (tool not found on that
        server), while other 4xx/5xx responses raise MCPServerError.

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
            MCPToolError: Tool not found or server rejected the call.
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
                200,
                endpoint,
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

        Used by the schema drift detection system to identify tools that
        have been added, removed, or changed since the last inspection.
        Changes are flagged as breaking or non-breaking using
        compare_tool_definitions().

        Typical flow:
          1. On first inspection, store the tool list somewhere (DB, cache).
          2. On subsequent inspections, call diff_tools() with the stored list.
          3. If the ToolDiff shows any changes, trigger a notification
             (e.g. notify_schema_change Celery task).

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
        """Close all cached HTTP clients and release connections.

        MUST be called when the MCPClient is no longer needed to avoid
        leaking connections. Iterates over every cached httpx.AsyncClient,
        calls aclose() on each, then clears the internal client dict.
        """
        for client in self._clients.values():
            await client.aclose()
        self._clients.clear()
