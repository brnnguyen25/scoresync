from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend

from app.api.ratelimit import rate_limit
from app.api.routes import media, rankings, system
from app.core.cache import CACHE_PREFIX, url_key_builder
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url(settings.redis_url)
    app.state.redis = redis  # shared with the rate limiter
    FastAPICache.init(RedisBackend(redis), prefix=CACHE_PREFIX, key_builder=url_key_builder)
    yield
    await redis.close()  # close(), not aclose(): fastapi-cache2 pins redis-py 4.x
    await engine.dispose()


app = FastAPI(
    title="ScoreSync API",
    version="1.0.0",
    description="Critic and user scores for movies, TV, and games from multiple platforms, "
    "normalized to a 0–100 scale. Data via TMDB, OMDb, RAWG, OpenCritic, and Steam.",
    lifespan=lifespan,
    dependencies=[Depends(rate_limit)],  # runs the rate limiter before every endpoint
)

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

app.include_router(media.router)
app.include_router(rankings.router)
app.include_router(system.router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/docs")
