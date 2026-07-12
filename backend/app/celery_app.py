"""
Celery Worker Configuration — horizontal agent scaling.

Run workers with:
  celery -A app.celery_app worker --loglevel=info -Q arise_agents

For local dev without Redis:
  Set CELERY_BROKER_URL=memory:// in .env (in-memory, single-process)

For production:
  Set CELERY_BROKER_URL=redis://localhost:6379/0 in .env
"""

import os
from celery import Celery
from app.config import settings

# ─── Broker & Backend ───────────────────────────────────────────────────────
BROKER_URL = getattr(
    settings, "CELERY_BROKER_URL", os.getenv("CELERY_BROKER_URL", "memory://")
)
RESULT_BACKEND = getattr(
    settings,
    "CELERY_RESULT_BACKEND",
    os.getenv("CELERY_RESULT_BACKEND", "cache+memory://"),
)

celery_app = Celery(
    "arise",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks.agent_tasks"],
)

celery_app.conf.update(
    # Task routing — all ARISE agents go to the arise_agents queue
    task_routes={
        "app.tasks.agent_tasks.*": {"queue": "arise_agents"},
    },
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    # Reliability
    task_acks_late=True,  # Only ack after task completes
    worker_prefetch_multiplier=1,  # Fair dispatch — one task per worker at a time
    task_reject_on_worker_lost=True,  # Re-queue on worker crash
    # Retry policy
    task_max_retries=3,
    task_default_retry_delay=10,  # 10s between retries
    # Result expiry — 24hr
    result_expires=86400,
    # Timezone
    timezone="UTC",
    enable_utc=True,
)
