from decimal import Decimal

import allure
from hypothesis import given
from hypothesis import strategies as st

from app.normalize.converters import parse_rating, to_100

pytestmark = [allure.feature("Normalization")]

scores_out_of_10 = st.decimals(min_value=0, max_value=10, places=1)


@given(data=st.data(), top=st.sampled_from([Decimal(5), Decimal(10), Decimal(100)]))
def test_result_always_between_0_and_100(data: st.DataObject, top: Decimal) -> None:
    value = data.draw(st.decimals(min_value=0, max_value=top, places=2))
    assert Decimal(0) <= to_100(value, top) <= Decimal(100)


@given(a=scores_out_of_10, b=scores_out_of_10)
def test_higher_input_never_gives_lower_score(a: Decimal, b: Decimal) -> None:
    low, high = sorted((a, b))
    assert to_100(low, 10) <= to_100(high, 10)


@given(v=scores_out_of_10)
def test_parsing_text_matches_direct_conversion(v: Decimal) -> None:
    assert parse_rating(f"{v}/10") == to_100(v, 10)
