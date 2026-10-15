import asyncio
import logging
from typing import Any

import redis
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.config import get_settings
from app.core.enums import Medium
from app.db.session import make_engine
from app.ingest import jobs
from app.worker.celery_app import celery_app

log = logging.getLogger(__name__)
CACHE_PREFIX = "scoresync-cache"  # must match the prefix used in Module 7


async def _run(job: str, pages: int) -> dict[str, Any]:
    engine = make_engine(for_worker=True)
    sm = async_sessionmaker(engine, expire_on_commit=False)
    try:
        if job == "games":
            run = await jobs.ingest_games(sm, pages)
        else:
            run = await jobs.ingest_screen(sm, Medium.movie if job == "movies" else Medium.tv, pages)
        return {"job": run.job, "status": run.status, "ok": run.items_ok, "failed": run.items_failed}
    finally:
        await engine.dispose()


def _clear_api_cache(r: redis.Redis) -> None:
    for key in r.scan_iter(f"{CACHE_PREFIX}:*"):
        r.delete(key)


@celery_app.task(name="ingest", bind=True, max_retries=2, default_retry_delay=600)
def ingest(self: Any, job: str, pages: int = 1) -> dict[str, Any]:
    r = redis.Redis.from_url(get_settings().redis_url)
    lock = r.lock(f"lock:ingest:{job}", timeout=35 * 60)
    if not lock.acquire(blocking=False):  # the same job is already running
        log.info("skipping %s: already running", job)
        return {"job": job, "status": "skipped"}
    try:
        result = asyncio.run(_run(job, pages))
        _clear_api_cache(r)  # new data → drop stale cached responses
        return result
    except Exception as exc:
        raise self.retry(exc=exc) from exc
    finally:
        lock.release()
