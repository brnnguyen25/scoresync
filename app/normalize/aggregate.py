from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.core.enums import SourceKind

MIN_USER_SAMPLE = 20  # ignore user scores backed by fewer reviews than this
TWO_PLACES = Decimal("0.01")


@dataclass(frozen=True)
class WeightedScore:
    normalized: Decimal
    weight: Decimal
    kind: SourceKind
    sample_size: int | None = None


PRIOR_MEAN = Decimal("70")  # C: a typical user score
PRIOR_WEIGHT = Decimal("100")  # m: how many reviews the prior counts as


def _shrink(s: WeightedScore) -> WeightedScore:
    """Pull user scores from small samples toward PRIOR_MEAN (a Bayesian average)."""
    if s.kind is not SourceKind.user or not s.sample_size:
        return s
    n = Decimal(s.sample_size)
    adjusted = (n * s.normalized + PRIOR_WEIGHT * PRIOR_MEAN) / (n + PRIOR_WEIGHT)
    return WeightedScore(adjusted, s.weight, s.kind, s.sample_size)


def _weighted_mean(items: list[WeightedScore]) -> Decimal | None:
    total_weight = sum((s.weight for s in items), Decimal(0))
    if total_weight == 0:
        return None
    mean = sum((s.normalized * s.weight for s in items), Decimal(0)) / total_weight
    return mean.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def combine(scores: list[WeightedScore]) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Return (critic, user, aggregate). Thin user samples are dropped."""
    usable = [
        s
        for s in map(_shrink, scores)
        if s.kind is SourceKind.critic or (s.sample_size or 0) >= MIN_USER_SAMPLE
    ]
    critic = _weighted_mean([s for s in usable if s.kind is SourceKind.critic])
    user = _weighted_mean([s for s in usable if s.kind is SourceKind.user])
    return critic, user, _weighted_mean(usable)
