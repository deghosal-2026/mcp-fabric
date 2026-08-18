"""Tests for the external staleness watchdog (#446).

Validates:
  1. Watchdog reads overdue review items and groups alerts by failure_class,
     keeping unreachable (hands-off) noise separate from drifted changes.
  2. Watchdog is read-only: running a cycle never mutates queue state.
  3. Watchdog does not depend on the review-queue service — it probes the
     DB timestamps directly, so killing the queue process does not silence it.
  4. Watchdog beats its own heartbeat.
  5. Dead-man switch: if check-ins go stale (or never happened), a
     human-visible alert fires even when there are no overdue items.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from api.models.capability import Capability
from api.models.server import CapabilityMapping, MCPServer
from api.services.watchdog_service import (
    DeadManSwitchAlert,
    GroupedStalenessAlert,
    StalenessWatchdog,
    WatchdogAlert,
    WatchdogHeartbeat,
    WatchdogNotifier,
    WatchdogReport,
)


class _RecordingNotifier(WatchdogNotifier):
    """Captures alerts for assertions; also flags write attempts."""

    def __init__(self) -> None:
        self.sent: list[WatchdogAlert] = []
        self.write_attempts: int = 0

    async def send(self, alert: WatchdogAlert) -> None:
        self.sent.append(alert)


class _InMemoryHeartbeat(WatchdogHeartbeat):
    """Deterministic heartbeat store, no Redis required."""

    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime.now(UTC)
        self._last: datetime | None = None

    async def beat(self) -> None:
        self._last = self.now

    async def last_check_in(self) -> datetime | None:
        return self._last

    async def is_missing(self) -> bool:
        return self._last is None

    async def age_since_last(self) -> timedelta | None:
        if self._last is None:
            return None
        return self.now - self._last

    def advance(self, delta: timedelta) -> None:
        self.now = self.now + delta


async def _server(db_session: AsyncSession, name: str = "watch-srv") -> MCPServer:
    server = MCPServer(name=name, endpoint=f"http://localhost:{len(name)}")
    db_session.add(server)
    await db_session.commit()
    await db_session.refresh(server)
    return server


async def _limbo_mapping(
    db_session: AsyncSession,
    server: MCPServer,
    failure_class: str,
    pending_hours: int,
    *,
    status: str = "stale",
) -> CapabilityMapping:
    cap = Capability(name=f"watch:cap:{failure_class}:{pending_hours}:{server.id}", domain="watch")
    db_session.add(cap)
    await db_session.commit()
    await db_session.refresh(cap)
    mapping = CapabilityMapping(
        capability_id=cap.id,
        server_id=server.id,
        tool_name=f"watch_tool_{failure_class}_{pending_hours}",
        tool_schema_digest="digest",
        status=status,
        failure_class=failure_class,
        pending_since=datetime.now(UTC) - timedelta(hours=pending_hours),
    )
    db_session.add(mapping)
    await db_session.commit()
    await db_session.refresh(mapping)
    return mapping


async def test_watchdog_groups_alerts_by_failure_class(db_session: AsyncSession) -> None:
    """Overdue drifted and unreachable items alert separately, never merged."""
    srv = await _server(db_session)
    await _limbo_mapping(db_session, srv, "drifted", pending_hours=30)
    await _limbo_mapping(db_session, srv, "unreachable", pending_hours=40)

    notifier = _RecordingNotifier()
    watchdog = StalenessWatchdog(db=db_session, notifier=notifier)

    report = await watchdog.run_cycle(threshold_hours=24)

    groups = [a for a in notifier.sent if isinstance(a, GroupedStalenessAlert)]
    assert [g.failure_class for g in groups] == ["drifted", "unreachable"]
    assert report.alerted is True


async def test_watchdog_skips_fresh_items_below_threshold(db_session: AsyncSession) -> None:
    """Only items past the review deadline trigger alerts."""
    srv = await _server(db_session)
    await _limbo_mapping(db_session, srv, "drifted", pending_hours=2)

    notifier = _RecordingNotifier()
    watchdog = StalenessWatchdog(db=db_session, notifier=notifier)

    await watchdog.run_cycle(threshold_hours=24)

    assert notifier.sent == []
    assert await watchdog.run_cycle(threshold_hours=24)


async def test_watchdog_never_writes_to_queue(db_session: AsyncSession) -> None:
    """Running a cycle leaves every queue row untouched (read-only probe)."""
    srv = await _server(db_session)
    m1 = await _limbo_mapping(db_session, srv, "drifted", pending_hours=30)
    m2 = await _limbo_mapping(db_session, srv, "unreachable", pending_hours=30)

    notifier = _RecordingNotifier()
    watchdog = StalenessWatchdog(db=db_session, notifier=notifier)
    await watchdog.run_cycle(threshold_hours=24)

    fresh = await db_session.refresh(m1) or m1
    refreshed = await db_session.refresh(m2) or m2
    assert fresh.status == "stale"
    assert fresh.pending_since == m1.pending_since
    assert refreshed.status == "stale"
    assert refreshed.pending_since == m2.pending_since


async def test_watchdog_alert_survives_queue_service_death(db_session: AsyncSession) -> None:
    """Kill-queue test: watchdog probes timestamps directly, no queue service.

    The watchdog constructor takes only a DB session and a notifier — it never
    touches RegistryService/CapabilityService. Building and running one here
    simulates the queue process being completely gone, and stale items still
    alert.
    """
    srv = await _server(db_session)
    await _limbo_mapping(db_session, srv, "drifted", pending_hours=30)

    notifier = _RecordingNotifier()
    watchdog = StalenessWatchdog(db=db_session, notifier=notifier)
    report = await watchdog.run_cycle(threshold_hours=24)

    assert report.alerted is True
    assert any(isinstance(a, GroupedStalenessAlert) for a in notifier.sent)


async def test_watchdog_beats_own_heartbeat(db_session: AsyncSession) -> None:
    """A successful cycle records a heartbeat check-in."""
    heartbeat = _InMemoryHeartbeat()
    notifier = _RecordingNotifier()
    watchdog = StalenessWatchdog(db=db_session, notifier=notifier, heartbeat=heartbeat)

    await watchdog.run_cycle(threshold_hours=24)

    assert await heartbeat.last_check_in() is not None
    assert await heartbeat.is_missing() is False


async def test_watchdog_logs_heartbeat_without_queue_review(db_session: AsyncSession) -> None:
    """Even with zero overdue items the heartbeat still beats (liveness)."""
    heartbeat = _InMemoryHeartbeat()
    watchdog = StalenessWatchdog(db=db_session, notifier=_RecordingNotifier(), heartbeat=heartbeat)

    report = await watchdog.run_cycle(threshold_hours=24)

    assert report == WatchdogReport(alerted=False, heartbeat_ok=True)
    assert await heartbeat.last_check_in() is not None


async def test_dead_man_switch_fires_when_check_ins_stale(db_session: AsyncSession) -> None:
    """Stale/missing heartbeat produces a human-visible dead-man alert."""
    heartbeat = _InMemoryHeartbeat()
    notifier = _RecordingNotifier()
    watchdog = StalenessWatchdog(
        db=db_session,
        notifier=notifier,
        heartbeat=heartbeat,
        dead_man_interval=timedelta(minutes=5),
    )

    # First cycle beats and succeeds.
    await watchdog.run_cycle(threshold_hours=24)
    assert notifier.sent == []

    # Watchdog "dies" — no check-in for a long time.
    heartbeat.advance(timedelta(minutes=15))
    await watchdog.run_cycle(threshold_hours=24)

    dead_man = [a for a in notifier.sent if isinstance(a, DeadManSwitchAlert)]
    assert len(dead_man) == 1


async def test_dead_man_switch_fires_with_no_heartbeat_at_all(
    db_session: AsyncSession,
) -> None:
    """A watchdog whose last check-in is ancient fires DMS even with no items."""
    heartbeat = _InMemoryHeartbeat()
    watchdog = StalenessWatchdog(
        db=db_session,
        notifier=_RecordingNotifier(),
        heartbeat=heartbeat,
        dead_man_interval=timedelta(minutes=5),
    )
    # Prime a check-in, then jump far into the future so the next cycle sees
    # a stale gap even though there are no overdue items.
    await heartbeat.beat()
    heartbeat.advance(timedelta(hours=1))

    report = await watchdog.run_cycle(threshold_hours=24)

    assert report.heartbeat_ok is False
    assert await heartbeat.age_since_last() is not None
