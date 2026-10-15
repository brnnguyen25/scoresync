from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.dialects.mysql import insert as mysql_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Genre, Media, ScoreSnapshot, Source
from app.normalize.aggregate import WeightedScore, combine
from app.normalize.schemas import MediaIn

ID_FIELDS = ("imdb_id", "rawg_id", "steam_appid", "opencritic_id")


async def _find_existing(s: AsyncSession, item: MediaIn) -> Media | None:
    for field in ID_FIELDS:
        value = getattr(item, field)
        if value is not None:
            found = await s.scalar(select(Media).where(getattr(Media, field) == value))
            if found:
                return found
    if item.tmdb_id is not None:
        return await s.scalar(select(Media).where(Media.medium == item.medium, Media.tmdb_id == item.tmdb_id))
    return None


async def _genres(s: AsyncSession, names: list[str]) -> list[Genre]:
    # Race-safe get-or-create. INSERT IGNORE skips names another job already inserted instead
    # of raising a duplicate-key error; FOR UPDATE reads the latest committed rows rather than
    # this transaction's older snapshot (MySQL's default REPEATABLE READ isolation).
    await s.execute(mysql_insert(Genre).prefix_with("IGNORE").values([{"name": n} for n in names]))
    rows = await s.scalars(select(Genre).where(Genre.name.in_(names)).with_for_update())
    by_name = {g.name: g for g in rows}
    return [by_name[n] for n in names]


async def save(s: AsyncSession, item: MediaIn, sources: dict[str, Source]) -> Media:
    # Resolve genres BEFORE touching media: assigning to an unloaded collection would trigger
    # a lazy load, which async SQLAlchemy can't do implicitly (MissingGreenlet).
    genres = await _genres(s, item.genres) if item.genres else None
    media = await _find_existing(s, item)
    if media is None:
        media = Media(medium=item.medium, title=item.title, genres=genres or [])
        s.add(media)
    elif genres is not None:
        media.genres = genres  # already loaded by lazy="selectin"
    media.title = item.title
    media.release_year = item.release_year or media.release_year
    for field in (*ID_FIELDS, "tmdb_id"):
        if getattr(item, field) is not None:
            setattr(media, field, getattr(item, field))
    await s.flush()  # assigns media.id

    now = datetime.now(UTC).replace(tzinfo=None)  # MySQL DATETIME has no zone: store UTC
    for score in item.scores:
        source = sources[score.source]
        latest = await s.scalar(
            select(ScoreSnapshot)
            .where(ScoreSnapshot.media_id == media.id, ScoreSnapshot.source_id == source.id)
            .order_by(ScoreSnapshot.captured_at.desc())
            .limit(1)
        )
        if latest is None or latest.normalized != score.normalized:
            s.add(
                ScoreSnapshot(
                    media_id=media.id,
                    source=source,
                    raw_value=score.raw_value,
                    normalized=score.normalized,
                    sample_size=score.sample_size,
                    raw_payload=score.raw_payload,
                )
            )
        source.last_run_at = now
    await s.flush()
    await recompute(s, media)
    return media


async def recompute(s: AsyncSession, media: Media) -> None:
    snaps = (
        await s.scalars(
            select(ScoreSnapshot)
            .where(ScoreSnapshot.media_id == media.id)
            .order_by(ScoreSnapshot.captured_at.desc())
        )
    ).all()
    latest: dict[int, ScoreSnapshot] = {}
    for snap in snaps:
        latest.setdefault(snap.source_id, snap)  # first seen = newest
    weighted = [
        WeightedScore(x.normalized, x.source.weight, x.source.kind, x.sample_size) for x in latest.values()
    ]
    media.critic_score, media.user_score, media.aggregate_score = combine(weighted)
