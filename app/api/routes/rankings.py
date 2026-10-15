from fastapi import APIRouter, Query
from fastapi_cache.decorator import cache
from sqlalchemy import func, select

from app.api.deps import SessionDep
from app.api.schemas import MediaSummary
from app.core.enums import Medium, SourceKind
from app.db.models import Genre, Media, ScoreSnapshot, Source
from app.normalize.aggregate import MIN_USER_SAMPLE

router = APIRouter(prefix="/v1/rankings", tags=["rankings"])


@router.get("/top", response_model=list[MediaSummary], summary="Leaderboard")
@cache(expire=3600)
async def top(
    session: SessionDep,
    medium: Medium,
    year: int | None = Query(None, ge=1870, le=2100),
    genre: str | None = None,
    limit: int = Query(25, ge=1, le=100),
) -> list[MediaSummary]:
    # Count only sources that actually feed the score: all critic sources, and user sources
    # backed by enough reviews (the same rule combine() applies).
    source_count = (
        select(func.count(func.distinct(ScoreSnapshot.source_id)))
        .join(Source, Source.id == ScoreSnapshot.source_id)
        .where(
            ScoreSnapshot.media_id == Media.id,
            (Source.kind == SourceKind.critic) | (ScoreSnapshot.sample_size >= MIN_USER_SAMPLE),
        )
        .scalar_subquery()
    )
    stmt = select(Media).where(Media.medium == medium, Media.aggregate_score.is_not(None), source_count >= 2)
    if year:
        stmt = stmt.where(Media.release_year == year)
    if genre:
        stmt = stmt.join(Media.genres).where(Genre.name == genre.lower())
    rows = await session.scalars(stmt.order_by(Media.aggregate_score.desc()).limit(limit))
    return [MediaSummary.model_validate(m) for m in rows]
