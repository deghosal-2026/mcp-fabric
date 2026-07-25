"""Capability-aware request routing to MCP servers.

Resolves capability names (including aliases) to server endpoints
via capability mappings and routing rules, then executes tool calls
with latency instrumentation.
"""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from api.mcp import MCPClient
from api.models.capability import Capability
from api.models.server import CapabilityMapping, RoutingRule
from api.schemas.routing import CapabilityRequest, RouteResult, RoutingRuleCreate


class CapabilityNotFoundError(Exception):
    """Raised when a capability name or alias cannot be resolved."""


class NoServerFoundError(Exception):
    """Raised when no server is mapped for the given capability."""


class RoutingService:
    """Resolves capabilities to server endpoints and executes routed tool calls."""

    def __init__(self, db: AsyncSession, mcp: MCPClient | None = None):
        self.db = db
        self.mcp = mcp or MCPClient()

    async def resolve_capability(self, name: str) -> Capability:
        """Resolve a capability by name, falling back to alias lookup."""
        stmt = select(Capability).where(Capability.name == name)
        result = await self.db.execute(stmt)
        cap = result.scalar_one_or_none()
        if cap is None:
            from api.models.capability import CapabilityAlias

            stmt = (
                select(Capability)
                .join(CapabilityAlias)
                .where(CapabilityAlias.alias == name)
            )
            result = await self.db.execute(stmt)
            cap = result.scalar_one_or_none()
        if cap is None:
            raise CapabilityNotFoundError(f"Capability '{name}' not found")
        return cap

    async def select_server(self, capability_id: UUID) -> CapabilityMapping:
        """Select the highest-weighted server mapping for a capability."""
        stmt = (
            select(CapabilityMapping)
            .options(joinedload(CapabilityMapping.server))
            .where(CapabilityMapping.capability_id == capability_id)
            .order_by(CapabilityMapping.routing_weight.desc())
        )
        result = await self.db.execute(stmt)
        mapping = result.scalars().first()
        if mapping is None:
            raise NoServerFoundError(f"No server mapped for capability {capability_id}")
        return mapping

    async def execute(self, request: CapabilityRequest) -> RouteResult:
        """\
        Resolve and execute a capability request against the selected \
        server, recording latency.
        """
        import time

        start = time.monotonic()
        cap = await self.resolve_capability(request.capability)
        mapping = await self.select_server(cap.id)
        endpoint = mapping.server.endpoint
        tool_name = mapping.tool_name

        response = await self.mcp.call_tool(
            endpoint=endpoint,
            tool_name=tool_name,
            arguments=request.params,
        )

        latency_s = time.monotonic() - start
        latency_ms = int(latency_s * 1000)
        from api.telemetry.metrics import fabric_routing_overhead_seconds

        fabric_routing_overhead_seconds.labels(
            server_id=str(mapping.server_id),
        ).observe(latency_s)
        return RouteResult(
            result=response.result,
            server=mapping.server.name,
            server_id=mapping.server_id,
            latency_ms=latency_ms,
            routing_reason=f"routing_weight={mapping.routing_weight}",
        )

    async def create_routing_rule(self, params: RoutingRuleCreate) -> RoutingRule:
        """Create a new routing rule with priority and optional condition."""
        rule = RoutingRule(
            capability_id=params.capability_id,
            server_id=params.server_id,
            priority=params.priority,
            condition=params.condition,
        )
        self.db.add(rule)
        await self.db.commit()
        await self.db.refresh(rule)
        return rule

    async def list_routing_rules(self) -> list[RoutingRule]:
        """Return all routing rules ordered by priority."""
        stmt = select(RoutingRule).order_by(RoutingRule.priority)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_routing_rule(self, rule_id: UUID) -> bool:
        """Delete a routing rule by ID. Returns True if deleted, False if not found."""
        stmt = select(RoutingRule).where(RoutingRule.id == rule_id)
        result = await self.db.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule is None:
            return False
        await self.db.delete(rule)
        await self.db.commit()
        return True
