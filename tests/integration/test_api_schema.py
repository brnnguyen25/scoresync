import allure
import schemathesis
from hypothesis import settings

from app.api.main import app

pytestmark = [allure.feature("Public API")]

schema = schemathesis.openapi.from_asgi("/openapi.json", app).exclude(path_regex="^/v1/admin")


@schema.parametrize()
@settings(max_examples=50)
def test_api_matches_its_own_spec(case: schemathesis.Case) -> None:
    case.call_and_validate()
