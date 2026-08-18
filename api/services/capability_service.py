"""Capability CRUD and lifecycle management for MCP Fabric.

Provides create, list, get, and deprecate operations for capabilities
that define the normalized interface for MCP server tools.

Architectural notes:
  - Capabilities are the "what" — they define a normalized interface
    (input/output schema) independently of any specific MCP server.
  - Mappings (CapabilityMapping, managed by registry_service) connect
    capabilities to actual server endpoints.
  - Aliases provide alternative names for a capability, supporting
    backward compatibility and cross-team naming conventions.
  - Deprecation is a soft-delete: status='deprecated' with a grace period
    before the capability can be removed. Callers can check the status
    to warn about deprecated capabilities.
  - Schema-digest: every CapabilityMapping stores a SHA-256 digest of
    (tool_name + input_schema + output_schema) at creation time. When a
    server is re-inspected, affected mappings are marked stale if the
    digest no longer matches. Routing only uses active, digest-verified
    mappings.
"""

from __future__ import annotations

import builtins
import hashlib
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from api.models.capability import Capability, CapabilityAlias
from api.models.server import CapabilityMapping, MappingReview, ServerTool
from api.schemas.capability import (
    CapabilityCreate,
    CapabilityMappingCreate,
    CapabilityMappingResponse,
    CapabilityResponse,
    MappingReviewCreate,
    MappingReviewResponse,
    ReviewQueueSummary,
)

# Failure classes that signal an offline server (hands-off: retire-or-wait).
# These never count toward the reviewer's critical tally (#447).
_UNREACHABLE_CLASSES = ("unreachable", "timeout")
# Failure classes that signal a genuine schema change (hands-on: review + re-approve).
_CRITICAL_CLASSES = ("drifted", "schema_mismatch")
_LIMBO_STATUSES = ("stale", "pending_review", "stale-unverified")


