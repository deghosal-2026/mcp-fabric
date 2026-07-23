"""Celery async task definitions and beat schedule.

Registered tasks are auto-discovered by the Celery worker.
Beat schedule is driven by Settings.celery_beat_schedule.
"""

from celery import Celery

from api.config import settings

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
