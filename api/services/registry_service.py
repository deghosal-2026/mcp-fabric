from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.mcp import MCPClient, MCPError, ToolDefinition
from api.models import MCPServer, ServerTool, ToolVersion
from api.schemas.server import (
    ServerCreate,
    ServerInspectResponse,
    ServerResponse,
    ToolResponse,
)
from api.schemas.server import (
    ToolChange as ToolChangeSchema,
)
from api.services.exceptions import (
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
    ) -> None:
        self.db = db
        self.mcp = mcp_client
        self.audit = audit_service

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
            change = self.mcp._compare_tool_definitions(prev_def, curr_def)
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
