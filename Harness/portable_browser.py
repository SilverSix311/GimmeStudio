"""Open the studio with its bundled browser and project-local user data."""
import os
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
os.environ['PLAYWRIGHT_BROWSERS_PATH'] = str(ROOT / 'Tools/browsers')
from playwright.sync_api import sync_playwright
with sync_playwright() as playwright:
    browser = playwright.chromium.launch_persistent_context(str(ROOT / 'User/gimmestudio-browser'),
                headless=False, no_viewport=True, downloads_path=str(ROOT / 'Downloads/browser'),
                accept_downloads=True, args=['--start-maximized', '--disable-breakpad', '--disable-crash-reporter'])
    page = browser.pages[0] if browser.pages else browser.new_page()
    page.goto('http://127.0.0.1:8190')
    while browser.pages:
        try:
            browser.pages[0].wait_for_timeout(1000)
        except Exception:
            break
