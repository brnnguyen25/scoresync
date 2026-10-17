import os

import allure
import httpx
import pytest
from pydantic import BaseModel, ConfigDict

from tests.contract.test_contracts import RawgPage, SteamReviews, TmdbMovie

pytestmark = [
    allure.feature("Source contracts"),
    pytest.mark.contract_live,
    pytest.mark.skipif(not os.getenv("LIVE_CONTRACTS"), reason="live API checks run nightly only"),
]


def key(name: str) -> str:
    value = os.getenv(name, "")
    if not value:
        pytest.skip(f"{name} not set")
    return value


class OmdbRating(BaseModel):
    Source: str
    Value: str


class OmdbContract(BaseModel):
    model_config = ConfigDict(extra="allow")
    Title: str
    imdbID: str
    imdbVotes: str
    Ratings: list[OmdbRating]


def test_live_omdb_matches_contract() -> None:
    r = httpx.get(
        "https://www.omdbapi.com/", params={"apikey": key("OMDB_API_KEY"), "i": "tt1375666"}, timeout=15
    )
    OmdbContract.model_validate(r.json())


def test_live_tmdb_matches_contract() -> None:
    r = httpx.get(
        "https://api.themoviedb.org/3/movie/27205",
        params={"api_key": key("TMDB_API_KEY"), "append_to_response": "external_ids"},
        timeout=15,
    )
    TmdbMovie.model_validate(r.json())


def test_live_rawg_matches_contract() -> None:
    r = httpx.get(
        "https://api.rawg.io/api/games",
        params={"key": key("RAWG_API_KEY"), "page_size": 3, "ordering": "-metacritic", "metacritic": "1,100"},
        timeout=15,
    )
    RawgPage.model_validate(r.json())


def test_live_steam_matches_contract() -> None:
    r = httpx.get(
        "https://store.steampowered.com/appreviews/620",
        params={"json": 1, "language": "all", "purchase_type": "all", "num_per_page": 0},
        timeout=15,
    )
    SteamReviews.model_validate(r.json())


def ok_json(r: httpx.Response) -> object:
    """Fail with the status and body, never the URL, which contains the API key."""
    assert r.status_code == 200, f"HTTP {r.status_code}: {r.text[:200]}"
    return r.json()
