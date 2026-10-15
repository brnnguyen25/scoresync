from collections.abc import AsyncIterator, Iterator
from decimal import Decimal
from typing import Any

import pytest
from httpx import ASGITransport, AsyncClient

# No app imports at module level. pytest may load this file before the root conftest
# points DATABASE_URL at the test container; importing app code here would bind the
# engine to your development database instead.


@pytest.fixture(scope="session")
def session_maker() -> Any:
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.db.session import make_engine

    return async_sessionmaker(make_engine(for_worker=True), expire_on_commit=False)


@pytest.fixture(scope="session", autouse=True)
def _app_overrides(session_maker: Any) -> Iterator[None]:
    from app.api.main import app
    from app.api.ratelimit import rate_limit
    from app.db.session import get_session

    async def _test_session() -> AsyncIterator[Any]:
        async with session_maker() as s:
            yield s

    app.dependency_overrides[get_session] = _test_session
    app.dependency_overrides[rate_limit] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _in_memory_cache() -> None:
    from fastapi_cache import FastAPICache
    from fastapi_cache.backends.inmemory import InMemoryBackend

    FastAPICache.init(InMemoryBackend(), prefix="test")


@pytest.fixture
async def client() -> AsyncIterator[AsyncClient]:
    from app.api.main import app

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def two_games(session_maker: Any) -> AsyncIterator[list[int]]:
    from sqlalchemy import delete

    from app.core.enums import Medium
    from app.db.models import Media

    async with session_maker() as s:
        games = [
            Media(medium=Medium.game, title="Test High", release_year=2024, aggregate_score=Decimal("91")),
            Media(medium=Medium.game, title="Test Low", release_year=2024, aggregate_score=Decimal("42")),
        ]
        s.add_all(games)
        await s.commit()
        ids = [g.id for g in games]
    yield ids
    async with session_maker() as s:
        await s.execute(delete(Media).where(Media.id.in_(ids)))
        await s.commit()
