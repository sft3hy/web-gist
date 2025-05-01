from bs4 import BeautifulSoup
import re
from collections import deque
import time
import csv
import random
from utils.scraping_utils import scrape_site, remove_paths_and_urls
from utils.llm_utils import ArticleInfo

USE_REP_LINKS = False


from config import (
    BEGIN_ROW,
    END_ROW,
    GEMINI_MODEL,
    CHAR_LIMIT,
    URL_MODEL,
)
from utils.llm_utils import (
    gemini_parse_web_content,
    groq_parse_url,
)
from utils.json_ld_finder import extract_ld_json_and_article


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


representative_urls = []

with open("txt_files/representative_links.txt", "r") as in_file:
    for url in in_file.read().split("\n"):
        representative_urls.append(url)
in_file.close()


urls = []
if USE_REP_LINKS:
    # use one article from each source
    urls = representative_urls

else:
    # use Links.txt as the in file (~3300 links)

    urls = []
    rows = open("txt_files/Links.txt", "r").read().split("\n")
    for row in rows:
        if row == "":
            urls.append("")
        else:
            urls.append(row)

    urls = urls[BEGIN_ROW:END_ROW]


naughty_links = open("txt_files/new_naughty_links.txt", "r").read().split("\n")
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
    tries = 3
    parsed_dict = groq_parse_url(url)
    while parsed_dict is None and tries > 0:
        parsed_dict = groq_parse_url(url)
        tries -= 1
    data = parsed_dict.to_dict()
    cleaned_data = {k: "" if v == "unknown" else v for k, v in data.items()}
    cleaned = ArticleInfo(**cleaned_data)
    llm = URL_MODEL
    writer.writerow(
        [
            url,
            cleaned.article_text,
            cleaned.title,
            cleaned.authors,
            cleaned.source,
            cleaned.published_date,
            cleaned.updated_date,
            llm,
        ]
    )
    return parsed_dict


def do_the_scraping(
    url_list: list,
    for_streamlit: bool = False,
) -> dict["articles" : list[ArticleInfo], "file_path":str]:
    filename_to_write = f"personal_batched_csvs/Parsed_links{BEGIN_ROW+1}-{END_ROW}.csv"
    if for_streamlit:
        filename_to_write = "user_facing_csvs/Enriched_URL_Data.csv"
    with open(filename_to_write, "w", newline="") as f:
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
        total_tokens = 0
        parsed_dicts = []
        for i, url in enumerate(url_list, 1):
            parsed_dict = ArticleInfo
            link_is_good = True
            # headers["User-Agent"] = random.choice(user_agents)
            print(f"[{i}/{len(url_list)}] Fetching: {url}")
            # Small delay to avoid getting blocked
            # time.sleep(random.randint(1, 2))

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
                        parsed_dict = call_groq(writer=writer, url=url)
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
                            "link",
                            "picture",
                            "source",
                            "img",
                        ]
                    ):
                        tag.decompose()

                    # Optionally keep only relevant top-level sections (e.g. <article>, <main>, etc.)
                    # You could also consider extracting just these elements instead of cleaning in-place
                    main_content = (
                        soup.find("article") or soup.find("main") or soup.body
                    )

                    # If found, keep only the main content; else fallback to the cleaned soup
                    if main_content:
                        cleaned_html = str(main_content)
                    else:
                        cleaned_html = str(soup)

                    # write output to a html files

                    # with open("sample.html", "w") as f:
                    #     f.write(str(cleaned_html))
                    pass_dict = {"URL": url}
                    if json_ld_try is not None:
                        pass_dict["json_ld"] = json_ld_try
                    pass_dict["raw_html"] = cleaned_html

                    token_est = len(str(pass_dict)) / 4
                    total_tokens += token_est

                    print("token estimate of pass_dict:", token_est)
                    parsed_dict = gemini_parse_web_content(str(pass_dict))
                    writer.writerow(
                        [
                            url,
                            remove_paths_and_urls(parsed_dict.article_text)[
                                :CHAR_LIMIT
                            ],
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
                print("writing url with no metadata row")
                writer.writerow(
                    [
                        url,
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                        "",
                    ]
                )
        parsed_dicts.append({"article_info": parsed_dict, "llm": llm, "url": url})
    print("total tokens:", total_tokens)
    print("average token count per article:", total_tokens / len(url_list))
    print(f"total estimated cost: ${round(((total_tokens/1000000) * 0.1), 2)}")

    return {"articles": parsed_dicts, "file_path": filename_to_write}


do_the_scraping(urls)
print("🎉 Done!")
