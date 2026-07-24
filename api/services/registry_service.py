from __future__ import annotations

import base64
import json
import logging
from datetime import UTC, datetime
from typing import Any
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

logger = logging.getLogger(__name__)

_READ_ONLY_PREFIXES = ("get", "list", "search", "read", "find", "query", "check")


def _is_read_only_tool(tool: ToolDefinition) -> bool:
    name = tool.name.lower()
    return any(name.startswith(p) for p in _READ_ONLY_PREFIXES)


def _suggest_trust_level(tools: list[ToolDefinition]) -> str:
    if tools and all(_is_read_only_tool(t) for t in tools):
        return "trusted"
    return "unreviewed"


class RegistryService:
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
            removed_responses.append(ToolResponse(
                id=tool.id, tool_name=tool.tool_name,
                description=tool.description,
                input_schema=tool.input_schema, output_schema=tool.output_schema,
            ))
            self.db.add(ToolVersion(
                server_id=server.id, tool_name=tool.tool_name,
                input_schema=tool.input_schema, output_schema=tool.output_schema,
                is_breaking=True,
            ))
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
                self.db.add(ToolVersion(
                    server_id=server.id, tool_name=db_tool.tool_name,
                    input_schema=db_tool.input_schema, output_schema=db_tool.output_schema,
                    is_breaking=change.is_breaking,
                ))
                db_tool.description = curr_def.description
                db_tool.input_schema = curr_def.input_schema
                db_tool.output_schema = curr_def.output_schema
                changed_schema.append(ToolChangeSchema(
                    tool_name=name, changes=change.changes, is_breaking=change.is_breaking,
                ))

        added_responses: list[ToolResponse] = []
        for name in added_names:
            curr_def = curr_by_name[name]
            tool = ServerTool(
                server_id=server.id, tool_name=curr_def.name,
                description=curr_def.description,
                input_schema=curr_def.input_schema,
                output_schema=curr_def.output_schema,
            )
            self.db.add(tool)
            await self.db.flush()
            added_responses.append(ToolResponse(
                id=tool.id, tool_name=tool.tool_name,
                description=tool.description,
                input_schema=tool.input_schema, output_schema=tool.output_schema,
            ))

        server.updated_at = now
        server.health_status = "reachable"
        await self.db.commit()
        await self.db.refresh(server, ["tools"])

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
        query = select(MCPServer).options(selectinload(MCPServer.tools))

        if team is not None:
            query = query.where(MCPServer.team_namespace == team)
        if trust is not None:
            query = query.where(MCPServer.trust_level == trust)
        if health is not None:
            query = query.where(MCPServer.health_status == health)
        if search is not None:
            query = query.where(MCPServer.name.ilike(f"%{search}%"))

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
                cursor_dt = None
                cursor_id = None
            if cursor_dt is not None and cursor_id is not None:
                query = query.where(
                    or_(
                        MCPServer.created_at < cursor_dt,
                        (MCPServer.created_at == cursor_dt) & (MCPServer.id < cursor_id),
                    )
                )

        query = query.order_by(
            MCPServer.created_at.desc(), MCPServer.id.desc()
        ).limit(per_page + 1)

        result = await self.db.execute(query)
        servers = list(result.scalars().all())

        has_more = len(servers) > per_page
        if has_more:
            servers = servers[:per_page]

        next_cursor: str | None = None
        if has_more and servers:
            last = servers[-1]
            payload = json.dumps(
                {"t": last.created_at.isoformat(), "i": str(last.id)}
            ).encode()
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

    async def get_server(self, server_id: UUID) -> ServerDetail:
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
            labels=server.labels,
            trust_level=server.trust_level,
            health_status=server.health_status,
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
            routing_rules=[
                RoutingRuleResponse.model_validate(r) for r in server.routing_rules
            ],
            decommission_timeline=timeline,
        )

    async def decommission(
        self,
        server_id: UUID,
        phase: str,
        replacement_id: UUID | None = None,
    ) -> DecommissionResult:
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

        agent_class_names = sorted({
            a.agent_class.name for a in server.trust_assignments if a.agent_class
        })
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
                for mapping in server.mappings:
                    mapping.server_id = replacement_id
            server.decommission_phase = "migration"
        elif phase == "sunset":
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
        now = datetime.now(UTC)
        result = await self.db.execute(
            select(MCPServer).where(MCPServer.id == server_id)
        )
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
        result = await self.db.execute(
            select(MCPServer.id, MCPServer.health_status)
        )
        return {str(row[0]): row[1] for row in result.all()}
