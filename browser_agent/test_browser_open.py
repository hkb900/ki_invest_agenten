"""Open a visible Chromium browser and print the page title."""

from __future__ import annotations

from playwright.sync_api import sync_playwright


TARGET_URL = "https://www.finanzen.net/aktienkurse"


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        page = browser.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(3000)
        print(page.title())
        input("Browser bleibt offen. Enter drücken zum Schließen...")
        browser.close()


if __name__ == "__main__":
    main()
