"""External staleness watchdog — independent of the review-queue service (#446).

WHY: The staleness alarm must not share liveness with the queue it watches.
If the review-queue process dies, stale items still need to trigger alerts.
This module is therefore read-only against the database (it never writes to
the queue) and exposes its own heartbeat so a dead-man switch can detect a
watchdog that has stopped checking in.

DEPLOYMENT: Run via ``scripts/watchdog.py`` as a standalone process/container
that depends only on the database (and optional Redis for the heartbeat). It
must NOT depend on the API/worker/beat services.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Protocol, runtime_checkable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.models.server import CapabilityMapping

# Limbo statuses the watchdog probes. Mirrors capability_service._LIMBO_STATUSES
# without importing it — the watchdog must not depend on the queue service.
_LIMBO_STATUSES = ("stale", "pending_review", "stale-unverified")

# Critical vs unreachable classes — kept in sync with capability_service so
# grouped notifications separate actionable change from hands-off noise.
_CRITICAL_CLASSES = ("drifted", "schema_mismatch")
_UNREACHABLE_CLASSES = ("unreachable", "timeout")


@runtime_checkable
class WatchdogHeartbeat(Protocol):
    """Liveness store owned by the watchdog, not the queue."""

    async def beat(self) -> None: ...
    async def last_check_in(self) -> datetime | None: ...
    async def is_missing(self) -> bool: ...
    async def age_since_last(self) -> timedelta | None: ...


@runtime_checkable
class WatchdogNotifier(Protocol):
    """Delivery channel for watchdog alerts (webhook/dashboard/log)."""

    async def send(self, alert: WatchdogAlert) -> None: ...


@dataclass
class WatchdogAlert:
    """Base type for watchdog alerts."""

    emitted_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass
class GroupedStalenessAlert(WatchdogAlert):
    """Overdue items grouped by failure_class so unreachable ≠ drift stay apart."""

    failure_class: str = ""
    item_count: int = 0
    oldest_pending_since: datetime | None = None
    sample_mapping_ids: list[UUID] = field(default_factory=list)
    is_critical: bool = False
    threshold_hours: int = 24


@dataclass
class DeadManSwitchAlert(WatchdogAlert):
    """Watchdog liveness alert — fired when check-ins stop arriving."""

    last_check_in: datetime | None = None
    age: timedelta | None = None
    dead_man_interval: timedelta = timedelta(minutes=10)


@dataclass(frozen=True)
class WatchdogReport:
    """Outcome of a single watchdog cycle."""

    alerted: bool
    heartbeat_ok: bool


class StalenessWatchdog:
    """Read-only staleness probe + liveness heartbeat, independent of the queue.

    Dependencies: only an ``AsyncSession`` (read) and a ``WatchdogNotifier``.
    Never imports or calls ``CapabilityService``/``RegistryService`` — those are
    queue-service components and must not be on the watchdog's critical path.
    """

    def __init__(
        self,
        db: AsyncSession,
        notifier: WatchdogNotifier,
        heartbeat: WatchdogHeartbeat | None = None,
        dead_man_interval: timedelta = timedelta(minutes=10),
    ) -> None:
        self.db = db
        self.notifier = notifier
        self.heartbeat = heartbeat
        self.dead_man_interval = dead_man_interval

    async def run_cycle(self, threshold_hours: int = 24) -> WatchdogReport:
        """Probe overdue items, beat the heartbeat, evaluate the dead-man switch.

        Order matters for the dead-man switch: we measure the gap *before* this
        cycle's beat so a watchdog that just woke up after a long silence still
        reports the missed window. The very first cycle has no prior check-in
        and is treated as bootstrapping (no DMS alert).
        """
        prior_age: timedelta | None = None
        if self.heartbeat is not None:
            prior_age = await self.heartbeat.age_since_last()

        alerted = await self._probe_overdue(threshold_hours)

        heartbeat_ok = True
        if self.heartbeat is not None:
            await self.heartbeat.beat()
            if prior_age is not None and prior_age > self.dead_man_interval:
                await self.notifier.send(
                    DeadManSwitchAlert(
                        last_check_in=await self.heartbeat.last_check_in(),
                        age=prior_age,
                        dead_man_interval=self.dead_man_interval,
                    )
                )
                heartbeat_ok = False
                alerted = True

        return WatchdogReport(alerted=alerted, heartbeat_ok=heartbeat_ok)

    async def _probe_overdue(self, threshold_hours: int) -> bool:
        """Read-only: query limbo items past the deadline, grouped by failure_class."""
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
        rows = list(result.scalars().all())

        if not rows:
            return False

        grouped: dict[str, list[CapabilityMapping]] = {}
        for row in rows:
            key = row.failure_class or "unknown"
            grouped.setdefault(key, []).append(row)

        # Critical classes first so a human sees real changes before noise.
        ordered_keys = sorted(
            grouped.keys(),
            key=lambda k: (
                0 if k in _CRITICAL_CLASSES else 1 if k in _UNREACHABLE_CLASSES else 2,
                k,
            ),
        )

        for failure_class in ordered_keys:
            items = grouped[failure_class]
            await self.notifier.send(
                GroupedStalenessAlert(
                    failure_class=failure_class,
                    item_count=len(items),
                    oldest_pending_since=items[0].pending_since,
                    sample_mapping_ids=[m.id for m in items[:5]],
                    is_critical=failure_class in _CRITICAL_CLASSES,
                    threshold_hours=threshold_hours,
                )
            )
        return True


class InMemoryHeartbeat(WatchdogHeartbeat):
    """Process-local heartbeat for tests and single-process deployments."""

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


class StructuredLogNotifier(WatchdogNotifier):
    """Notifier that records alerts to structured logs (default channel)."""

    def __init__(self, logger: logging.Logger | None = None) -> None:
        self._log = logger if logger is not None else logging.getLogger("api.watchdog")

    async def send(self, alert: WatchdogAlert) -> None:
        if isinstance(alert, GroupedStalenessAlert):
            self._log.warning(
                "staleness_alert failure_class=%s count=%d critical=%s",
                alert.failure_class,
                alert.item_count,
                alert.is_critical,
            )
        elif isinstance(alert, DeadManSwitchAlert):
            self._log.error(
                "dead_man_switch age=%s interval=%s",
                alert.age,
                alert.dead_man_interval,
            )


class RedisHeartbeat(WatchdogHeartbeat):
    """Redis-backed heartbeat for multi-process/HA watchdog deployments.

    Stores a timestamped key with a TTL so a dead watchdog's check-in expires
    and the dead-man switch fires. Falls back gracefully if Redis is unavailable.
    """

    KEY_DEFAULT = "mcp_fabric:watchdog:heartbeat"

    def __init__(
        self,
        redis_url: str,
        key: str = KEY_DEFAULT,
        ttl_seconds: int = 600,
    ) -> None:
        import redis.asyncio as aioredis

        self._redis = aioredis.from_url(redis_url, decode_responses=True)
        self._key = key
        self._ttl = ttl_seconds
        self._last: datetime | None = None

    async def beat(self) -> None:
        now = datetime.now(UTC).isoformat()
        try:
            await self._redis.set(self._key, now, ex=self._ttl)
            self._last = datetime.now(UTC)
        except Exception:
            logging.getLogger("api.watchdog").warning("redis heartbeat write failed")

    async def last_check_in(self) -> datetime | None:
        try:
            value = await self._redis.get(self._key)
            if value is None:
                return None
            return datetime.fromisoformat(str(value))
        except Exception:
            return self._last

    async def is_missing(self) -> bool:
        return await self.last_check_in() is None

    async def age_since_last(self) -> timedelta | None:
        last = await self.last_check_in()
        if last is None:
            return None
        return datetime.now(UTC) - last
