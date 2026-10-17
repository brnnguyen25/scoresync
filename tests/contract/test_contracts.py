import json
from pathlib import Path
from typing import Any

import httpx
import respx
from pydantic import BaseModel, ConfigDict

from app.core.enums import Medium
from app.ingest.clients import omdb, opencritic, rawg, steam, tmdb

FIXTURES = Path(__file__).parent / "fixtures"


def load(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text())


class Contract(BaseModel):
    """Only the fields ScoreSync relies on. Extra fields are allowed: we don't own their schema."""

    model_config = ConfigDict(extra="allow")


class Named(Contract):
    name: str


# --- TMDB --------------------------------------------------------------
class TmdbExternalIds(Contract):
    imdb_id: str | None


class TmdbMovie(Contract):
    id: int
    title: str
    release_date: str
    vote_average: float
    vote_count: int
    genres: list[Named]
    external_ids: TmdbExternalIds


def test_tmdb_response_matches_contract() -> None:
    TmdbMovie.model_validate(load("tmdb_inception.json"))


def test_tmdb_response_maps_to_media() -> None:
    item = tmdb.to_media(Medium.movie, load("tmdb_inception.json"))
    assert item.imdb_id == "tt1375666"
    assert item.release_year == 2010
    assert [s.source for s in item.scores] == ["tmdb"]


# --- RAWG --------------------------------------------------------------
class RawgGame(Contract):
    id: int
    name: str
    released: str | None
    rating: float
    ratings_count: int
    metacritic: int | None
    genres: list[Named]


class RawgPage(Contract):
    results: list[RawgGame]


def test_rawg_response_matches_contract() -> None:
    RawgPage.model_validate(load("rawg_games_page.json"))


def test_rawg_games_map_to_media_with_metacritic() -> None:
    for g in load("rawg_games_page.json")["results"]:
        item = rawg.to_media(g)
        assert item.rawg_id == g["id"]
        assert "metacritic" in {s.source for s in item.scores}


# --- Steam -------------------------------------------------------------
class SteamSummary(Contract):
    total_positive: int
    total_reviews: int


class SteamReviews(Contract):
    query_summary: SteamSummary


def test_steam_response_matches_contract() -> None:
    SteamReviews.model_validate(load("steam_portal2.json"))


@respx.mock
async def test_steam_fetch_converts_ratio() -> None:
    data = load("steam_portal2.json")
    respx.get(url__startswith="https://store.steampowered.com/appreviews/620").respond(json=data)
    async with httpx.AsyncClient() as client:
        score = await steam.fetch_score(client, 620)
    assert score is not None
    assert score.sample_size == data["query_summary"]["total_reviews"]
    assert 0 <= score.normalized <= 100


# --- OMDb unhappy path -------------------------------------------------
@respx.mock
async def test_omdb_unknown_id_returns_none() -> None:
    respx.get(url__startswith="https://www.omdbapi.com/").respond(json=load("omdb_not_found.json"))
    async with httpx.AsyncClient() as client:
        assert await omdb.fetch(client, "tt0000000") is None


@respx.mock
async def test_opencritic_finds_exact_title_after_stripping_year() -> None:
    """Regression: RAWG titles like 'Soulcalibur (1998)' never matched OpenCritic's 'Soulcalibur'."""
    respx.get(url__startswith="https://opencritic-api.p.rapidapi.com/game/search").respond(
        json=[{"id": 99, "name": "Soulcalibur II"}, {"id": 42, "name": "Soulcalibur"}]
    )
    async with httpx.AsyncClient() as client:
        assert await opencritic.find_id(client, "Soulcalibur (1998)") == 42


@respx.mock
async def test_opencritic_minus_one_means_no_score() -> None:
    respx.get(url__startswith="https://opencritic-api.p.rapidapi.com/game/42").respond(
        json={"topCriticScore": -1, "numTopCriticReviews": 0, "tier": None}
    )
    async with httpx.AsyncClient() as client:
        assert await opencritic.fetch_score(client, 42) is None
