from typing import Any

import httpx

from app.core.config import get_settings
from app.ingest.http import get_json
from app.normalize.converters import parse_rating
from app.normalize.schemas import ScoreIn

URL = "https://www.omdbapi.com/"
SOURCE_SLUGS = {
    "Internet Movie Database": "imdb",
    "Rotten Tomatoes": "rotten_tomatoes",
    "Metacritic": "metacritic",
}


async def fetch(client: httpx.AsyncClient, imdb_id: str) -> dict[str, Any] | None:
    data = await get_json(client, URL, params={"apikey": get_settings().omdb_api_key, "i": imdb_id})
    return None if data.get("Response") == "False" else data


def to_scores(data: dict[str, Any]) -> list[ScoreIn]:
    votes = int(data.get("imdbVotes", "0").replace(",", "") or 0) if data.get("imdbVotes") != "N/A" else None
    scores = []
    for rating in data.get("Ratings", []):
        slug = SOURCE_SLUGS.get(rating.get("Source", ""))
        if slug is None:
            continue
        try:
            normalized = parse_rating(rating["Value"])
        except ValueError:
            continue                                   # skip "N/A" and oddities, keep the rest
        scores.append(ScoreIn(
            source=slug, raw_value=rating["Value"], normalized=normalized,
            sample_size=votes if slug == "imdb" else None, raw_payload=rating,
        ))
    return scores