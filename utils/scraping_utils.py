# utils/scraping_utils.py
import random
import time
import logging
from playwright.sync_api import (
    sync_playwright,
    Route,
    Playwright,
    BrowserContext,
    Page,
    Response,
)

# --- Constants ---
USER_AGENTS = [
    # "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    # "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/113.0.5672.127 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
]

EXTRA_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "DNT": "1",
    "Upgrade-Insecure-Requests": "1",
}


# --- Asset Blocker ---
def block_unnecessary_assets(route: Route):
    """Blocks non-essential resources to speed up page loads."""
    if route.request.resource_type in (
        "image",
        "stylesheet",
        "font",
        "media",
        "script",
    ):
        # Allow scripts for now as some sites need them to render content
        if route.request.resource_type != "script":
            return route.abort()
    return route.continue_()


# --- Main Scraping Function ---
def scrape_site(url: str, max_retries: int = 2) -> bytes:
    """
    Scrapes a website using Playwright with stealth settings and returns the raw HTML content as bytes.

    Args:
        url: The URL to scrape.
        max_retries: The maximum number of times to retry on failure.

    Returns:
        The raw HTML content as bytes.

    Raises:
        RuntimeError: If scraping fails after all retries.
    """
    for attempt in range(max_retries):
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                context = browser.new_context(
                    user_agent=random.choice(USER_AGENTS),
                    viewport=random.choice(VIEWPORTS),
                    extra_http_headers=EXTRA_HEADERS,
                    locale="en-US",
                )
                page = context.new_page()
                page.set_default_timeout(20000)  # 20 seconds

                # Block assets for speed, but scripts may be needed for some sites
                # page.route("**/*", block_unnecessary_assets)

                response = page.goto(url, wait_until="domcontentloaded")

                if not response or not response.ok:
                    raise IOError(
                        f"Bad status code {response.status if response else 'N/A'}"
                    )

                # Wait for the body to ensure content is loaded
                page.wait_for_selector("body")

                # CRITICAL: Return raw bytes to let BeautifulSoup handle encoding
                html_bytes = response.body()

                browser.close()
                return html_bytes

        except Exception as e:
            logging.warning(
                f"[Attempt {attempt + 1}/{max_retries}] Failed to scrape {url}: {e}"
            )
            if attempt < max_retries - 1:
                time.sleep(1 + random.random())  # Simple backoff
            else:
                raise RuntimeError(
                    f"Failed to scrape {url} after {max_retries} attempts"
                ) from e


# --- Text Cleaning Utilities ---


def fix_mojibake(text: str) -> str:
    """
    Attempts to fix common mojibake issues where UTF-8 text was
    incorrectly decoded as a single-byte encoding like latin-1.
    """
    if not isinstance(text, str):
        return text
    try:
        # Re-encode the wrongly-decoded string into bytes and then decode correctly.
        return (
            text.encode("windows-1252")
            .decode("utf-8")
            .encode("latin-1")
            .decode("utf-8")
        )
    except (UnicodeEncodeError, UnicodeDecodeError):
        # If it fails, the string was likely not mojibake, so return it as-is.
        return text
