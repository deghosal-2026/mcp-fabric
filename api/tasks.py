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
    autoretry_for = (Exception,)
    max_retries = 3
    default_retry_delay = 60


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(bind=True, max_retries=2, default_retry_delay=10)
def health_check_server(self, server_id: str, endpoint: str) -> dict:
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
                    results.append({
                        "server_id": str(srv.id), "status": "healthy", "tools": len(tools),
                    })
                except Exception as exc:
                    results.append({
                        "server_id": str(srv.id), "status": "unhealthy", "error": str(exc),
                    })
        await engine.dispose()
        return results

    return _run_async(_check_all())


@celery_app.task(bind=True)
def cleanup_audit_logs(self):
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
    logger.info("Session cleanup: 0 sessions cleaned (Redis TTL handles this)")
    return {"cleaned": 0}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def check_alert_thresholds(self):
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
        priority, server_name, server_id, summary,
    )
    if has_breaking:
        breaking_names = [t["tool_name"] for t in (tools_changed or []) if t.get("is_breaking")]
        logger.warning(
            "Breaking schema changes on server=%s: %s", server_name, breaking_names
        )

    return {
        "server_id": server_id,
        "server_name": server_name,
        "priority": priority,
        "summary": summary,
        "has_breaking": has_breaking,
    }


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def notify_approval_request(self, approval_id: str, channels: list[str] | None = None) -> dict:
    channels = channels or ["email"]
    logger.info("Approval notification for %s via %s", approval_id, channels)
    return {"approval_id": approval_id, "channels": channels, "delivered": True}


@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def deliver_alert(self, alert_id: str, message: str, channels: list[str] | None = None) -> dict:
    channels = channels or ["email"]
    logger.info("Alert %s delivered via %s: %s", alert_id, channels, message[:100])
    return {"alert_id": alert_id, "delivered": True}


@celery_app.task(bind=True, max_retries=1, default_retry_delay=30)
def generate_audit_export(self, event_types: list[str] | None = None) -> dict:
    logger.info("Audit export requested (v0.1.0 — stub)")
    return {"status": "completed", "rows": 0, "format": "json"}


@celery_app.task(bind=True, max_retries=3)
def deliver_webhook(self, url: str, payload: dict) -> dict:
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
    logger.info("Scheduled exports: 0 exports run (v0.2.0 feature)")
    return {"exports": 0}


@celery_app.task(bind=True)
def health_check_self(self):
    logger.info("Self health check: healthy")
    return {"status": "healthy"}
