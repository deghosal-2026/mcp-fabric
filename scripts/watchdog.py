#!/usr/bin/env python3
"""Standalone staleness watchdog entrypoint (#446).

Runs as an independent process/container that depends only on the database
(and optional Redis for the heartbeat). It must NOT depend on the API/worker/
beat services — that independence is the whole point of #446.

Prometheus metrics are exposed on ``WATCHDOG_METRICS_PORT`` (default 9100) so
Alertmanager can scrape the watchdog's own liveness via a dead-man-switch rule.

Usage::

    python scripts/watchdog.py --interval 60 --threshold-hours 24
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import signal
import sys
from datetime import timedelta

from prometheus_client import Counter, Gauge, start_http_server

from api.config import settings
from api.database import async_session
from api.services.watchdog_service import (
    StructuredLogNotifier,
    StalenessWatchdog,
)

log = logging.getLogger("api.watchdog")

# Watchdog-owned metrics. These are scraped independently of the API's
# /v1/metrics endpoint — the watchdog is a separate process.
watchdog_cycles_total = Counter(
    "fabric_watchdog_cycles_total",
    "Total watchdog cycles completed",
)
watchdog_alerts_total = Counter(
    "fabric_watchdog_alerts_total",
    "Watchdog alerts emitted by failure_class",
    labelnames=["failure_class"],
)
watchdog_last_success_timestamp = Gauge(
    "fabric_watchdog_last_success_timestamp",
    "Unix timestamp of the last successful watchdog cycle",
)
watchdog_overdue_items = Gauge(
    "fabric_watchdog_overdue_items",
    "Overdue review items observed in the last cycle",
    labelnames=["failure_class"],
)


def build_heartbeat():  # type: ignore[no-untyped-def]
    """Build a heartbeat store. Uses Redis if configured, else in-memory."""
    redis_url = os.getenv("REDIS_URL", settings.redis_url)
    if redis_url and redis_url.startswith("redis://"):
        try:
            from api.services.watchdog_service import RedisHeartbeat  # noqa: F401
        except ImportError:
            log.warning("redis not available; falling back to in-memory heartbeat")
            from api.services.watchdog_service import InMemoryHeartbeat

            return InMemoryHeartbeat()
        return RedisHeartbeat(redis_url, key="mcp_fabric:watchdog:heartbeat")
    from api.services.watchdog_service import InMemoryHeartbeat

    return InMemoryHeartbeat()


async def run_forever(interval: int, threshold_hours: int, dead_man_minutes: int) -> None:
    notifier = StructuredLogNotifier()
    heartbeat = build_heartbeat()
    watchdog = StalenessWatchdog(
        db=None,  # type: ignore[arg-type]
        notifier=notifier,
        heartbeat=heartbeat,
        dead_man_interval=timedelta(minutes=dead_man_minutes),
    )

    stop = asyncio.Event()

    def _stop() -> None:
        stop.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop = asyncio.get_running_loop()
            loop.add_signal_handler(sig, _stop)
        except NotImplementedError:
            signal.signal(sig, lambda *_: _stop())

    log.info("watchdog started (interval=%ss threshold=%sh)", interval, threshold_hours)

    while not stop.is_set():
        async with async_session() as db:
            watchdog.db = db
            try:
                report = await watchdog.run_cycle(threshold_hours=threshold_hours)
                watchdog_cycles_total.inc()
                watchdog_last_success_timestamp.set(asyncio.get_event_loop().time())
                if report.alerted:
                    log.warning("watchdog cycle alerted heartbeat_ok=%s", report.heartbeat_ok)
                else:
                    log.debug("watchdog cycle clean")
            except Exception:
                log.exception("watchdog cycle failed")
        try:
            await asyncio.wait_for(stop.wait(), timeout=interval)
        except TimeoutError:
            pass

    log.info("watchdog stopped")


def main() -> None:
    parser = argparse.ArgumentParser(description="MCP Fabric staleness watchdog")
    parser.add_argument("--interval", type=int, default=60, help="seconds between cycles")
    parser.add_argument("--threshold-hours", type=int, default=24, help="overdue threshold")
    parser.add_argument("--dead-man-minutes", type=int, default=10, help="DMS interval")
    parser.add_argument(
        "--metrics-port", type=int, default=int(os.getenv("WATCHDOG_METRICS_PORT", "9100"))
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=os.getenv("LOG_LEVEL", "INFO"),
        format='{"event":"%(message)s","level":"%(levelname)s","logger":"%(name)s"}',
    )

    start_http_server(args.metrics_port)
    log.info("prometheus metrics on :%s", args.metrics_port)

    try:
        asyncio.run(
            run_forever(args.interval, args.threshold_hours, args.dead_man_minutes)
        )
    except KeyboardInterrupt:
        sys.exit(0)


if __name__ == "__main__":
    main()
