"""Celery application configuration."""

from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "llmo_workers",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.csv_tasks",
        "app.workers.nlp_tasks",
        "app.workers.crawler_tasks",
        "app.workers.matcher_tasks",
    ],
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_reject_on_worker_lost=True,
)

# Task routes
celery_app.conf.task_routes = {
    "app.workers.csv_tasks.*": {"queue": "csv"},
    "app.workers.nlp_tasks.*": {"queue": "nlp"},
    "app.workers.crawler_tasks.*": {"queue": "crawler"},
    "app.workers.matcher_tasks.*": {"queue": "matcher"},
}

