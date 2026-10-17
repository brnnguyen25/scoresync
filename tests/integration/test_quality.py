from decimal import Decimal
from typing import Any
from uuid import uuid4

import allure
from sqlalchemy import select, text

from app.core.enums import Medium
from app.db.models import Media, Source
from app.quality.checks import run_checks

pytestmark = [allure.feature("Data quality")]


async def test_detects_out_of_range_score(session_maker: Any) -> None:
    async with session_maker() as s:
        before = await run_checks(s)
        media = Media(medium=Medium.game, title=f"QA {uuid4().hex[:8]}")
        s.add(media)
        await s.flush()
        source_id = await s.scalar(select(Source.id).limit(1))
        # Raw SQL bypasses Pydantic, which would reject 140 before it reached the database
        await s.execute(
            text(
                "INSERT INTO score_snapshots (media_id, source_id, raw_value, normalized) "
                "VALUES (:m, :s, 'bad', 140)"
            ),
            {"m": media.id, "s": source_id},
        )
        after = await run_checks(s)
        await s.rollback()  # nothing is ever committed, so no cleanup is needed
    assert after["score_out_of_range"] == before["score_out_of_range"] + 1


async def test_detects_aggregate_without_snapshots(session_maker: Any) -> None:
    async with session_maker() as s:
        before = await run_checks(s)
        s.add(Media(medium=Medium.game, title=f"QA {uuid4().hex[:8]}", aggregate_score=Decimal("90")))
        await s.flush()
        after = await run_checks(s)
        await s.rollback()
    assert after["aggregate_without_snapshots"] == before["aggregate_without_snapshots"] + 1


async def test_detects_duplicate_titles(session_maker: Any) -> None:
    title = f"QA {uuid4().hex[:8]}"
    async with session_maker() as s:
        before = await run_checks(s)
        s.add_all([Media(medium=Medium.movie, title=title, release_year=2020) for _ in range(2)])
        await s.flush()
        after = await run_checks(s)
        await s.rollback()
    assert after["duplicate_titles"] == before["duplicate_titles"] + 1


async def test_never_run_source_counts_as_stale(session_maker: Any) -> None:
    """Regression: NULL last_run_at failed the < comparison, hiding never-run sources."""
    from app.core.enums import SourceKind

    async with session_maker() as s:
        before = await run_checks(s)
        s.add(
            Source(slug=f"qa-{uuid4().hex[:8]}", name="QA source", kind=SourceKind.user, weight=Decimal("1"))
        )
        await s.flush()
        after = await run_checks(s)
        await s.rollback()
    assert after["stale_sources"] == before["stale_sources"] + 1
