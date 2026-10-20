import os
from decimal import Decimal

import allure
import httpx
import pytest

BASE = os.getenv("BASE_URL", "")
pytestmark = [
    allure.feature("Production smoke"),
    pytest.mark.skipif(not BASE, reason="set BASE_URL to the deployed site"),
]


def test_health_is_ok() -> None:
    assert httpx.get(f"{BASE}/health", timeout=10).json() == {"status": "ok"}


def test_rankings_have_valid_scores_and_respond_fast() -> None:
    r = httpx.get(f"{BASE}/v1/rankings/top", params={"medium": "game", "limit": 10}, timeout=10)
    assert r.status_code == 200
    assert r.elapsed.total_seconds() < 1.0
    items = r.json()
    assert items, "production should have ranked games"
    assert all(Decimal(0) <= Decimal(str(i["aggregate_score"])) <= Decimal(100) for i in items)


def test_http_redirects_to_https() -> None:
    r = httpx.get(BASE.replace("https://", "http://") + "/health", follow_redirects=False, timeout=10)
    assert r.status_code in (301, 308)
    assert r.headers["location"].startswith("https://")


def test_security_headers_present() -> None:
    headers = httpx.get(f"{BASE}/health", timeout=10).headers
    assert "max-age" in headers.get("strict-transport-security", "")
    assert headers.get("x-content-type-options") == "nosniff"
    assert "server" not in headers
