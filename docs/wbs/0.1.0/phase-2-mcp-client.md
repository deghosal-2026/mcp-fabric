# Phase 2: MCP Client Layer

> **Tasks:** 12 · **Effort:** 12h (1.5 days)  
> **Status:** ✅ COMPLETE — 12 tasks finished, 18 MCPClient tests, lint + typecheck clean  
> **Dependencies:** Phase 0, Phase 1

### P2-01: MCPClient Class Structure (#221)
**Effort:** 1h | **Deps:** P0-07
**Status:** ✅ Complete — `api/mcp/client.py:MCPClient`
- [x] `api/mcp/__init__.py` — exports MCPClient
- [x] `api/mcp/client.py` — class MCPClient with __init__(settings)
- [x] Uses httpx.AsyncClient with configurable timeout (default 5s)
- [x] Retry logic: 1 retry via httpx transport
- [x] Connection error → MCPConnectionError, non-200 → MCPServerError

### P2-02: list_tools Method (#222)
**Effort:** 2h | **Deps:** P2-01
**Status:** ✅ Complete — `api/mcp/client.py:MCPClient.list_tools`
- [x] `async list_tools(endpoint, timeout=5.0) -> list[ToolDefinition]`
- [x] Calls GET /tools/list on target server
- [x] Parses JSON response into ToolDefinition dataclass
- [x] Timeout handling: configurable, raises MCPTimeoutError
- [x] Response validation: parses various MCP response shapes
- [x] Error handling: 4xx/5xx → MCPServerError

### P2-03: call_tool Method (#223)
**Effort:** 2h | **Deps:** P2-01
**Status:** ✅ Complete — `api/mcp/client.py:MCPClient.call_tool`
- [x] `async call_tool(endpoint, tool_name, arguments, timeout=5.0) -> ToolResponse`
- [x] Calls POST /tools/call with tool name + arguments
- [x] Returns ToolResponse(result, metadata)
- [x] Timeout: configurable with 1 retry
- [x] Invalid tool → MCPToolError, timeout → MCPTimeoutError

### P2-04: diff_tools Method (#224)
**Effort:** 2h | **Deps:** P2-02
**Status:** ✅ Complete — `api/mcp/client.py:MCPClient.diff_tools`
- [x] `async diff_tools(endpoint, previous_tools) -> ToolDiff`
- [x] Calls list_tools, compares against previous ToolDefinition list
- [x] Returns ToolDiff: tools_added, tools_removed, tools_changed
- [x] Change detection: param added → non-breaking, required param added → breaking, param removed → breaking
- [x] Flags is_breaking per changed tool

### P2-05: Error Types (#225)
**Effort:** 1h | **Deps:** P2-01
**Status:** ✅ Complete — `api/mcp/client.py` error classes
- [x] MCPTimeoutError(error, endpoint, timeout)
- [x] MCPServerError(status_code, endpoint, body)
- [x] MCPToolError(tool_name, message)
- [x] MCPConnectionError(endpoint, original_error)
- [x] All extend MCPError base class

### P2-06: Health Integration (#226)
**Effort:** 1h | **Deps:** P2-02
**Status:** ⏳ Deferred — Redis health state tracking moved to Phase 3 (RegistryService). MCPClient remains stateless.

### P2-07: ToolDefinition Dataclass (#227)
**Effort:** 0.5h | **Deps:** None
**Status:** ✅ Complete — `api/mcp/client.py:ToolDefinition`
- [x] name, description, input_schema, output_schema with proper types

### P2-08: ToolResponse Dataclass (#228)
**Effort:** 0.5h | **Deps:** None
**Status:** ✅ Complete — `api/mcp/client.py:ToolResponse`
- [x] result, metadata, server_name, tool_name

### P2-09: ToolDiff Dataclass (#229)
**Effort:** 0.5h | **Deps:** P2-07
**Status:** ✅ Complete — `api/mcp/client.py:ToolDiff`
- [x] tools_added, tools_removed, tools_changed
- [x] ToolChange: tool_name, changes dict, is_breaking bool

### P2-10: Connection Pool (#230)
**Effort:** 1h | **Deps:** P2-01
**Status:** ✅ Complete — `api/mcp/client.py:MCPClient._get_client`
- [x] httpx.AsyncClient with connection pooling: max_connections=20, max_keepalive=10
- [x] Per-endpoint client caching: dict[endpoint→client]
- [x] Connection reuse for same server across requests
- [x] Pool cleanup via `close()` method

### P2-11: Timeout Configuration (#231)
**Effort:** 0.5h | **Deps:** P2-01
**Status:** ✅ Complete
- [x] Configurable per call: list_tools(timeout=5.0), call_tool(timeout=5.0)
- [x] Default 5s from settings
- [x] Connect timeout: 2s, read/write timeout: configurable

### P2-12: MCPClient Unit Tests (#232)
**Effort:** 1h | **Deps:** P2-01 through P2-09
**Status:** ✅ Complete — `tests/services/test_mcp_client.py`
- [x] Test list_tools with mock MCP server → returns tools
- [x] Test call_tool with mock → returns response
- [x] Test timeout → raises MCPTimeoutError
- [x] Test unreachable → raises MCPConnectionError
- [x] Test server error → raises MCPServerError
- [x] Test tool not found → raises MCPToolError
- [x] Test diff_tools with identical tools → empty diff
- [x] Test diff_tools with added tool → tools_added
- [x] Test diff_tools with removed tool → tools_removed
- [x] Test diff_tools with changed param → is_breaking flag
- [x] Test diff_tools with new required param → is_breaking
- [x] Test output schema change → is_breaking
- [x] Test connection pool reuse
- [x] Test create/close client lifecycle
- [x] Test error messages include context
