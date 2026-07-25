"""MCP server registry — register, inspect, list, and decommission servers.

Manages the lifecycle of MCP server endpoints, including tool schema
discovery, health tracking, decommissioning with dependency reporting,
and Redis-backed health caching.

Architectural notes:
  - Server registration involves tool discovery: when a server is registered,
    an MCPClient lists its tools and persists them as ServerTool rows.
  - Inspection detects schema changes (added, removed, changed tools) and
    records ToolVersion rows for audit trail. Breaking changes are flagged.
  - Decommission follows a phased approach (grace_period -> migration -> sunset)
    to give dependent teams time to migrate.
  - Health status is cached in Redis with a 60s TTL for fast reads.
  - Audit events are logged for registration and inspection schema changes,
    but audit failures never block the main operation.
  - Cursor-based pagination is used for listing servers (not offset/limit)
    for consistent results under concurrent writes.
"""

from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime
from typing import Any, cast
from uuid import UUID

from redis.asyncio import Redis
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.mcp import MCPClient, MCPError, ToolDefinition, compare_tool_definitions
from api.models import MCPServer, ServerTool, ToolVersion
from api.schemas.agent import TrustAssignmentResponse
from api.schemas.capability import CapabilityMappingResponse
from api.schemas.common import PaginatedServers, PaginationMeta
from api.schemas.server import (
    DecommissionResult,
    DecommissionTimeline,
    DependencyReport,
    RoutingRuleResponse,
    ServerCreate,
    ServerDetail,
    ServerInspectResponse,
    ServerResponse,
    ToolResponse,
    ToolVersionResponse,
)
from api.schemas.server import (
    ToolChange as ToolChangeSchema,
)
from api.services.exceptions import (
    DecommissionError,
    DuplicateServerError,
    ServerNotFoundError,
    ServerUnreachableError,
)
from api.tasks import notify_schema_change

logger = logging.getLogger(__name__)

# Tools with these prefixes are considered read-only for trust-level heuristics.
_READ_ONLY_PREFIXES = ("get", "list", "search", "read", "find", "query", "check")


def _is_read_only_tool(tool: ToolDefinition) -> bool:
    """Return True if the tool name starts with a known read-only prefix.

    WHY: Used by the trust level suggestion heuristic. A server that only
    exposes read-only tools can be suggested as 'trusted' automatically,
    while servers with mutation tools default to 'unreviewed'.
    """
    name = tool.name.lower()
    return any(name.startswith(p) for p in _READ_ONLY_PREFIXES)


def _suggest_trust_level(tools: list[ToolDefinition]) -> str:
    """Suggest 'trusted' if all tools are read-only, otherwise 'unreviewed'.

    WHY: Automation-friendly heuristic — servers with only read-only tools
    are lower risk and can be auto-trusted. This is a suggestion; admins
    can override it via trust assignments.
    """
    if tools and all(_is_read_only_tool(t) for t in tools):
        return "trusted"
    return "unreviewed"


