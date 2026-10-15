import re
from typing import Any

import httpx

from app.core.config import get_settings
from app.core.enums import Medium
from app.ingest.http import get_json
from app.normalize.converters import to_100
from app.normalize.schemas import MediaIn, ScoreIn

BASE = "https://api.rawg.io/api"
STEAM_URL = re.compile(r"store\.steampowered\.com/app/(\d+)")


async def list_games(client: httpx.AsyncClient, page: int) -> list[dict[str, Any]]:
    data = await get_json(
        client,
        f"{BASE}/games",
        params={
            "key": get_settings().rawg_api_key,
            "page": page,
            "page_size": 40,
            "ordering": "-metacritic",
            "metacritic": "1,100",
        },
    )
    return data["results"]


async def steam_appid(client: httpx.AsyncClient, rawg_id: int) -> int | None:
    data = await get_json(
        client, f"{BASE}/games/{rawg_id}/stores", params={"key": get_settings().rawg_api_key}
    )
    for store in data.get("results", []):
        if m := STEAM_URL.search(store.get("url", "")):
            return int(m[1])
    return None


def to_media(g: dict[str, Any]) -> MediaIn:
    scores = []
    if g.get("ratings_count"):
        scores.append(
            ScoreIn(
                source="rawg",
                raw_value=f"{g['rating']}/5",
                normalized=to_100(g["rating"], 5),
                sample_size=g["ratings_count"],
            )
        )
    if g.get("metacritic"):
        scores.append(
            ScoreIn(
                source="metacritic",
                raw_value=f"{g['metacritic']}/100",
                normalized=to_100(g["metacritic"], 100),
            )
        )
    released = g.get("released") or ""
    return MediaIn(
        medium=Medium.game,
        title=g["name"],
        rawg_id=g["id"],
        release_year=int(released[:4]) if released[:4].isdigit() else None,
        genres=[x["name"] for x in g.get("genres", [])],
        scores=scores,
    )
