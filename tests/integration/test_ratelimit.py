import logging
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import pytest
import redis.asyncio as aioredis
from fastapi import HTTPException

from app.api import ratelimit
from app.core.config import get_settings

FIXED_NOW = 1_800_000_000.0  # a fixed moment, so the test can't straddle a minute boundary


def fake_request(redis: Any) -> Any:
    """Just enough of a Request for rate_limit(): a client IP and app.state.redis."""
    return SimpleNamespace(
        client=SimpleNamespace(host=f"test-{uuid4().hex[:8]}"),  # unique IP per test
        app=SimpleNamespace(state=SimpleNamespace(redis=redis)),
    )


@pytest.fixture
def three_per_minute(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(ratelimit, "get_settings", lambda: SimpleNamespace(rate_limit_per_minute=3))
    monkeypatch.setattr(ratelimit.time, "time", lambda: FIXED_NOW)


async def test_allows_up_to_limit_then_returns_429(three_per_minute: None) -> None:
    redis = aioredis.from_url(get_settings().redis_url)
    request = fake_request(redis)
    try:
        for _ in range(3):
            await ratelimit.rate_limit(request)  # requests 1–3 pass
        with pytest.raises(HTTPException) as exc:
            await ratelimit.rate_limit(request)  # request 4 is over the limit
        assert exc.value.status_code == 429
        assert exc.value.headers is not None and "Retry-After" in exc.value.headers
    finally:
        await redis.close()


async def test_fails_open_and_logs_when_redis_is_down(
    three_per_minute: None, caplog: pytest.LogCaptureFixture
) -> None:
    class BrokenRedis:
        async def incr(self, key: str) -> int:
            raise ConnectionError("redis unreachable")

    with caplog.at_level(logging.ERROR):
        await ratelimit.rate_limit(fake_request(BrokenRedis()))  # must not raise
    assert "rate limiter unavailable" in caplog.text  # ...but must not be silent either
