from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.mcp import MCPClient, MCPError, ToolDefinition
from api.models import MCPServer, ServerTool
from api.schemas.server import ServerCreate, ServerResponse
from api.services.exceptions import DuplicateServerError, ServerUnreachableError

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
