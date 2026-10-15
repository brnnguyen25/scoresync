from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from playwright.async_api import async_playwright
from selectolax.parser import HTMLParser

from app.ingest.http import USER_AGENT


def allowed(url: str) -> bool:
    parts = urlsplit(url)
    robots = RobotFileParser(f"{parts.scheme}://{parts.netloc}/robots.txt")
    robots.read()
    return robots.can_fetch(USER_AGENT, url)


async def render(url: str, wait_for: str) -> HTMLParser:
    if not allowed(url):
        raise PermissionError(f"robots.txt disallows {url}")
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(user_agent=USER_AGENT)
        await page.goto(url, wait_until="domcontentloaded")
        await page.wait_for_selector(wait_for, timeout=15_000)   # wait for JS to draw the content
        html = await page.content()
        await browser.close()
    return HTMLParser(html)                                      # selectolax: fast CSS-selector parsing