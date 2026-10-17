from decimal import Decimal

import allure
import pytest

from app.normalize.converters import from_ratio, to_100

pytestmark = [allure.feature("Normalization")]


@pytest.mark.parametrize(
    ("value", "out_of", "expected"),
    [
        pytest.param("0", 10, "0.00", id="lower-bound"),
        pytest.param("0.01", 10, "0.10", id="just-above-lower"),
        pytest.param("7.8", 10, "78.00", id="typical"),
        pytest.param("9.99", 10, "99.90", id="just-below-upper"),
        pytest.param("10", 10, "100.00", id="upper-bound"),
        pytest.param("2.345", 5, "46.90", id="exact-no-rounding-needed"),
        pytest.param("1.0005", 10, "10.01", id="half-up-not-half-even"),
        pytest.param("0.5", 1, "50.00", id="scale-of-one"),
    ],
)
def test_valid_boundaries(value: str, out_of: int, expected: str) -> None:
    assert to_100(value, out_of) == Decimal(expected)


@pytest.mark.parametrize(
    ("value", "out_of", "message"),
    [
        pytest.param("-0.01", 10, "outside", id="just-below-lower"),
        pytest.param("10.01", 10, "outside", id="just-above-upper"),
        pytest.param("5", 0, "must be positive", id="zero-scale"),
        pytest.param("5", -1, "must be positive", id="negative-scale"),
    ],
)
def test_invalid_boundaries(value: str, out_of: int, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        to_100(value, out_of)


@pytest.mark.parametrize(
    ("positive", "total", "expected"),
    [
        pytest.param(0, 10, "0.00", id="none-positive"),
        pytest.param(10, 10, "100.00", id="all-positive"),
        pytest.param(1, 3, "33.33", id="repeating-decimal-rounds"),
        pytest.param(1, 1, "100.00", id="single-review"),
    ],
)
def test_ratio_valid(positive: int, total: int, expected: str) -> None:
    assert from_ratio(positive, total) == Decimal(expected)


@pytest.mark.parametrize(
    ("positive", "total"),
    [
        pytest.param(1, 0, id="zero-total"),
        pytest.param(0, -5, id="negative-total"),
        pytest.param(-1, 10, id="negative-positive"),
        pytest.param(11, 10, id="more-positive-than-total"),
        pytest.param(0, 0, id="no-reviews"),
    ],
)
def test_ratio_invalid(positive: int, total: int) -> None:
    with pytest.raises(ValueError, match="invalid ratio"):
        from_ratio(positive, total)
