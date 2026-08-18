"""OPA-backed policy engine for MCP Fabric.

Provides policy evaluation via Open Policy Agent, agent class and trust
assignment management, and policy bundle deployment with Redis caching.

Architectural notes:
  - OPA is the policy decision point: it evaluates Rego policies and
    returns allow/deny decisions with metadata (trust level, approval
    requirements, cross-team access).
  - Policy decisions are cached in Redis with a 300s TTL. When Redis
    is unavailable, the system falls back to uncached evaluation.
  - Agent classes define groups of agents with shared policy context.
  - Trust assignments define the trust relationship between an agent
    class and a server (trust level + optional tool scope).
  - Policy versions are tracked in the database for audit trail and
    rollback capability.
  - Cache invalidation happens on: bundle deploy, agent class delete,
    trust assignment changes.
"""

from typing import Any, cast
from uuid import UUID

import httpx
from sqlalchemy import delete, select
from sqlalchemy.engine import CursorResult
from sqlalchemy.ext.asyncio import AsyncSession

from api.config import settings
from api.models.agent import AgentClass, TrustAssignment
from api.models.policy import OPAPolicyVersion
from api.schemas.agent import (
    AgentClassCreate,
    AgentClassResponse,
    TrustAssignmentCreate,
    TrustAssignmentResponse,
)
from api.schemas.common import PolicyDecision


class OPAServiceError(Exception):
    """Base error for OPA communication failures."""


class OPAEvaluationError(OPAServiceError):
    """OPA returned an unexpected evaluation result."""


class OPABundleError(OPAServiceError):
    """Failed to deploy or validate an OPA policy bundle."""


