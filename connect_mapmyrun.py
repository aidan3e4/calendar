from enum import Enum

from dotenv import load_dotenv
import json
import os
import requests

from playwright.async_api import async_playwright
from playwright_stealth import Stealth


class DistanceUnit(Enum):
    KM = "km"
    M = "m"


load_dotenv()

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
USER_ARGS = [  # Helps evade some detection
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-infobars",
    "--window-size=1280,800",
    "--disable-dev-shm-usage",
]


async def get_distance(
    start_date,
    end_date,
    unit: DistanceUnit = DistanceUnit.KM,
    run_headless: bool = True,
):

    total_meters = 0

    async with Stealth().use_async(async_playwright()) as p:
        browser = await p.chromium.launch(headless=run_headless, args=USER_ARGS)

        context = await browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            locale="en-US",
            timezone_id="Europe/Zurich",
            bypass_csp=True,  # Sometimes helps
            java_script_enabled=True,
            ignore_https_errors=True,
            geolocation={"latitude": 46.2044, "longitude": 6.1432},  # Geneva approx
            permissions=["geolocation"],
        )

        page = await context.new_page()

        # Add this before goto to mimic real user more
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        await page.goto(
            "https://www.mapmyrun.com/auth/login/",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        # Mimick human behaviour to avoid detection
        await page.mouse.move(200, 300)
        await page.mouse.down()
        await page.mouse.up()
        await page.evaluate("window.scrollBy(0, 300)")

        # Fill the email field
        await page.wait_for_selector("#email-input", state="visible", timeout=20000)
        email_locator = page.locator("#email-input")
        # Click/focus to activate (MUI often needs this)
        await email_locator.click(
            force=True
        )  # force=True bypasses some visibility/actionability checks
        await email_locator.press_sequentially(
            os.environ["MAP_MY_RUN_EMAIL"], delay=80
        )  # slower delay for realism
        # Force dispatch change/input events (critical for controlled React inputs)
        await page.evaluate("""
            const el = document.querySelector('#email-input');
            if (el) {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
                el.dispatchEvent(new Event('blur', { bubbles: true }));
            }
        """)

        # Now password – use similar pattern
        password_locator = page.locator("#Password-input")
        await password_locator.click(force=True)
        await password_locator.press_sequentially(
            os.environ["MAP_MY_RUN_PASSWORD"], delay=80
        )
        await page.evaluate("""
            const el = document.querySelector('#password-input');
            if (el) {
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }
        """)

        # Submit – use text-based for reliability (from your snippet: "LOG IN")
        await page.get_by_role(
            "button", name="LOG IN"
        ).click()  # exact text match, case-sensitive
        await page.wait_for_timeout(5000)  # buffer for cookies
        cookies = await context.cookies()
        auth_token = next(
            (c["value"] for c in cookies if c["name"] == "auth-token"), None
        )

        if auth_token:
            # Use in requests
            session = requests.Session()
            for c in cookies:
                session.cookies.set(c["name"], c["value"], domain=c["domain"])

            # Call API
            params = {
                "user": os.environ["MAP_MY_RUN_USER_ID"],
                "started_after": start_date,
                "started_before": end_date,
                "limit": 1000,
            }
            resp = session.get(
                "https://www.mapmyrun.com/internal/allWorkouts/", params=params
            )

            total_meters = 0
            for run in json.loads(resp.text):
                total_meters += run["aggregates"]["distance_total"]

    if unit == DistanceUnit.KM:
        total = total_meters / 1000
    elif unit == DistanceUnit.M:
        total = total_meters

    return total


start_date = "2026-01-01T00:00:00.000Z"
