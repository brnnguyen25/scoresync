from collections.abc import AsyncIterator
from decimal import Decimal

import pytest
from fastapi_cache import FastAPICache
from fastapi_cache.backends.inmemory import InMemoryBackend
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.main import app
from app.api.ratelimit import rate_limit
from app.core.enums import Medium
from app.db.models import Media
from app.db.session import get_session, make_engine

_sm = async_sessionmaker(make_engine(for_worker=True), expire_on_commit=False)


async def _test_session() -> AsyncIterator[AsyncSession]:
    async with _sm() as s:
        yield s


app.dependency_overrides[get_session] = _test_session


@pytest.fixture(autouse=True)
def _no_cache_no_limits() -> None:
    FastAPICache.init(InMemoryBackend(), prefix="test")
    app.dependency_overrides[rate_limit] = lambda: None  # no rate limiting in tests


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def two_games() -> AsyncIterator[list[int]]:
    async with _sm() as s:
        games = [
            Media(medium=Medium.game, title="Test High", release_year=2024, aggregate_score=Decimal("91")),
            Media(medium=Medium.game, title="Test Low", release_year=2024, aggregate_score=Decimal("42")),
        ]
        s.add_all(games)
        await s.commit()
        ids = [g.id for g in games]
    yield ids
    async with _sm() as s:
        await s.execute(delete(Media).where(Media.id.in_(ids)))
        await s.commit()
