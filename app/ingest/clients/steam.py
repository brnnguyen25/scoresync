import httpx

from app.ingest.http import get_json
from app.normalize.converters import from_ratio
from app.normalize.schemas import ScoreIn


async def fetch_score(client: httpx.AsyncClient, appid: int) -> ScoreIn | None:
    data = await get_json(
        client,
        f"https://store.steampowered.com/appreviews/{appid}",
        params={"json": 1, "language": "all", "purchase_type": "all", "num_per_page": 0},
    )
    summary = data.get("query_summary", {})
    total, positive = summary.get("total_reviews", 0), summary.get("total_positive", 0)
    if not total:
        return None
    return ScoreIn(
        source="steam",
        raw_value=f"{positive}/{total}",
        normalized=from_ratio(positive, total),
        sample_size=total,
        raw_payload=summary,
    )
