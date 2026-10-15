from typing import Any

import httpx

from app.core.config import get_settings
from app.core.enums import Medium
from app.ingest.http import get_json
from app.normalize.converters import to_100
from app.normalize.schemas import MediaIn, ScoreIn

BASE = "https://api.themoviedb.org/3"


def _path(medium: Medium) -> str:
    return "movie" if medium is Medium.movie else "tv"


async def top_rated_ids(client: httpx.AsyncClient, medium: Medium, page: int) -> list[int]:
    data = await get_json(client, f"{BASE}/{_path(medium)}/top_rated",
                          params={"api_key": get_settings().tmdb_api_key, "page": page})
    return [r["id"] for r in data["results"]]


async def details(client: httpx.AsyncClient, medium: Medium, tmdb_id: int) -> dict[str, Any]:
    return await get_json(client, f"{BASE}/{_path(medium)}/{tmdb_id}",
                          params={"api_key": get_settings().tmdb_api_key,
                                  "append_to_response": "external_ids"})


def to_media(medium: Medium, d: dict[str, Any]) -> MediaIn:
    date = d.get("release_date") or d.get("first_air_date") or ""
    scores = []
    if d.get("vote_count"):
        scores.append(ScoreIn(
            source="tmdb", raw_value=f"{d['vote_average']}/10",
            normalized=to_100(d["vote_average"], 10), sample_size=d["vote_count"],
        ))
    return MediaIn(
        medium=medium,
        title=d.get("title") or d.get("name") or "",
        release_year=int(date[:4]) if date[:4].isdigit() else None,
        genres=[g["name"] for g in d.get("genres", [])],
        tmdb_id=d["id"],
        imdb_id=(d.get("external_ids") or {}).get("imdb_id") or None,
        scores=scores,
    )