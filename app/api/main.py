from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import redis.asyncio as aioredis
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.routes import media, rankings, system
from app.core.cache import CACHE_PREFIX, url_key_builder
from app.core.config import get_settings
from app.db.session import engine

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    redis = aioredis.from_url(settings.redis_url)
    FastAPICache.init(RedisBackend(redis), prefix=CACHE_PREFIX, key_builder=url_key_builder)
    yield
    await redis.aclose()
    await engine.dispose()


limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"],
                  storage_uri=settings.redis_url)

app = FastAPI(
    title="ScoreSync API",
    version="1.0.0",
    description="Critic and user scores for movies, TV, and games from multiple platforms, "
                "normalized to a 0–100 scale. Data via TMDB, OMDb, RAWG, OpenCritic, and Steam.",
    lifespan=lifespan,
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"], allow_headers=["*"])

app.include_router(media.router)
app.include_router(rankings.router)
app.include_router(system.router)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    return RedirectResponse("/docs")