from pathlib import Path

from playwright.sync_api import Locator, Page

DEMO = Path(__file__).resolve().parents[2] / "site" / "index.html"


class LeaderboardPage:
    def __init__(self, page: Page) -> None:
        self.page = page
        self.medium: Locator = page.locator("#medium")
        self.rows: Locator = page.locator("#rows tr")
        self.status: Locator = page.locator("#status")
        self.chart_title: Locator = page.locator("#chartTitle")

    def open(self) -> "LeaderboardPage":
        self.page.goto(f"{DEMO.as_uri()}?api=http://api.test")
        return self

    def choose_medium(self, value: str) -> None:
        self.medium.select_option(value)

    def open_history(self, title: str) -> None:
        self.rows.filter(has_text=title).click()
