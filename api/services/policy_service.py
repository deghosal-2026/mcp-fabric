"""OPA-backed policy engine for MCP Fabric.

Provides policy evaluation via Open Policy Agent, agent class and trust
assignment management, and policy bundle deployment with Redis caching.
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
        self.opa_url = (opa_url or settings.opa_url).rstrip("/")

    async def evaluate(
        self,
        agent_class: str,
        server_id: str,
        capability: str,
        team_namespace: str,
    ) -> PolicyDecision:
        """Evaluate a policy decision from OPA for the given agent class, server, and capability."""
        input_data = {
            "input": {
                "agent_class": agent_class,
                "server_id": server_id,
                "capability": capability,
                "team_namespace": team_namespace,
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
            raise OPAEvaluationError(
                f"OPA returned HTTP {resp.status_code}: {resp.text}"
            )
        body = resp.json()
        result = body.get("result", {})
        return PolicyDecision(
            allow=result.get("allow", False),
            approval_required=result.get("approval_required", False),
            trust_level=result.get("trust_level", "unreviewed"),
            agent_class=result.get("agent_class", agent_class),
            cross_team=result.get("cross_team", False),
        )

    async def evaluate_cached(
        self,
        agent_class: str,
        server_id: str,
        capability: str,
        team_namespace: str,
    ) -> PolicyDecision:
        """Evaluate policy with Redis caching (300s TTL), falling back to uncached evaluation."""

        try:
            import json

            import redis.asyncio as aioredis

            r = aioredis.from_url(settings.redis_url, decode_responses=True)
            cache_key = f"policy:eval:{agent_class}:{server_id}:{capability}"
            cached = await r.get(cache_key)
            if cached is not None:
                data = json.loads(cached)
                await r.aclose()
                return PolicyDecision(**data)
            decision = await self.evaluate(agent_class, server_id, capability, team_namespace)
            await r.setex(cache_key, 300, decision.model_dump_json())
            await r.aclose()
            return decision
        except Exception:
            return await self.evaluate(agent_class, server_id, capability, team_namespace)

    async def _invalidate_policy_cache(self) -> None:
        """Scan and delete all Redis keys matching the policy:* pattern."""

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
        """Deploy a Rego policy bundle to OPA, record the version, and invalidate the cache."""

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.put(
                f"{self.opa_url}/v1/policies/fabric/policy",
                content=rego_content,
                headers={"Content-Type": "text/plain"},
            )
        if resp.status_code not in (200, 201, 204):
            raise OPABundleError(
                f"OPA bundle deploy returned HTTP {resp.status_code}: {resp.text}"
            )
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
        """List deployed policy versions ordered by most recent first."""

        stmt = (
            select(OPAPolicyVersion)
            .order_by(OPAPolicyVersion.deployed_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def create_agent_class(self, params: AgentClassCreate) -> AgentClassResponse:
        """Create a new agent class."""

        ac = AgentClass(
            name=params.name,
            description=params.description,
            team_namespace=params.team_namespace,
        )
        self.db.add(ac)
        await self.db.commit()
        await self.db.refresh(ac)
        return AgentClassResponse(
            id=ac.id,
            name=ac.name,
            description=ac.description,
            team_namespace=ac.team_namespace,
            created_at=ac.created_at,
        )

    async def list_agent_classes(
        self,
        team_namespace: str | None = None,
    ) -> list[AgentClassResponse]:
        """List agent classes, optionally filtered by team namespace."""

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
        """Get a single agent class by ID, or None if not found."""

        result = await self.db.execute(
            select(AgentClass).where(AgentClass.id == class_id)
        )
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
        """Update an existing agent class. Returns None if not found."""

        result = await self.db.execute(
            select(AgentClass).where(AgentClass.id == class_id)
        )
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
        """\
        Delete an agent class by ID. Returns False if not found. \
        Invalidates policy cache on success.
        """

        result = await self.db.execute(
            select(AgentClass).where(AgentClass.id == class_id)
        )
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
        """Create or update a trust assignment between an agent class and a server."""

        result = await self.db.execute(
            select(TrustAssignment).where(
                TrustAssignment.agent_class_id == agent_class_id,
                TrustAssignment.server_id == params.server_id,
            )
        )
        existing = result.scalar_one_or_none()
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
        """List trust assignments, optionally filtered by agent class or server."""

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
        """Remove a trust assignment and invalidate the policy cache. Returns True if deleted."""

        stmt = delete(TrustAssignment).where(
            TrustAssignment.agent_class_id == agent_class_id,
            TrustAssignment.server_id == server_id,
        )
        result = cast(CursorResult, await self.db.execute(stmt))
        await self.db.commit()
        await self._invalidate_policy_cache()
        return result.rowcount > 0


def _compute_hash(content: str) -> str:
    """Compute the SHA-256 hex digest of the given content string."""
    import hashlib

    return hashlib.sha256(content.encode()).hexdigest()


def _next_version() -> str:
    """Generate a version string based on the current UTC timestamp."""
    from datetime import UTC, datetime

    return datetime.now(UTC).strftime("v%Y%m%d%H%M%S")


def _extract_tool_scope(value: Any) -> list[str] | None:
    """\
    Extract a list of tool names from a trust assignment's tool_scope \
    field, supporting dict and list formats.
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