class PolicyService:
    """\
    OPA-backed policy engine — evaluate, deploy bundles, manage agent \
    classes and trust assignments.
    """

    def __init__(
        self,
        db: AsyncSession,
        opa_url: str | None = None,
    ):
        self.db = db
        # Strip trailing slash to normalize URL construction.
        self.opa_url = (opa_url or settings.opa_url).rstrip("/")

    async def evaluate(
        self,
        agent_class: str,
        server_id: str,
        capability: str,
        team_namespace: str,
        identity_resources: dict[str, list[str]] | None = None,
        request_resources: dict[str, str] | None = None,
        mapping_status: str | None = None,
        tool_name: str | None = None,
        agent_read_only: bool = False,
        tool_class: str = "",
    ) -> PolicyDecision:
        """Evaluate a policy decision from OPA for the given inputs.

        WHY: Core authorization flow — before executing a capability for
        an agent, the system asks OPA: "should this agent_class be allowed
        to use this capability on this server?"

        The input includes: agent_class, server_id, capability, team_namespace.
        OPA returns: allow (bool), approval_required (bool), trust_level (str),
        agent_class (str), cross_team (bool).

        New in v0.3.0:
          - mapping_status: used by deny_stale_mapping rule to reject stale/rejected
            mappings even if trust levels pass.
          - tool_name: used by untrusted_write rule to deny write operations
            on unreviewed servers.

        Uses OPA's REST API at /v1/data/fabric/policy/result with a 5s timeout.

        RAISES: OPAEvaluationError on connection failure, timeout, or
        non-200 response.
        RETURN: PolicyDecision with the evaluation result.
        """
        # Build the OPA input dict including the new mapping_status and tool_name
        # fields so OPA policies can enforce deny_stale_mapping and untrusted_write rules.
        input_data: dict[str, dict[str, object]] = {
            "input": {
                "agent_class": agent_class,
                "server_id": server_id,
                "capability": capability,
                "team_namespace": team_namespace,
                "identity_resources": identity_resources or {},
                "request_resources": request_resources or {},
                "declared_dimensions": list((identity_resources or {}).keys()),
                "mapping_status": mapping_status or "",
                "tool_name": tool_name or "",
                "agent_read_only": agent_read_only,
                "tool_class": tool_class,
            }
        }
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    f"{self.opa_url}/v1/data/fabric/policy/result",
                    json=input_data,
                )
        except httpx.ConnectError as e:
            raise OPAEvaluationError(f"OPA unreachable: {e}") from e
        except httpx.TimeoutException as e:
            raise OPAEvaluationError(f"OPA timed out: {e}") from e
        if resp.status_code != 200:
            raise OPAEvaluationError(f"OPA returned HTTP {resp.status_code}: {resp.text}")
        body = resp.json()
        result = body.get("result", {})
        return PolicyDecision(
            allow=result.get("allow", False),
            approval_required=result.get("approval_required", False),
            trust_level=result.get("trust_level", "unreviewed"),
            agent_class=result.get("agent_class", agent_class),
            cross_team=result.get("cross_team", False),
            resource_allowed=result.get("resource_allowed", True),
            resource_violations=result.get("resource_violations", []),
            deny_stale_mapping=result.get("deny_stale_mapping", False),
            untrusted_write=result.get("untrusted_write", False),
            read_only_denied=result.get("read_only_denied", False),
        )

    async def evaluate_cached(
        self,
        agent_class: str,
        server_id: str,
        capability: str,
        team_namespace: str,
        identity_resources: dict[str, list[str]] | None = None,
        request_resources: dict[str, str] | None = None,
    ) -> PolicyDecision:
        """Evaluate policy with Redis caching (300s TTL), falling back to uncached evaluation.

        WHY: Performance optimization for the hot path — policy evaluation
        with identical inputs is cached in Redis to avoid OPA round-trips.

        Cache key: policy:eval:{agent_class}:{server_id}:{capability}
        Cache TTL: 300 seconds

        When Redis is unavailable (exception during get/set), falls through
        to the uncached evaluate() method. This is deliberate — we always
        prefer a correct decision over a fast failure.

        RETURN: PolicyDecision from cache or fresh evaluation.
        """
        try:
            import json

            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            cache_key = f"policy:eval:{agent_class}:{server_id}:{capability}"
            if identity_resources:
                import json

                cache_key += f":ir={json.dumps(identity_resources, sort_keys=True)}"
            if request_resources:
                import json

                cache_key += f":rr={json.dumps(request_resources, sort_keys=True)}"
            cache_ttl = 60 if (identity_resources or request_resources) else 300
            cached = await r.get(cache_key)
            if cached is not None:
                data = json.loads(cached)
                await r.aclose()
                return PolicyDecision(**data)
            decision = await self.evaluate(
                agent_class,
                server_id,
                capability,
                team_namespace,
                identity_resources=identity_resources,
                request_resources=request_resources,
            )
            await r.setex(cache_key, cache_ttl, decision.model_dump_json())
            await r.aclose()
            return decision
        except Exception:
            # Redis failure: fall through to uncached evaluation.
            return await self.evaluate(
                agent_class,
                server_id,
                capability,
                team_namespace,
                identity_resources=identity_resources,
                request_resources=request_resources,
            )

    async def _invalidate_policy_cache(self) -> None:
        """Scan and delete all Redis keys matching the policy:* pattern.

        WHY: When policy state changes (bundle deploy, trust update, class
        delete), cached decisions may be stale. Invalidating all policy:*
        keys forces fresh evaluation on the next request.

        Uses Redis SCAN (not KEYS) to avoid blocking on large key sets.
        SCAN is cursor-based and non-blocking, suitable for production use.
        Errors are silently ignored — stale cache is acceptable as TTL
        will eventually expire stale entries.
        """
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor=cursor, match="policy:*")
                if keys:
                    await r.delete(*keys)
                if cursor == 0:
                    break
            await r.aclose()
        except Exception:
            pass

    async def deploy_bundle(
        self,
        rego_content: str,
        deployed_by: str | None = None,
    ) -> OPAPolicyVersion:
        """Deploy a Rego policy bundle to OPA, record the version, and invalidate the cache.

        WHY: Admin user journey — update the OPA policies that govern
        authorization decisions. The Rego content is sent to OPA's
        policy API and a version record is created in the database.

        After deployment, the Redis cache is invalidated so subsequent
        evaluations use the new policy.

        SIDE EFFECTS:
          - PUTs the Rego content to OPA at /v1/policies/fabric/policy
          - Creates OPAPolicyVersion row in DB
          - Invalidates all policy:* Redis cache keys

        RAISES: OPABundleError if OPA returns a non-success status code.
        RETURN: The created OPAPolicyVersion record.
        """
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{self.opa_url}/v1/policies/fabric/policy",
                content=rego_content,
                headers={"Content-Type": "text/plain"},
            )
        if resp.status_code not in (200, 201, 204):
            raise OPABundleError(f"OPA bundle deploy returned HTTP {resp.status_code}: {resp.text}")
        bundle_hash = _compute_hash(rego_content)
        version = OPAPolicyVersion(
            version=_next_version(),
            bundle_hash=bundle_hash,
            deployed_by=deployed_by,
            rego_content=rego_content,
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)
        await self._invalidate_policy_cache()
        return version

    async def get_policy_versions(
        self,
        limit: int = 10,
        offset: int = 0,
    ) -> list[OPAPolicyVersion]:
        """List deployed policy versions ordered by most recent first.

        WHY: Admin UI — view policy version history for audit and rollback.
        The rego_content field allows re-deploying a previous version.
        """
        stmt = (
            select(OPAPolicyVersion)
            .order_by(OPAPolicyVersion.deployed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_agent_class(self, params: AgentClassCreate) -> AgentClassResponse:
        """Create a new agent class.

        WHY: Admin user journey — define a new agent class for grouping
        agents with shared policy context and capability access.

        Agent classes are linked to packs (via pack_service) and to
        trust assignments (via this service).

        SIDE EFFECTS: Persists AgentClass row.
        """
        ac = AgentClass(
            name=params.name,
            description=params.description,
            team_namespace=params.team_namespace,
            is_read_only=params.is_read_only,
        )
        self.db.add(ac)
        await self.db.commit()
        await self.db.refresh(ac)
        return AgentClassResponse(
            id=ac.id,
            name=ac.name,
            description=ac.description,
            team_namespace=ac.team_namespace,
            is_read_only=ac.is_read_only,
            created_at=ac.created_at,
        )

    async def list_agent_classes(
        self,
        team_namespace: str | None = None,
    ) -> list[AgentClassResponse]:
        """List agent classes, optionally filtered by team namespace.

        WHY: Admin UI — browse agent classes. Used in class selection
        dropdowns and management dashboards.
        """
        stmt = select(AgentClass).order_by(AgentClass.name)
        if team_namespace:
            stmt = stmt.where(AgentClass.team_namespace == team_namespace)
        result = await self.db.execute(stmt)
        classes = result.scalars().all()
        return [
            AgentClassResponse(
                id=ac.id,
                name=ac.name,
                description=ac.description,
                team_namespace=ac.team_namespace,
                created_at=ac.created_at,
            )
            for ac in classes
        ]

    async def get_agent_class(self, class_id: UUID) -> AgentClassResponse | None:
        """Get a single agent class by ID.

        WHY: Admin UI — view a specific agent class's details.
        RETURN: AgentClassResponse or None if not found.
        """
        result = await self.db.execute(select(AgentClass).where(AgentClass.id == class_id))
        ac = result.scalar_one_or_none()
        if ac is None:
            return None
        return AgentClassResponse(
            id=ac.id,
            name=ac.name,
            description=ac.description,
            team_namespace=ac.team_namespace,
            created_at=ac.created_at,
        )

    async def update_agent_class(
        self,
        class_id: UUID,
        params: AgentClassCreate,
    ) -> AgentClassResponse | None:
        """Update an existing agent class.

        WHY: Admin user journey — modify the name, description, or
        namespace of an agent class.

        RETURN: Updated AgentClassResponse or None if not found.
        """
        result = await self.db.execute(select(AgentClass).where(AgentClass.id == class_id))
        ac = result.scalar_one_or_none()
        if ac is None:
            return None
        ac.name = params.name
        ac.description = params.description
        ac.team_namespace = params.team_namespace
        await self.db.commit()
        await self.db.refresh(ac)
        return AgentClassResponse(
            id=ac.id,
            name=ac.name,
            description=ac.description,
            team_namespace=ac.team_namespace,
            created_at=ac.created_at,
        )

    async def delete_agent_class(self, class_id: UUID) -> bool:
        """Delete an agent class by ID. Invalidates policy cache on success.

        WHY: Admin user journey — remove an agent class that is no longer needed.
        After deletion, the policy cache is invalidated so stale class references
        in cached decisions are cleared.

        RETURN: True if deleted, False if not found.
        SIDE EFFECTS: Invalidates all policy:* Redis cache keys.
        """
        result = await self.db.execute(select(AgentClass).where(AgentClass.id == class_id))
        ac = result.scalar_one_or_none()
        if ac is None:
            return False
        await self.db.delete(ac)
        await self.db.commit()
        await self._invalidate_policy_cache()
        return True

    async def set_trust(
        self,
        agent_class_id: UUID,
        params: TrustAssignmentCreate,
    ) -> TrustAssignmentResponse:
        """Create or update a trust assignment between an agent class and a server.

        WHY: Admin user journey — define the trust level for how a class
        of agents can interact with a server. Upsert pattern: if an assignment
        already exists for this (class, server) pair, update it; otherwise create.

        The trust level determines what policies OPA applies (e.g., 'trusted'
        agents may skip certain checks). The optional tool_scope restricts
        which tools on the server the class can use.

        SIDE EFFECTS:
          - Creates or updates TrustAssignment row
          - Invalidates the policy cache so new trust levels take effect immediately
        """
        result = await self.db.execute(
            select(TrustAssignment).where(
                TrustAssignment.agent_class_id == agent_class_id,
                TrustAssignment.server_id == params.server_id,
            )
        )
        existing = result.scalar_one_or_none()
        # Wrap tool_scope in a dict for consistent JSON storage format.
        tool_scope: dict[str, Any] | None = (
            {"tools": params.tool_scope} if params.tool_scope else None
        )
        if existing:
            existing.trust_level = params.trust_level
            existing.tool_scope = tool_scope
            ta = existing
        else:
            ta = TrustAssignment(
                agent_class_id=agent_class_id,
                server_id=params.server_id,
                trust_level=params.trust_level,
                tool_scope=tool_scope,
            )
            self.db.add(ta)
        await self.db.commit()
        await self.db.refresh(ta)
        await self._invalidate_policy_cache()
        return TrustAssignmentResponse(
            id=ta.id,
            agent_class_id=ta.agent_class_id,
            server_id=ta.server_id,
            trust_level=ta.trust_level,
            tool_scope=_extract_tool_scope(ta.tool_scope),
        )

    async def get_trust_assignments(
        self,
        agent_class_id: UUID | None = None,
        server_id: UUID | None = None,
    ) -> list[TrustAssignmentResponse]:
        """List trust assignments, optionally filtered by agent class or server.

        WHY: Admin UI — view and manage trust relationships.
        Sorted by trust_level to group related assignments together.
        """
        stmt = select(TrustAssignment).order_by(TrustAssignment.trust_level)
        if agent_class_id:
            stmt = stmt.where(TrustAssignment.agent_class_id == agent_class_id)
        if server_id:
            stmt = stmt.where(TrustAssignment.server_id == server_id)
        result = await self.db.execute(stmt)
        assignments = result.scalars().all()
        return [
            TrustAssignmentResponse(
                id=ta.id,
                agent_class_id=ta.agent_class_id,
                server_id=ta.server_id,
                trust_level=ta.trust_level,
                tool_scope=_extract_tool_scope(ta.tool_scope),
            )
            for ta in assignments
        ]

    async def remove_trust_assignment(
        self,
        agent_class_id: UUID,
        server_id: UUID,
    ) -> bool:
        """Remove a trust assignment and invalidate the policy cache.

        WHY: Admin user journey — revoke a trust relationship.
        Uses bulk DELETE (not load-and-delete) for efficiency.

        RETURN: True if a row was deleted, False otherwise.
        SIDE EFFECTS: Invalidates the policy cache.
        """
        stmt = delete(TrustAssignment).where(
            TrustAssignment.agent_class_id == agent_class_id,
            TrustAssignment.server_id == server_id,
        )
        result = cast(CursorResult[Any], await self.db.execute(stmt))
        await self.db.commit()
        await self._invalidate_policy_cache()
        return result.rowcount > 0


def _compute_hash(content: str) -> str:
    """Compute the SHA-256 hex digest of the given content string.

    WHY: Used to generate a content-addressed hash for policy bundles.
    This enables detecting whether the policy content has changed between
    deployments.
    """
    import hashlib

    return hashlib.sha256(content.encode()).hexdigest()


def _next_version() -> str:
    """Generate a version string based on the current UTC timestamp.

    WHY: Policy versions are identified by timestamp (e.g., v20250101120000).
    This provides a human-readable, sortable, and unique version identifier
    without requiring a monotonic counter.
    """
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("v%Y%m%d%H%M%S")


def _extract_tool_scope(value: Any) -> list[str] | None:
    """Extract a list of tool names from a trust assignment's tool_scope field.

    WHY: The tool_scope is stored as a JSON dict in the database, but the
    response schema expects a flat list of tool names. This function handles
    the normalization, supporting both dict format ({tools: [...]}) and
    explicit list format.

    The dual-format support is for backward compatibility with different
    API versions that may send tool_scope differently.
    """
    if value is None:
        return None
    if isinstance(value, dict):
        tools = value.get("tools", value.get("tool_scope"))
        if isinstance(tools, list):
            return [str(t) for t in tools]
        return None
    if isinstance(value, list):
        return [str(t) for t in value]
    return None
