"""Celery async task definitions and beat schedule.

Registered tasks are auto-discovered by the Celery worker.
Beat schedule is driven by Settings.celery_beat_schedule.
"""

import logging

from celery import Celery, Task

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
