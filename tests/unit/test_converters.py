from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.core.enums import Medium, SourceKind
from app.normalize.aggregate import WeightedScore, combine
from app.normalize.converters import from_ratio, from_verdict, parse_rating, to_100
from app.normalize.schemas import MediaIn, ScoreIn


@pytest.mark.parametrize(
    ("text", "expected"),
    [("92%", "92.00"), ("74/100", "74.00"), ("7.8/10", "78.00"), (" 8 / 10 ", "80.00")],
)
def test_parse_rating(text: str, expected: str) -> None:
    assert parse_rating(text) == Decimal(expected)


@pytest.mark.parametrize(
    ("bad", "message"),
    [
        pytest.param("N/A", "unrecognized rating format", id="not-applicable"),
        pytest.param("", "unrecognized rating format", id="empty"),
        pytest.param("abc%", "unrecognized rating format", id="non-numeric-percent"),
        pytest.param("11/10", "outside", id="above-scale"),
        pytest.param("5/0", "must be positive", id="zero-scale"),
    ],
)
def test_parse_rating_rejects_garbage(bad: str, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        parse_rating(bad)


def test_five_star_and_ratio() -> None:
    assert to_100("4.21", 5) == Decimal("84.20")
    assert from_ratio(9120, 10000) == Decimal("91.20")


def test_verdict_is_case_insensitive() -> None:
    assert from_verdict("  Very Positive ") == Decimal("89.5")


def test_schema_rejects_out_of_range_score() -> None:
    with pytest.raises(ValidationError):
        ScoreIn(source="imdb", raw_value="x", normalized=Decimal("140"))


def test_media_cleans_title_and_genres() -> None:
    m = MediaIn(medium=Medium.game, title="  Elden\n Ring ", genres=["RPG", "rpg", " Action"])
    assert m.title == "Elden Ring"
    assert m.genres == ["rpg", "action"]


def test_combine_drops_thin_user_samples() -> None:
    critic, user, agg = combine(
        [
            WeightedScore(Decimal("90"), Decimal(1), SourceKind.critic),
            WeightedScore(Decimal("10"), Decimal(1), SourceKind.user, sample_size=3),
        ]
    )
    assert (critic, user, agg) == (Decimal("90.00"), None, Decimal("90.00"))


def test_small_user_samples_are_pulled_toward_the_prior() -> None:
    small = WeightedScore(Decimal("100"), Decimal(1), SourceKind.user, sample_size=30)
    huge = WeightedScore(Decimal("95"), Decimal(1), SourceKind.user, sample_size=200_000)
    _, small_user, _ = combine([small])
    _, huge_user, _ = combine([huge])
    assert small_user is not None and small_user < Decimal("80")  # 30 perfect reviews aren't trusted
    assert huge_user is not None and abs(huge_user - Decimal("95")) < 1  # a huge sample barely moves


def test_unknown_verdict_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown verdict"):
        from_verdict("Kinda Okay")
