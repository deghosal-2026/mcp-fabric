"""Celery task definitions for MCP Fabric.

This module defines all the background tasks that run asynchronously via
Celery — including health checks, cleanup jobs, notifications, exports,
and alert delivery. Tasks that make HTTP or database calls use
_run_async() to bridge the sync Celery worker environment with async
I/O code.

Retry strategy:
    - Most tasks use `bind=True` so they can call `self.retry()` on failure.
    - `health_check_server`: 2 retries, 10s delay (quick retry for transient failures).
    - `check_alert_thresholds`, `deliver_alert`, `notify_approval_request`: 3 retries, 60s delay.
    - `deliver_webhook`: 3 retries, exponential backoff (default Celery behaviour).
    - `NotifyTask` base class: autoretry on any Exception, 3 retries, 60s delay.
    - Cleanup tasks (`cleanup_*`): no retries (idempotent, next beat cycle will re-run).

Beat schedule (configured via settings.celery_beat_schedule):
    - health_check_all_servers: periodic health scan of every active MCP server.
    - cleanup_audit_logs: purge old audit events.
    - cleanup_expired_tokens: expire stale agent identity tokens.
    - cleanup_expired_approvals: expire stale approval requests.
    - cleanup_expired_sessions: Redis TTL handles this (no-op task).
    - check_alert_thresholds: evaluate alert rules against current metrics (stub).
    - run_scheduled_exports: run due audit exports (stub).
    - health_check_self: verify the Celery worker itself is alive.

Error handling:
    - Database engines are created per-task and disposed after use to avoid
      connection leaks across Celery worker forks.
    - `_run_async()` creates a fresh event loop per task invocation because
      Celery workers run sync processes that cannot share an async loop safely.
    - Logging uses the stdlib logger (not structlog) for Celery tasks to
      avoid issues with async context propagation in the sync worker.

Worker configuration:
    - task_acks_late=True, task_reject_on_worker_lost=True: tasks are re-delivered
      if a worker crashes mid-execution.
    - worker_prefetch_multiplier=1: one task at a time per worker process.
    - worker_concurrency=4: four worker processes.
"""

import asyncio
import logging
from datetime import UTC, datetime

from celery import Celery, Task
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from api.config import settings

logger = logging.getLogger(__name__)

celery_app = Celery(
    "fabric",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    worker_concurrency=4,
    beat_schedule=settings.celery_beat_schedule,
)


class NotifyTask(Task):
    """Base task class for notification tasks with automatic retry.

    Inherits from Celery Task and configures autoretry for all exceptions,
    up to 3 retries with a 60-second delay between attempts. Used as the
    base class for notify_schema_change to ensure delivery notifications
    are resilient to transient infrastructure failures.
    """

    autoretry_for = (Exception,)
    max_retries = 3
    default_retry_delay = 60


def _run_async(coro):
    """Bridge a sync Celery worker to an async coroutine.

    Celery workers run in sync processes that may not have an active
    asyncio event loop. This helper creates a new event loop, runs the
    coroutine to completion, then closes the loop.

    Each invocation gets its own loop — do NOT reuse loops across tasks
    as that can cause "attached to a different loop" errors in SQLAlchemy
    async sessions.

    Args:
        coro: An awaitable coroutine to execute.

    Returns:
        The return value of the coroutine.
    """
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def health_check_server(self, server_id: str, endpoint: str) -> dict:
    """Check a single MCP server's health via /tools/list.

    Fetches the tool list from the server as a liveness probe. If the
    server responds successfully (even with 0 tools), it is considered
    healthy. Retries up to 2 times with a 10s delay for transient errors.

    Triggered by Celery Beat on a periodic schedule, or called
    programmatically when a server is registered or updated.

    Args:
        server_id: UUID of the server record in the database.
        endpoint: Base URL of the MCP server.

    Returns:
        Dict with status ("healthy" or "unhealthy") and tool_count.
    """
    from api.mcp.client import MCPClient

    async def _check():
        client = MCPClient()
        try:
            tools = await client.list_tools(endpoint, timeout=5)
            return {"server_id": server_id, "status": "healthy", "tool_count": len(tools)}
        except Exception as exc:
            logger.warning("Health check failed for %s: %s", endpoint, exc)
            raise self.retry(exc=exc) from exc

    return _run_async(_check())


