import random
import time
from playwright.sync_api import sync_playwright, Route
from playwright_stealth import stealth_sync
import re

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_5) AppleWebKit/605.1.15"
    " (KHTML, like Gecko) Version/16.5 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    " (KHTML, like Gecko) Chrome/113.0.5672.127 Safari/537.36",
]

VIEWPORTS = [
    {"width": 1920, "height": 1080},
    {"width": 1366, "height": 768},
    {"width": 1440, "height": 900},
]

EXTRA_HEADERS = {
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}


def remove_paths_and_urls(html_string: str) -> str:
    """
    Uses regex to remove '<div', '<span', URLs, and common file path patterns
    (case-insensitive for tags).

    WARNING: This is a brittle approach using regex directly on HTML. It will
             likely result in invalid/broken HTML structure and may remove
             unintended text that resembles a URL or path. Use with caution.

    Args:
        html_string: The HTML content as a string.

    Returns:
        The modified string.
    """
    # 1. Pattern for URLs/URIs (common web protocols, protocol-relative, www.)
    # Designed to match typical structures found in attributes like href or src.
    url_patterns = r"""
        (?:https?|ftp|file):\/\/[\-A-Z0-9+&@#\/%?=~_|!:,.;]*[\-A-Z0-9+&@#\/%=~_|]  # http, https, ftp, file
        |
        \/\/[^\s<>"']+  # Protocol-relative //...
        |
        (?<!\w)www\.[^\s<>"']+ # www. links (negative lookbehind to avoid matching things like 'abcwww.')
    """

    # 2. Pattern for common file paths (Unix/Windows style, relative/absolute)
    # Matches starting patterns like /, ./, ../, C:\ followed by typical path characters.
    path_patterns = r"""
        (?:[a-zA-Z]:\\|\.\.?[\\\/]|\/)[a-zA-Z0-9\/\\._-]+ # Drive paths, relative paths, absolute paths
    """

    # Combine patterns with OR (|). Order: URLs, Paths, Tags. Use verbose regex for readability.
    combined_pattern = re.compile(
        f"({url_patterns})|({path_patterns})",
        re.IGNORECASE | re.VERBOSE,
    )

    # Perform the substitution, replacing any match with an empty string
    cleaned_html = combined_pattern.sub("", html_string)

    return cleaned_html


def scrape_site(url, proxies=None, max_retries=3):
    proxies = proxies.copy() if proxies else []
    for attempt in range(1, max_retries + 1):
        proxy = random.choice(proxies) if proxies else None

        try:
            with sync_playwright() as p:
                ua = random.choice(USER_AGENTS)
                vp = random.choice(VIEWPORTS)

                browser = p.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"],
                )
                ctx_args = {
                    "user_agent": ua,
                    "viewport": vp,
                    "locale": "en-US",
                    "timezone_id": "America/Los_Angeles",
                    "extra_http_headers": EXTRA_HEADERS,
                }
                if proxy:
                    ctx_args["proxy"] = proxy

                context = browser.new_context(**ctx_args)
                stealth_sync(context)

                page = context.new_page()
                page.set_default_timeout(10000)  # 10s

                # Block non-HTML assets for speed and minimal fingerprint
                def _block_assets(route: Route):
                    if route.request.resource_type in (
                        "image",
                        "stylesheet",
                        "font",
                        "media",
                    ):
                        return route.abort()
                    return route.continue_()

                page.route("**/*", _block_assets)

                # Faster load event: DOMContentLoaded
                response = page.goto(url)  # , wait_until="domcontentloaded")
                if not response or response.status != 200:
                    raise Exception(
                        f"Bad status: {response.status if response else 'no response'}"
                    )

                html = page.content()
                browser.close()
                return html

        except Exception as e:
            msg = str(e)
            print(f"[Attempt {attempt}/{max_retries}] {msg}")

            # drop unusable proxy
            if proxy and "ERR_PROXY_CONNECTION_FAILED" in msg:
                print(f"Dropping bad proxy: {proxy['server']}")
                proxies.remove(proxy)

            time.sleep(2**attempt * 0.5 + random.random())

    raise RuntimeError(f"Failed to scrape {url} after {max_retries} attempts")
