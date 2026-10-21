import allure
from playwright.sync_api import Page, expect

from tests.e2e.pages import LeaderboardPage

pytestmark = [allure.feature("Demo page")]
CORS = {"Access-Control-Allow-Origin": "*"}
GAME = {
    "id": 1,
    "medium": "game",
    "title": "Test Game",
    "release_year": 2024,
    "genres": ["rpg"],
    "critic_score": 91.0,
    "user_score": 88.5,
    "aggregate_score": 90.0,
}


def stub(page: Page, url: str, body: object, status: int = 200) -> None:
    page.route(url, lambda route: route.fulfill(status=status, json=body, headers=CORS))


def test_leaderboard_lists_titles(page: Page) -> None:
    stub(page, "http://api.test/v1/rankings/top*", [GAME])
    lb = LeaderboardPage(page).open()
    expect(lb.rows).to_have_count(1)
    expect(lb.rows.first).to_contain_text("Test Game")


def test_clicking_a_title_shows_its_history(page: Page) -> None:
    stub(page, "http://api.test/v1/rankings/top*", [GAME])
    stub(
        page,
        "http://api.test/v1/media/1/history",
        [
            {"source": "steam", "normalized": 88.0, "captured_at": "2026-10-01T03:00:00Z"},
            {"source": "steam", "normalized": 89.0, "captured_at": "2026-10-02T03:00:00Z"},
        ],
    )
    lb = LeaderboardPage(page).open()
    lb.open_history("Test Game")
    expect(lb.chart_title).to_contain_text("Test Game")


@allure.severity(allure.severity_level.CRITICAL)
def test_titles_from_the_api_cannot_inject_html(page: Page) -> None:
    evil = {**GAME, "title": "<img src=x onerror=alert(1)>"}
    stub(page, "http://api.test/v1/rankings/top*", [evil])
    lb = LeaderboardPage(page).open()
    expect(lb.rows.first).to_contain_text("<img src=x onerror=alert(1)>")  # shown as plain text
    expect(page.locator("#rows img")).to_have_count(0)  # never rendered


def test_api_outage_shows_a_friendly_message(page: Page) -> None:
    stub(page, "http://api.test/v1/rankings/top*", {"detail": "boom"}, status=500)
    lb = LeaderboardPage(page).open()
    expect(lb.status).to_contain_text("Couldn't load rankings")
    expect(lb.rows).to_have_count(0)