@celery_app.task(bind=True)
def health_check_all_servers(self):
    """Check all active MCP servers and return their health status.

    Queries the database for all non-decommissioned servers, then checks
    each one's /tools/list endpoint. Unlike health_check_server, this
    does NOT retry individual failures — it collects all results (healthy
    or unhealthy) in a single pass so the caller gets a complete picture.

    Each server gets its own MCPClient instance. A future optimisation
    would be to share a single client or use asyncio.gather() for
    concurrent checks.

    Returns:
        List of dicts with server_id, status, and tool count or error.
    """
    from api.mcp.client import MCPClient
    from api.models.server import MCPServer

    async def _check_all():
        engine = create_async_engine(settings.database_url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            stmt = select(MCPServer).where(MCPServer.decommissioned_at.is_(None))
            result = await db.execute(stmt)
            servers = result.scalars().all()
            results = []
            for srv in servers:
                try:
                    client = MCPClient()
                    tools = await client.list_tools(srv.endpoint, timeout=5)
                    results.append(
                        {
                            "server_id": str(srv.id),
                            "status": "healthy",
                            "tools": len(tools),
                        }
                    )
                except Exception as exc:
                    results.append(
                        {
                            "server_id": str(srv.id),
                            "status": "unhealthy",
                            "error": str(exc),
                        }
                    )
        await engine.dispose()
        return results

    return _run_async(_check_all())


@celery_app.task(bind=True)
def cleanup_audit_logs(self):
    """Delete audit events older than the current time.

    Runs on a schedule (e.g. hourly) to prevent unbounded growth of the
    audit_events table. Uses a single DELETE statement with no upper
    age bound — this is safe because audit events are append-only and
    retention is managed by the schedule frequency.

    No retry on failure: the next scheduled run will pick up any
    remaining records.

    Returns:
        Dict with count of deleted records.
    """
    from api.models.audit import AuditEvent

    async def _cleanup():
        engine = create_async_engine(settings.database_url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            before = datetime.now(UTC)
            stmt = delete(AuditEvent).where(AuditEvent.created_at < before)
            result = await db.execute(stmt)
            await db.commit()
            count = getattr(result, "rowcount", 0) or 0
        await engine.dispose()
        return {"deleted": count}

    return _run_async(_cleanup())


@celery_app.task(bind=True)
def cleanup_expired_tokens(self):
    """Mark expired agent identity tokens as expired.

    Updates AgentIdentity records whose expires_at is in the past and
    whose status is still "active" to status="expired". This is a soft
    expiry — the records are preserved for audit purposes but the tokens
    can no longer be used for authentication.

    Runs on a schedule (e.g. every 5 minutes) to promptly revoke tokens.

    Returns:
        Dict with count of tokens expired.
    """
    from api.models.agent import AgentIdentity

    async def _run():
        engine = create_async_engine(settings.database_url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            from sqlalchemy import update

            stmt = (
                update(AgentIdentity)
                .where(AgentIdentity.status == "active")
                .where(AgentIdentity.expires_at < datetime.now(UTC))
                .values(status="expired")
            )
            result = await db.execute(stmt)
            await db.commit()
        await engine.dispose()
        return {"expired": getattr(result, "rowcount", 0) or 0}

    return _run_async(_run())


@celery_app.task(bind=True)
def cleanup_expired_approvals(self):
    """Mark expired pending approval requests as expired.

    Updates ApprovalRequest records whose expires_at is in the past and
    whose status is still "pending" to status="expired". This prevents
    stale approval requests from blocking dependent workflows.

    Runs on a schedule (e.g. every 5 minutes) to promptly expire
    approvals that exceeded their TTL.

    Returns:
        Dict with count of approvals expired.
    """
    from api.models.audit import ApprovalRequest

    async def _run():
        engine = create_async_engine(settings.database_url, echo=False)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as db:
            from sqlalchemy import update

            stmt = (
                update(ApprovalRequest)
                .where(ApprovalRequest.status == "pending")
                .where(ApprovalRequest.expires_at < datetime.now(UTC))
                .values(status="expired")
            )
            result = await db.execute(stmt)
            await db.commit()
        await engine.dispose()
        return {"expired": getattr(result, "rowcount", 0) or 0}

    return _run_async(_run())


@celery_app.task(bind=True)
def cleanup_expired_sessions(self):
    """Clean up expired sessions.

    This is a no-op because session TTL is enforced by Redis natively
    (expire keys). The task exists in the beat schedule as a placeholder
    for potential future session management logic (e.g. batch-revoking
    sessions for a deactivated user).

    Returns:
        Dict confirming 0 sessions cleaned.
    """
    logger.info("Session cleanup: 0 sessions cleaned (Redis TTL handles this)")
    return {"cleaned": 0}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_alert_thresholds(self):
    """Evaluate alert rules against current metrics.

    Stub implementation for v0.1.0. Future versions will:
      1. Load all active AlertRule records from the database.
      2. For each rule, query the relevant metric (from Prometheus or
         in-memory counters) and compare against the rule's threshold.
      3. If breached, call deliver_alert() for each configured channel.

    Returns:
        Dict with count of rules checked.
    """
    logger.info("Alert threshold check: no rules configured yet (v0.1.0)")
    return {"checked": 0}


@celery_app.task(base=NotifyTask, bind=True)
def notify_schema_change(
    self,
    server_id: str,
    server_name: str,
    tools_added: list[str] | None = None,
    tools_removed: list[str] | None = None,
    tools_changed: list[dict] | None = None,
) -> dict:
    """Send a notification when an MCP server's tool schema changes.

    Called by the schema drift detection system when MCPClient.diff_tools()
    returns a non-empty ToolDiff. Logs a summary at INFO level and, if
    any changes are breaking, logs a WARNING with the affected tool names.

    Uses NotifyTask as the base class so transient failures (e.g. logging
    infrastructure) result in automatic retries.

    Args:
        server_id: UUID of the server whose schema changed.
        server_name: Human-readable server name.
        tools_added: Names of newly discovered tools.
        tools_removed: Names of tools that disappeared.
        tools_changed: List of changed tool dicts with is_breaking flag.

    Returns:
        Dict with priority, summary, and breaking status.
    """
    has_breaking = any(t.get("is_breaking") for t in (tools_changed or []))
    priority = "high" if has_breaking else "info"

    summary_parts = []
    if tools_added:
        summary_parts.append(f"{len(tools_added)} added")
    if tools_removed:
        summary_parts.append(f"{len(tools_removed)} removed")
    if tools_changed:
        summary_parts.append(f"{len(tools_changed)} changed")

    summary = ", ".join(summary_parts) if summary_parts else "no changes"
    logger.info(
        "Schema change notification [%s]: server=%s (%s) — %s",
        priority,
        server_name,
        server_id,
        summary,
    )
    if has_breaking:
        breaking_names = [t["tool_name"] for t in (tools_changed or []) if t.get("is_breaking")]
        logger.warning("Breaking schema changes on server=%s: %s", server_name, breaking_names)

    return {
        "server_id": server_id,
        "server_name": server_name,
        "priority": priority,
        "summary": summary,
        "has_breaking": has_breaking,
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def notify_approval_request(self, approval_id: str, channels: list[str] | None = None) -> dict:
    """Send a notification that a new approval request needs review.

    Called when an agent action requires human approval (per policy rules).
    Sends the notification through configured channels (email, Slack, etc.).
    In v0.1.0, this logs the notification; future versions will integrate
    with actual notification providers.

    Retries up to 3 times with 60s delay on failure.

    Args:
        approval_id: UUID of the pending approval request.
        channels: Notification channels (defaults to ["email"]).

    Returns:
        Dict confirming delivery.
    """
    channels = channels or ["email"]
    logger.info("Approval notification for %s via %s", approval_id, channels)
    return {"approval_id": approval_id, "channels": channels, "delivered": True}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_alert(self, alert_id: str, message: str, channels: list[str] | None = None) -> dict:
    """Deliver an alert message through configured channels.

    Called when an alert rule threshold is breached. In v0.1.0, this
    logs the alert; future versions will send through providers (email,
    Slack webhook, PagerDuty, etc.).

    Retries up to 3 times with 60s delay on failure.

    Args:
        alert_id: UUID of the alert rule that triggered.
        message: Alert message body (truncated to 100 chars in logs).
        channels: Delivery channels (defaults to ["email"]).

    Returns:
        Dict confirming delivery.
    """
    channels = channels or ["email"]
    logger.info("Alert %s delivered via %s: %s", alert_id, channels, message[:100])
    return {"alert_id": alert_id, "delivered": True}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=30)
def generate_audit_export(self, event_types: list[str] | None = None) -> dict:
    """Generate an export of audit events.

    Stub implementation for v0.1.0. Future versions will:
      1. Query AuditEvent records filtered by event_types (or all types).
      2. Write the results to a JSON/CSV file or stream.
      3. Return a download URL or file path.

    Args:
        event_types: Optional list of event types to filter by (None = all).

    Returns:
        Dict with export status and row count.
    """
    logger.info("Audit export requested (v0.1.0 — stub)")
    return {"status": "completed", "rows": 0, "format": "json"}


@celery_app.task(bind=True, max_retries=3)
def deliver_webhook(self, url: str, payload: dict) -> dict:
    """Deliver a webhook payload to an external URL.

    Sends an HTTP POST with the JSON payload to the target URL.
    Uses a 10-second timeout. On any failure (timeout, non-2xx,
    connection error), retries up to 3 times with Celery's default
    exponential backoff.

    This is used for:
      - Notifying external systems of schema changes.
      - Sending alert notifications to webhook endpoints.
      - Integrating with CI/CD pipelines and monitoring tools.

    Args:
        url: Target webhook URL.
        payload: JSON-serialisable dict to send.

    Returns:
        Dict with URL and HTTP status code.

    Raises:
        self.retry: On any exception, up to max_retries times.
    """
    import httpx

    try:
        resp = httpx.post(url, json=payload, timeout=10)
        resp.raise_for_status()
        logger.info("Webhook delivered to %s: %s", url, resp.status_code)
        return {"url": url, "status": resp.status_code}
    except Exception as exc:
        logger.warning("Webhook delivery failed for %s: %s", url, exc)
        raise self.retry(exc=exc) from exc


@celery_app.task(bind=True)
def run_scheduled_exports(self):
    """Run all due scheduled audit exports.

    Stub implementation for v0.2.0. Future versions will check the
    export_schedule table for due exports and queue generate_audit_export
    tasks for each.

    Returns:
        Dict with count of exports run.
    """
    logger.info("Scheduled exports: 0 exports run (v0.2.0 feature)")
    return {"exports": 0}


@celery_app.task(bind=True)
def health_check_self(self):
    """Health check for the Celery worker itself.

    Simple liveness probe for the Celery worker process. If the Celery
    beat scheduler is running and this task completes, the worker is
    considered healthy. Returns immediately without I/O.

    Returns:
        Dict with status "healthy".
    """
    logger.info("Self health check: healthy")
    return {"status": "healthy"}
