"""Exercise a running clean dashboard using the bundled browser (CI/manual)."""
import json
import urllib.request
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
errors = []
with urllib.request.urlopen('http://127.0.0.1:8190/api/studio') as response:
    assert json.load(response)['mode'] == 'local'
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = browser.new_page()
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8190')
    page.locator('#project option').first.wait_for(state='attached')
    for route, title in [('characters', 'Character workshop'), ('ai', 'AI Director'), ('sets3d', '3D set workshop'), ('help', 'Help & tutorials')]:
        page.goto('http://127.0.0.1:8190/#' + route)
        page.locator('#title').filter(has_text=title).wait_for()
        page.wait_for_timeout(500)
    page.screenshot(path=str(ROOT / 'Logs/portable-smoke.png'))
    browser.close()
assert not errors, errors
print('Portable dashboard/browser smoke passed')
