from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import re
from collections import deque
from bs4.element import Comment
import urllib.request
import time
import csv
import random
from playwright.sync_api import sync_playwright

from config import (
    BEGIN_ROW,
    END_ROW,
    HTML_MODEL,
    VISIBLE_TEXT_MODEL,
    URL_MODEL,
)
from utils.llm_utils import (
    gemini_parse_web_content,
    groq_parse_dict,
    groq_parse_url,
    groq_parse_visible_text,
)
from json_ld_finder import extract_ld_json_and_article


gemma_requests = deque()
gemma_tokens = deque()

GEMMA_REQ_PER_MIN = 30
GEMMA_TOK_PER_MIN = 15000


# Token estimator (roughly 4 chars/token)
def estimate_tokens(text):
    return max(1, len(text) // 4)


# Deques to hold (timestamp, token count)
llama_requests = deque()
llama_tokens = deque()

gemma_requests = deque()
gemma_tokens = deque()


def throttle_model(requests_deque, tokens_deque, max_req, max_tok, new_tok):
    now = time.time()

    # Purge requests older than 60 seconds
    while requests_deque and now - requests_deque[0] > 60:
        requests_deque.popleft()
    while tokens_deque and now - tokens_deque[0][0] > 60:
        tokens_deque.popleft()

    # Wait if we exceed limits
    while (
        len(requests_deque) >= max_req
        or sum(tok for _, tok in tokens_deque) + new_tok > max_tok
    ):
        print("sleeping while groq models cool down...")
        time.sleep(1)
        now = time.time()
        while requests_deque and now - requests_deque[0] > 60:
            requests_deque.popleft()
        while tokens_deque and now - tokens_deque[0][0] > 60:
            tokens_deque.popleft()

    requests_deque.append(now)
    tokens_deque.append((now, new_tok))


# Step 1: Read all full URLs from the file
with open("Links.txt", "r") as file:
    raw_links = [line.strip() for line in file if line.strip()][1:]

# Step 2: Map base domains to a representative full URL
domain_to_url = {}

for url in raw_links:
    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}"

    # Only keep the first full URL we see for each domain
    if base_url not in domain_to_url:
        domain_to_url[base_url] = url

# Step 3: Extract the list of unique full URLs (one per base domain)
representative_urls = list(domain_to_url.values())

# Optional: Save to a new file so you can inspect them
with open("representative_links.txt", "w") as out_file:
    for url in representative_urls:
        out_file.write(url + "\n")

print(f"Extracted {len(representative_urls)} unique full URLs.")


urls = representative_urls

# urls = []
# rows = open("Links.txt", "r").read().split("\n")[1:]
# for row in rows:
#     if row == "":
#         urls.append("")
#     elif re.match(
#         r"http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+",
#         row,
#     ):
#         urls.append(row)

# urls = urls[BEGIN_ROW:END_ROW]

# === User-Agent headers ===

user_agents = [
    # Windows - Chrome
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36",
    # Windows - Firefox
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    # Windows - Edge
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.6312.86 Safari/537.36 Edg/123.0.2420.65",
    # macOS - Chrome
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.129 Safari/537.36",
    # macOS - Safari
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    # macOS - Firefox
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:124.0) Gecko/20100101 Firefox/124.0",
    # iOS - Safari (iPhone)
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    # Android - Chrome (Pixel)
    "Mozilla/5.0 (Linux; Android 14; Pixel 8 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.129 Mobile Safari/537.36",
    # Android - Samsung Browser
    "Mozilla/5.0 (Linux; Android 14; SAMSUNG SM-G991U) AppleWebKit/537.36 (KHTML, like Gecko) SamsungBrowser/25.0 Chrome/122.0.6261.129 Mobile Safari/537.36",
    # Linux - Firefox
    "Mozilla/5.0 (X11; Linux x86_64; rv:124.0) Gecko/20100101 Firefox/124.0",
]

headers = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/135.0.0.0 Safari/537.36",
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
    "Referer": "https://www.google.com/",
}


def tag_visible(element):
    if element.parent.name in [
        "style",
        "script",
        "head",
        "title",
        "meta",
        "[document]",
    ]:
        return False
    if isinstance(element, Comment):
        return False
    return True


def text_from_html(body):
    soup = BeautifulSoup(body, "html.parser")
    texts = soup.find_all(string=True)
    visible_texts = filter(tag_visible, texts)
    raw_text = " ".join(t.strip() for t in visible_texts)
    clean_text = re.sub(
        r"\s+", " ", raw_text
    )  # Replace all whitespace (tabs, newlines, etc.) with a single space
    return clean_text.strip()


count = 1
with open(f"Parsed_links{BEGIN_ROW}-{END_ROW}.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(
        [
            "URL",
            "article_text",
            "title",
            "author",
            "source",
            "published_date",
            "updated_date",
            "LLM",
        ]
    )
    all_text = ""
    for i, url in enumerate(urls, 1):
        # headers["User-Agent"] = random.choice(user_agents)
        print(f"[{i}/{len(urls)}] Fetching: {url}")
        # Small delay to avoid getting blocked
        time.sleep(random.randint(2, 4))
        try:
            if url == "":
                print("writing blank row")
                writer.writerow(["", "", "", "", "", ""])
                continue
            session = requests.Session()
            session.headers.update(headers)
            response = session.get(url, timeout=8)
            response.raise_for_status()

            json_ld_try = extract_ld_json_and_article(response.text)

            gemma_tok = estimate_tokens(str(json_ld_try))

            parsed_dict = {}
            llm = ""

            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                page = browser.new_page()
                page.set_default_timeout(8000)  # timeout in milliseconds (10 seconds)
                page.goto(url)
                html = page.content()
                browser.close()
            # html = urllib.request.urlopen(url)
            soup = BeautifulSoup(html, "html.parser")

            # Remove noisy elements to reduce token count
            for tag in soup(
                ["script", "style", "nav", "footer", "aside", "noscript", "iframe"]
            ):
                tag.decompose()

            # Optionally keep only relevant top-level sections (e.g. <article>, <main>, etc.)
            # You could also consider extracting just these elements instead of cleaning in-place
            main_content = soup.find("article") or soup.find("main") or soup.body

            # If found, keep only the main content; else fallback to the cleaned soup
            if main_content:
                cleaned_html = str(main_content)
            else:
                cleaned_html = str(soup)

            pass_dict = {"URL": url}
            if json_ld_try is not None:
                pass_dict["json_ld"] = json_ld_try
            pass_dict["raw_html"] = cleaned_html
            llm = HTML_MODEL
            parsed_dict = gemini_parse_web_content(str(pass_dict))
            # print(pass_dict)
            writer.writerow(
                [
                    url,
                    parsed_dict.article_text,
                    parsed_dict.title,
                    parsed_dict.authors,
                    parsed_dict.source,
                    parsed_dict.published_date,
                    parsed_dict.updated_date,
                    llm,
                ]
            )
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            parsed_dict = groq_parse_url(url)
            llm = URL_MODEL
            writer.writerow(
                [
                    url,
                    parsed_dict.article_text,
                    parsed_dict.title,
                    parsed_dict.authors,
                    parsed_dict.source,
                    parsed_dict.published_date,
                    parsed_dict.updated_date,
                    llm,
                ]
            )


print("\n🎉 Done!")
