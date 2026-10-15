import httpx
import re

from app.core.config import get_settings
from app.ingest.http import get_json
from app.normalize.converters import to_100
from app.normalize.schemas import ScoreIn

HOST = "opencritic-api.p.rapidapi.com"


def _headers() -> dict[str, str]:
    return {"X-RapidAPI-Key": get_settings().rapidapi_key, "X-RapidAPI-Host": HOST}


async def find_id(client: httpx.AsyncClient, title: str) -> int | None:
    title = re.sub(r"\s*\(\d{4}\)$", "", title)        # RAWG appends "(1998)" to some titles
    results = await get_json(client, f"https://{HOST}/game/search",
                             params={"criteria": title}, headers=_headers())
    for r in results:
        if r.get("name", "").casefold() == title.casefold():   # exact match only: avoid wrong games
            return int(r["id"])
    return None


async def fetch_score(client: httpx.AsyncClient, oc_id: int) -> ScoreIn | None:
    g = await get_json(client, f"https://{HOST}/game/{oc_id}", headers=_headers())
    score = g.get("topCriticScore")
    if score is None or score < 0:                     # OpenCritic uses -1 for "not enough reviews"
        return None
    return ScoreIn(source="opencritic", raw_value=f"{round(score)}/100",
                   normalized=to_100(round(score, 2), 100),
                   sample_size=g.get("numTopCriticReviews"), raw_payload={"tier": g.get("tier")})