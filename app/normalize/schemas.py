from decimal import Decimal
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.enums import Medium

Score100 = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]


class ScoreIn(BaseModel):
    model_config = ConfigDict(frozen=True)

    source: str  # slug from the sources table, e.g. "metacritic"
    raw_value: str = Field(max_length=32)
    normalized: Score100
    sample_size: int | None = Field(default=None, ge=0)
    raw_payload: dict[str, Any] | None = None


class MediaIn(BaseModel):
    medium: Medium
    title: str = Field(min_length=1, max_length=300)
    release_year: int | None = Field(default=None, ge=1870, le=2100)
    genres: list[str] = []

    imdb_id: str | None = None
    tmdb_id: int | None = None
    rawg_id: int | None = None
    steam_appid: int | None = None
    opencritic_id: int | None = None

    scores: list[ScoreIn] = []

    @field_validator("title")
    @classmethod
    def strip_title(cls, v: str) -> str:
        return " ".join(v.split())  # collapse stray whitespace and newlines

    @field_validator("genres")
    @classmethod
    def clean_genres(cls, v: list[str]) -> list[str]:
        seen: dict[str, None] = {}
        for g in v:
            key = g.strip().lower()
            if key:
                seen[key] = None  # dict keeps order and removes duplicates
        return list(seen)
