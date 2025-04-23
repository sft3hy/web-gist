from urllib.parse import urlparse
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
import os
from datetime import datetime
import time
import csv
from config import CHAR_LIMIT, BEGIN_ROW, END_ROW
from json_ld_finder import extract_ld_json_and_article
from utils.llm_utils import gemini_parse_html, groq_parse_dict


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


# === User-Agent headers ===
headers = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/135.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;"
        "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    ),
    "Accept-Encoding": "gzip, deflate, br",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.google.com/",
    "Connection": "keep-alive",
}
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
        ]
    )

    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}] Fetching: {url}")
        try:
            if url == "":
                print("writing blank row")
                writer.writerow(["", "", "", "", "", ""])
                continue
            response = requests.get(url, headers=headers, timeout=4)
            response.raise_for_status()

            json_ld_try = extract_ld_json_and_article(response.text)
            parsed_dict = groq_parse_dict(json_ld_try)
            if json_ld_try is None:
                html_string = BeautifulSoup(response.text, "html.parser")
                parsed_dict = gemini_parse_html(str(html_string))

            # print(parsed_dict)
            writer.writerow(
                [
                    url,
                    parsed_dict.article_text,
                    parsed_dict.title,
                    parsed_dict.authors,
                    parsed_dict.source,
                    parsed_dict.published_date,
                    parsed_dict.updated_date,
                ]
            )
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            print("writing url with blank row")
            writer.writerow([url, "", "", "", "", ""])

        # Small delay to avoid getting blocked
        time.sleep(0.5)

print("\n🎉 Done!")
