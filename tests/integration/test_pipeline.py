import asyncio
from collections.abc import AsyncIterator
from decimal import Decimal
from uuid import uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.core.enums import Medium
from app.db.models import Genre, Media, Source
from app.db.session import make_engine
from app.ingest import pipeline
from app.normalize.schemas import MediaIn, ScoreIn

# NullPool engine: each test may run in its own event loop
sm = async_sessionmaker(make_engine(for_worker=True), expire_on_commit=False)


def unique_id() -> int:
    return uuid4().int % 1_000_000_000


def game(title: str, rawg_id: int, genres: list[str]) -> MediaIn:
    return MediaIn(
        medium=Medium.game,
        title=title,
        rawg_id=rawg_id,
        release_year=2020,
        genres=genres,
        scores=[
            ScoreIn(source="metacritic", raw_value="90/100", normalized=Decimal("90")),
            ScoreIn(source="steam", raw_value="900/1000", normalized=Decimal("90"), sample_size=1000),
        ],
    )


async def save(item: MediaIn) -> None:
    async with sm() as s:
        sources = {src.slug: src for src in (await s.scalars(select(Source))).all()}
        await pipeline.save(s, item, sources)
        await s.commit()


@pytest.fixture
async def cleanup() -> AsyncIterator[tuple[list[int], list[str]]]:
    rawg_ids: list[int] = []
    genres: list[str] = []
    yield rawg_ids, genres
    async with sm() as s:
        await s.execute(delete(Media).where(Media.rawg_id.in_(rawg_ids)))
        await s.execute(delete(Genre).where(Genre.name.in_(genres)))
        await s.commit()


async def test_saved_title_gets_cached_scores(cleanup: tuple[list[int], list[str]]) -> None:
    """Regression: duplicate enum classes made every cached score silently NULL."""
    rawg_ids, _ = cleanup
    rawg_ids.append(rawg_id := unique_id())
    await save(game("Enum Regression", rawg_id, ["rpg"]))

    async with sm() as s:
        media = await s.scalar(select(Media).where(Media.rawg_id == rawg_id))
    assert media is not None
    assert media.critic_score == Decimal("90.00")
    assert media.user_score is not None and media.user_score > Decimal("85")
    assert media.aggregate_score is not None


async def test_concurrent_saves_share_a_new_genre(cleanup: tuple[list[int], list[str]]) -> None:
    """Regression: two jobs inserting the same new genre at once raised a duplicate-key error."""
    rawg_ids, genres = cleanup
    genre = f"genre-{uuid4().hex[:8]}"  # brand-new name, so both saves must create it
    genres.append(genre)
    rawg_ids.extend(ids := [unique_id(), unique_id()])

    await asyncio.gather(save(game("Race A", ids[0], [genre])), save(game("Race B", ids[1], [genre])))

    async with sm() as s:
        saved = await s.scalar(select(func.count()).select_from(Media).where(Media.rawg_id.in_(ids)))
        rows = (await s.scalars(select(Genre).where(Genre.name == genre))).all()
    assert saved == 2  # both titles saved: no duplicate-key failure
    assert len(rows) == 1  # exactly one genre row
