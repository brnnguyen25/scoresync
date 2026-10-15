from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "scoresync",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.worker.tasks"],
)

celery_app.conf.update(
    timezone="UTC",
    task_acks_late=True,  # a task is removed from the queue only after it finishes
    worker_prefetch_multiplier=1,  # each worker takes one long task at a time
    task_soft_time_limit=25 * 60,  # raises an exception inside the task at 25 min
    task_time_limit=30 * 60,  # hard kill at 30 min
    result_expires=7 * 24 * 3600,
    beat_schedule={
        "movies-nightly": {"task": "ingest", "schedule": crontab(hour=3, minute=0), "args": ("movies", 2)},
        "tv-nightly": {"task": "ingest", "schedule": crontab(hour=3, minute=30), "args": ("tv", 2)},
        "games-nightly": {"task": "ingest", "schedule": crontab(hour=4, minute=0), "args": ("games", 2)},
    },
)