class CapabilityService:
    """CRUD operations for capability definitions.

    Depends on: AsyncSession for DB access.
    Used by: admin capability UI, pack_service (for assigning capabilities
    to packs), routing_service (for capability resolution).

    Capabilities are the fundamental building block of the MCP Fabric
    abstraction layer. Every MCP server tool is mapped to a capability.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, params: CapabilityCreate) -> CapabilityResponse:
        """Create a new capability definition.

        WHY: Admin user journey — define a new capability that MCP servers
        can map to. The normalized schemas define the contract that all
        mapped servers must conform to.

        SIDE EFFECTS: Persists Capability row.
        RETURN: The created capability with server-generated id and timestamps.
        """
        cap = Capability(
            name=params.name,
            domain=params.domain,
            normalized_input_schema=params.normalized_input_schema,
            normalized_output_schema=params.normalized_output_schema,
            description=params.description,
        )
        self.db.add(cap)
        await self.db.commit()
        await self.db.refresh(cap)
        return CapabilityResponse(
            id=cap.id,
            name=cap.name,
            domain=cap.domain,
            normalized_input_schema=cap.normalized_input_schema,
            normalized_output_schema=cap.normalized_output_schema,
            description=cap.description,
            status=cap.status or "active",
            created_at=cap.created_at,
            mappings_count=0,
            aliases=[],
        )

    async def list(
        self,
        domain: str | None = None,
        status: str | None = None,
        search: str | None = None,
    ) -> builtins.list[CapabilityResponse]:
        """List capabilities with optional filters.

        WHY: Admin UI — browse available capabilities.
        Filters (domain, status, name/description search) are applied as SQL
        WHERE clauses for efficient querying at scale, unlike the previous
        in-memory approach.
        Sorted alphabetically by name for a predictable ordering.
        """
        stmt = (
            select(Capability)
            .options(selectinload(Capability.mappings), selectinload(Capability.aliases))
            .order_by(Capability.name)
        )
        if domain:
            stmt = stmt.where(Capability.domain == domain)
        if status:
            stmt = stmt.where(Capability.status == status)
        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                Capability.name.ilike(pattern) | Capability.description.ilike(pattern)
            )
        result = await self.db.execute(stmt)
        caps = result.scalars().all()
        return [await self._to_response(c) for c in caps]

    async def get(self, cap_id: UUID) -> CapabilityResponse | None:
        """Get a single capability by ID.

        WHY: Admin UI — view/edit a specific capability's details.
        RETURN: CapabilityResponse or None if not found.
        """
        result = await self.db.execute(
            select(Capability)
            .options(selectinload(Capability.mappings), selectinload(Capability.aliases))
            .where(Capability.id == cap_id)
        )
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        return await self._to_response(cap)

    async def deprecate(self, cap_id: UUID) -> CapabilityResponse | None:
        """Mark a capability as deprecated.

        WHY: Admin user journey — soft-delete a capability that should
        no longer be used. Deprecated capabilities remain in the database
        with their mappings intact, but callers should warn when they
        are used. After the grace period, the capability can be removed.

        SIDE EFFECTS: Sets status to 'deprecated'.
        RETURN: Updated CapabilityResponse or None if not found.
        """
        result = await self.db.execute(
            select(Capability)
            .options(selectinload(Capability.mappings), selectinload(Capability.aliases))
            .where(Capability.id == cap_id)
        )
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        cap.status = "deprecated"
        await self.db.commit()
        await self.db.refresh(cap)
        return await self._to_response(cap)

    async def add_alias(self, cap_id: UUID, alias: str) -> CapabilityResponse | None:
        """Add an alias to a capability.

        WHY: Admin user journey — provide an alternative name for a capability.
        This supports backward compatibility (old agent configurations using
        a previous name) and cross-team naming conventions.

        Aliases are resolved in routing_service.resolve_capability(): when
        a capability name is not found directly, aliases are checked.

        SIDE EFFECTS: Creates a CapabilityAlias row.
        RETURN: Updated CapabilityResponse or None if capability not found.
        """
        result = await self.db.execute(
            select(Capability)
            .options(selectinload(Capability.mappings), selectinload(Capability.aliases))
            .where(Capability.id == cap_id)
        )
        cap = result.scalar_one_or_none()
        if cap is None:
            return None
        cap.aliases.append(CapabilityAlias(capability_id=cap_id, alias=alias))
        await self.db.commit()
        await self.db.refresh(cap)
        return await self._to_response(cap)

    @staticmethod
    def _compute_tool_digest(
        tool_name: str,
        input_schema: dict[str, object],
        output_schema: dict[str, object] | None,
    ) -> str:
        """Compute SHA-256 digest from a tool's schema identity.

        WHY: The digest captures the tool's semantic identity — name plus
        input/output schemas. When the server's tool schema changes, the
        digest changes, allowing routing to detect drift and skip stale
        mappings.

        The digest is a hex-encoded SHA-256 hash of deterministic JSON:
          hash(tool_name + canonical_json(input_schema) + canonical_json(output_schema))
        """
        # sort_keys + separators gives deterministic JSON so identical schemas
        # always produce the same digest regardless of key ordering.
        raw = (
            tool_name
            + json.dumps(input_schema, sort_keys=True, separators=(",", ":"))
            + json.dumps(output_schema, sort_keys=True, separators=(",", ":"))
        )
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    async def create_mapping(
        self, capability_id: UUID, params: CapabilityMappingCreate
    ) -> CapabilityMappingResponse:
        """Create a mapping from a capability to a tool on an MCP server.

        WHY: Admin user journey — links a normalized capability to a concrete
        tool on a registered MCP server. Multiple servers can map to the same
        capability for redundancy and load distribution.

        SIDE EFFECTS: Persists CapabilityMapping row with computed schema digest
        and active status.
        RETURN: The created mapping with server-generated id, digest, and status.
        """
        tool_stmt = select(ServerTool).where(
            ServerTool.server_id == params.server_id,
            ServerTool.tool_name == params.tool_name,
        )
        tool_result = await self.db.execute(tool_stmt)
        tool = tool_result.scalar_one_or_none()
        if tool is None:
            from api.services.exceptions import ToolNotFoundError

            raise ToolNotFoundError(params.tool_name, str(params.server_id))

        # Compute digest from the current tool schema so the mapping
        # captures the exact tool identity at creation time.
        digest = self._compute_tool_digest(tool.tool_name, tool.input_schema, tool.output_schema)

        # Many-to-one collision detection (#441): if this capability already
        # has a mapping to a *different* tool (distinct tool_name or digest),
        # the new mapping is a collision. Name-based normalization may grant
        # equivalence the raw schemas never intended, so a collision is NOT
        # routable until an admin reviews and approves it.
        collides = await self._has_collision(capability_id, params.tool_name, digest)
        status = "pending_review" if collides else "active"
        failure_class = "schema_mismatch" if collides else None

        pending_since = datetime.now(UTC) if collides else None

        # Store both the digest (for drift detection) and the lifecycle status.
        mapping = CapabilityMapping(
            capability_id=capability_id,
            server_id=params.server_id,
            tool_name=params.tool_name,
            input_mapping=params.input_mapping,
            output_mapping=params.output_mapping,
            is_primary=params.is_primary,
            tool_schema_digest=digest,
            status=status,
            failure_class=failure_class,
            pending_since=pending_since,
        )
        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)
        return self._to_mapping_response(mapping)

    async def _has_collision(self, capability_id: UUID, tool_name: str, digest: str) -> bool:
        """True when another mapping maps a *different* tool_name to this capability (#441).

        Two mappings collide when they resolve the same normalized capability
        to materially different tools (different tool_name). Same-name tools
        on different servers are NOT collisions — they are legitimate
        load-balancing (schema-digest drift is handled separately by #414).
        """
        stmt = select(CapabilityMapping).where(CapabilityMapping.capability_id == capability_id)
        result = await self.db.execute(stmt)
        return any(existing.tool_name != tool_name for existing in result.scalars().all())

    async def get_collisions(self, capability_id: UUID) -> builtins.list[CapabilityMappingResponse]:
        """List many-to-one collisions for a capability (#441).

        Returns mappings that resolve the same capability to multiple distinct
        tools (different tool_name). These must be reviewed before they are
        routable — a low-trust server could otherwise present a high-trust
        capability name (confused deputy).
        """
        stmt = select(CapabilityMapping).where(CapabilityMapping.capability_id == capability_id)
        result = await self.db.execute(stmt)
        mappings = list(result.scalars().all())

        # Group by distinct tool_name.
        identities: dict[str, list[CapabilityMapping]] = {}
        for m in mappings:
            identities.setdefault(m.tool_name, []).append(m)

        # A collision exists when >1 distinct tool_name maps to the capability.
        collisions: list[CapabilityMapping] = []
        if len(identities) > 1:
            for group in identities.values():
                collisions.extend(group)

        return [CapabilityMappingResponse.model_validate(m) for m in collisions]

    async def get_stale_mappings(
        self, failure_class: str | None = None
    ) -> builtins.list[CapabilityMappingResponse]:
        """List all mappings in limbo that need admin review (#444).

        WHY: Admin dashboard shows pending reviews. Includes all non-active,
        non-rejected statuses: 'stale' (schema changed), 'pending_review'
        (collision), 'stale-unverified' (re-inspection failed, fail-closed).
        Ordered oldest-first so the most overdue items surface at the top.
        Optionally filtered to a single failure_class (#447).
        """
        stmt = (
            select(CapabilityMapping)
            .options(selectinload(CapabilityMapping.server))
            .where(CapabilityMapping.status.in_(_LIMBO_STATUSES))
            .order_by(CapabilityMapping.pending_since.asc())
        )
        if failure_class:
            stmt = stmt.where(CapabilityMapping.failure_class == failure_class)
        result = await self.db.execute(stmt)
        mappings = result.scalars().all()
        return [self._to_mapping_response(m) for m in mappings]

    async def get_overdue_reviews(
        self, threshold_hours: int = 24
    ) -> builtins.list[CapabilityMappingResponse]:
        """List limbo mappings that have outlived the review deadline (#444).

        WHY: A pending review with no clock is just a slower version of the
        original staleness problem — limbo grows silently. This method surfaces
        items whose pending_since is older than the threshold so the system can
        alert loudly (email/dashboard/webhook).
        """
        cutoff = datetime.now(UTC) - timedelta(hours=threshold_hours)
        stmt = (
            select(CapabilityMapping)
            .where(
                CapabilityMapping.status.in_(_LIMBO_STATUSES),
                CapabilityMapping.pending_since.is_not(None),
                CapabilityMapping.pending_since <= cutoff,
            )
            .order_by(CapabilityMapping.pending_since.asc())
        )
        result = await self.db.execute(stmt)
        mappings = result.scalars().all()
        return [self._to_mapping_response(m) for m in mappings]

    async def get_prioritized_reviews(self) -> builtins.list[CapabilityMappingResponse]:
        """Review queue ordered so real changes surface above unreachable noise (#447).

        WHY: A queue of 50 unreachable servers + 2 schema changes must not bury
        the changes a human actually needs to act on. Critical classes (drifted,
        schema_mismatch) are bucketed first (oldest within class first), then the
        unreachable classes (unreachable, timeout). Both groups keep an
        oldest-first ordering inside themselves.
        """
        stmt = (
            select(CapabilityMapping)
            .where(CapabilityMapping.status.in_(_LIMBO_STATUSES))
            .order_by(
                CapabilityMapping.failure_class.in_(list(_CRITICAL_CLASSES)).desc(),
                CapabilityMapping.pending_since.asc().nulls_last(),
            )
        )
        result = await self.db.execute(stmt)
        mappings = result.scalars().all()
        return [self._to_mapping_response(m) for m in mappings]

    async def get_queue_summary(self) -> ReviewQueueSummary:
        """Live priority summary of the review queue (#447).

        WHY: Gives the admin UI and the external watchdog a fast, grouped view
        so unreachable items are visually and computationally separated from
        genuine schema changes. The critical tally excludes unreachable classes
        so they never exert review pressure.
        """
        result = await self.db.execute(
            select(CapabilityMapping.status, CapabilityMapping.failure_class).where(
                CapabilityMapping.status.in_(_LIMBO_STATUSES)
            )
        )
        rows = result.all()

        by_failure_class: dict[str, int] = {}
        for _, failure_class in rows:
            if failure_class:
                by_failure_class[failure_class] = by_failure_class.get(failure_class, 0) + 1

        critical = sum(v for k, v in by_failure_class.items() if k in _CRITICAL_CLASSES)
        unreachable = sum(v for k, v in by_failure_class.items() if k in _UNREACHABLE_CLASSES)
        return ReviewQueueSummary(
            total=len(rows),
            critical=critical,
            unreachable=unreachable,
            by_failure_class=by_failure_class,
        )

    async def bulk_retire(
        self,
        failure_class: str | None = None,
        mapping_ids: builtins.list[UUID] | None = None,
    ) -> int:
        """Retire every limbo mapping in a class, or an explicit set of IDs (#447).

        WHY: A bulk "retire all unreachable" action removes stale items without
        making a human click through each of them — unreachable servers are a
        hands-off decision. Also supports retiring an explicit ID list.

        SIDE EFFECTS:
          - Sets status='rejected' and clears pending_since for matching items.
          - Records a MappingReview ('rejected') per retired mapping for audit.
        """
        if not failure_class and not mapping_ids:
            raise ValueError("Specify either failure_class or mapping_ids")

        stmt = select(CapabilityMapping).where(CapabilityMapping.status.in_(_LIMBO_STATUSES))
        if failure_class:
            stmt = stmt.where(CapabilityMapping.failure_class == failure_class)
        if mapping_ids:
            stmt = stmt.where(CapabilityMapping.id.in_(mapping_ids))
        result = await self.db.execute(stmt)
        mappings = list(result.scalars().all())

        now = datetime.now(UTC)
        for m in mappings:
            m.status = "rejected"
            m.pending_since = None
            self.db.add(
                MappingReview(
                    mapping_id=m.id,
                    previous_digest=m.tool_schema_digest,
                    new_digest=m.tool_schema_digest,
                    decision="rejected",
                    reason=f"bulk retired ({failure_class or 'selected'})",
                    reviewed_by=None,
                    created_at=now,
                )
            )
        await self.db.commit()
        return len(mappings)

    async def review_mapping(
        self,
        mapping_id: UUID,
        params: MappingReviewCreate,
        reviewed_by: UUID | None = None,
    ) -> MappingReviewResponse:
        """Approve or reject a stale schema-digest mapping.

        WHY: Admin reviews a mapping whose schema digest has drifted.
        On approval: mapping is re-activated with an updated digest.
        On rejection: mapping status becomes 'rejected' and is skipped
        by routing.

        SIDE EFFECTS:
          - Creates a MappingReview row for audit trail.
          - Updates CapabilityMapping.status and (if approved) digest.
        """
        result = await self.db.execute(
            select(CapabilityMapping).where(CapabilityMapping.id == mapping_id)
        )
        mapping = result.scalar_one_or_none()
        if mapping is None:
            from api.services.exceptions import ServerNotFoundError

            raise ServerNotFoundError(str(mapping_id))

        # Snapshot the old digest before any updates for audit comparison.
        previous_digest = mapping.tool_schema_digest

        if params.decision == "approved":
            # Recompute digest from current ServerTool schema to capture
            # the new tool identity that the admin is accepting.
            tool_stmt = select(ServerTool).where(
                ServerTool.server_id == mapping.server_id,
                ServerTool.tool_name == mapping.tool_name,
            )
            tool_result = await self.db.execute(tool_stmt)
            tool = tool_result.scalar_one_or_none()
            if tool is not None:
                mapping.tool_schema_digest = self._compute_tool_digest(
                    tool.tool_name, tool.input_schema, tool.output_schema
                )
            # Reactivate the mapping so routing picks it up again.
            mapping.status = "active"
            mapping.pending_since = None
        elif params.decision == "rejected":
            # Keep the mapping but mark it rejected so routing skips it.
            mapping.status = "rejected"
            mapping.pending_since = None
            mapping.status = "rejected"
        else:
            raise ValueError(f"Invalid decision: {params.decision}")

        # Create audit trail record so every decision is traceable.
        review = MappingReview(
            mapping_id=mapping.id,
            previous_digest=previous_digest,
            new_digest=mapping.tool_schema_digest,
            decision=params.decision,
            reason=params.reason,
            reviewed_by=reviewed_by,
        )
        self.db.add(review)
        await self.db.commit()
        await self.db.refresh(review)

        return MappingReviewResponse(
            id=review.id,
            mapping_id=review.mapping_id,
            previous_digest=review.previous_digest,
            new_digest=review.new_digest,
            decision=review.decision,
            reason=review.reason,
            reviewed_by=review.reviewed_by,
            created_at=review.created_at,
        )

    @staticmethod
    def _to_mapping_response(m: CapabilityMapping) -> CapabilityMappingResponse:
        """Convert a CapabilityMapping ORM row to its response schema.

        Centralizes the mapping so every review-queue listing carries the same
        fields (including failure_class for #447) without per-call drift.
        """
        return CapabilityMappingResponse(
            id=m.id,
            capability_id=m.capability_id,
            server_id=m.server_id,
            tool_name=m.tool_name,
            input_mapping=m.input_mapping,
            output_mapping=m.output_mapping,
            is_primary=m.is_primary or True,
            routing_weight=m.routing_weight or 1.0,
            tool_schema_digest=m.tool_schema_digest,
            status=m.status,
            pending_since=m.pending_since,
            failure_class=m.failure_class,
        )

    async def _to_response(self, cap: Capability) -> CapabilityResponse:
        return CapabilityResponse(
            id=cap.id,
            name=cap.name,
            domain=cap.domain,
            normalized_input_schema=cap.normalized_input_schema,
            normalized_output_schema=cap.normalized_output_schema,
            description=cap.description,
            status=cap.status or "active",
            deprecated_at=cap.deprecated_at,
            grace_period_days=cap.grace_period_days or 14,
            migration_guidance=cap.migration_guidance,
            created_at=cap.created_at,
            mappings_count=len(cap.mappings) if cap.mappings else 0,
            aliases=[a.alias for a in cap.aliases] if cap.aliases else [],
        )
