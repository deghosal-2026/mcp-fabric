# Phase 2: MCP Client Layer

> **Tasks:** 12 · **Effort:** 12h (1.5 days)  
> **Dependencies:** Phase 0, Phase 1

### P2-01: MCPClient Class Structure
**Effort:** 1h | **Deps:** P0-07
**Checklist:**
- [ ] `api/mcp/__init__.py` — exports MCPClient
- [ ] `api/mcp/client.py` — class MCPClient with __init__(settings)
- [ ] Uses official `mcp` Python SDK
- [ ] httpx.AsyncClient with configurable timeout (default 5s)
- [ ] Retry logic: 1 retry with 1s backoff
- [ ] Connection error → MCPTimeoutError, non-200 → MCPServerError

**Success Criteria:** Client initializes. Connection to mock MCP server succeeds.

### P2-02: list_tools Method
**Effort:** 2h | **Deps:** P2-01
**Checklist:**
- [ ] `async list_tools(endpoint, timeout=5.0) -> list[ToolDefinition]`
- [ ] Calls GET /tools/list on target server
- [ ] Parses JSON response into ToolDefinition dataclass (name, description, input_schema JSON Schema, output_schema JSON Schema)
- [ ] Timeout handling: 5s hard timeout, raises MCPTimeoutError
- [ ] Response validation: checks expected MCP response structure
- [ ] Error handling: 4xx/5xx → MCPServerError with status code + body

**Success Criteria:** Real MCP server → tool list. Mock server → parsed correctly. Unreachable → MCPTimeoutError.

### P2-03: call_tool Method
**Effort:** 2h | **Deps:** P2-01
**Checklist:**
- [ ] `async call_tool(endpoint, tool_name, arguments, timeout=5.0) -> ToolResponse`
- [ ] Calls POST /tools/call with tool name + arguments in MCP protocol format
- [ ] Returns ToolResponse(result, metadata)
- [ ] Timeout: 5s with 1 retry
- [ ] Invalid tool → MCPToolError, timeout → MCPTimeoutError

**Success Criteria:** Call valid tool → response. Call invalid tool → MCPToolError. Timeout → MCPTimeoutError.

### P2-04: diff_tools Method
**Effort:** 2h | **Deps:** P2-02
**Checklist:**
- [ ] `async diff_tools(endpoint, previous_tools) -> ToolDiff`
- [ ] Calls list_tools, compares against previous ToolDefinition list
- [ ] Returns ToolDiff: tools_added list, tools_removed list, tools_changed list
- [ ] Change detection: param added → non-breaking, required param added → breaking, param removed → breaking, output schema changed → breaking
- [ ] Flags is_breaking per changed tool

**Success Criteria:** Identical tools → empty diff. New tool added → tools_added. Breaking change → is_breaking=True.

### P2-05: Error Types
**Effort:** 1h | **Deps:** P2-01
**Checklist:**
- [ ] MCPTimeoutError(error, endpoint, timeout) — timeout errors
- [ ] MCPServerError(status_code, endpoint, body) — HTTP errors from MCP server
- [ ] MCPToolError(tool_name, message) — invalid tool invocation
- [ ] MCPConnectionError(endpoint, original_error) — network/connection errors
- [ ] All extend FabricError for consistent error handling

**Success Criteria:** All error types catchable. Error messages include endpoint + context.

### P2-06: Health Integration
**Effort:** 1h | **Deps:** P2-02
**Checklist:**
- [ ] After each list_tools or call_tool: update Redis health state
- [ ] Key: fcp:health:{server_id}, value: "healthy" | "degraded", TTL: 60s
- [ ] On timeout: mark "degraded", increment Redis counter fcp:health:{server_id}:failures
- [ ] On success: mark "healthy", reset failure counter
- [ ] On connection error: mark "unhealthy" if failures > 3

**Success Criteria:** Healthy server → "healthy" in Redis. Timeout → "degraded". 4 consecutive failures → "unhealthy".

### P2-07: ToolDefinition Dataclass
**Effort:** 0.5h | **Deps:** None
**Checklist:**
- [ ] name: str, description: Optional[str], input_schema: dict, output_schema: Optional[dict]

### P2-08: ToolResponse Dataclass
**Effort:** 0.5h | **Deps:** None
**Checklist:**
- [ ] result: Any, metadata: dict, server_name: str, tool_name: str

### P2-09: ToolDiff Dataclass
**Effort:** 0.5h | **Deps:** P2-07
**Checklist:**
- [ ] tools_added: list[ToolDefinition], tools_removed: list[ToolDefinition], tools_changed: list[ToolChange]
- [ ] ToolChange: tool_name, changes dict, is_breaking bool

**Success Criteria:** Structures carry all diff information.

### P2-10: Connection Pool
**Effort:** 1h | **Deps:** P2-01
**Checklist:**
- [ ] httpx.AsyncClient with connection pool: max_connections=20, max_keepalive=10
- [ ] Per-endpoint client caching: dict[endpoint → client]
- [ ] Connection reuse for same server across requests
- [ ] Pool cleanup on shutdown

**Success Criteria:** Repeated calls to same endpoint reuse connection. Pool closed on app shutdown.

### P2-11: Timeout Configuration
**Effort:** 0.5h | **Deps:** P2-01
**Checklist:**
- [ ] Configurable per call: list_tools(timeout=5.0), call_tool(timeout=5.0)
- [ ] Default 5s from settings.MCP_TIMEOUT
- [ ] Connect timeout: 2s, read timeout: configurable, write timeout: configurable
- [ ] Admin UI health checks use shorter timeout (2s)

**Success Criteria:** Timeouts configurable per use case. Default 5s for agent requests, 2s for health checks.

### P2-12: MCPClient Unit Tests
**Effort:** 1h | **Deps:** P2-01 through P2-09
**Checklist:**
- [ ] Test list_tools with mock MCP server → returns tools
- [ ] Test call_tool with mock → returns response
- [ ] Test timeout → raises MCPTimeoutError
- [ ] Test unreachable → raises MCPConnectionError
- [ ] Test diff_tools with identical tools → empty diff
- [ ] Test diff_tools with added tool → tools_added populated
- [ ] Test diff_tools with changed param → is_breaking flag
- [ ] Test health integration → Redis updated

**Success Criteria:** 8/8 tests pass. Mock server in tests/fixtures/.
