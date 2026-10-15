from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi_cache.decorator import cache
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.api.schemas import HistoryPoint, MediaDetail, MediaSummary, Page, ScoreOut
from app.core.enums import Medium
from app.db.models import Genre, Media, ScoreSnapshot

router = APIRouter(prefix="/v1/media", tags=["media"])

ORDER = {
    "-score": (Media.aggregate_score.desc(),),
    "score": (Media.aggregate_score.is_(None), Media.aggregate_score.asc()),
    "-year": (Media.release_year.desc(),),
    "year": (Media.release_year.is_(None), Media.release_year.asc()),
    "title": (Media.title.asc(),),
}


@router.get("", response_model=Page[MediaSummary], summary="Search and filter titles")
@cache(expire=300)
async def list_media(
    session: SessionDep,
    medium: Medium | None = None,
    genre: str | None = Query(None, examples=["rpg"]),
    year: int | None = Query(None, ge=1870, le=2100),
    year_from: int | None = Query(None, ge=1870, le=2100),
    year_to: int | None = Query(None, ge=1870, le=2100),
    min_score: float | None = Query(None, ge=0, le=100, description="Minimum aggregate score"),
    q: str | None = Query(None, min_length=2, max_length=100, description="Title contains"),
    sort: Literal["-score", "score", "-year", "year", "title"] = "-score",
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
) -> Page[MediaSummary]:
    stmt = select(Media)
    if medium:
        stmt = stmt.where(Media.medium == medium)
    if genre:
        stmt = stmt.join(Media.genres).where(Genre.name == genre.lower())
    if year:
        stmt = stmt.where(Media.release_year == year)
    if year_from:
        stmt = stmt.where(Media.release_year >= year_from)
    if year_to:
        stmt = stmt.where(Media.release_year <= year_to)
    if min_score is not None:
        stmt = stmt.where(Media.aggregate_score >= min_score)
    if q:
        stmt = stmt.where(Media.title.ilike(f"%{q}%"))

    total = await session.scalar(select(func.count()).select_from(stmt.subquery()))
    rows = await session.scalars(
        stmt.order_by(*ORDER[sort], Media.id).offset((page - 1) * page_size).limit(page_size)
    )
    return Page(
        items=[MediaSummary.model_validate(m) for m in rows], total=total or 0, page=page, page_size=page_size
    )


@router.get("/{media_id}", response_model=MediaDetail, summary="One title with every source's latest score")
@cache(expire=300)
async def get_media(media_id: int, session: SessionDep) -> MediaDetail:
    media = await session.get(Media, media_id)
    if media is None:
        raise HTTPException(404, "Media not found")

    # Window function: number each source's snapshots newest-first, keep #1
    rn = (
        func.row_number()
        .over(partition_by=ScoreSnapshot.source_id, order_by=ScoreSnapshot.captured_at.desc())
        .label("rn")
    )
    ranked = select(ScoreSnapshot.id, rn).where(ScoreSnapshot.media_id == media_id).subquery()
    snaps = await session.scalars(
        select(ScoreSnapshot).join(ranked, ranked.c.id == ScoreSnapshot.id).where(ranked.c.rn == 1)
    )
    scores = [
        ScoreOut(
            source=s.source.slug,
            source_name=s.source.name,
            kind=s.source.kind,
            raw_value=s.raw_value,
            normalized=s.normalized,
            sample_size=s.sample_size,
            captured_at=s.captured_at,
        )
        for s in snaps
    ]
    summary = MediaSummary.model_validate(media)
    return MediaDetail(**summary.model_dump(), scores=sorted(scores, key=lambda s: s.source))


@router.get("/{media_id}/history", response_model=list[HistoryPoint], summary="Score history")
@cache(expire=300)
async def get_history(media_id: int, session: SessionDep) -> list[HistoryPoint]:
    snaps = await session.scalars(
        select(ScoreSnapshot).where(ScoreSnapshot.media_id == media_id).order_by(ScoreSnapshot.captured_at)
    )
    return [
        HistoryPoint(source=s.source.slug, normalized=s.normalized, captured_at=s.captured_at) for s in snaps
    ]
