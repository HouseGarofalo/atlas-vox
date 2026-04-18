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
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    result_expires=86400,  # 24 hours
    task_default_retry_delay=60,
    task_max_retries=3,
    task_routes={
        "app.tasks.preprocessing.*": {"queue": "preprocessing"},
        "app.tasks.training.*": {"queue": "training"},
        "app.tasks.preferences.*": {"queue": "preferences"},
    },
    task_default_queue="default",
    beat_schedule={
        "cleanup-old-audio": {
            "task": "app.tasks.cleanup.cleanup_old_audio",
            "schedule": 3600.0,  # every hour
        },
        # SL-26 — nightly preference rollup (24h ≈ 86400s)
        "rollup-preferences-nightly": {
            "task": "app.tasks.preferences.rollup_preferences",
            "schedule": 86400.0,
        },
    },
)

# Auto-discover tasks in these modules
celery_app.autodiscover_tasks([
    "app.tasks.preprocessing",
    "app.tasks.training",
    "app.tasks.cleanup",
    "app.tasks.preferences",
])
