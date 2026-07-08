import os
from celery import Celery

broker_url = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
result_backend = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/1")
worker_prefetch_multiplier = int(os.getenv("MPIPS_WORKER_PREFETCH_MULTIPLIER", "1"))
task_soft_time_limit = int(os.getenv("MPIPS_WORKER_TASK_SOFT_TIME_LIMIT", "900"))
task_time_limit = int(os.getenv("MPIPS_WORKER_TASK_TIME_LIMIT", "960"))

app = Celery(
    "mpips",
    broker=broker_url,
    backend=result_backend,
    include=["mpips.worker.tasks"],
)

app.conf.update(
    result_serializer="json",
    accept_content=["json"],
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_serializer="json",
    task_soft_time_limit=task_soft_time_limit,
    task_time_limit=task_time_limit,
    task_track_started=True,
    worker_prefetch_multiplier=worker_prefetch_multiplier,
)
