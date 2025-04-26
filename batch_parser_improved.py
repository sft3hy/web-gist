from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
import re
from collections import deque
import time
import csv
import random
from utils.scraping_utils import scrape_site

from config import (
    BEGIN_ROW,
    END_ROW,
    GEMINI_MODEL,
    VISIBLE_TEXT_MODEL,
    URL_MODEL,
)
from utils.llm_utils import (
    gemini_parse_web_content,
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


urls = representative_urls[BEGIN_ROW:END_ROW]

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

naughty_links = open("new_naughty_links.txt", "r").read().split("\n")
naughty_links = [link.strip() for link in naughty_links if link.strip()]


def get_naughty_links():
    just_base_urls = []
    for link in naughty_links:
        splitted = link.split("/")
        tmp_text = "/".join(splitted[:3])  # Join first 3 parts with slashes
        just_base_urls.append(tmp_text)

    return just_base_urls


final_naughty_links = get_naughty_links()


def call_groq(writer, url):
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


def strip_tags(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text)


def do_the_scraping():
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
        for i, url in enumerate(urls, 1):
            link_is_good = True
            # headers["User-Agent"] = random.choice(user_agents)
            print(f"[{i}/{len(urls)}] Fetching: {url}")
            # Small delay to avoid getting blocked
            time.sleep(random.randint(1, 4))

            try:
                if url == "":
                    print("writing blank row")
                    writer.writerow(["", "", "", "", "", ""])
                    continue
                # pre processed and found these links don't work - we don't need to try to scrape them
                # just pass to groq to infer info from URL
                for link in final_naughty_links:
                    if link in url:
                        print("link did not pass vibe check")
                        # call_groq(writer=writer, url=url)
                        link_is_good = False

                parsed_dict = {}
                llm = GEMINI_MODEL
                if link_is_good:
                    print("link passed the vibe check")
                    html = scrape_site(url)

                    soup = BeautifulSoup(html, "html.parser")

                    json_ld_try = extract_ld_json_and_article(soup)

                    # Remove noisy elements to reduce token count
                    for tag in soup(
                        [
                            "script",
                            "style",
                            "nav",
                            "footer",
                            "aside",
                            "noscript",
                            "iframe",
                        ]
                    ):
                        tag.decompose()

                    # Optionally keep only relevant top-level sections (e.g. <article>, <main>, etc.)
                    # You could also consider extracting just these elements instead of cleaning in-place
                    main_content = (
                        soup.find("article") or soup.find("main") or soup.body
                    )

                    # soup = strip_tags(str(soup))

                    # If found, keep only the main content; else fallback to the cleaned soup
                    if main_content:
                        print("found main_content")
                        cleaned_html = str(
                            main_content
                        )  # strip_tags(str(main_content))
                    else:
                        cleaned_html = str(soup)
                    with open("sample.html", "w") as f:
                        f.write(str(cleaned_html))
                    pass_dict = {"URL": url}
                    if json_ld_try is not None:
                        pass_dict["json_ld"] = json_ld_try
                    pass_dict["raw_html"] = cleaned_html

                    print("token estimate of pass_dict:", len(str(pass_dict)) / 4)
                    # parsed_dict = gemini_parse_web_content(str(pass_dict))
                    # writer.writerow(
                    #     [
                    #         url,
                    #         parsed_dict.article_text,
                    #         parsed_dict.title,
                    #         parsed_dict.authors,
                    #         parsed_dict.source,
                    #         parsed_dict.published_date,
                    #         parsed_dict.updated_date,
                    #         llm,
                    #     ]
                    # )
            except Exception as e:
                print(f"Error fetching {url}: {e}")
                # call_groq(writer=writer, url=url)


do_the_scraping()
print("\n🎉 Done!")
