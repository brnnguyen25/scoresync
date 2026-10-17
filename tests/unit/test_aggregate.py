from decimal import Decimal

import pytest

from app.core.enums import SourceKind
from app.normalize.aggregate import MIN_USER_SAMPLE, WeightedScore, combine

CRITIC = SourceKind.critic
USER = SourceKind.user


def score(kind: SourceKind, sample_size: int | None = None, value: str = "80") -> WeightedScore:
    return WeightedScore(Decimal(value), Decimal(1), kind, sample_size)


# Decision table: does a single score count toward the result?
@pytest.mark.parametrize(
    ("kind", "sample_size", "counted"),
    [
        pytest.param(CRITIC, None, True, id="critic-no-sample"),
        pytest.param(CRITIC, 3, True, id="critic-tiny-sample"),
        pytest.param(USER, MIN_USER_SAMPLE, True, id="user-at-threshold"),
        pytest.param(USER, 50_000, True, id="user-large-sample"),
        pytest.param(USER, MIN_USER_SAMPLE - 1, False, id="user-just-below-threshold"),
        pytest.param(USER, None, False, id="user-no-sample"),
    ],
)
def test_decision_table(kind: SourceKind, sample_size: int | None, counted: bool) -> None:
    critic, user, aggregate = combine([score(kind, sample_size)])
    produced = critic if kind is CRITIC else user
    assert (produced is not None) is counted
    assert (aggregate is not None) is counted


def test_critic_scores_are_never_shrunk() -> None:
    critic, _, _ = combine([score(CRITIC, 3, value="95")])
    assert critic == Decimal("95.00")


def test_user_score_at_threshold_is_pulled_toward_prior() -> None:
    # (20 × 80 + 100 × 70) ÷ 120 = 71.666… → 71.67
    _, user, _ = combine([score(USER, MIN_USER_SAMPLE, value="80")])
    assert user == Decimal("71.67")


def test_thin_user_score_does_not_affect_aggregate() -> None:
    _, _, aggregate = combine([score(CRITIC, value="90"), score(USER, 5, value="10")])
    assert aggregate == Decimal("90.00")


def test_no_scores_gives_no_result() -> None:
    assert combine([]) == (None, None, None)


def test_weights_change_the_mean() -> None:
    critic, _, aggregate = combine(
        [
            WeightedScore(Decimal("90"), Decimal("1"), CRITIC),
            WeightedScore(Decimal("60"), Decimal("0.5"), CRITIC),
        ]
    )
    # (90 × 1 + 60 × 0.5) ÷ (1 + 0.5) = 120 ÷ 1.5 = 80
    assert critic == Decimal("80.00")
    assert aggregate == Decimal("80.00")


def test_zero_total_weight_gives_no_score() -> None:
    critic, _, aggregate = combine([WeightedScore(Decimal("90"), Decimal("0"), CRITIC)])
    assert critic is None
    assert aggregate is None


def test_mean_rounds_half_up() -> None:
    critic, _, _ = combine([score(CRITIC, value="80.01"), score(CRITIC, value="80.00")])
    # (80.01 + 80.00) ÷ 2 = 80.005 → half-up gives 80.01; banker's rounding would give 80.00
    assert critic == Decimal("80.01")
