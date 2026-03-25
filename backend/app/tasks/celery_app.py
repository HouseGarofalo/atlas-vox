"""Celery application configuration."""

from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "atlas_vox",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.tasks.preprocessing.*": {"queue": "preprocessing"},
        "app.tasks.training.*": {"queue": "training"},
    },
    task_default_queue="default",
)

# Auto-discover tasks in these modules
celery_app.autodiscover_tasks(["app.tasks.preprocessing", "app.tasks.training"])
