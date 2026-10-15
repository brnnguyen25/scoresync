import re
from decimal import ROUND_HALF_UP, Decimal

TWO_PLACES = Decimal("0.01")
_PERCENT = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*%\s*$")
_FRACTION = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*/\s*(\d+(?:\.\d+)?)\s*$")

# Steam review labels → approximate midpoint of each label's % range (fallback only)
VERDICT_MIDPOINTS: dict[str, Decimal] = {
    "overwhelmingly positive": Decimal("97.5"),
    "very positive": Decimal("89.5"),
    "positive": Decimal("89.5"),
    "mostly positive": Decimal("74.5"),
    "mixed": Decimal("54.5"),
    "mostly negative": Decimal("29.5"),
    "negative": Decimal("9.5"),
    "very negative": Decimal("9.5"),
    "overwhelmingly negative": Decimal("9.5"),
}


def to_100(value: Decimal | float | str, out_of: Decimal | float | str) -> Decimal:
    """Scale value from [0, out_of] to [0, 100], rounded to 2 decimal places."""
    v, top = Decimal(str(value)), Decimal(str(out_of))
    if top <= 0:
        raise ValueError(f"scale maximum must be positive, got {top}")
    if not 0 <= v <= top:
        raise ValueError(f"{v} is outside 0..{top}")
    return (v / top * 100).quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


def parse_rating(text: str) -> Decimal:
    """Parse '92%', '74/100' or '7.8/10' into a 0–100 Decimal."""
    if m := _PERCENT.match(text):
        return to_100(m[1], 100)
    if m := _FRACTION.match(text):
        return to_100(m[1], m[2])
    raise ValueError(f"unrecognized rating format: {text!r}")


def from_ratio(positive: int, total: int) -> Decimal:
    if total <= 0 or not 0 <= positive <= total:
        raise ValueError(f"invalid ratio {positive}/{total}")
    return to_100(positive, total)


def from_verdict(label: str) -> Decimal:
    try:
        return VERDICT_MIDPOINTS[label.strip().lower()]
    except KeyError:
        raise ValueError(f"unknown verdict: {label!r}") from None
