from httpx import AsyncClient


async def test_min_score_filter(client: AsyncClient, two_games: list[int]) -> None:
    r = await client.get("/v1/media", params={"medium": "game", "min_score": 80, "q": "Test"})
    assert r.status_code == 200
    titles = [i["title"] for i in r.json()["items"]]
    assert "Test High" in titles and "Test Low" not in titles


async def test_scores_are_json_numbers(client: AsyncClient, two_games: list[int]) -> None:
    r = await client.get(f"/v1/media/{two_games[0]}")
    assert isinstance(r.json()["aggregate_score"], float)


async def test_unknown_media_is_404(client: AsyncClient) -> None:
    assert (await client.get("/v1/media/999999999")).status_code == 404


async def test_invalid_query_is_422(client: AsyncClient) -> None:
    assert (await client.get("/v1/media", params={"min_score": 150})).status_code == 422


async def test_admin_requires_key(client: AsyncClient) -> None:
    assert (await client.post("/v1/admin/ingest/games")).status_code == 401


async def test_page_above_limit_is_422(client: AsyncClient) -> None:
    """Regression for #N: a huge page number overflowed MySQL's OFFSET and returned 500."""
    r = await client.get("/v1/media", params={"page": 922337203685477582})
    assert r.status_code == 422
