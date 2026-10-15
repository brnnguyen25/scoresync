from collections.abc import Callable
from typing import Any

from starlette.requests import Request

CACHE_PREFIX = "scoresync-cache"


def url_key_builder(
    func: Callable[..., Any], namespace: str = "", *, request: Request | None = None, **_: Any
) -> str:
    query = str(request.url.query) if request else ""
    path = request.url.path if request else func.__name__
    return f"{CACHE_PREFIX}:{namespace}:{path}?{query}"
