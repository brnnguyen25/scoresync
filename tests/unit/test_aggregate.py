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
