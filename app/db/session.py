from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.config import get_settings


def make_engine(*, for_worker: bool = False) -> AsyncEngine:
    url = get_settings().database_url
    if for_worker:
        # Celery tasks each run in a fresh event loop; pooled connections can't cross loops.
        return create_async_engine(url, poolclass=NullPool)
    return create_async_engine(url, pool_pre_ping=True, pool_recycle=3600)


engine = make_engine()
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
