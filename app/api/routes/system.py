from typing import Literal

import redis.asyncio as aioredis
from fastapi import APIRouter, Depends, Query, status
from fastapi_cache.decorator import cache
from sqlalchemy import select, text

from app.api.deps import SessionDep, require_api_key
from app.core.config import get_settings
from app.db.models import Source
from app.worker.celery_app import celery_app

router = APIRouter(tags=["system"])


@router.get("/v1/sources", summary="Data sources and freshness")
@cache(expire=300)
async def sources(session: SessionDep) -> list[dict]:
    rows = await session.scalars(select(Source).order_by(Source.slug))
    return [
        {
            "slug": s.slug,
            "name": s.name,
            "kind": s.kind,
            "weight": float(s.weight),
            "last_run_at": s.last_run_at,
        }
        for s in rows
    ]


@router.get("/health", include_in_schema=False)
async def health(session: SessionDep) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    r = aioredis.from_url(get_settings().redis_url)
    await r.ping()
    await r.close()
    return {"status": "ok"}


@router.post(
    "/v1/admin/ingest/{job}",
    status_code=status.HTTP_202_ACCEPTED,
    dependencies=[Depends(require_api_key)],
    summary="Queue an ingestion run",
)
async def trigger_ingest(job: Literal["movies", "tv", "games"], pages: int = Query(1, ge=1, le=10)) -> dict:
    task = celery_app.send_task("ingest", args=[job, pages])
    return {"task_id": task.id, "job": job, "pages": pages}
