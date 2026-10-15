import logging
import time

from fastapi import HTTPException, Request, status

from app.core.config import get_settings

log = logging.getLogger(__name__)


async def rate_limit(request: Request) -> None:
    """Fixed-window limit per client IP, shared across API processes through Redis."""
    limit = get_settings().rate_limit_per_minute
    now = int(time.time())
    client = request.client.host if request.client else "unknown"
    key = f"ratelimit:{client}:{now // 60}"  # a new key every minute
    try:
        redis = request.app.state.redis
        count = await redis.incr(key)  # atomic +1, creates the key at 1
        if count == 1:
            await redis.expire(key, 60)  # Redis deletes old windows itself
    except Exception:  # noqa: BLE001 — fail open, but loudly
        log.exception("rate limiter unavailable; allowing request")
        return
    if count > limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Rate limit exceeded: {limit} requests per minute",
            headers={"Retry-After": str(60 - now % 60)},
        )
