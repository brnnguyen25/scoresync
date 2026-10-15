from decimal import Decimal

import pytest

from app.normalize.converters import to_100


@pytest.mark.parametrize(
    ("value", "out_of", "expected"),
    [
        pytest.param("0", 10, "0.00", id="lower-bound"),
        pytest.param("0.01", 10, "0.10", id="just-above-lower"),
        pytest.param("7.8", 10, "78.00", id="typical"),
        pytest.param("9.99", 10, "99.90", id="just-below-upper"),
        pytest.param("10", 10, "100.00", id="upper-bound"),
        pytest.param("2.345", 5, "46.90", id="rounds-half-up"),
    ],
)
def test_valid_boundaries(value: str, out_of: int, expected: str) -> None:
    assert to_100(value, out_of) == Decimal(expected)


@pytest.mark.parametrize(
    ("value", "out_of"),
    [
        pytest.param("-0.01", 10, id="just-below-lower"),
        pytest.param("10.01", 10, id="just-above-upper"),
        pytest.param("5", 0, id="zero-scale"),
        pytest.param("5", -1, id="negative-scale"),
    ],
)
def test_invalid_boundaries(value: str, out_of: int) -> None:
    with pytest.raises(ValueError):
        to_100(value, out_of)