class RegistryService:
    """MCP server registry — register, inspect, list, decommission, and monitor server health.

    Depends on:
      - AsyncSession for DB access
      - MCPClient for communicating with MCP server endpoints
      - AuditService (optional) for audit logging
      - Redis client (optional) for health status caching

    Used by: admin server management UI, automated server discovery pipeline.
    """

    def __init__(
        self,
        db: AsyncSession,
        mcp_client: MCPClient,
        audit_service: Any | None = None,
        redis_client: Redis | None = None,
    ) -> None:
        self.db = db
        self.mcp = mcp_client
        self.audit = audit_service
        self.redis = redis_client

    async def register(self, params: ServerCreate) -> ServerResponse:
        """Register a new MCP server, discover its tools, and suggest a trust level.

        WHY: Admin user journey — add a new MCP server to the fabric.
        The registration process:
          1. Check for duplicate endpoint.
          2. Connect to the server and discover its tools (via MCP protocol).
          3. Suggest a trust level based on tool read-only heuristics.
          4. Persist the server and its tools in a transaction.
          5. Log an audit event (best-effort, failure does not roll back registration).

        RAISES:
          - DuplicateServerError if the endpoint is already registered.
          - ServerUnreachableError if the MCP server does not respond.

        SIDE EFFECTS: Creates MCPServer + ServerTool rows, logs audit event.
        """
        result = await self.db.execute(
            select(MCPServer).where(MCPServer.endpoint == params.endpoint)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            raise DuplicateServerError(params.endpoint)

        try:
            tools = await self.mcp.list_tools(params.endpoint)
        except MCPError as exc:
            raise ServerUnreachableError(params.endpoint) from exc

        trust_level = _suggest_trust_level(tools)
        now = datetime.now(UTC)

        server = MCPServer(
            name=params.name,
            endpoint=params.endpoint,
            owner_team=params.owner_team,
            description=params.description,
            labels=params.labels,
            team_namespace=params.team_namespace,
            trust_level=trust_level,
            health_status="unknown",
            updated_at=now,
        )
        self.db.add(server)
        # Flush to get the server.id before creating tools that reference it.
        await self.db.flush()

        for tool_def in tools:
            tool = ServerTool(
                server_id=server.id,
                tool_name=tool_def.name,
                description=tool_def.description,
                input_schema=tool_def.input_schema,
                output_schema=tool_def.output_schema,
            )
            self.db.add(tool)

        await self.db.commit()
        await self.db.refresh(server, ["tools"])

        # Audit logging is best-effort. A failure here should not prevent
        # the server from being registered. The try/except ensures resilience.
        if self.audit is not None:
            try:
                await self.audit.log_event(
                    event_type="server_registered",
                    actor="system",
                    resource_id=str(server.id),
                    metadata={"name": server.name, "endpoint": server.endpoint},
                )
            except Exception:
                logger.exception("Failed to log audit event for server registration")

        return ServerResponse.model_validate(server)

    async def inspect(self, server_id: UUID) -> ServerInspectResponse:
        """Inspect a server, detect tool changes (added, removed, changed), and record versions.

        WHY: Admin or automated pipeline — re-discover a server's tools and
        detect schema changes since the last inspection. Each detected change:
          - Added tools: new ServerTool rows created.
          - Removed tools: ServerTool rows deleted, ToolVersion recorded as breaking.
          - Changed tools: ToolVersion recorded with is_breaking flag,
            ServerTool schema updated.

        Uses compare_tool_definitions() for schema diffing. Breaking changes
        are those that would break existing callers (e.g., removed required params).

        SIDE EFFECTS:
          - Creates/deletes ServerTool rows.
          - Creates ToolVersion rows for any change.
          - Updates server.health_status to 'reachable'.
          - Logs audit event if any changes detected.
          - Dispatches async notification task.

        RAISES:
          - ServerNotFoundError if server_id is missing.
          - ServerUnreachableError if the MCP server does not respond.
        """
        result = await self.db.execute(
            select(MCPServer)
            .options(selectinload(MCPServer.tools))
            .where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        if server is None:
            raise ServerNotFoundError(str(server_id))

        try:
            current_defs = await self.mcp.list_tools(server.endpoint)
        except MCPError as exc:
            raise ServerUnreachableError(server.endpoint) from exc

        # Index tools by name for efficient comparison.
        db_by_name = {t.tool_name: t for t in server.tools}
        curr_by_name = {t.name: t for t in current_defs}

        db_names = set(db_by_name)
        curr_names = set(curr_by_name)

        added_names = curr_names - db_names
        removed_names = db_names - curr_names
        common_names = db_names & curr_names

        now = datetime.now(UTC)
        removed_responses: list[ToolResponse] = []
        changed_schema: list[ToolChangeSchema] = []

        for name in removed_names:
            tool = db_by_name[name]
            removed_responses.append(
                ToolResponse(
                    id=tool.id,
                    tool_name=tool.tool_name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                    output_schema=tool.output_schema,
                )
            )
            # Removed tools are always marked as breaking (existing callers will fail).
            self.db.add(
                ToolVersion(
                    server_id=server.id,
                    tool_name=tool.tool_name,
                    input_schema=tool.input_schema,
                    output_schema=tool.output_schema,
                    is_breaking=True,
                )
            )
            await self.db.delete(tool)

        for name in common_names:
            db_tool = db_by_name[name]
            curr_def = curr_by_name[name]
            prev_def = ToolDefinition(
                name=db_tool.tool_name,
                description=db_tool.description,
                input_schema=db_tool.input_schema,
                output_schema=db_tool.output_schema,
            )
            change = compare_tool_definitions(prev_def, curr_def)
            if change is not None:
                self.db.add(
                    ToolVersion(
                        server_id=server.id,
                        tool_name=db_tool.tool_name,
                        input_schema=db_tool.input_schema,
                        output_schema=db_tool.output_schema,
                        is_breaking=change.is_breaking,
                    )
                )
                db_tool.description = curr_def.description
                db_tool.input_schema = curr_def.input_schema
                db_tool.output_schema = curr_def.output_schema
                changed_schema.append(
                    ToolChangeSchema(
                        tool_name=name,
                        changes=change.changes,
                        is_breaking=change.is_breaking,
                    )
                )

        added_responses: list[ToolResponse] = []
        for name in added_names:
            curr_def = curr_by_name[name]
            tool = ServerTool(
                server_id=server.id,
                tool_name=curr_def.name,
                description=curr_def.description,
                input_schema=curr_def.input_schema,
                output_schema=curr_def.output_schema,
            )
            self.db.add(tool)
            await self.db.flush()
            added_responses.append(
                ToolResponse(
                    id=tool.id,
                    tool_name=tool.tool_name,
                    description=tool.description,
                    input_schema=tool.input_schema,
                    output_schema=tool.output_schema,
                )
            )

        server.updated_at = now
        server.health_status = "reachable"
        await self.db.commit()
        await self.db.refresh(server, ["tools"])

        # Audit logging for schema changes is best-effort.
        if self.audit is not None and (added_names or removed_names or changed_schema):
            try:
                await self.audit.log_event(
                    event_type="schema_change_detected",
                    actor="system",
                    resource_id=str(server.id),
                    metadata={
                        "name": server.name,
                        "tools_added": len(added_names),
                        "tools_removed": len(removed_names),
                        "tools_changed": len(changed_schema),
                    },
                )
            except Exception:
                logger.exception("Failed to log audit event for schema change")

        # Async notification to subscribers (e.g., Slack webhook, email).
        # Uses Celery's delay() for fire-and-forget execution.
        if added_names or removed_names or changed_schema:
            try:
                cast(Any, notify_schema_change).delay(
                    server_id=str(server.id),
                    server_name=server.name,
                    tools_added=list(added_names),
                    tools_removed=list(removed_names),
                    tools_changed=[
                        {"tool_name": t.tool_name, "is_breaking": t.is_breaking}
                        for t in changed_schema
                    ],
                )
            except Exception:
                logger.exception("Failed to dispatch schema change notification")

        base = ServerResponse.model_validate(server)
        return ServerInspectResponse(
            **base.model_dump(),
            tools_added=added_responses,
            tools_removed=removed_responses,
            tools_changed=changed_schema,
        )

    async def list_servers(
        self,
        team: str | None = None,
        trust: str | None = None,
        health: str | None = None,
        search: str | None = None,
        cursor: str | None = None,
        per_page: int = 50,
    ) -> PaginatedServers:
        """List servers with optional filters and cursor-based pagination.

        WHY: Admin UI — browse servers with filtering by team, trust level,
        health status, or name search.

        Uses cursor-based pagination instead of offset/limit. Cursor pagination
        is more reliable under concurrent writes because the cursor references
        a specific position in the result set that doesn't shift when rows are
        added/deleted.

        Cursor format: base64url-encoded JSON {"t": timestamp, "i": server_id}.
        The cursor encodes both the created_at timestamp and the id (for tie-breaking).

        Filters are composable (e.g., team + health + search can be combined).
        """
        query = select(MCPServer).options(selectinload(MCPServer.tools))

        if team is not None:
            query = query.where(MCPServer.team_namespace == team)
        if trust is not None:
            query = query.where(MCPServer.trust_level == trust)
        if health is not None:
            query = query.where(MCPServer.health_status == health)
        if search is not None:
            # ilike is case-insensitive, supported by PostgreSQL and SQLite.
            query = query.where(MCPServer.name.ilike(f"%{search}%"))

        # Count query for total metadata.
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        if cursor is not None:
            try:
                raw = base64.urlsafe_b64decode(cursor.encode()).decode()
                parts = json.loads(raw)
                cursor_dt = datetime.fromisoformat(parts["t"])
                cursor_id = UUID(parts["i"])
            except (ValueError, KeyError, TypeError):
                # Invalid cursor: fall back to no cursor (start from beginning).
                cursor_dt = None
                cursor_id = None
            if cursor_dt is not None and cursor_id is not None:
                query = query.where(
                    or_(
                        MCPServer.created_at < cursor_dt,
                        (MCPServer.created_at == cursor_dt) & (MCPServer.id < cursor_id),
                    )
                )

        # Fetch per_page + 1 to detect if there are more results.
        query = query.order_by(MCPServer.created_at.desc(), MCPServer.id.desc()).limit(per_page + 1)

        result = await self.db.execute(query)
        servers = list(result.scalars().all())

        has_more = len(servers) > per_page
        if has_more:
            servers = servers[:per_page]

        next_cursor: str | None = None
        if has_more and servers:
            last = servers[-1]
            payload = json.dumps({"t": last.created_at.isoformat(), "i": str(last.id)}).encode()
            next_cursor = base64.urlsafe_b64encode(payload).decode()

        return PaginatedServers(
            servers=[ServerResponse.model_validate(s) for s in servers],
            pagination=PaginationMeta(
                next_cursor=next_cursor,
                has_more=has_more,
                per_page=per_page,
                total=total,
            ),
        )

    async def count_by_health(self) -> dict[str, int]:
        stmt = select(MCPServer.health_status, func.count(MCPServer.id)).group_by(MCPServer.health_status)
        result = await self.db.execute(stmt)
        counts: dict[str, int] = {"total": 0, "healthy": 0, "degraded": 0}
        for status, count in result.all():
            counts["total"] += count
            if status == "healthy":
                counts["healthy"] += count
            elif status in {"degraded", "unhealthy"}:
                counts["degraded"] += count
        return counts

    async def get_server(self, server_id: UUID) -> ServerDetail:
        """Get detailed server information including all related data.

        WHY: Admin UI — view a server's full details including tools,
        tool version history, trust assignments, capability mappings,
        and routing rules.

        Uses selectinload to eagerly load all relationships in a single
        query (avoiding N+1). The ServerDetail response includes all
        related entities in a single response.

        RAISES: ServerNotFoundError if server_id is missing.
        """
        result = await self.db.execute(
            select(MCPServer)
            .options(
                selectinload(MCPServer.tools),
                selectinload(MCPServer.tool_versions),
                selectinload(MCPServer.trust_assignments),
                selectinload(MCPServer.mappings),
                selectinload(MCPServer.routing_rules),
            )
            .where(MCPServer.id == server_id)
        )
        server = result.scalar_one_or_none()
        if server is None:
            raise ServerNotFoundError(str(server_id))

        timeline = None
        if server.decommissioned_at is not None or server.decommission_phase is not None:
            timeline = DecommissionTimeline(
                phase=server.decommission_phase,
                decommissioned_at=server.decommissioned_at,
                status=server.decommission_phase or "active",
            )

        return ServerDetail(
            id=server.id,
            name=server.name,
            endpoint=server.endpoint,
            owner_team=server.owner_team,
            description=server.description,
            labels=server.labels or [],
            trust_level=server.trust_level or "unverified",
            health_status=server.health_status or "unknown",
            version=server.version,
            team_namespace=server.team_namespace,
            created_at=server.created_at,
            updated_at=server.updated_at,
            decommissioned_at=server.decommissioned_at,
            tools=[ToolResponse.model_validate(t) for t in server.tools],
            tool_versions=[ToolVersionResponse.model_validate(v) for v in server.tool_versions],
            trust_assignments=[
                TrustAssignmentResponse.model_validate(a) for a in server.trust_assignments
            ],
            capability_mappings=[
                CapabilityMappingResponse.model_validate(m) for m in server.mappings
            ],
            routing_rules=[RoutingRuleResponse.model_validate(r) for r in server.routing_rules],
            decommission_timeline=timeline,
        )

    async def decommission(
        self,
        server_id: UUID,
        phase: str,
        replacement_id: UUID | None = None,
    ) -> DecommissionResult:
        """Transition a server through decommission phases.

        WHY: Admin user journey — gracefully remove a server from the fabric.
        The decommission follows three sequential phases:
          1. grace_period: Mark the server, notify dependents but keep it running.
          2. migration: Re-point capability mappings to a replacement server.
          3. sunset: Delete all mappings and mark as fully decommissioned.

        Phase transitions are validated: you cannot skip phases or go backward.
        Once in "sunset", no further transitions are allowed.

        Uses SELECT...FOR UPDATE to lock the server row, preventing concurrent
        decommission operations from causing inconsistent state.

        RAISES:
          - ServerNotFoundError if server_id is missing.
          - DecommissionError for invalid phase, skipped phase, or re-decommission.

        SIDE EFFECTS:
          - Updates decommission_phase and decommissioned_at.
          - In migration phase: re-points mappings to replacement_id.
          - In sunset phase: deletes all CapabilityMapping rows.
          - Logs audit event (best-effort).
        """
        valid_phases = ["grace_period", "migration", "sunset"]
        if phase not in valid_phases:
            raise DecommissionError(f"Invalid phase '{phase}'. Must be one of {valid_phases}")

        result = await self.db.execute(
            select(MCPServer)
            .options(
                selectinload(MCPServer.tools),
                selectinload(MCPServer.trust_assignments),
                selectinload(MCPServer.mappings),
            )
            .where(MCPServer.id == server_id)
            .with_for_update()
        )
        server = result.scalar_one_or_none()
        if server is None:
            raise ServerNotFoundError(str(server_id))

        current_phase = server.decommission_phase

        # Validate phase transition order.
        if current_phase == "sunset":
            raise DecommissionError(f"Server {server_id} is already fully decommissioned")

        if current_phase is not None:
            phase_order = {p: i for i, p in enumerate(valid_phases)}
            if phase_order[phase] != phase_order[current_phase] + 1:
                expected = valid_phases[phase_order[current_phase] + 1]
                raise DecommissionError(
                    f"Cannot transition from '{current_phase}' to '{phase}'. "
                    f"Must proceed in order: {expected}"
                )
        elif phase != "grace_period":
            raise DecommissionError(
                f"First decommission phase must be 'grace_period', got '{phase}'"
            )

        # Build dependency report before modifying state.
        agent_class_names = sorted(
            {a.agent_class.name for a in server.trust_assignments if a.agent_class}
        )
        deps = DependencyReport(
            capability_names=[m.capability.name for m in server.mappings if m.capability],
            agent_class_names=agent_class_names,
            trust_assignment_count=len(server.trust_assignments),
            mapping_count=len(server.mappings),
        )

        if phase == "grace_period":
            server.decommission_phase = "grace_period"
            server.decommissioned_at = datetime.now(UTC)
        elif phase == "migration":
            if replacement_id is not None:
                # Re-point all capability mappings to the replacement server.
                for mapping in server.mappings:
                    mapping.server_id = replacement_id
            server.decommission_phase = "migration"
        elif phase == "sunset":
            # Delete all mappings. Use list() to copy because we're modifying
            # the collection during iteration.
            for mapping in list(server.mappings):
                await self.db.delete(mapping)
            server.decommission_phase = "sunset"

        await self.db.commit()

        if self.audit is not None:
            try:
                await self.audit.log_event(
                    event_type="server_decommissioned",
                    actor="system",
                    resource_id=str(server.id),
                    metadata={
                        "name": server.name,
                        "phase": phase,
                        "replacement_id": str(replacement_id) if replacement_id else None,
                    },
                )
            except Exception:
                logger.exception("Failed to log audit event for server decommission")

        return DecommissionResult(
            server_id=server.id,
            phase=phase,
            dependencies=deps,
            timeline=DecommissionTimeline(
                phase=server.decommission_phase,
                decommissioned_at=server.decommissioned_at,
                status=server.decommission_phase or "active",
            ),
        )

    async def update_health(self, server_id: UUID, status: str) -> None:
        """Update a server's health status in the database and optionally cache it in Redis.

        WHY: Called by the health monitoring pipeline to record the current
        health status of a server. The status is persisted to the database
        and cached in Redis (60s TTL) for fast reads via get_server_health.

        RAISES: ServerNotFoundError if server_id is missing.
        SIDE EFFECTS:
          - Updates MCPServer.health_status and last_health_check.
          - Sets Redis key health:{server_id} with 60s TTL.
        """
        now = datetime.now(UTC)
        result = await self.db.execute(select(MCPServer).where(MCPServer.id == server_id))
        server = result.scalar_one_or_none()
        if server is None:
            raise ServerNotFoundError(str(server_id))
        server.health_status = status
        server.last_health_check = now
        await self.db.commit()

        if self.redis is not None:
            key = f"health:{server_id}"
            await self.redis.set(key, status, ex=60)

    async def get_server_health(self, server_id: UUID) -> str | None:
        """Get a server's health status from Redis cache or fall back to the database.

        WHY: Fast health reads — Redis provides sub-millisecond reads for
        health status, with the database as a fallback when the cache is cold.

        RETURN: Health status string or None (though ServerNotFoundError is
        raised if the server doesn't exist in the DB).
        RAISES: ServerNotFoundError if server_id is not found in the database.
        """
        if self.redis is not None:
            cached = await self.redis.get(f"health:{server_id}")
            if cached is not None:
                return cached.decode()
        result = await self.db.execute(
            select(MCPServer.health_status).where(MCPServer.id == server_id)
        )
        row = result.scalar_one_or_none()
        if row is None:
            raise ServerNotFoundError(str(server_id))
        return row

    async def get_all_health_statuses(self) -> dict[str, str]:
        """Return a dict mapping server IDs to health statuses.

        WHY: Dashboard UI — show health status for all servers.
        Uses Redis SCAN for efficient bulk reads when Redis is available.
        Falls back to a full database query when Redis is not configured.

        Redis SCAN is cursor-based and non-blocking, suitable for production.
        It returns all keys matching the "health:*" pattern in batches.

        RETURN: Dict of {server_id_string: health_status_string}.
        """
        if self.redis is not None:
            cursor = 0
            pattern = "health:*"
            results: dict[str, str] = {}
            while True:
                cursor, keys = await self.redis.scan(cursor=cursor, match=pattern, count=100)
                if keys:
                    values = await self.redis.mget(*keys)
                    for key, val in zip(keys, values, strict=False):
                        if val is not None:
                            sid = key.decode().split(":", 1)[1]
                            results[sid] = val.decode()
                if cursor == 0:
                    break
            return results
        result = await self.db.execute(select(MCPServer.id, MCPServer.health_status))
        return {str(row[0]): row[1] for row in result.all()}
