from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.admin import AdminUser
from api.models.agent import (
    AgentClass,
    AgentClassPack,
    AgentIdentity,
    CapabilityPack,
    PackAssignment,
    TrustAssignment,
)
from api.models.audit import AlertEvent, ApprovalRequest, AuditEvent, AlertRule
from api.models.capability import Capability
from api.models.server import CapabilityMapping, MCPServer, ServerTool
from api.seeders.demo_data import seed_demo_data


@pytest.mark.asyncio
async def test_seed_demo_data_creates_full_ui_dataset(db_session: AsyncSession) -> None:
    await seed_demo_data(db_session)

    assert len((await db_session.execute(select(AdminUser))).scalars().all()) >= 4
    assert len((await db_session.execute(select(MCPServer))).scalars().all()) >= 10
    assert len((await db_session.execute(select(ServerTool))).scalars().all()) >= 10
    assert len((await db_session.execute(select(Capability))).scalars().all()) >= 12
    assert len((await db_session.execute(select(CapabilityMapping))).scalars().all()) >= 10
    assert len((await db_session.execute(select(AgentClass))).scalars().all()) >= 4
    assert len((await db_session.execute(select(AgentIdentity))).scalars().all()) >= 4
    assert len((await db_session.execute(select(CapabilityPack))).scalars().all()) >= 3
    assert len((await db_session.execute(select(PackAssignment))).scalars().all()) >= 6
    assert len((await db_session.execute(select(AgentClassPack))).scalars().all()) >= 3
    assert len((await db_session.execute(select(TrustAssignment))).scalars().all()) >= 8
    assert len((await db_session.execute(select(ApprovalRequest))).scalars().all()) >= 8
    assert len((await db_session.execute(select(AuditEvent))).scalars().all()) >= 12
    assert len((await db_session.execute(select(AlertRule))).scalars().all()) >= 2
    assert len((await db_session.execute(select(AlertEvent))).scalars().all()) >= 4


@pytest.mark.asyncio
async def test_seed_demo_data_is_idempotent(db_session: AsyncSession) -> None:
    await seed_demo_data(db_session)
    first_counts = {
        'admins': len((await db_session.execute(select(AdminUser))).scalars().all()),
        'servers': len((await db_session.execute(select(MCPServer))).scalars().all()),
        'approvals': len((await db_session.execute(select(ApprovalRequest))).scalars().all()),
        'audit': len((await db_session.execute(select(AuditEvent))).scalars().all()),
    }

    await seed_demo_data(db_session)
    second_counts = {
        'admins': len((await db_session.execute(select(AdminUser))).scalars().all()),
        'servers': len((await db_session.execute(select(MCPServer))).scalars().all()),
        'approvals': len((await db_session.execute(select(ApprovalRequest))).scalars().all()),
        'audit': len((await db_session.execute(select(AuditEvent))).scalars().all()),
    }

    assert second_counts == first_counts


@pytest.mark.asyncio
async def test_seed_demo_data_creates_mixed_status_records(db_session: AsyncSession) -> None:
    await seed_demo_data(db_session)

    approvals = (await db_session.execute(select(ApprovalRequest))).scalars().all()
    approval_statuses = {approval.status for approval in approvals}
    assert {'pending', 'approved', 'denied'}.issubset(approval_statuses)

    servers = (await db_session.execute(select(MCPServer))).scalars().all()
    health_statuses = {server.health_status for server in servers}
    trust_levels = {server.trust_level for server in servers}
    assert {'healthy', 'degraded', 'unhealthy'}.issubset(health_statuses)
    assert {'trusted', 'restricted', 'approval-gated', 'unreviewed'}.issubset(trust_levels)

    alerts = (await db_session.execute(select(AlertEvent))).scalars().all()
    assert any(alert.acknowledged_at is None for alert in alerts)
    assert any(alert.acknowledged_at is not None for alert in alerts)
