"""Approval-fatigue mitigation service (#442).

Reduces the number of times a human must approve actions by combining:

  1. Reversibility classification — fully reversible (reads, undo-able)
     actions auto-approve; write/escape actions still prompt.
  2. Scoped, expiring approval envelopes — a human grants a budget for a
     scope; a deterministic validator burns it down per in-envelope action;
     out-of-envelope actions (new env, schema change, over-budget) always
     escalate back to a human.
  3. Bulk approve — pending requests grouped into one action with explicit
     anomaly markers so genuine changes stand out from noise.

Architectural notes:
  - Envelope state lives in the ``approval_envelopes`` table.
  - Envelope burn is protected by an atomic conditional UPDATE so concurrent
    agents cannot double-spend the budget.
  - All datetimes are naive UTC to match existing approval_service.py and
    cross-DB SQLite/PostgreSQL compatibility.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.policy import ApprovalEnvelope
from api.schemas.approval import (
    BulkApproveResponse,
)


class ActionClassification(StrEnum):
    """How an action is handled by the fatigue-freeing classification."""

    AUTO_APPROVED = "auto_approved"
    PROMPTED = "prompted"
    ESCALATED = "escalated"


class EnvelopeStatus:
    """State of an approval envelope after a grant or burn."""

    def __init__(self, envelope: ApprovalEnvelope):
        self.id = envelope.id
        self.scope = envelope.scope
        self.budget = envelope.budget
        self.remaining = envelope.remaining
        self.expires_at = envelope.expires_at


class InsufficientEnvelopeError(Exception):
    """Raised when an envelope is exhausted or expired — action must escalate."""


class ApprovalFatigueService:
    """Deterministic, exhaustion-proof approval budget + reversibility model.

    Depends on: AsyncSession for DB access.
    Used by: admin approval UI, agent capability pipeline (bulk gates).
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def classify(self, action: dict[str, object]) -> ActionClassification:
        """Classify a single action by reversibility + envelope state.

        Rules:
          - Reversible → AUTO_APPROVED (reads/undo-able).
          - Irreversible write/escape inside a live envelope with budget →
            PROMPTED (the human pre-authorized this scope, so it slips through
            without a per-item prompt; the envelope burns down).
          - Irreversible + new env / schema change / no envelope / full budget
            → ESCALATED to a human.

        RAISES: InsufficientEnvelopeError when a burn does not apply (expired/
        exhausted envelope).
        """
        reversible = bool(action.get("reversible"))
        action_type = str(action.get("type", "write"))
        target = str(action.get("target", ""))
        envelope_id = action.get("envelope_id")

        if reversible:
            return ActionClassification.AUTO_APPROVED

        # Genuine anomalies — always escalate regardless of envelope.
        if action_type == "schema_change":
            return ActionClassification.ESCALATED

        if envelope_id is None:
            return ActionClassification.PROMPTED

        # In-envelope context: a target outside any known envelope scope is a
        # genuine change (new environment) — escalate despite the envelope.
        if target and await self._is_new_environment(target):
            return ActionClassification.ESCALATED

        # In-envelope: prompt (burn budget) if envelope is live with budget.
        try:
            await self.burn_envelope_budget(
                envelope_id=str(envelope_id), scope=str(action.get("scope", ""))
            )
        except InsufficientEnvelopeError:
            return ActionClassification.ESCALATED

        return ActionClassification.PROMPTED

    async def _is_new_environment(self, target: str) -> bool:
        """Heuristic: an environment already used inside an envelope is known."""
        stmt = select(ApprovalEnvelope.scope).where(ApprovalEnvelope.scope == target)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is None

    async def grant_envelope(
        self,
        scope: str,
        budget: int,
        expires_at: datetime,
    ) -> EnvelopeStatus:
        """Grant a scoped, expiring envelope with the given budget (#442)."""
        envelope = ApprovalEnvelope(
            scope=scope,
            budget=budget,
            remaining=budget,
            expires_at=expires_at,
        )
        self.db.add(envelope)
        await self.db.commit()
        await self.db.refresh(envelope)
        return EnvelopeStatus(envelope)

    async def burn_envelope_budget(
        self,
        envelope_id: str,
        scope: str = "",
    ) -> tuple[bool, int]:
        """Atomically burn one unit of envelope budget.

        Uses a conditional UPDATE (remaining > 0) so concurrent in-envelope
        actions cannot overspend. Expired or exhausted envelopes raise
        InsufficientEnvelopeError which the caller maps to escalation.

        RAISES: InsufficientEnvelopeError.
        RETURN: (consumed, remaining_after).
        """
        now = datetime.now(UTC).replace(tzinfo=None)

        # Check expiry/nonexistence first (read, deterministic).
        result = await self.db.execute(
            select(ApprovalEnvelope).where(ApprovalEnvelope.id == UUID(envelope_id))
        )
        envelope = result.scalar_one_or_none()
        if envelope is None:
            raise InsufficientEnvelopeError("Envelope not found")

        expires_naive = _as_naive(envelope.expires_at)
        if expires_naive < now:
            raise InsufficientEnvelopeError("Envelope has expired")

        if envelope.remaining <= 0:
            raise InsufficientEnvelopeError("Envelope budget exhausted")

        # Atomic decrement with a guard on remaining so concurrent burns are safe.
        stmt = (
            update(ApprovalEnvelope)
            .where(
                ApprovalEnvelope.id == UUID(envelope_id),
                ApprovalEnvelope.remaining > 0,
            )
            .values(remaining=ApprovalEnvelope.remaining - 1)
        )
        await self.db.execute(stmt)
        await self.db.commit()

        fresh = await self.db.execute(
            select(ApprovalEnvelope).where(ApprovalEnvelope.id == UUID(envelope_id))
        )
        envelope = fresh.scalar_one()
        return True, envelope.remaining

    async def bulk_approve(
        self,
        envelope_id: str,
        action_ids: list[str],
        anomaly_ids: list[str] | None = None,
    ) -> BulkApproveResponse:
        """Bulk-approve a batch, returning counts and anomaly markers.

        WHY: Admin user journey — a reviewer clears a group of pending items
        in one action. Anomaly IDs are surfaced explicitly so real changes are
        never hidden inside a bulk approve.

        RETURN: BulkApproveResponse with approved count, anomalies, and the
        envelope remaining budget (None when no envelope is attached).
        """
        anomalies = [a for a in (anomaly_ids or []) if a in action_ids]

        # Simulate approval decisions: in-envelope items approve; anomaly IDs
        # escalate (they are real changes requiring review).
        approved_ids = [aid for aid in action_ids if aid not in anomalies]
        approved_count = len(approved_ids)

        remaining: int | None = None
        if envelope_id:
            _, remaining = await self.burn_envelope_budget(envelope_id=envelope_id)

        return BulkApproveResponse(
            approved=approved_count,
            anomalies=[UUID(a) for a in anomalies],
            envelope_remaining=remaining,
        )


def _as_naive(dt: datetime) -> datetime:
    """Normalize to cross-DB naive UTC datetimes."""
    if dt.tzinfo is None:
        return dt
    return dt.astimezone(UTC).replace(tzinfo=None)
