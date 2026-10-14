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


def _weighted_mean(items: list[WeightedScore]) -> Decimal | None:
    total_weight = sum((s.weight for s in items), Decimal(0))
    if total_weight == 0:
        return None
    mean = sum((s.normalized * s.weight for s in items), Decimal(0)) / total_weight
    return mean.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def combine(scores: list[WeightedScore]) -> tuple[Decimal | None, Decimal | None, Decimal | None]:
    """Return (critic, user, aggregate). Thin user samples are dropped."""
    usable = [
        s for s in scores
        if s.kind is SourceKind.critic or (s.sample_size or 0) >= MIN_USER_SAMPLE
    ]
    critic = _weighted_mean([s for s in usable if s.kind is SourceKind.critic])
    user = _weighted_mean([s for s in usable if s.kind is SourceKind.user])
    return critic, user, _weighted_mean(usable)