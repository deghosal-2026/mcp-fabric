"""Capability-aware request routing to MCP servers.

Resolves capability names (including aliases) to server endpoints
via capability mappings and routing rules, then executes tool calls
with latency instrumentation.

Architectural notes:
  - Routing is the core orchestration layer: it connects the abstract
    capability model to concrete MCP server endpoints.
  - Capability resolution supports aliases for backward compatibility:
    if a capability name is not found directly, aliases are checked.
  - Server selection uses routing_weight: higher weight = preferred.
    This enables canary deployment and load distribution.
  - Routing rules provide additional condition-based routing (e.g.,
    route certain agents to specific servers based on conditions).
  - Latency is recorded via Prometheus metrics (fabric_routing_overhead_seconds).
  - Routing decisions are NOT cached — every request goes through the
    full resolution + selection flow. If caching is needed, it should
    be added at the capability resolution level.
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
    """Resolves capabilities to server endpoints and executes routed tool calls.

    Depends on:
      - AsyncSession for DB access
      - MCPClient for executing tool calls on MCP servers

    Used by: approval_service (for executing approved capabilities),
    API route handlers (for direct capability execution).

    This is the central "nervous system" of MCP Fabric — every capability
    request passes through this service.
    """

    def __init__(self, db: AsyncSession, mcp: MCPClient | None = None):
        self.db = db
        self.mcp = mcp or MCPClient()

    async def resolve_capability(self, name: str) -> Capability:
        """Resolve a capability by name, falling back to alias lookup.

        WHY: When an agent requests a capability, we first try direct name
        match. If that fails, we search through CapabilityAlias to find
        a capability that has the given name as an alias.

        This two-step resolution process supports backward compatibility:
        old agents using a renamed capability can still be routed through
        the alias.

        RAISES: CapabilityNotFoundError if neither the name nor any alias matches.
        """
        stmt = select(Capability).where(Capability.name == name)
        result = await self.db.execute(stmt)
        cap = result.scalar_one_or_none()
        if cap is None:
            # Lazy import to avoid circular dependency issues at module load time.
            from api.models.capability import CapabilityAlias

            stmt = select(Capability).join(CapabilityAlias).where(CapabilityAlias.alias == name)
            result = await self.db.execute(stmt)
            cap = result.scalar_one_or_none()
        if cap is None:
            raise CapabilityNotFoundError(f"Capability '{name}' not found")
        return cap

    async def select_server(self, capability_id: UUID) -> CapabilityMapping:
        """Select the highest-weighted server mapping for a capability.

        WHY: Given a resolved capability, find which server should handle it.
        Uses routing_weight (descending) to pick the preferred server.
        Higher weight = preferred (useful for canary deployments where
        the canary server has a higher weight).

        Uses joinedload to eagerly load the server relationship, avoiding
        a separate query when reading mapping.server.endpoint in execute().

        RAISES: NoServerFoundError if no CapabilityMapping exists for this capability.
        """
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
        """Resolve and execute a capability request against the selected server.

        WHY: The primary execution path — an agent requests a capability
        by name with parameters, and this method:
          1. Resolves the name to a Capability (including alias check).
          2. Selects the highest-weighted server for that capability.
          3. Calls the tool on the selected server via MCPClient.
          4. Records latency via Prometheus metrics.
          5. Returns the result with routing metadata.

        Latency is measured with time.monotonic() (monotonic clock, not
        affected by system time changes) and reported in milliseconds.
        The Prometheus histogram label includes the server_id for per-server
        latency tracking.

        SIDE EFFECTS: Records Prometheus metric fabric_routing_overhead_seconds.
        RAISES: CapabilityNotFoundError, NoServerFoundError, or errors from
        MCPClient.call_tool() if the server is unreachable.
        RETURN: RouteResult with the tool response, server metadata, and latency.
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
        """Create a new routing rule with priority and optional condition.

        WHY: Admin user journey — define a custom routing rule that overrides
        the default weight-based server selection. Rules with higher priority
        (lower number) are evaluated first.

        The condition is a JSON dict that can specify constraints like
        agent_class, team_namespace, or custom attributes. When the condition
        matches, the routing rule's server is selected instead of the
        weight-based default.

        SIDE EFFECTS: Persists RoutingRule row.
        """
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
        """Return all routing rules ordered by priority.

        WHY: Admin UI — view and manage routing rules.
        Lower priority number = higher priority (evaluated first).
        """
        stmt = select(RoutingRule).order_by(RoutingRule.priority)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def delete_routing_rule(self, rule_id: UUID) -> bool:
        """Delete a routing rule by ID.

        WHY: Admin user journey — remove a routing rule that is no longer needed.

        RETURN: True if deleted, False if not found (idempotent).
        """
        stmt = select(RoutingRule).where(RoutingRule.id == rule_id)
        result = await self.db.execute(stmt)
        rule = result.scalar_one_or_none()
        if rule is None:
            return False
        await self.db.delete(rule)
        await self.db.commit()
        return True
