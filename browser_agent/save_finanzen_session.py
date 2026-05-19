"""Open finanzen.net and save the manual browser login session."""

from __future__ import annotations

from pathlib import Path

from playwright.sync_api import sync_playwright


TARGET_URL = "https://www.finanzen.net"
SESSION_PATH = (
    Path(__file__).resolve().parent
    / "login_sessions"
    / "finanzen_net_state.json"
)


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        context = browser.new_context()
        page = context.new_page()
        page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=30000)
        input("Nach manuellem Login Enter drücken, um die Session zu speichern...")

        SESSION_PATH.parent.mkdir(parents=True, exist_ok=True)
        context.storage_state(path=str(SESSION_PATH))
        browser.close()


if __name__ == "__main__":
    main()
