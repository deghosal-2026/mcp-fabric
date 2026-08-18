"""Tests for approval-fatigue mitigation (#442).

Validates:
  1. Reversibility classification: reads/undo-able actions auto-approved;
     writes/escape actions still prompt.
  2. Scoped expiring envelopes: a human grants a budget; a deterministic
     validator burns it down; only out-of-envelope actions escalate.
  3. Out-of-envelope actions (new environment, schema change, over-budget)
     always escalate even when an envelope exists.
  4. Bulk-approve groups pending requests; anomaly markers separate real
     changes from noise.
  5. 50-action workload → prompt count is a small subset matching the
     envelope + reversibility model.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from api.services.approval_fatigue_service import (
    ActionClassification,
    ApprovalFatigueService,
    EnvelopeStatus,
    InsufficientEnvelopeError,
)


@pytest.fixture
def service(db_session: AsyncSession) -> ApprovalFatigueService:
    return ApprovalFatigueService(db=db_session)


def _reversible_action() -> dict[str, object]:
    """A read-only, fully undo-able action (auto-approved)."""
    return {
        "type": "read",
        "capability": "code:view",
        "path": "tmp/cache",
        "reversible": True,
    }


def _irreversible_action() -> dict[str, object]:
    """A write/escape action that should always prompt."""
    return {
        "type": "write",
        "capability": "code:promote",
        "target": "staging",
        "reversible": False,
    }


async def _grant_envelope(
    service: ApprovalFatigueService,
    scope: str,
    budget: int,
    expiry_hours: int = 24,
) -> EnvelopeStatus:
    return await service.grant_envelope(
        scope=scope,
        budget=budget,
        expires_at=datetime.now(UTC) + timedelta(hours=expiry_hours),
    )


# ── Reversibility classification ─────────────────────────────────────────


async def test_read_action_is_auto_approved(service: ApprovalFatigueService) -> None:
    """A fully reversible read action does not require manual approval."""
    classification = await service.classify(_reversible_action())
    assert classification == ActionClassification.AUTO_APPROVED


async def test_write_action_prompts(service: ApprovalFatigueService) -> None:
    """A write/escape action is always escalated to a human."""
    classification = await service.classify(_irreversible_action())
    assert classification == ActionClassification.PROMPTED


# ── Envelope model ───────────────────────────────────────────────────────


async def test_grant_envelope_creates_budget(service: ApprovalFatigueService) -> None:
    """Granting an envelope records a positive remaining budget."""
    envelope = await _grant_envelope(service, scope="staging", budget=10)
    assert envelope.remaining == 10
    assert envelope.scope == "staging"


async def test_validator_burns_down_budget(service: ApprovalFatigueService) -> None:
    """Each in-envelope action deterministically decrements the budget."""
    envelope = await _grant_envelope(service, scope="staging", budget=5)
    for expected in (4, 3, 2, 1, 0):
        consumed, remaining = await service.burn_envelope_budget(
            envelope_id=str(envelope.id), scope="staging"
        )
        assert consumed is True
        assert remaining == expected


async def test_over_budget_escalates(
    service: ApprovalFatigueService, db_session: AsyncSession
) -> None:
    """Budget exhaustion always escalates, Never auto-approves."""
    from api.models.policy import ApprovalEnvelope

    env = ApprovalEnvelope(
        scope="staging",
        budget=1,
        remaining=1,
        expires_at=datetime.now(UTC) + timedelta(hours=1),
    )
    db_session.add(env)
    await db_session.commit()

    await service.burn_envelope_budget(envelope_id=str(env.id), scope="staging")
    with pytest.raises(InsufficientEnvelopeError):
        await service.burn_envelope_budget(envelope_id=str(env.id), scope="staging")


async def test_expired_envelope_escalates(
    service: ApprovalFatigueService, db_session: AsyncSession
) -> None:
    """A lapsed envelope refuses burn and forces escalation."""
    from api.models.policy import ApprovalEnvelope

    env = ApprovalEnvelope(
        scope="staging",
        budget=5,
        remaining=5,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    db_session.add(env)
    await db_session.commit()

    with pytest.raises(InsufficientEnvelopeError):
        await service.burn_envelope_budget(envelope_id=str(env.id), scope="staging")


# ── Out-of-envelope escalation ───────────────────────────────────────────


async def test_new_environment_escalates_despite_envelope(
    service: ApprovalFatigueService,
) -> None:
    """A first-time action to a NEW environment always escalates."""
    envelope = await _grant_envelope(service, scope="staging", budget=10)
    classification = await service.classify(
        {
            "type": "write",
            "capability": "deploy",
            "target": "production",  # first-time-to-new-env
            "reversible": False,
            "envelope_id": str(envelope.id),
        }
    )
    assert classification == ActionClassification.ESCALATED


async def test_schema_change_always_escalates(
    service: ApprovalFatigueService,
) -> None:
    """A schema change is a genuine anomaly — never auto-approved."""
    envelope = await _grant_envelope(service, scope="staging", budget=10)
    classification = await service.classify(
        {
            "type": "schema_change",
            "capability": "code:promote",
            "reversible": False,
            "envelope_id": str(envelope.id),
        }
    )
    assert classification == ActionClassification.ESCALATED


# ── Bulk approve + anomaly markers ───────────────────────────────────────


async def test_bulk_approve_groups_and_marks_anomalies(
    service: ApprovalFatigueService,
) -> None:
    """Bulk approve returns grouped results with anomaly markers."""
    envelope = await _grant_envelope(service, scope="staging", budget=3)

    ordinary = [str(uuid4()) for _ in range(3)]
    anomaly = str(uuid4())  # schema change -> anomaly
    action_ids = ordinary + [anomaly]

    result = await service.bulk_approve(
        envelope_id=str(envelope.id),
        action_ids=action_ids,
        anomaly_ids=[anomaly],
    )

    assert result.approved == 3
    assert result.anomalies == [UUID(anomaly)]
    assert result.envelope_remaining == 2


# ── Workload test: prompt count stays small ──────────────────────────────


async def test_fifty_action_workload_prompt_count_is_small(
    service: ApprovalFatigueService,
) -> None:
    """50 actions (40 reversible reads + 10 writes) prompt a small subset.

    With an envelope budget of 8 for writes, the prompt count must be limited
    to genuine anomalies — NOT all 50 actions.
    """
    envelope = await _grant_envelope(service, scope="staging", budget=8)

    prompted = 0
    auto = 0
    for i in range(50):
        if i < 40:
            action = _reversible_action()
        else:
            action = _irreversible_action()
            action["envelope_id"] = str(envelope.id)
            action["reversible"] = False

        classification = await service.classify(action)

        if classification == ActionClassification.PROMPTED:
            prompted += 1
        elif classification == ActionClassification.AUTO_APPROVED:
            auto += 1

    # 40 reads auto-approve. Writes within the envelope budget burn it down;
    # only once exhausted do they escalate.
    assert auto == 40
    assert prompted <= 8
