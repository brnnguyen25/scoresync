from typing import Any

import httpx
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_random_exponential

USER_AGENT = "ScoreSync/1.0 (+https://github.com/<your-username>/scoresync)"


def make_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(15.0, connect=5.0),
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
    )


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, httpx.TransportError):  # timeouts, dropped connections
        return True
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in {429, 500, 502, 503, 504}
    return False


@retry(
    retry=retry_if_exception(_is_retryable),
    wait=wait_random_exponential(multiplier=1, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
async def get_json(client: httpx.AsyncClient, url: str, **kwargs: Any) -> Any:
    response = await client.get(url, **kwargs)
    response.raise_for_status()
    return response.json()
