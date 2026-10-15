from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer, field_validator

from app.core.enums import Medium, SourceKind

# Decimals are exact internally but sent as JSON numbers (Pydantic would send strings by default)
Score = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class MediaSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    medium: Medium
    title: str
    release_year: int | None
    genres: list[str]
    critic_score: Score | None
    user_score: Score | None
    aggregate_score: Score | None

    @field_validator("genres", mode="before")
    @classmethod
    def genre_names(cls, v: list) -> list[str]:
        return [g if isinstance(g, str) else g.name for g in v]


class ScoreOut(BaseModel):
    source: str
    source_name: str
    kind: SourceKind
    raw_value: str
    normalized: Score
    sample_size: int | None
    captured_at: datetime


class MediaDetail(MediaSummary):
    scores: list[ScoreOut]


class HistoryPoint(BaseModel):
    source: str
    normalized: Score
    captured_at: datetime


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int