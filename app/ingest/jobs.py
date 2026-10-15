import asyncio
import logging
from collections.abc import Awaitable
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.core.enums import Medium
from app.db.models import IngestRun, Media, Source
from app.ingest import pipeline
from app.ingest.clients import omdb, opencritic, rawg, steam, tmdb
from app.ingest.http import make_client
from app.normalize.schemas import MediaIn

log = logging.getLogger(__name__)
CONCURRENCY = 4
OPENCRITIC_MAX_PER_RUN = 20  # protects the free daily quota


async def _optional[T](label: str, coro: Awaitable[T]) -> T | None:
    """A failure in one optional source drops that score, not the whole title."""
    try:
        return await coro
    except Exception as exc:  # noqa: BLE001
        log.warning("%s skipped: %s", label, exc)
        return None


async def _paced[T](sem: asyncio.Semaphore, coro: Awaitable[T]) -> T:
    """One call at a time, roughly one per second, for rate-limited APIs."""
    async with sem:
        try:
            return await coro
        finally:
            await asyncio.sleep(1.1)


async def _run(sm: async_sessionmaker[AsyncSession], job: str, items: list[MediaIn]) -> IngestRun:
    async with sm() as s:
        run = IngestRun(job=job)
        s.add(run)
        await s.commit()
        sources = {src.slug: src for src in (await s.scalars(select(Source))).all()}
        for item in items:
            try:
                async with s.begin_nested():  # SAVEPOINT: one bad title can't sink the batch
                    await pipeline.save(s, item, sources)
                run.items_ok += 1
            except Exception as exc:  # noqa: BLE001 — log and continue
                log.warning("failed to save %r: %s", item.title, exc)
                run.items_failed += 1
        run.status = "ok" if run.items_failed == 0 else "partial"
        run.finished_at = datetime.now(UTC).replace(tzinfo=None)
        await s.commit()
        return run


async def ingest_screen(sm: async_sessionmaker[AsyncSession], medium: Medium, pages: int = 1) -> IngestRun:
    sem = asyncio.Semaphore(CONCURRENCY)
    async with make_client() as client:
        ids = [i for p in range(1, pages + 1) for i in await tmdb.top_rated_ids(client, medium, p)]

        async def one(tmdb_id: int) -> MediaIn | None:
            async with sem:
                try:
                    item = tmdb.to_media(medium, await tmdb.details(client, medium, tmdb_id))
                    if item.imdb_id and (data := await omdb.fetch(client, item.imdb_id)):
                        item = item.model_copy(update={"scores": [*item.scores, *omdb.to_scores(data)]})
                    return item
                except Exception as exc:  # noqa: BLE001
                    log.warning("tmdb %s failed: %s", tmdb_id, exc)
                    return None

        items = [i for i in await asyncio.gather(*(one(i) for i in ids)) if i]
    return await _run(sm, medium.value, items)


async def ingest_games(sm: async_sessionmaker[AsyncSession], pages: int = 1) -> IngestRun:
    sem = asyncio.Semaphore(CONCURRENCY)
    oc_sem = asyncio.Semaphore(1)  # OpenCritic's free tier rejects bursts
    async with sm() as s:  # reuse OpenCritic IDs we already know
        known_oc = dict(
            (
                await s.execute(
                    select(Media.rawg_id, Media.opencritic_id).where(Media.opencritic_id.is_not(None))
                )
            ).all()
        )
    oc_budget = OPENCRITIC_MAX_PER_RUN

    async with make_client() as client:
        games = [g for p in range(1, pages + 1) for g in await rawg.list_games(client, p)]

        async def one(g: dict) -> MediaIn | None:
            nonlocal oc_budget
            async with sem:
                try:
                    item = rawg.to_media(g)
                    extra, updates = [], {}
                    if appid := await rawg.steam_appid(client, g["id"]):
                        updates["steam_appid"] = appid
                        if sc := await _optional("steam", steam.fetch_score(client, appid)):
                            extra.append(sc)
                    oc_id = known_oc.get(g["id"])
                    if oc_id is None and oc_budget > 0:
                        oc_budget -= 1
                        oc_id = await _optional(
                            "opencritic search", _paced(oc_sem, opencritic.find_id(client, item.title))
                        )
                    if oc_id is not None and oc_budget > 0:
                        oc_budget -= 1
                        updates["opencritic_id"] = oc_id
                        if sc := await _optional(
                            "opencritic score", _paced(oc_sem, opencritic.fetch_score(client, oc_id))
                        ):
                            extra.append(sc)
                    return item.model_copy(update={**updates, "scores": [*item.scores, *extra]})
                except Exception as exc:  # noqa: BLE001
                    log.warning("rawg %s failed: %s", g.get("id"), exc)
                    return None

        items = [i for i in await asyncio.gather(*(one(g) for g in games)) if i]
    return await _run(sm, "games", items)
